"""Sobe o banco para a última migração, na partida do serviço.

Por que na partida e não num passo separado do deploy: o Postgres do serviço
**não aceita conexão de fora** (a lista de endereços permitidos está vazia, o que
é o certo), então não há como rodar `alembic upgrade head` da máquina de ninguém.
O único lugar de dentro da rede do banco é o próprio serviço.

Quando isto é seguro e quando não é, dito com clareza:

- **Seguro com uma instância**, que é o caso deste serviço. `upgrade head` num
  banco já atualizado não faz nada, então reiniciar não causa dano.
- **Não é seguro com várias instâncias subindo juntas**: duas rodando a mesma
  migração ao mesmo tempo podem se atropelar. Quando o serviço crescer para mais
  de uma instância, isto sai daqui e vira um passo de pré-deploy. Está escrito em
  `docs/producao.md`.

A migração pode ser desligada com `RADAR_MIGRAR_NA_PARTIDA=0`, para o caso de
alguém precisar subir o serviço com o banco em outra versão de propósito.

Falha na migração **não derruba o serviço**: o erro vai para o log e o site sobe
mostrando a tela de "banco não ligado", que diz o que fazer. Derrubar o serviço
deixaria a equipe sem a tela que explica o problema.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

VARIAVEL = "RADAR_MIGRAR_NA_PARTIDA"
RAIZ = Path(__file__).resolve().parent.parent.parent

_log = logging.getLogger("radar.migracao")


def ligada() -> bool:
    return os.environ.get(VARIAVEL, "1").strip() not in ("0", "nao", "não", "false")


def subir() -> str | None:
    """Roda `alembic upgrade head`. Devolve a versão que ficou, ou None se não rodou."""
    from app.banco import sessao as banco

    if not banco.usar_banco():
        return None
    if not ligada():
        _log.info("migração desligada por %s", VARIAVEL)
        return None

    from alembic.config import Config

    from alembic import command

    configuracao = Config(str(RAIZ / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ / "alembic"))
    # A URL vem do ambiente, pela mesma função que o resto do sistema usa: duas
    # formas de descobrir a URL é uma a mais do que o necessário para divergirem.
    configuracao.set_main_option("sqlalchemy.url", banco.url() or "")
    try:
        command.upgrade(configuracao, "head")
    except Exception:       # noqa: BLE001 - o serviço sobe mesmo assim, com a tela que explica
        _log.exception("a migração do banco falhou; o site sobe sem banco")
        return None

    from sqlalchemy import text

    with banco.motor().connect() as conexao:
        versao = conexao.execute(text("select version_num from alembic_version")).scalar()
    _log.info("banco na migração %s", versao)
    return versao
