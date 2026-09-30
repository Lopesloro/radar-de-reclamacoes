"""Rotas do Radar de Reclamações.

A home é pública e apresenta o projeto. Tudo que mostra dado de parceiro fica
atrás de login: painel, ficha do comércio, previsão, alertas, etapas e acurácia.
Tudo é renderizado no servidor, o conteúdo nasce no HTML e o JavaScript só
troca estado depois.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app import demo, formatos, seguranca
from app.conteudo import (
    DISPENSADO, ENTREGAS, ETAPAS_PROJETO, IA_NO_SISTEMA, INTEGRANTES,
    LIMITES_DA_IA, MENU, MENU_PUBLICO, MODELOS, MOVIMENTOS, PROJETO, ROBUSTEZ,
    TECNOLOGIAS, VERSAO,
)
from app.graficos import svg

RAIZ = Path(__file__).resolve().parent
ACOES_ALERTA = {"confirmar", "descartar", "reabrir"}


def _impressao_dos_estaticos() -> str:
    """Identificador que muda quando o CSS ou o JavaScript mudam.

    Sem isso o endereço do arquivo fica igual entre versões, o navegador serve
    o que tem em cache e a tela nova aparece com o estilo velho. Já aconteceu.
    """
    marcas = sorted(
        f"{caminho.name}:{caminho.stat().st_mtime_ns}"
        for caminho in (RAIZ / "static").rglob("*")
        if caminho.is_file()
    )
    return hashlib.sha256("|".join(marcas).encode()).hexdigest()[:12]


IMPRESSAO = _impressao_dos_estaticos()

app = FastAPI(title=PROJETO["nome"], version=VERSAO, docs_url=None, redoc_url=None)
app.add_middleware(
    SessionMiddleware,
    secret_key=seguranca.CHAVE_SESSAO,
    session_cookie="radar_sessao",
    https_only=False,      # o Render encerra o TLS antes da aplicação
    same_site="lax",
    max_age=8 * 60 * 60,
)
app.mount("/static", StaticFiles(directory=RAIZ / "static"), name="static")

paginas = Jinja2Templates(directory=str(RAIZ / "templates"))
paginas.env.filters.update(
    inteiro=formatos.inteiro,
    decimal=formatos.decimal,
    pct=formatos.pct,
    contagem=formatos.contagem,
    data_curta=formatos.data_curta,
    data_longa=formatos.data_longa,
    mes_longo=formatos.mes_longo,
    mes_curto=svg.mes_curto,
)
paginas.env.globals.update(
    projeto=PROJETO,
    integrantes=INTEGRANTES,
    menu=MENU,
    menu_publico=MENU_PUBLICO,
    versao=VERSAO,
    impressao=IMPRESSAO,
    hoje=demo.HOJE,
)


@app.middleware("http")
async def cabecalhos_de_defesa(request: Request, chamar):
    resposta: Response = await chamar(request)
    for chave, valor in seguranca.CABECALHOS.items():
        resposta.headers.setdefault(chave, valor)
    if request.url.scheme == "https":
        resposta.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return resposta


def _logado(request: Request) -> bool:
    return bool(request.session.get("usuario"))


def _pagina(request: Request, nome: str, ativo: str, **contexto) -> HTMLResponse:
    return paginas.TemplateResponse(request, nome, {
        "ativo": ativo,
        "logado": _logado(request),
        "usuario": request.session.get("usuario"),
        "csrf": seguranca.token_csrf(request.session),
        **contexto,
    })


def _exige_login(request: Request) -> RedirectResponse | None:
    if _logado(request):
        return None
    destino = request.url.path
    if request.url.query:
        destino = f"{destino}?{request.url.query}"
    return RedirectResponse(f"/entrar?proximo={destino}", status_code=303)


def _origem(request: Request) -> str:
    return request.client.host if request.client else "desconhecida"


# ---------------------------------------------------------------- público

@app.get("/", response_class=HTMLResponse)
def projeto(request: Request):
    return _pagina(
        request, "projeto.html", "projeto",
        entregas=ENTREGAS,
        movimentos=MOVIMENTOS,
        dispensado=DISPENSADO,
        modelos=MODELOS,
        total_parceiros=len(demo.comercios()),
    )


@app.get("/entrar", response_class=HTMLResponse)
def tela_entrar(request: Request, proximo: str = "/painel", erro: str | None = None):
    if _logado(request):
        return RedirectResponse(proximo, status_code=303)
    return _pagina(
        request, "entrar.html", "entrar",
        proximo=proximo,
        erro=erro,
        senha_demo=seguranca.SENHA_E_DEMONSTRACAO,
        usuario_demo=seguranca.USUARIO,
    )


@app.post("/entrar")
def fazer_login(
    request: Request,
    usuario: str = Form(""),
    senha: str = Form(""),
    proximo: str = Form("/painel"),
    csrf: str = Form(""),
):
    destino = proximo if proximo.startswith("/") else "/painel"
    if not seguranca.csrf_confere(request.session, csrf):
        return RedirectResponse("/entrar?erro=sessao", status_code=303)

    origem = _origem(request)
    if not seguranca.pode_tentar(origem):
        return RedirectResponse(f"/entrar?erro=bloqueado&proximo={destino}", status_code=303)

    if not seguranca.senha_confere(usuario, senha):
        seguranca.registrar_tentativa(origem)
        return RedirectResponse(f"/entrar?erro=credencial&proximo={destino}", status_code=303)

    seguranca.limpar_tentativas(origem)
    request.session.clear()
    request.session["usuario"] = usuario.strip().lower()
    seguranca.token_csrf(request.session)
    return RedirectResponse(destino, status_code=303)


@app.post("/sair")
def fazer_logout(request: Request, csrf: str = Form("")):
    if seguranca.csrf_confere(request.session, csrf):
        request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.get("/saude")
def saude():
    return JSONResponse({
        "estado": "ok",
        "versao": VERSAO,
        "dados": "demonstração",
        "comercios": len(demo.comercios()),
        "alertas_abertos": sum(1 for a in demo.alertas() if a.estado == "aberto"),
        "senha_de_demonstracao": seguranca.SENHA_E_DEMONSTRACAO,
    })


# ---------------------------------------------------------------- protegido

@app.get("/painel", response_class=HTMLResponse)
def painel(request: Request):
    if (desvio := _exige_login(request)) is not None:
        return desvio
    comercios = demo.comercios()
    linhas = [{
        "comercio": c,
        "prontidao": demo.prontidao(c),
        "grafico": svg.sparkline(
            [v for _, v in c.dominante.pontos],
            f"Tendência de {c.dominante.categoria} em {c.nome}",
        ),
    } for c in comercios]
    abertos = [a for a in demo.alertas() if a.estado == "aberto"]
    return _pagina(
        request, "painel.html", "painel",
        linhas=linhas,
        mes=comercios[0].pontos_fechados[-1][0],
        abertos=abertos,
        criticos=[a for a in abertos if a.gravidade == "critico"],
        total_avaliacoes=sum(c.total_avaliacoes for c in comercios),
        total_reclamacoes=sum(c.total_reclamacoes for c in comercios),
        etapas_pendentes=sum(7 - demo.prontidao(c) for c in comercios),
    )


@app.get("/comercio/{identificador}", response_class=HTMLResponse)
def comercio(request: Request, identificador: str):
    if (desvio := _exige_login(request)) is not None:
        return desvio
    alvo = demo.comercio(identificador)
    if alvo is None:
        return _nao_encontrado(request)
    ordenadas = sorted(alvo.series, key=lambda s: s.ultimo, reverse=True)
    return _pagina(
        request, "comercio.html", "painel",
        comercio=alvo,
        comercios=demo.comercios(),
        ordenadas=ordenadas,
        mes=alvo.pontos_fechados[-1][0],
        grafico_categorias=svg.barras_categorias(
            [(s.categoria, s.ultimo, s.variacao) for s in ordenadas],
            f"Reclamações por categoria em {alvo.nome}",
        ),
        grafico_variacao=svg.variacao(
            [(s.categoria, s.variacao) for s in ordenadas],
            f"Variação por categoria em {alvo.nome}",
        ),
        avaliacoes=alvo.avaliacoes[:12],
        limite=demo.LIMITE_CONFIANCA,
        prontidao=demo.prontidao(alvo),
    )


@app.get("/previsao", response_class=HTMLResponse)
def previsao_inicial(request: Request):
    if (desvio := _exige_login(request)) is not None:
        return desvio
    return RedirectResponse(f"/previsao/{demo.comercios()[0].id}", status_code=307)


@app.get("/previsao/{identificador}", response_class=HTMLResponse)
def previsao(request: Request, identificador: str, categoria: str | None = None):
    if (desvio := _exige_login(request)) is not None:
        return desvio
    alvo = demo.comercio(identificador)
    if alvo is None:
        return _nao_encontrado(request)
    escolhida = categoria if categoria in demo.CATEGORIAS else alvo.em_alta.categoria
    serie = alvo.serie(escolhida)
    return _pagina(
        request, "previsao.html", "previsao",
        comercio=alvo,
        comercios=demo.comercios(),
        serie=serie,
        categorias=demo.CATEGORIAS,
        escolhida=escolhida,
        grafico=svg.leque(serie, f"Previsão de {escolhida} em {alvo.nome}"),
        horizonte=demo.HORIZONTE,
    )


@app.get("/alertas", response_class=HTMLResponse)
def alertas(request: Request):
    if (desvio := _exige_login(request)) is not None:
        return desvio
    lista = demo.alertas()
    return _pagina(
        request, "alertas.html", "alertas",
        alertas=lista,
        abertos=[a for a in lista if a.estado == "aberto"],
        fechados=[a for a in lista if a.estado != "aberto"],
    )


@app.post("/alertas/{alerta_id}")
def mudar_alerta(request: Request, alerta_id: str, acao: str = Form(...), csrf: str = Form("")):
    if (desvio := _exige_login(request)) is not None:
        return desvio
    if seguranca.csrf_confere(request.session, csrf) and acao in ACOES_ALERTA:
        demo.mudar_estado(alerta_id, acao)
    return RedirectResponse("/alertas", status_code=303)


@app.get("/etapas", response_class=HTMLResponse)
def etapas(request: Request):
    if (desvio := _exige_login(request)) is not None:
        return desvio
    comercios = demo.comercios()
    return _pagina(
        request, "etapas.html", "etapas",
        etapas_projeto=ETAPAS_PROJETO,
        fases=("Entregue", "Próxima", "Depois"),
        por_comercio=[{
            "comercio": c,
            "etapas": demo.etapas(c),
            "prontidao": demo.prontidao(c),
        } for c in comercios],
        entregues=sum(1 for e in ETAPAS_PROJETO if e["estado"] == "feito"),
        total_etapas=len(ETAPAS_PROJETO),
        senha_demo=seguranca.SENHA_E_DEMONSTRACAO,
        ia=IA_NO_SISTEMA,
        limites=LIMITES_DA_IA,
        tecnologias=TECNOLOGIAS,
        robustez=ROBUSTEZ,
    )


@app.get("/acuracia", response_class=HTMLResponse)
def acuracia(request: Request):
    if (desvio := _exige_login(request)) is not None:
        return desvio
    classificacao = demo.acuracia_classificacao()
    previsao_ = demo.acuracia_previsao()
    return _pagina(
        request, "acuracia.html", "acuracia",
        classificacao=classificacao,
        previsao=previsao_,
        ganho=round(1 - previsao_["mae"] / previsao_["mae_regua"], 3),
        grafico_f1=svg.barras_f1(
            classificacao["linhas"], classificacao["macro"], classificacao["macro_regua"],
            "F1 por categoria, com o macro do modelo e o da régua",
        ),
        grafico_previsao=svg.previsto_realizado(
            previsao_["pontos"], "Previsto um mês antes contra o realizado",
        ),
    )


def _nao_encontrado(request: Request) -> HTMLResponse:
    resposta = _pagina(request, "nao_encontrado.html", "painel", comercios=demo.comercios())
    resposta.status_code = 404
    return resposta
