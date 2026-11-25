"""As duas rotas que mudam quem está dentro: entrar e sair.

O token contra CSRF já foi conferido pelo middleware quando a rota roda.
"""

from __future__ import annotations

import anyio
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.seguranca import sessao
from app.seguranca.destino import caminho_interno
from app.seguranca.isolamento import usuario_atual
from app.seguranca.limite import origem_do_pedido

rotas = APIRouter()

# Cada conferência de senha aloca ~19 MiB de Argon2id (m=19456 KiB), de
# propósito: é o que torna a força bruta cara. Mas a rota roda no threadpool de
# 40 do AnyIO, e 40 conferências ao mesmo tempo passam de 700 MiB — acima dos
# 512 MB do plano em que o site roda. O portão abaixo limita quantas conferências acontecem juntas.
# Quem espera, espera; o serviço não morre.
_CONFERENCIAS_SIMULTANEAS = anyio.Semaphore(2)


def _para(destino: str) -> RedirectResponse:
    return RedirectResponse(destino, status_code=303)


@rotas.post("/entrar")
async def fazer_entrada(
    request: Request, usuario: str = Form(""), senha: str = Form(""), proximo: str = Form(""),
):
    limite = request.app.state.limite_de_entrada
    origem = origem_do_pedido(request)

    # Bloqueada, a origem não chega nem a testar a senha: acertar não adianta depois de errar demais.
    if limite.bloqueada(origem):
        return _para("/entrar?erro=bloqueado")

    async with _CONFERENCIAS_SIMULTANEAS:
        conta = await anyio.to_thread.run_sync(request.app.state.contas.autenticar, usuario, senha)
    if conta is None:
        limite.registrar_falha(origem)
        return _para("/entrar?erro=credencial")

    sessao.iniciar(request, conta.usuario, conta.empresa_id, conta.papel,
                   conta.usuario_id or None)
    _anotar(conta, "entrou", origem)
    destino = caminho_interno(proximo)
    # Administrador cai na área dele: as telas de cliente não têm o que mostrar a
    # quem não é dono de negócio. Só segue o pedido se ele for da área da equipe.
    if conta.e_admin and not (destino == "/admin" or destino.startswith("/admin/")):
        return _para("/admin")
    return _para(destino)


@rotas.post("/sair")
def sair(request: Request):
    atual = usuario_atual(request)
    if atual is not None:
        _anotar_saida(atual)
    sessao.encerrar(request)
    return _para("/")


def _anotar(conta, acao: str, origem: str) -> None:
    """Grava a entrada na trilha. Sem banco, não há trilha: a função sai calada."""
    from app.banco import sessao as banco

    if not banco.usar_banco():
        return
    from app import auditoria

    with banco.Sessao() as transacao:
        auditoria.registrar(
            transacao, empresa_id=conta.empresa_id, usuario_id=conta.usuario_id or None,
            acao=acao, objeto=conta.usuario, detalhe=f"origem {origem}",
        )
        transacao.commit()


def _anotar_saida(usuario) -> None:
    from app.banco import sessao as banco

    if not banco.usar_banco():
        return
    from app import auditoria

    with banco.Sessao() as transacao:
        auditoria.registrar(
            transacao, empresa_id=usuario.empresa_id, acao="saiu", objeto=usuario.nome,
        )
        transacao.commit()
