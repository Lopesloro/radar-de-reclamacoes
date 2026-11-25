"""O banco guarda o dado real: isolado por empresa e sem contar avaliação duas vezes.

Tudo em PostgreSQL, o mesmo banco da produção: cada teste que precisa de banco
ganha um banco novo e vazio (`tests/postgres.py`), criado pelo script
`app/banco/esquema.sql`, que é o mesmo que o serviço roda na partida.
"""

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.banco import consultas, esquema, modelo
from app.banco import sessao as fonte
from app.contratos import CATEGORIAS, Alerta, AvaliacaoTela, ResumoComercio, SerieMensal
from tests import postgres

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
    ordem de INSERT entre tabelas, e a chave estrangeira do Postgres recusa a
    linha que chega antes da tabela de que depende.
    """
    for identificador, nome in (("alfa", "Parceira Alfa"), ("beta", "Parceira Beta")):
        sessao.add(modelo.Empresa(id=identificador, nome=nome))
    # Os cinco assuntos já vêm do script do banco (app/banco/esquema.sql).
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
def banco_vazio():
    """Um banco Postgres novo, com as tabelas do script e nenhum dado além dos assuntos."""
    with postgres.banco_novo() as endereco:
        motor = create_engine(endereco)
        esquema.criar(motor)
        yield motor
        motor.dispose()


@pytest.fixture
def sessao(banco_vazio):
    with Session(banco_vazio) as aberta:
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

def test_sem_database_url_o_sistema_devolve_vazio_e_nao_inventa(monkeypatch):
    """Requisito duro: sem banco, toda leitura é vazia.

    Na versão anterior o sistema caía num gerador de dados fictícios quando não
    havia banco. Isso foi removido: tela com número inventado é pior que tela
    vazia, porque o dono decide em cima dela. Agora a falta de banco aparece
    como falta de banco.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    fonte.esquecer()
    assert fonte.usar_banco() is False
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        fonte.motor()

    from app import servicos
    assert servicos.tem_banco() is False
    assert servicos.quantos_negocios() == 0
    assert servicos.comercios("bella-massa") == ()
    assert servicos.alertas("bella-massa") == ()
    assert servicos.serie("bella-massa", "bella-massa", "demora") is None
    assert servicos.tem_dados("bella-massa") is False
    fonte.esquecer()


def test_com_database_url_o_banco_entra(monkeypatch):
    endereco = postgres.criar()
    monkeypatch.setenv("DATABASE_URL", endereco)
    fonte.esquecer()
    assert fonte.usar_banco() is True
    esquema.criar(fonte.motor())
    with fonte.Sessao() as aberta:
        _popular(aberta)
        assert len(consultas.comercios(aberta, "alfa")) == 1
    fonte.esquecer()
    postgres.apagar(endereco)


def test_postgres_do_render_vira_url_que_o_sqlalchemy_entende(monkeypatch):
    """O Render entrega `postgres://`; o SQLAlchemy 2 só aceita `postgresql+psycopg://`."""
    monkeypatch.setenv("DATABASE_URL", "postgres://u:s@host:5432/radar")
    assert fonte.url().startswith("postgresql+psycopg://")


# ------------------------------------------------------------ o script do banco

def test_o_script_sql_cria_o_mesmo_esquema_do_modelo(banco_vazio):
    """Se a tabela mudar em app/banco/modelo.py e ninguém mudar o esquema.sql, este teste quebra."""
    criado = inspect(banco_vazio)
    assert set(criado.get_table_names()) == set(modelo.Base.metadata.tables)
    for nome, tabela in modelo.Base.metadata.tables.items():
        colunas = {c["name"]: c for c in criado.get_columns(nome)}
        assert set(colunas) == {c.name for c in tabela.columns}, nome
        for coluna in tabela.columns:
            assert colunas[coluna.name]["nullable"] == coluna.nullable, f"{nome}.{coluna.name}"
            tamanho = getattr(coluna.type, "length", None)
            if tamanho:
                assert colunas[coluna.name]["type"].length == tamanho, f"{nome}.{coluna.name}"


def test_o_script_deixa_os_cinco_assuntos_prontos(banco_vazio):
    with banco_vazio.connect() as conexao:
        assuntos = conexao.execute(text("SELECT id FROM categoria ORDER BY ordem")).scalars().all()
    assert tuple(assuntos) == CATEGORIAS


