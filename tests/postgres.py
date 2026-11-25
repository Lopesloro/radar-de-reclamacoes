"""Bancos Postgres descartáveis para os testes.

O teste roda no mesmo banco da produção (PostgreSQL), nunca em SQLite. Dois
defeitos deste projeto só apareceram no Postgres — o tamanho da coluna de senha
e a ordem dos INSERT entre tabelas — e um teste em outro banco não os veria.

`RADAR_TESTE_POSTGRES` aponta para um servidor Postgres onde o teste pode criar
e apagar bancos. Cada banco criado aqui tem nome `radar_t_<sorteio>` e é apagado
no fim. Sem a variável, a suíte **para com erro**, em vez de pular os testes de
banco: teste pulado aparece verde e não prova nada.

    RADAR_TESTE_POSTGRES=postgresql://radar@127.0.0.1:5432/postgres
"""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager

from sqlalchemy import create_engine, text

VARIAVEL = "RADAR_TESTE_POSTGRES"


def servidor() -> str:
    bruta = os.environ.get(VARIAVEL, "").strip()
    if not bruta:
        raise SystemExit(
            f"Os testes precisam de um Postgres. Defina {VARIAVEL}, por exemplo "
            f"{VARIAVEL}=postgresql://radar@127.0.0.1:5432/postgres"
        )
    for prefixo in ("postgres://", "postgresql://"):
        if bruta.startswith(prefixo):
            return "postgresql+psycopg://" + bruta[len(prefixo):]
    return bruta


def _trocar_banco(endereco: str, nome: str) -> str:
    base, _, _ = endereco.rpartition("/")
    return f"{base}/{nome}"


def criar() -> str:
    """Cria um banco vazio e devolve o endereço dele."""
    nome = f"radar_t_{uuid.uuid4().hex[:12]}"
    administrador = create_engine(servidor(), isolation_level="AUTOCOMMIT")
    with administrador.connect() as conexao:
        conexao.execute(text(f'CREATE DATABASE "{nome}"'))
    administrador.dispose()
    return _trocar_banco(servidor(), nome)


def apagar(endereco: str) -> None:
    nome = endereco.rpartition("/")[2]
    administrador = create_engine(servidor(), isolation_level="AUTOCOMMIT")
    with administrador.connect() as conexao:
        conexao.execute(text(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)'))
    administrador.dispose()


@contextmanager
def banco_novo():
    endereco = criar()
    try:
        yield endereco
    finally:
        apagar(endereco)
