"""Fontes de avaliação, plano do cliente e espaço para o hash Argon2id.

O que esta migração acrescenta, e por quê:

- **`fonte`**: de onde as avaliações de cada negócio são lidas (Google, iFood ou
  arquivo enviado). O segredo de acesso fica na coluna `segredo_cifrado`, sempre
  cifrado por `app/seguranca/cofre.py`; o sistema recusa gravar sem a chave do
  cofre, em vez de gravar em texto.
- **`empresa.plano` e `empresa.email_aviso`**: o plano contratado e para onde o
  aviso vai. Nenhuma tela de cliente mostra o plano.
- **`usuario.ultimo_acesso`**: quando a conta entrou pela última vez. Serve para
  a equipe ver conta que nunca foi usada.
- **`usuario.senha_hash` de 200 para 400 caracteres**: o hash do Argon2id carrega
  os parâmetros dentro dele (`$argon2id$v=19$m=19456,t=2,p=1$sal$derivada`) e
  passa de 200. Sem este aumento, a primeira senha gravada em produção seria
  cortada pelo banco e **ninguém entraria** — e o erro só apareceria no Postgres,
  nunca no SQLite do teste, que ignora o tamanho de VARCHAR.

Revision ID: 0002_fontes_planos_e_argon2
Revises: 0001_inicial
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002_fontes_planos_e_argon2"
down_revision = "0001_inicial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fonte",
        sa.Column("id", sa.String(length=60), nullable=False),
        sa.Column("empresa_id", sa.String(length=60), nullable=False),
        sa.Column("comercio_id", sa.String(length=60), nullable=False),
        sa.Column("plataforma", sa.String(length=30), nullable=False),
        sa.Column("identificador_externo", sa.String(length=200), nullable=False),
        sa.Column("segredo_cifrado", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("erro", sa.Text(), nullable=True),
        sa.Column("ultima_coleta", sa.DateTime(), nullable=True),
        sa.Column("criada_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["comercio_id"], ["comercio.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("comercio_id", "plataforma", name="uq_fonte_comercio_plataforma"),
    )
    op.create_index(op.f("ix_fonte_comercio_id"), "fonte", ["comercio_id"])
    op.create_index(op.f("ix_fonte_empresa_id"), "fonte", ["empresa_id"])

    # `server_default` nas colunas novas e obrigatórias: sem ele, a migração
    # falha numa tabela que já tem linha, que é o caso de qualquer banco em uso.
    op.add_column("empresa", sa.Column("plano", sa.String(length=30), nullable=False,
                                       server_default="piloto"))
    op.add_column("empresa", sa.Column("email_aviso", sa.String(length=200), nullable=True))
    op.add_column("usuario", sa.Column("ultimo_acesso", sa.DateTime(), nullable=True))

    # O batch existe para o SQLite, que não sabe mudar o tipo de uma coluna:
    # o Alembic recria a tabela por baixo. No Postgres vira um ALTER comum.
    with op.batch_alter_table("usuario") as lote:
        lote.alter_column("senha_hash", existing_type=sa.String(length=200),
                          type_=sa.String(length=400), existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("usuario") as lote:
        lote.alter_column("senha_hash", existing_type=sa.String(length=400),
                          type_=sa.String(length=200), existing_nullable=True)
    op.drop_column("usuario", "ultimo_acesso")
    op.drop_column("empresa", "email_aviso")
    op.drop_column("empresa", "plano")
    op.drop_index(op.f("ix_fonte_empresa_id"), table_name="fonte")
    op.drop_index(op.f("ix_fonte_comercio_id"), table_name="fonte")
    op.drop_table("fonte")
