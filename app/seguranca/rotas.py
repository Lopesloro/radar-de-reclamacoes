"""As duas rotas que mudam quem está dentro: entrar e sair.

O token contra CSRF já foi conferido pelo middleware quando a rota roda.
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.seguranca import sessao
from app.seguranca.destino import caminho_interno
from app.seguranca.limite import origem_de

rotas = APIRouter()


def _para(destino: str) -> RedirectResponse:
    return RedirectResponse(destino, status_code=303)


@rotas.post("/entrar")
def fazer_entrada(request: Request, usuario: str = Form(""), senha: str = Form(""), proximo: str = Form("")):
    limite = request.app.state.limite_de_entrada
    origem = origem_de(request.client.host if request.client else None)

    # Bloqueada, a origem não chega nem a testar a senha: acertar não adianta depois de errar demais.
    if limite.bloqueada(origem):
        return _para("/entrar?erro=bloqueado")

    conta = request.app.state.contas.autenticar(usuario, senha)
    if conta is None:
        limite.registrar_falha(origem)
        return _para("/entrar?erro=credencial")

    sessao.iniciar(request, conta.usuario, conta.empresa_id)
    return _para(caminho_interno(proximo))


@rotas.post("/sair")
def sair(request: Request):
    sessao.encerrar(request)
    return _para("/")
