"""A camada que todo pedido atravessa: sessão, porta de entrada, token CSRF e cabeçalhos.

Ela vale para o site inteiro e nega por padrão. Uma tela nova já nasce atrás da senha, sem ninguém
lembrar de proteger, e a lista de páginas abertas é a de `PUBLICAS`, curta de propósito.
"""

from __future__ import annotations

import hmac
from urllib.parse import parse_qs, urlencode

from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse, PlainTextResponse, RedirectResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.seguranca import sessao as _sessao
from app.seguranca.cabecalhos import CABECALHOS
from app.seguranca.sessao import Assinador, Sessao

PUBLICAS = frozenset({"/", "/entrar", "/saude"})
PREFIXO_ESTATICO = "/static/"
# A área de administração nega por padrão aqui, no caminho, e não rota por rota.
# Uma tela nova de administração já nasce fechada ao cliente mesmo se quem a
# escreveu esquecer a dependência `exigir_admin`.
PREFIXO_ADMINISTRACAO = "/admin"
METODOS_SEM_EFEITO = frozenset({"GET", "HEAD", "OPTIONS"})
# Os formulários do site têm poucas linhas, e um corpo gigante é jeito baixo de
# encher a memória do serviço. O limite é por caminho porque UM formulário é
# legitimamente grande: o de importar avaliações.
#
# O número saiu de uma medida, não de um palpite: um primeiro arquivo de 15 meses
# de um negócio pequeno tem ~450 avaliações, que depois de codificado passa de
# 64 KiB. Com o limite único, a importação era **recusada em silêncio** — o
# navegador recebia 413 e o operador via a tela voltar sem recado. Aconteceu no
# primeiro teste em produção.
TAMANHO_MAXIMO_DO_FORMULARIO = 64 * 1024
TAMANHO_MAXIMO_DA_IMPORTACAO = 2 * 1024 * 1024
CAMINHOS_DE_IMPORTACAO = frozenset({"/admin/importar"})


def _publica(caminho: str) -> bool:
    return caminho in PUBLICAS or caminho.startswith(PREFIXO_ESTATICO)


def _da_administracao(caminho: str) -> bool:
    return caminho == PREFIXO_ADMINISTRACAO or caminho.startswith(PREFIXO_ADMINISTRACAO + "/")


class Defesa:
    def __init__(self, app: ASGIApp, *, assinador: Assinador):
        self.app = app
        self._assinador = assinador

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        cookie = _cookie_da_requisicao(scope)
        _sessao.guardar(scope, (cookie and self._assinador.abrir(cookie)) or Sessao.anonima())
        seguro = scope.get("scheme") == "https"
        iniciou = False

        async def enviar(mensagem: Message) -> None:
            nonlocal iniciou
            if mensagem["type"] == "http.response.start":
                iniciou = True
                cabecalhos = MutableHeaders(scope=mensagem)
                for nome, valor in CABECALHOS.items():
                    cabecalhos[nome] = valor
                atual = scope["state"]["sessao"]
                pagina = cabecalhos.get("content-type", "").startswith("text/html")
                if atual.alterada or (atual.nova and pagina):
                    cookie = _sessao.cabecalho_set_cookie(atual, self._assinador, seguro)
                    cabecalhos.append("set-cookie", cookie)
            await send(mensagem)

        try:
            resposta, receber = await self._decidir(scope, receive)
            if resposta is not None:
                await resposta(scope, receive, enviar)
            else:
                await self.app(scope, receber, enviar)
        except Exception:
            if not iniciou:
                await PlainTextResponse("Erro interno do servidor.", status_code=500)(scope, receive, enviar)
            raise

    async def _decidir(self, scope: Scope, receive: Receive) -> tuple[Response | None, Receive]:
        """Devolve a resposta que barra o pedido, ou None para deixá-lo seguir (com o corpo no lugar)."""
        atual: Sessao = scope["state"]["sessao"]
        caminho = scope["path"]

        if atual.usuario is None and not _publica(caminho):
            return _para_a_entrada(scope), receive

        if _da_administracao(caminho) and atual.papel != "admin":
            return JSONResponse({"erro": "Essa área é da equipe do Radar."}, status_code=403), receive

        if scope["method"] not in METODOS_SEM_EFEITO:
            corpo = None
            formulario: dict[str, list[str]] = {}
            if _e_formulario(scope):
                corpo = await _ler_formulario(receive, _limite_do_caminho(caminho))
                if corpo is None:
                    return JSONResponse({
                        "erro": "Formulário grande demais.",
                        "limite_em_kib": _limite_do_caminho(caminho) // 1024,
                    }, status_code=413), receive
                formulario = parse_qs(corpo.decode("utf-8", "replace"), keep_blank_values=True)
            enviado = _cabecalho(scope, b"x-csrf-token") or (formulario.get("csrf") or [""])[0]
            if not hmac.compare_digest(atual.csrf.encode(), enviado.encode()):
                if caminho == "/entrar":
                    return RedirectResponse("/entrar?erro=sessao", status_code=303), receive
                return JSONResponse({"erro": "Token de segurança inválido."}, status_code=403), receive
            scope["state"]["formulario"] = formulario     # a trava de empresa lê daqui, depois do roteador
            if corpo is not None:
                receive = _devolver_corpo(corpo, receive)
        return None, receive


