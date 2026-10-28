"""Ligação do Alembic com as entidades de `app/banco/modelo.py`.

A URL vem de `DATABASE_URL` (tratada em `app/banco/sessao.py`, que conserta o
`postgres://` do Render). O teste passa a dela por `-x` ou pela configuração.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.banco import modelo, sessao

configuracao = context.config
if configuracao.config_file_name is not None:
    fileConfig(configuracao.config_file_name)

endereco = configuracao.get_main_option("sqlalchemy.url") or sessao.url()
if not endereco:
    raise SystemExit("Defina DATABASE_URL antes de rodar a migração.")
configuracao.set_main_option("sqlalchemy.url", endereco)

destino = modelo.Base.metadata


def offline() -> None:
    context.configure(url=endereco, target_metadata=destino, literal_binds=True,
                      render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def online() -> None:
    motor = engine_from_config(
        configuracao.get_section(configuracao.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    sessao.ligar_chaves_estrangeiras(motor)
    with motor.connect() as conexao:
        context.configure(connection=conexao, target_metadata=destino, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


offline() if context.is_offline_mode() else online()
