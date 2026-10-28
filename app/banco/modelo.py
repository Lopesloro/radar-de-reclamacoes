"""As tabelas do banco.

Regra que organiza tudo: **toda tabela de dado operacional chega à empresa por
chave estrangeira**. É o que deixa uma consulta filtrar por empresa sem depender
de o programador lembrar — a coluna está lá para ser usada. Só `empresa` (a raiz)
e `categoria` (vocabulário igual para as três) ficam de fora.

Nomes em português, como no resto do código.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Um objeto ForeignKey pertence a uma coluna só, por isso cada uso cria o seu.
def _para_empresa() -> ForeignKey:
    return ForeignKey("empresa.id", ondelete="CASCADE")


def _para_comercio() -> ForeignKey:
    return ForeignKey("comercio.id", ondelete="CASCADE")


def _para_categoria() -> ForeignKey:
    return ForeignKey("categoria.id")


class Base(DeclarativeBase):
    pass


def _empresa_id() -> Mapped[str]:
    """O caminho até a empresa, em toda tabela de dado operacional."""
    return mapped_column(String(60), _para_empresa(), nullable=False, index=True)


class Empresa(Base):
    """A parceira que autorizou a leitura das avaliações. Raiz do isolamento."""

    __tablename__ = "empresa"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    criada_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Categoria(Base):
    """Os cinco assuntos. Vocabulário comum, igual para todas as empresas."""

    __tablename__ = "categoria"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    nome: Mapped[str] = mapped_column(String(60), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)


class Usuario(Base):
    """Quem entra no sistema. A sessão dele é a única origem do `empresa_id`."""

    __tablename__ = "usuario"
    __table_args__ = (UniqueConstraint("email", name="uq_usuario_email"),)

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    empresa_id: Mapped[str] = _empresa_id()
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    papel: Mapped[str] = mapped_column(String(30), nullable=False, default="dono")
    senha_hash: Mapped[str | None] = mapped_column(String(200))
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Comercio(Base):
    """Um negócio da parceira. É o `empresa_id` que aparece na URL e nos contratos.

    As quatro marcas do combinado alimentam a tela "O que falta": é fato do
    negócio, não configuração de código.
    """

    __tablename__ = "comercio"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    empresa_id: Mapped[str] = _empresa_id()
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    ramo: Mapped[str] = mapped_column(String(80), nullable=False)
    cidade: Mapped[str] = mapped_column(String(120), nullable=False)
    tem_termo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tem_fonte: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    categorias_combinadas: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tem_canal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)


class Avaliacao(Base):
    """Uma avaliação pública já lida. O texto é guardado mascarado.

    `id_origem` é o identificador que a fonte deu. A unicidade com o comércio é
    o que impede a mesma avaliação de ser contada duas vezes quando a coleta roda
    de novo — e ainda deixa duas lojas terem, cada uma, a sua avaliação nº 1.
    """

    __tablename__ = "avaliacao"
    __table_args__ = (
        UniqueConstraint("comercio_id", "id_origem", name="uq_avaliacao_comercio_origem"),
        CheckConstraint("estrelas BETWEEN 1 AND 5", name="ck_avaliacao_estrelas"),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    empresa_id: Mapped[str] = _empresa_id()
    comercio_id: Mapped[str] = mapped_column(String(60), _para_comercio(), nullable=False, index=True)
    id_origem: Mapped[str] = mapped_column(String(200), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    estrelas: Mapped[int] = mapped_column(Integer, nullable=False)
    texto: Mapped[str | None] = mapped_column(Text)
    coletada_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    execucao_coleta_id: Mapped[str | None] = mapped_column(
        String(60), ForeignKey("execucao_coleta.id")
    )


class Classificacao(Base):
    """O assunto que o modelo deu a uma avaliação.

    `categoria_id` nulo é a abstenção: o modelo não teve confiança e disse por quê.
    """

    __tablename__ = "classificacao"
    __table_args__ = (
        UniqueConstraint("avaliacao_id", "versao_modelo_id", name="uq_classificacao_avaliacao"),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    empresa_id: Mapped[str] = _empresa_id()
    avaliacao_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("avaliacao.id", ondelete="CASCADE"), nullable=False, index=True
    )
    categoria_id: Mapped[str | None] = mapped_column(String(30), _para_categoria())
    confianca: Mapped[float] = mapped_column(Float, nullable=False)
    motivo_sem_assunto: Mapped[str | None] = mapped_column(String(120))
    versao_modelo_id: Mapped[str] = mapped_column(
        String(60), ForeignKey("versao_modelo.id"), nullable=False
    )
    criada_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)


class SerieMensal(Base):
    """Quantas reclamações de um assunto num mês. `fechado` separa o mês corrente."""

    __tablename__ = "serie_mensal"
    __table_args__ = (
        UniqueConstraint("comercio_id", "categoria_id", "mes", name="uq_serie_comercio_cat_mes"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[str] = _empresa_id()
    comercio_id: Mapped[str] = mapped_column(String(60), _para_comercio(), nullable=False, index=True)
    categoria_id: Mapped[str] = mapped_column(String(30), _para_categoria(), nullable=False)
    mes: Mapped[date] = mapped_column(Date, nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    fechado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Previsao(Base):
    """A estimativa de um mês: o mais provável e o mínimo e máximo esperados."""

    __tablename__ = "previsao"
    __table_args__ = (
        UniqueConstraint("comercio_id", "categoria_id", "mes", "versao_modelo_id",
                         name="uq_previsao_comercio_cat_mes"),
        CheckConstraint("p10 <= p50 AND p50 <= p90", name="ck_previsao_faixa"),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    empresa_id: Mapped[str] = _empresa_id()
    comercio_id: Mapped[str] = mapped_column(String(60), _para_comercio(), nullable=False, index=True)
    categoria_id: Mapped[str] = mapped_column(String(30), _para_categoria(), nullable=False)
    mes: Mapped[date] = mapped_column(Date, nullable=False)
    p10: Mapped[int] = mapped_column(Integer, nullable=False)
    p50: Mapped[int] = mapped_column(Integer, nullable=False)
    p90: Mapped[int] = mapped_column(Integer, nullable=False)
    versao_modelo_id: Mapped[str] = mapped_column(
        String(60), ForeignKey("versao_modelo.id"), nullable=False
    )
    gerada_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)


class Alerta(Base):
    """Aviso de que um assunto deve crescer."""

    __tablename__ = "alerta"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    empresa_id: Mapped[str] = _empresa_id()
    comercio_id: Mapped[str] = mapped_column(String(60), _para_comercio(), nullable=False, index=True)
    categoria_id: Mapped[str] = mapped_column(String(30), _para_categoria(), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    atual: Mapped[int] = mapped_column(Integer, nullable=False)
    previsao_id: Mapped[str] = mapped_column(String(80), ForeignKey("previsao.id"), nullable=False)
    gerado_em: Mapped[date] = mapped_column(Date, nullable=False)
    situacao: Mapped[str] = mapped_column(String(20), nullable=False, default="aberto")


class VersaoModelo(Base):
    """Um modelo treinado. Leva `empresa_id` porque foi treinado no dado dela."""

    __tablename__ = "versao_modelo"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    empresa_id: Mapped[str] = _empresa_id()
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    treinada_em: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Medidas e régua do treino, em JSON: nenhuma tela lê daqui, a banca sim.
    metricas: Mapped[str | None] = mapped_column(Text)
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ExecucaoColeta(Base):
    """Uma rodada de leitura das avaliações, para saber quando e o que entrou."""

    __tablename__ = "execucao_coleta"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    empresa_id: Mapped[str] = _empresa_id()
    comercio_id: Mapped[str] = mapped_column(String(60), _para_comercio(), nullable=False, index=True)
    iniciada_em: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    terminada_em: Mapped[datetime | None] = mapped_column(DateTime)
    lidas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    novas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="em_andamento")
    erro: Mapped[str | None] = mapped_column(Text)


class Auditoria(Base):
    """Quem fez o quê. A trilha que o Matheus escreve e a banca lê."""

    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[str] = _empresa_id()
    usuario_id: Mapped[str | None] = mapped_column(String(60), ForeignKey("usuario.id"))
    quando: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    acao: Mapped[str] = mapped_column(String(60), nullable=False)
    objeto: Mapped[str] = mapped_column(String(120), nullable=False)
    detalhe: Mapped[str | None] = mapped_column(Text)
