"""Sessão assinada em cookie, com token contra CSRF dentro dela.

O cookie é `HttpOnly` (JavaScript não lê), `SameSite=Lax` (outro site não o manda em POST) e
`Secure` quando o acesso é https. A validade de oito horas conta da entrada e não renova com o uso:
o prazo vai dentro do cookie assinado, então não dá para estendê-lo por fora.

O cookie sozinho não é revogável: sair apaga o cookie do navegador, mas uma cópia dele, guardada
por quem a roubou, valeria até o prazo. Revogar de verdade pede sessão guardada no servidor.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from itsdangerous import BadData, URLSafeSerializer
from starlette.requests import HTTPConnection

NOME_DO_COOKIE = "radar_sessao"
VALIDADE_SEGUNDOS = 8 * 60 * 60
_FOLGA_DO_RELOGIO = 300


def _agora() -> float:
    return time.time()


@dataclass
class Sessao:
    csrf: str
    inicio: float
    usuario: str | None = None
    empresa_id: str | None = None
    # O que segue não vai para o cookie: diz ao middleware o que fazer com ele nesta resposta.
    nova: bool = False
    alterada: bool = False
    encerrada: bool = False

    @classmethod
    def anonima(cls) -> Sessao:
        return cls(csrf=secrets.token_urlsafe(32), inicio=_agora(), nova=True)

    @property
    def restante(self) -> int:
        return max(0, int(self.inicio + VALIDADE_SEGUNDOS - _agora()))


class Assinador:
    def __init__(self, chave: str):
        self._serializador = URLSafeSerializer(chave, salt="radar-sessao")

    def assinar(self, sessao: Sessao) -> str:
        return self._serializador.dumps(
            {"c": sessao.csrf, "i": sessao.inicio, "u": sessao.usuario, "e": sessao.empresa_id}
        )

    def abrir(self, texto: str) -> Sessao | None:
        """Devolve a sessão se a assinatura, o formato e o prazo estiverem certos; senão, nada."""
        try:
            dados = self._serializador.loads(texto)
        except BadData:
            return None
        if not isinstance(dados, dict):
            return None
        csrf, inicio = dados.get("c"), dados.get("i")
        usuario, empresa = dados.get("u"), dados.get("e")
        if not (isinstance(csrf, str) and csrf):
            return None
        if isinstance(inicio, bool) or not isinstance(inicio, int | float):
            return None
        if (usuario is None) != (empresa is None):
            return None
        if usuario is not None and not (isinstance(usuario, str) and isinstance(empresa, str)):
            return None
        if usuario is not None and not (usuario and empresa):
            return None
        if not -_FOLGA_DO_RELOGIO <= _agora() - inicio <= VALIDADE_SEGUNDOS:
            return None
        return Sessao(csrf=csrf, inicio=inicio, usuario=usuario, empresa_id=empresa)


def cabecalho_set_cookie(sessao: Sessao, assinador: Assinador, seguro: bool) -> str:
    valor, segundos = ("", 0) if sessao.encerrada else (assinador.assinar(sessao), sessao.restante)
    partes = [f"{NOME_DO_COOKIE}={valor}", "Path=/", f"Max-Age={segundos}", "HttpOnly", "SameSite=Lax"]
    if seguro:
        partes.append("Secure")
    return "; ".join(partes)


# ------------------------------------------------------------ o que as rotas usam

def guardar(scope: dict, sessao: Sessao) -> None:
    estado = scope.setdefault("state", {})
    estado["sessao"] = sessao
    estado["csrf"] = sessao.csrf          # é o `{{ request.state.csrf }}` dos formulários


def da_requisicao(conexao: HTTPConnection) -> Sessao | None:
    return conexao.scope.get("state", {}).get("sessao")


def iniciar(conexao: HTTPConnection, usuario: str, empresa_id: str) -> None:
    """Abre a sessão do usuário num cookie e num token novos: os de antes deixam de servir."""
    guardar(conexao.scope, Sessao(
        csrf=secrets.token_urlsafe(32), inicio=_agora(),
        usuario=usuario, empresa_id=empresa_id, alterada=True,
    ))


def encerrar(conexao: HTTPConnection) -> None:
    """Manda o navegador apagar o cookie. Quem ficar sem cookie recebe uma sessão anônima nova."""
    guardar(conexao.scope, Sessao(
        csrf=secrets.token_urlsafe(32), inicio=_agora(), alterada=True, encerrada=True,
    ))
