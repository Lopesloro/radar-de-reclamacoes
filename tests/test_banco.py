"""O banco guarda o dado real: isolado por empresa e sem contar avaliação duas vezes.

Tudo em SQLite na memória ou em arquivo temporário. Nenhum teste depende de um
Postgres de pé.
"""

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.banco import consultas, modelo
from app.banco import sessao as fonte
from app.contratos import CATEGORIAS, Alerta, AvaliacaoTela, ResumoComercio, SerieMensal

HOJE = date(2026, 10, 13)

# O mínimo combinado com o time. Faltar uma é defeito.
ENTIDADES = {
    "empresa", "usuario", "comercio", "avaliacao", "categoria", "classificacao",
    "serie_mensal", "previsao", "alerta", "versao_modelo", "execucao_coleta", "auditoria",
}
# A empresa é a raiz do isolamento e a categoria é vocabulário comum às três
# empresas; todas as outras são dado operacional e precisam chegar à empresa.
SEM_EMPRESA = {"empresa", "categoria"}


# ------------------------------------------------------------ banco de teste

def _popular(sessao: Session) -> None:
    """Duas empresas com o mesmo formato, para o isolamento ter o que separar.

    Os `flush()` são de propósito: sem `relationship()`, o SQLAlchemy não deduz a
    ordem de INSERT entre tabelas, e a chave estrangeira do SQLite está ligada.
    """
    for identificador, nome in (("alfa", "Parceira Alfa"), ("beta", "Parceira Beta")):
        sessao.add(modelo.Empresa(id=identificador, nome=nome))
    for ordem, categoria in enumerate(CATEGORIAS):
        sessao.add(modelo.Categoria(id=categoria, nome=categoria.capitalize(), ordem=ordem))
    sessao.flush()

    for empresa_id, comercio_id, nivel in (("alfa", "alfa-pizza", 30), ("beta", "beta-pet", 12)):
        sessao.add(modelo.Comercio(
            id=comercio_id, empresa_id=empresa_id, nome=comercio_id, ramo="Teste",
            cidade="Campinas, SP", tem_termo=True, tem_fonte=True,
            categorias_combinadas=True, tem_canal=False,
        ))
        sessao.add(modelo.VersaoModelo(
            id=f"{empresa_id}-v1", empresa_id=empresa_id, tipo="classificacao",
            nome="tfidf", treinada_em=datetime(2026, 10, 1, 8, 0), ativa=True,
        ))
        sessao.flush()
        for mes_atras in range(12, -1, -1):
            total = 12 * HOJE.year + HOJE.month - 1 - mes_atras
            mes = date(total // 12, total % 12 + 1, 1)
            for i, categoria in enumerate(CATEGORIAS):
                quantidade = nivel - 3 * i + (4 if categoria == "demora" and mes_atras < 4 else 0)
                sessao.add(modelo.SerieMensal(
                    empresa_id=empresa_id, comercio_id=comercio_id, categoria_id=categoria,
                    mes=mes, quantidade=max(0, quantidade), fechado=mes_atras > 0,
                ))
        for categoria in CATEGORIAS:
            for passo in (0, 1):
                sessao.add(modelo.Previsao(
                    id=f"{comercio_id}-{categoria}-{passo}", empresa_id=empresa_id,
                    comercio_id=comercio_id, categoria_id=categoria,
                    mes=date(HOJE.year, HOJE.month + passo, 1),
                    p10=nivel + 4 - 2 * passo, p50=nivel + 8, p90=nivel + 12 + 2 * passo,
                    versao_modelo_id=f"{empresa_id}-v1", gerada_em=datetime(2026, 10, 13, 6, 0),
                ))
        sessao.flush()
        sessao.add(modelo.Alerta(
            id=f"{comercio_id}-demora", empresa_id=empresa_id, comercio_id=comercio_id,
            categoria_id="demora", estado="vai_piorar", atual=nivel,
            previsao_id=f"{comercio_id}-demora-0", gerado_em=HOJE, situacao="aberto",
        ))
        for dia in (2, 9, 16):
            avaliacao = modelo.Avaliacao(
                id=f"{comercio_id}-{dia}", empresa_id=empresa_id, comercio_id=comercio_id,
                id_origem=f"origem-{dia}", data=date(2026, 9, dia), estrelas=2,
                texto="Esperei muito tempo.", coletada_em=datetime(2026, 9, dia, 22, 0),
            )
            sessao.add(avaliacao)
            sessao.flush()
            sessao.add(modelo.Classificacao(
                id=f"{comercio_id}-{dia}-c", empresa_id=empresa_id,
                avaliacao_id=avaliacao.id, categoria_id="demora" if dia > 2 else None,
                confianca=0.9 if dia > 2 else 0.2,
                motivo_sem_assunto=None if dia > 2 else "frase vaga demais",
                versao_modelo_id=f"{empresa_id}-v1", criada_em=datetime(2026, 9, dia, 23, 0),
            ))
    sessao.commit()


@pytest.fixture
def sessao():
    motor = create_engine("sqlite://")
    fonte.ligar_chaves_estrangeiras(motor)
    modelo.Base.metadata.create_all(motor)
    with Session(motor) as aberta:
        _popular(aberta)
        yield aberta


# ------------------------------------------------------------ formato das tabelas

def test_as_entidades_combinadas_existem():
    assert ENTIDADES <= set(modelo.Base.metadata.tables)


def test_todo_dado_operacional_chega_na_empresa():
    """Sem este caminho, uma consulta não tem como filtrar por empresa."""
    for nome, tabela in modelo.Base.metadata.tables.items():
        if nome in SEM_EMPRESA:
            continue
        alvos = {
            chave.column.table.name
            for coluna in tabela.columns if coluna.name == "empresa_id"
            for chave in coluna.foreign_keys
        }
        assert alvos == {"empresa"}, f"{nome} não aponta para empresa"


def test_a_mesma_avaliacao_nao_entra_duas_vezes(sessao):
    comum = dict(
        empresa_id="alfa", comercio_id="alfa-pizza", id_origem="origem-2",
        data=date(2026, 9, 2), estrelas=1, texto="repetida",
        coletada_em=datetime(2026, 9, 2, 22, 0),
    )
    sessao.add(modelo.Avaliacao(id="alfa-pizza-repetida", **comum))
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_o_mesmo_identificador_de_origem_vale_em_outro_comercio(sessao):
    """A unicidade é por comércio: duas lojas podem ter a avaliação nº 1 cada uma."""
    donos = sessao.scalars(
        select(modelo.Avaliacao.comercio_id).where(modelo.Avaliacao.id_origem == "origem-2")
    ).all()
    assert sorted(donos) == ["alfa-pizza", "beta-pet"]


# ------------------------------------------------------------ isolamento

@pytest.mark.parametrize("empresa_id, comercio_id", [("alfa", "alfa-pizza"), ("beta", "beta-pet")])
def test_consulta_devolve_so_a_empresa_pedida(sessao, empresa_id, comercio_id):
    negocios = consultas.comercios(sessao, empresa_id)
    assert [c.empresa_id for c in negocios] == [comercio_id]
    assert all(isinstance(c, ResumoComercio) for c in negocios)
    assert all(a.empresa_id == comercio_id for a in consultas.alertas(sessao, empresa_id))


def test_empresa_nao_le_comercio_da_outra(sessao):
    assert consultas.serie(sessao, "alfa", "beta-pet", "demora", HOJE) is None
    assert consultas.avaliacoes(sessao, "alfa", "beta-pet") == ()


def test_empresa_desconhecida_nao_ve_nada(sessao):
    assert consultas.comercios(sessao, "nao-existe") == ()
    assert consultas.alertas(sessao, "nao-existe") == ()


# ------------------------------------------------------------ formato do contrato

def test_a_serie_sai_no_formato_que_a_tela_ja_consome(sessao):
    s = consultas.serie(sessao, "alfa", "alfa-pizza", "demora", HOJE)
    assert isinstance(s, SerieMensal)
    assert len(s.meses) == 12
    assert s.meses == tuple(sorted(s.meses))
    assert s.parcial[0] == date(HOJE.year, HOJE.month, 1)
    assert 0 < s.parcial_fracao <= 1
    assert len(s.previsoes) == 2
    assert s.previsoes[0].mes < s.previsoes[1].mes
    assert s.previsoes[0].p10 <= s.previsoes[0].p50 <= s.previsoes[0].p90


def test_o_cartao_do_resumo_vem_com_as_contas_feitas(sessao):
    cartao = consultas.comercios(sessao, "alfa")[0]
    assert cartao.mes_referencia == date(2026, 9, 1)
    assert cartao.avaliacoes_lidas == 3
    assert cartao.sem_assunto == 1
    assert cartao.nota_media == 2.0
    assert cartao.mais_reclamado == "demora"
    assert cartao.vai_crescer in CATEGORIAS
    assert cartao.etapas_total == 7
    assert cartao.etapas_concluidas < cartao.etapas_total


def test_avaliacao_sem_assunto_chega_com_o_motivo(sessao):
    lista = consultas.avaliacoes(sessao, "alfa", "alfa-pizza")
    assert all(isinstance(a, AvaliacaoTela) for a in lista)
    assert [a.data for a in lista] == sorted((a.data for a in lista), reverse=True)
    vaga = next(a for a in lista if a.categoria is None)
    assert vaga.motivo_sem_assunto
    assert vaga.certeza == "baixa"


def test_o_aviso_carrega_a_faixa_da_previsao(sessao):
    aviso = consultas.alertas(sessao, "alfa")[0]
    assert isinstance(aviso, Alerta)
    assert aviso.previsto.p10 <= aviso.previsto.p50 <= aviso.previsto.p90
    assert aviso.estado in ("vai_piorar", "fique_de_olho", "normal")


# ------------------------------------------------------------ troca em tempo de execução

def test_sem_database_url_nada_muda(monkeypatch):
    """Requisito duro: o site no ar continua lendo app/falsos.py."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert fonte.usar_banco() is False
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        fonte.motor()

    from app import servicos
    assert servicos.DADOS_DE_DEMONSTRACAO
    # A contagem sem empresa é a da página pública; a lista por empresa exige o filtro.
    assert servicos.quantos_negocios() == 3
    assert len(servicos.comercios("bella-massa")) == 1


def test_com_database_url_o_banco_entra(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'radar.sqlite3'}")
    fonte.esquecer()
    assert fonte.usar_banco() is True
    modelo.Base.metadata.create_all(fonte.motor())
    with fonte.Sessao() as aberta:
        _popular(aberta)
        assert len(consultas.comercios(aberta, "alfa")) == 1
    fonte.esquecer()


def test_postgres_do_render_vira_url_que_o_sqlalchemy_entende(monkeypatch):
    """O Render entrega `postgres://`; o SQLAlchemy 2 só aceita `postgresql+psycopg://`."""
    monkeypatch.setenv("DATABASE_URL", "postgres://u:s@host:5432/radar")
    assert fonte.url().startswith("postgresql+psycopg://")


# ------------------------------------------------------------ migração

def test_a_migracao_cria_o_mesmo_esquema_das_entidades(tmp_path, monkeypatch):
    """Se a entidade mudar e ninguém gerar a migração, este teste quebra."""
    from alembic.config import Config

    from alembic import command
    from app.banco import RAIZ

    arquivo = tmp_path / "migrado.sqlite3"
    configuracao = Config(str(RAIZ / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ / "alembic"))
    configuracao.set_main_option("sqlalchemy.url", f"sqlite:///{arquivo}")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    command.upgrade(configuracao, "head")

    migrado = inspect(create_engine(f"sqlite:///{arquivo}"))
    esperado = create_engine("sqlite://")
    modelo.Base.metadata.create_all(esperado)
    direto = inspect(esperado)

    assert set(migrado.get_table_names()) - {"alembic_version"} == set(direto.get_table_names())
    for tabela in direto.get_table_names():
        assert ({c["name"] for c in migrado.get_columns(tabela)}
                == {c["name"] for c in direto.get_columns(tabela)}), tabela


def test_a_migracao_deixa_o_vocabulario_de_assuntos_pronto(tmp_path, monkeypatch):
    from alembic.config import Config

    from alembic import command
    from app.banco import RAIZ

    arquivo = tmp_path / "assuntos.sqlite3"
    configuracao = Config(str(RAIZ / "alembic.ini"))
    configuracao.set_main_option("script_location", str(RAIZ / "alembic"))
    configuracao.set_main_option("sqlalchemy.url", f"sqlite:///{arquivo}")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    command.upgrade(configuracao, "head")

    with create_engine(f"sqlite:///{arquivo}").connect() as conexao:
        assuntos = conexao.execute(text("SELECT id FROM categoria ORDER BY ordem")).scalars().all()
    assert tuple(assuntos) == CATEGORIAS
