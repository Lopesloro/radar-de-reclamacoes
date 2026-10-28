"""Acesso PROVISÓRIO, só até a entrada segura do Matheus ficar pronta.

Hoje as telas internas abrem como o usuário de demonstração e só mostram os
negócios de demonstração. A tela de entrada já confere a credencial de
demonstração, mas ainda não cria sessão: quem souber o endereço entra sem
senha. Quando `app/seguranca/` existir (plano/02-matheus.md), as rotas passam a
usar `usuario_atual` e `empresa_do_usuario` de lá, e este arquivo é apagado.
"""

from __future__ import annotations

import hmac
import os
from dataclasses import dataclass

from fastapi import HTTPException, Request

from app import servicos

USUARIO_DEMO = "admin"
SENHA_DEMO = os.environ.get("RADAR_SENHA_DEMO", "admin")
SENHA_E_DEMO = SENHA_DEMO == "admin"


@dataclass(frozen=True)
class UsuarioProvisorio:
    nome: str
    papel: str


DEMONSTRACAO = UsuarioProvisorio(nome="demonstração", papel="demo")


def usuario_atual(request: Request) -> UsuarioProvisorio:
    return DEMONSTRACAO


def credencial_confere(usuario: str, senha: str) -> bool:
    """Compara em tempo constante. Sem hash e sem limite de tentativas: isso é do Matheus."""
    usuario_ok = hmac.compare_digest(usuario.strip().lower().encode(), USUARIO_DEMO.encode())
    senha_ok = hmac.compare_digest(senha.encode(), SENHA_DEMO.encode())
    return usuario_ok and senha_ok


def empresa_permitida(empresa_id: str) -> str:
    """Hoje só confere se o negócio existe. A regra de verdade (403) é do Matheus."""
    if not servicos.existe(empresa_id):
        raise HTTPException(status_code=404)
    return empresa_id
