"""Quem pode entrar, e em qual empresa.

Enquanto o banco de contas não existe, as contas de demonstração nascem de uma
única variável de ambiente (`RADAR_SENHA_DEMO`). Sem a variável, ninguém entra:
o padrão é fechado, nunca uma senha conhecida no código. Cada conta pertence a
uma empresa só, e é dessa ligação que sai o isolamento entre empresas.
"""

from __future__ import annotations

import functools
import os
import secrets
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from app.seguranca import senha as _senha

VARIAVEL_SENHA_DEMO = "RADAR_SENHA_DEMO"

# usuário -> empresa. São os negócios de mentira de `app/falsos.py`.
NEGOCIOS_DE_DEMONSTRACAO = {
    "bella": "bella-massa",
    "sorriso": "sorriso-claro",
    "patinhas": "patinhas",
}


@dataclass(frozen=True)
class Conta:
    usuario: str
    empresa_id: str
    hash_senha: str = field(repr=False)


@functools.cache
def _hash_de_mentira() -> str:
    return _senha.gerar_hash(secrets.token_urlsafe(16))


class Contas:
    def __init__(self, contas: Iterable[Conta] = ()):
        self._por_usuario = {c.usuario: c for c in contas}

    @classmethod
    def da_demonstracao(cls, ambiente: Mapping[str, str] | None = None) -> Contas:
        ambiente = os.environ if ambiente is None else ambiente
        valor = ambiente.get(VARIAVEL_SENHA_DEMO, "")
        if not valor:
            return cls()
        return cls(Conta(u, e, _senha.gerar_hash(valor)) for u, e in NEGOCIOS_DE_DEMONSTRACAO.items())

    def autenticar(self, usuario: str, senha: str) -> Conta | None:
        """Usuário que não existe também paga o custo do hash, para o tempo não entregar quem existe."""
        conta = self._por_usuario.get(usuario.strip().lower())
        confere = _senha.conferir(senha, conta.hash_senha if conta else _hash_de_mentira())
        return conta if conta and confere else None
