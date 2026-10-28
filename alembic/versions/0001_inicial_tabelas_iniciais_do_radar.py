"""As tabelas iniciais do Radar.

Doze tabelas. Fora de `empresa` (a raiz) e `categoria` (vocabulário comum), toda
tabela leva `empresa_id` apontando para `empresa`: é o que sustenta o isolamento
entre parceiras. A migração também deixa os cinco assuntos do contrato prontos.

Criada em: 2026-10-27
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = '0001_inicial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('categoria',
    sa.Column('id', sa.String(length=30), nullable=False),
    sa.Column('nome', sa.String(length=60), nullable=False),
    sa.Column('ordem', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('empresa',
    sa.Column('id', sa.String(length=60), nullable=False),
    sa.Column('nome', sa.String(length=160), nullable=False),
    sa.Column('criada_em', sa.DateTime(), nullable=False),
    sa.Column('ativa', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('comercio',
    sa.Column('id', sa.String(length=60), nullable=False),
    sa.Column('empresa_id', sa.String(length=60), nullable=False),
    sa.Column('nome', sa.String(length=160), nullable=False),
    sa.Column('ramo', sa.String(length=80), nullable=False),
    sa.Column('cidade', sa.String(length=120), nullable=False),
    sa.Column('tem_termo', sa.Boolean(), nullable=False),
    sa.Column('tem_fonte', sa.Boolean(), nullable=False),
    sa.Column('categorias_combinadas', sa.Boolean(), nullable=False),
    sa.Column('tem_canal', sa.Boolean(), nullable=False),
    sa.Column('criado_em', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresa.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('comercio', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_comercio_empresa_id'), ['empresa_id'], unique=False)

    op.create_table('usuario',
    sa.Column('id', sa.String(length=60), nullable=False),
    sa.Column('empresa_id', sa.String(length=60), nullable=False),
    sa.Column('email', sa.String(length=200), nullable=False),
    sa.Column('nome', sa.String(length=160), nullable=False),
    sa.Column('papel', sa.String(length=30), nullable=False),
    sa.Column('senha_hash', sa.String(length=200), nullable=True),
    sa.Column('criado_em', sa.DateTime(), nullable=False),
    sa.Column('ativo', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresa.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email', name='uq_usuario_email')
    )
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_usuario_empresa_id'), ['empresa_id'], unique=False)

    op.create_table('versao_modelo',
    sa.Column('id', sa.String(length=60), nullable=False),
    sa.Column('empresa_id', sa.String(length=60), nullable=False),
    sa.Column('tipo', sa.String(length=30), nullable=False),
    sa.Column('nome', sa.String(length=80), nullable=False),
    sa.Column('treinada_em', sa.DateTime(), nullable=False),
    sa.Column('metricas', sa.Text(), nullable=True),
    sa.Column('ativa', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresa.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('versao_modelo', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_versao_modelo_empresa_id'), ['empresa_id'], unique=False)

    op.create_table('auditoria',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.String(length=60), nullable=False),
    sa.Column('usuario_id', sa.String(length=60), nullable=True),
    sa.Column('quando', sa.DateTime(), nullable=False),
    sa.Column('acao', sa.String(length=60), nullable=False),
    sa.Column('objeto', sa.String(length=120), nullable=False),
    sa.Column('detalhe', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresa.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuario.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('auditoria', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_auditoria_empresa_id'), ['empresa_id'], unique=False)

    op.create_table('execucao_coleta',
    sa.Column('id', sa.String(length=60), nullable=False),
    sa.Column('empresa_id', sa.String(length=60), nullable=False),
    sa.Column('comercio_id', sa.String(length=60), nullable=False),
    sa.Column('iniciada_em', sa.DateTime(), nullable=False),
    sa.Column('terminada_em', sa.DateTime(), nullable=True),
    sa.Column('lidas', sa.Integer(), nullable=False),
    sa.Column('novas', sa.Integer(), nullable=False),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('erro', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['comercio_id'], ['comercio.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresa.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('execucao_coleta', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_execucao_coleta_comercio_id'), ['comercio_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_execucao_coleta_empresa_id'), ['empresa_id'], unique=False)

    op.create_table('previsao',
    sa.Column('id', sa.String(length=80), nullable=False),
    sa.Column('empresa_id', sa.String(length=60), nullable=False),
    sa.Column('comercio_id', sa.String(length=60), nullable=False),
    sa.Column('categoria_id', sa.String(length=30), nullable=False),
    sa.Column('mes', sa.Date(), nullable=False),
    sa.Column('p10', sa.Integer(), nullable=False),
    sa.Column('p50', sa.Integer(), nullable=False),
    sa.Column('p90', sa.Integer(), nullable=False),
    sa.Column('versao_modelo_id', sa.String(length=60), nullable=False),
    sa.Column('gerada_em', sa.DateTime(), nullable=False),
    sa.CheckConstraint('p10 <= p50 AND p50 <= p90', name='ck_previsao_faixa'),
    sa.ForeignKeyConstraint(['categoria_id'], ['categoria.id'], ),
    sa.ForeignKeyConstraint(['comercio_id'], ['comercio.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresa.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['versao_modelo_id'], ['versao_modelo.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('comercio_id', 'categoria_id', 'mes', 'versao_modelo_id', name='uq_previsao_comercio_cat_mes')  # noqa: E501
    )
    with op.batch_alter_table('previsao', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_previsao_comercio_id'), ['comercio_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_previsao_empresa_id'), ['empresa_id'], unique=False)

    op.create_table('serie_mensal',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.String(length=60), nullable=False),
    sa.Column('comercio_id', sa.String(length=60), nullable=False),
    sa.Column('categoria_id', sa.String(length=30), nullable=False),
    sa.Column('mes', sa.Date(), nullable=False),
    sa.Column('quantidade', sa.Integer(), nullable=False),
    sa.Column('fechado', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['categoria_id'], ['categoria.id'], ),
    sa.ForeignKeyConstraint(['comercio_id'], ['comercio.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresa.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('comercio_id', 'categoria_id', 'mes', name='uq_serie_comercio_cat_mes')
    )
    with op.batch_alter_table('serie_mensal', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_serie_mensal_comercio_id'), ['comercio_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_serie_mensal_empresa_id'), ['empresa_id'], unique=False)

    op.create_table('alerta',
    sa.Column('id', sa.String(length=80), nullable=False),
    sa.Column('empresa_id', sa.String(length=60), nullable=False),
    sa.Column('comercio_id', sa.String(length=60), nullable=False),
    sa.Column('categoria_id', sa.String(length=30), nullable=False),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('atual', sa.Integer(), nullable=False),
    sa.Column('previsao_id', sa.String(length=80), nullable=False),
    sa.Column('gerado_em', sa.Date(), nullable=False),
    sa.Column('situacao', sa.String(length=20), nullable=False),
    sa.ForeignKeyConstraint(['categoria_id'], ['categoria.id'], ),
    sa.ForeignKeyConstraint(['comercio_id'], ['comercio.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresa.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['previsao_id'], ['previsao.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('alerta', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_alerta_comercio_id'), ['comercio_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_alerta_empresa_id'), ['empresa_id'], unique=False)

    op.create_table('avaliacao',
    sa.Column('id', sa.String(length=80), nullable=False),
    sa.Column('empresa_id', sa.String(length=60), nullable=False),
    sa.Column('comercio_id', sa.String(length=60), nullable=False),
    sa.Column('id_origem', sa.String(length=200), nullable=False),
    sa.Column('data', sa.Date(), nullable=False),
    sa.Column('estrelas', sa.Integer(), nullable=False),
    sa.Column('texto', sa.Text(), nullable=True),
    sa.Column('coletada_em', sa.DateTime(), nullable=False),
    sa.Column('execucao_coleta_id', sa.String(length=60), nullable=True),
    sa.CheckConstraint('estrelas BETWEEN 1 AND 5', name='ck_avaliacao_estrelas'),
    sa.ForeignKeyConstraint(['comercio_id'], ['comercio.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresa.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['execucao_coleta_id'], ['execucao_coleta.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('comercio_id', 'id_origem', name='uq_avaliacao_comercio_origem')
    )
    with op.batch_alter_table('avaliacao', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_avaliacao_comercio_id'), ['comercio_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_avaliacao_data'), ['data'], unique=False)
        batch_op.create_index(batch_op.f('ix_avaliacao_empresa_id'), ['empresa_id'], unique=False)

    op.create_table('classificacao',
    sa.Column('id', sa.String(length=80), nullable=False),
    sa.Column('empresa_id', sa.String(length=60), nullable=False),
    sa.Column('avaliacao_id', sa.String(length=80), nullable=False),
    sa.Column('categoria_id', sa.String(length=30), nullable=True),
    sa.Column('confianca', sa.Float(), nullable=False),
    sa.Column('motivo_sem_assunto', sa.String(length=120), nullable=True),
    sa.Column('versao_modelo_id', sa.String(length=60), nullable=False),
    sa.Column('criada_em', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['avaliacao_id'], ['avaliacao.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['categoria_id'], ['categoria.id'], ),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresa.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['versao_modelo_id'], ['versao_modelo.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('avaliacao_id', 'versao_modelo_id', name='uq_classificacao_avaliacao')
    )
    with op.batch_alter_table('classificacao', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_classificacao_avaliacao_id'), ['avaliacao_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_classificacao_empresa_id'), ['empresa_id'], unique=False)



    # Os cinco assuntos vêm de `app/contratos.CATEGORIAS`; o nome com acento, de
    # `app/conteudo.NOMES_CATEGORIA`. Copiados aqui de propósito: migração antiga
    # não pode mudar de resultado porque o código de hoje mudou.
    op.bulk_insert(
        sa.table(
            "categoria",
            sa.column("id", sa.String),
            sa.column("nome", sa.String),
            sa.column("ordem", sa.Integer),
        ),
        [
            {"id": "atendimento", "nome": "atendimento", "ordem": 0},
            {"id": "demora", "nome": "demora", "ordem": 1},
            {"id": "preco", "nome": "pre\u00e7o", "ordem": 2},
            {"id": "qualidade", "nome": "qualidade", "ordem": 3},
            {"id": "ambiente", "nome": "ambiente", "ordem": 4},
        ],
    )


def downgrade() -> None:
    with op.batch_alter_table('classificacao', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_classificacao_empresa_id'))
        batch_op.drop_index(batch_op.f('ix_classificacao_avaliacao_id'))

    op.drop_table('classificacao')
    with op.batch_alter_table('avaliacao', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_avaliacao_empresa_id'))
        batch_op.drop_index(batch_op.f('ix_avaliacao_data'))
        batch_op.drop_index(batch_op.f('ix_avaliacao_comercio_id'))

    op.drop_table('avaliacao')
    with op.batch_alter_table('alerta', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_alerta_empresa_id'))
        batch_op.drop_index(batch_op.f('ix_alerta_comercio_id'))

    op.drop_table('alerta')
    with op.batch_alter_table('serie_mensal', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_serie_mensal_empresa_id'))
        batch_op.drop_index(batch_op.f('ix_serie_mensal_comercio_id'))

    op.drop_table('serie_mensal')
    with op.batch_alter_table('previsao', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_previsao_empresa_id'))
        batch_op.drop_index(batch_op.f('ix_previsao_comercio_id'))

    op.drop_table('previsao')
    with op.batch_alter_table('execucao_coleta', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_execucao_coleta_empresa_id'))
        batch_op.drop_index(batch_op.f('ix_execucao_coleta_comercio_id'))

    op.drop_table('execucao_coleta')
    with op.batch_alter_table('auditoria', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_auditoria_empresa_id'))

    op.drop_table('auditoria')
    with op.batch_alter_table('versao_modelo', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_versao_modelo_empresa_id'))

    op.drop_table('versao_modelo')
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_usuario_empresa_id'))

    op.drop_table('usuario')
    with op.batch_alter_table('comercio', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_comercio_empresa_id'))

    op.drop_table('comercio')
    op.drop_table('empresa')
    op.drop_table('categoria')