def _cookie_da_requisicao(scope: Scope) -> str | None:
    return HTTPConnection(scope).cookies.get(_sessao.NOME_DO_COOKIE)


def _cabecalho(scope: Scope, nome: bytes) -> str:
    for chave, valor in scope["headers"]:
        if chave == nome:
            return valor.decode("latin-1")
    return ""


def _para_a_entrada(scope: Scope) -> Response:
    if scope["method"] not in ("GET", "HEAD"):
        return RedirectResponse("/entrar", status_code=303)
    pedido = scope["path"] + (f"?{scope['query_string'].decode('latin-1')}" if scope["query_string"] else "")
    return RedirectResponse(f"/entrar?{urlencode({'proximo': pedido})}", status_code=303)


# Só urlencoded: formulário multipart (envio de arquivo) precisa mandar o token
# no cabeçalho X-CSRF-Token, porque o corpo não é lido aqui. Hoje não existe
# nenhum no projeto; o primeiro vai levar 403 se ignorar esta nota.
def _e_formulario(scope: Scope) -> bool:
    """Só o formulário comum é lido aqui. JSON e arquivo passam com o token no cabeçalho, de corpo intacto."""
    return _cabecalho(scope, b"content-type").strip().lower().startswith("application/x-www-form-urlencoded")


def _limite_do_caminho(caminho: str) -> int:
    return (TAMANHO_MAXIMO_DA_IMPORTACAO if caminho in CAMINHOS_DE_IMPORTACAO
            else TAMANHO_MAXIMO_DO_FORMULARIO)


async def _ler_formulario(receive: Receive,
                          limite: int = TAMANHO_MAXIMO_DO_FORMULARIO) -> bytes | None:
    """O corpo inteiro, ou None se passar do limite."""
    pedacos: list[bytes] = []
    total = 0
    while True:
        mensagem = await receive()
        if mensagem["type"] != "http.request":      # o cliente desistiu
            return b""
        pedacos.append(mensagem.get("body", b""))
        total += len(pedacos[-1])
        if total > limite:
            return None
        if not mensagem.get("more_body", False):
            return b"".join(pedacos)


def _devolver_corpo(corpo: bytes, receive: Receive) -> Receive:
    """A conferência consumiu o corpo; a rota precisa recebê-lo de novo, e depois seguir ouvindo o cliente."""
    entregue = False

    async def receber() -> Message:
        nonlocal entregue
        if not entregue:
            entregue = True
            return {"type": "http.request", "body": corpo, "more_body": False}
        return await receive()

    return receber
