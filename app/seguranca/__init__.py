"""Segurança do site: entrada, sessão, token CSRF, limite de tentativas, cabeçalhos e isolamento.

O recorte do projeto é **defesa**: nada aqui ataca nada. Para ligar tudo, uma linha em `app/web.py`,
logo depois de criar o `app` e **antes** de incluir os roteadores (a rota `/entrar` daqui precisa vir
antes da provisória):

    from app.seguranca import instalar
    instalar(app)

Variáveis de ambiente:

- `RADAR_CHAVE`: chave que assina o cookie da sessão. Sem ela o servidor sorteia uma a cada partida e
  as sessões caem a cada reinício (o `render.yaml` já gera uma).
- `RADAR_SENHA_DEMO`: senha das contas de demonstração (`contas.py`). Sem ela, ninguém entra.

Para as rotas e os templates:

- `usuario_atual(request)` -> `Usuario` ou `None`.
- `empresa_do_usuario(request)` -> a empresa de onde filtrar toda consulta.
- `exigir_empresa(request, empresa_id)` -> recusa com 403 a empresa que não é a do usuário.
- Em todo formulário que altera algo: `<input type="hidden" name="csrf" value="{{ request.state.csrf }}">`.
"""

from __future__ import annotations

import os
import secrets

from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute

from app.seguranca.contas import Contas
from app.seguranca.isolamento import (
    Usuario,
    empresa_do_usuario,
    exigir_empresa,
    usuario_atual,
    vigiar_empresa,
)
from app.seguranca.limite import LimiteDeTentativas
from app.seguranca.middleware import Defesa
from app.seguranca.rotas import rotas
from app.seguranca.sessao import Assinador

VARIAVEL_CHAVE = "RADAR_CHAVE"

__all__ = ["Usuario", "empresa_do_usuario", "exigir_empresa", "instalar", "usuario_atual"]


def _ja_tem_rotas(app: FastAPI) -> bool:
    # `include_router` e os decoradores fixam as dependências no momento em que a rota entra.
    return any(isinstance(r, APIRoute) or hasattr(r, "original_router") for r in app.router.routes)


def instalar(app: FastAPI, *, contas: Contas | None = None, chave: str | None = None) -> None:
    if _ja_tem_rotas(app):
        raise RuntimeError("instalar(app) vem antes de qualquer rota: sem isso a trava de empresa não vale.")
    app.state.contas = Contas.da_demonstracao() if contas is None else contas
    app.state.limite_de_entrada = LimiteDeTentativas()
    app.router.dependencies.append(Depends(vigiar_empresa))
    app.include_router(rotas)
    app.add_middleware(
        Defesa,
        assinador=Assinador(chave or os.environ.get(VARIAVEL_CHAVE) or secrets.token_urlsafe(48)),
    )
