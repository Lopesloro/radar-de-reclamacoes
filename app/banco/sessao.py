"""De onde os dados vêm, decidido em tempo de execução.

Requisito duro: **sem `DATABASE_URL`, nada aqui é aberto**, e toda tela diz que
não há banco ligado, em vez de inventar número. Importar este módulo não conecta
em nada; o motor nasce na primeira chamada de `motor()`.

O banco é sempre PostgreSQL, na produção e no teste.
"""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

_motor: Engine | None = None
_fabrica: sessionmaker[Session] | None = None


def url() -> str | None:
    """A URL do banco, pronta para o SQLAlchemy 2.

    O Render entrega `postgres://`; o SQLAlchemy 2 só aceita `postgresql+psycopg://`.
    Trocar isso aqui evita o erro aparecer no deploy, não no teste.
    """
    bruta = os.environ.get("DATABASE_URL", "").strip()
    if not bruta:
        return None
    if bruta.startswith("postgres://"):
        return "postgresql+psycopg://" + bruta[len("postgres://"):]
    if bruta.startswith("postgresql://"):
        return "postgresql+psycopg://" + bruta[len("postgresql://"):]
    return bruta


def usar_banco() -> bool:
    """True quando há banco configurado."""
    return url() is not None


def motor() -> Engine:
    global _motor
    if _motor is None:
        endereco = url()
        if endereco is None:
            raise RuntimeError("Sem DATABASE_URL não existe banco. Chame usar_banco() antes.")
        _motor = create_engine(endereco, pool_pre_ping=True, future=True)
    return _motor


def Sessao() -> Session:  # noqa: N802 - é uma fábrica, o nome segue o SQLAlchemy
    global _fabrica
    if _fabrica is None:
        _fabrica = sessionmaker(bind=motor(), expire_on_commit=False)
    return _fabrica()


def esquecer() -> None:
    """Descarta o motor. Serve para o teste trocar de banco na mesma execução."""
    global _motor, _fabrica
    if _motor is not None:
        _motor.dispose()
    _motor, _fabrica = None, None