def test_rodar_o_script_de_novo_nao_apaga_nem_duplica_nada(banco_vazio):
    """O serviço roda o script a cada partida: a segunda vez não pode mexer no que existe."""
    with Session(banco_vazio) as aberta:
        _popular(aberta)
    esquema.criar(banco_vazio)
    esquema.criar(banco_vazio)
    with banco_vazio.connect() as conexao:
        assert conexao.execute(text("SELECT count(*) FROM empresa")).scalar() == 2
        assert conexao.execute(text("SELECT count(*) FROM categoria")).scalar() == 5


def test_o_tamanho_da_coluna_de_senha_cabe_o_hash_argon2(banco_vazio):
    """Defeito real: com VARCHAR(200) o hash era cortado e ninguém entrava. Só o Postgres mostra."""
    from app.seguranca import senha

    with Session(banco_vazio) as aberta:
        aberta.add(modelo.Empresa(id="e1", nome="Empresa"))
        aberta.flush()
        aberta.add(modelo.Usuario(id="u1", empresa_id="e1", email="dono", nome="Dono",
                                  papel="dono", senha_hash=senha.gerar_hash("uma senha longa o bastante")))
        aberta.commit()
        gravado = aberta.get(modelo.Usuario, "u1").senha_hash
    assert senha.conferir("uma senha longa o bastante", gravado)


def test_o_assunto_em_alta_desempata_pelo_tamanho_e_nao_pelo_alfabeto(banco_vazio, monkeypatch):
    """Defeito real de produção, visto na tela antes de ser visto no código.

    Dois assuntos crescendo a mesma quantidade: um com 19 reclamações no mês e
    outro com 1. O desempate era pela ordem alfabética do nome do assunto, então
    "qualidade" (1 reclamação) ganhava de "demora" (19). A tela dizia "a demora é
    o que mais incomoda" no gráfico e abria a estimativa em qualidade.
    """
    monkeypatch.setenv("DATABASE_URL", banco_vazio.url.render_as_string(hide_password=False))
    fonte.esquecer()

    with fonte.Sessao() as sessao:
        sessao.add(modelo.Empresa(id="e1", nome="Empresa"))
        sessao.flush()
        sessao.add(modelo.Comercio(id="c1", empresa_id="e1", nome="Negócio",
                                   ramo="Teste", cidade="Campinas, SP"))
        sessao.add(modelo.VersaoModelo(id="v1", empresa_id="e1", tipo="previsao",
                                       nome="teste", treinada_em=datetime.now(), ativa=True))
        # O flush aqui não é zelo: sem `relationship()` no modelo, o SQLAlchemy não
        # conhece a dependência entre as tabelas e não garante a ordem dos INSERT.
        # Sem este flush, `serie_mensal` pode entrar antes de `categoria` e a chave
        # estrangeira falha. Ver a nota em app/banco/modelo.py.
        sessao.flush()
        # Outubro fechado: demora com 19, qualidade com 1, o resto com zero.
        quantidades = {"demora": 19, "qualidade": 1, "atendimento": 0,
                       "preco": 0, "ambiente": 0}
        for categoria, quantas in quantidades.items():
            sessao.add(modelo.SerieMensal(empresa_id="e1", comercio_id="c1",
                                          categoria_id=categoria, mes=date(2026, 10, 1),
                                          quantidade=quantas, fechado=True))
        # Novembro estimado: as duas crescem exatamente 1.
        for categoria, quantas in (("demora", 20), ("qualidade", 2)):
            sessao.add(modelo.Previsao(
                id=f"p-{categoria}", empresa_id="e1", comercio_id="c1",
                categoria_id=categoria, mes=date(2026, 11, 1),
                p10=quantas - 1, p50=quantas, p90=quantas + 1, versao_modelo_id="v1",
            ))
        sessao.add(modelo.Avaliacao(id="a1", empresa_id="e1", comercio_id="c1",
                                    id_origem="o1", data=date(2026, 10, 5), estrelas=2,
                                    texto="Esperei demais"))
        sessao.commit()

    with fonte.Sessao() as sessao:
        cartao = consultas.comercios(sessao, "e1")[0]
    fonte.esquecer()

    assert cartao.vai_crescer == "demora", (
        f"o assunto em alta saiu {cartao.vai_crescer!r}: o desempate voltou para o alfabeto"
    )
    assert cartao.vai_crescer_de == 19
    assert cartao.mais_reclamado == "demora"
