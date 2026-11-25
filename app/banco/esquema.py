"""Cria as tabelas do banco a partir de `esquema.sql`, na partida do serviço.

Um arquivo SQL só, lido de cima a baixo, é a definição inteira do banco. Não há
ferramenta de migração: todo comando do script usa `IF NOT EXISTS` ou
`ON CONFLICT DO NOTHING`, então rodar o script num banco que já existe não muda
nada e não apaga dado.

Por que na partida: o Postgres do serviço **não aceita conexão de fora** (a lista
de endereços permitidos está vazia, o que é o certo). O único lugar de dentro da
rede do banco é o próprio serviço.

Duas instâncias subindo juntas não se atropelam: o script roda dentro de uma
transação que segura uma trava do próprio Postgres (`pg_advisory_xact_lock`).

Falha ao criar **não derruba o serviço**: o erro vai para o log e o site sobe
mostrando a tela de "banco não ligado", que diz o que fazer.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import Engine, text

ARQUIVO = Path(__file__).with_name("esquema.sql")
# Número qualquer, fixo: identifica a trava deste script entre as do Postgres.
TRAVA = 7_202_611

_log = logging.getLogger("radar.esquema")


def comandos(conteudo: str | None = None) -> list[str]:
    """Os comandos do script, um por item, sem as linhas de comentário."""
    bruto = ARQUIVO.read_text(encoding="utf-8") if conteudo is None else conteudo
    linhas = [linha for linha in bruto.splitlines() if not linha.lstrip().startswith("--")]
    return [comando.strip() for comando in "\n".join(linhas).split(";") if comando.strip()]


def criar(motor: Engine) -> None:
    """Roda o script inteiro numa transação. Ou tudo entra, ou nada muda."""
    with motor.begin() as conexao:
        conexao.execute(text("SELECT pg_advisory_xact_lock(:trava)"), {"trava": TRAVA})
        for comando in comandos():
            conexao.exec_driver_sql(comando)


def subir() -> bool:
    """Cria as tabelas no banco do serviço. Devolve False se não há banco ou se falhou."""
    from app.banco import sessao as banco

    if not banco.usar_banco():
        return False
    try:
        criar(banco.motor())
    except Exception:       # noqa: BLE001 - o serviço sobe mesmo assim, com a tela que explica
        _log.exception("criar as tabelas do banco falhou; o site sobe sem banco")
        return False
    _log.info("tabelas do banco conferidas")
    return True
