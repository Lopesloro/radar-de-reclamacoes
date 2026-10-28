"""A régua. Os dois modelos têm de ganhar do palpite mais simples.

Se o classificador perder de "responder sempre o assunto mais comum", ou se a
previsão perder de "repetir o mês anterior", este arquivo quebra a build. É o
que a regra do CLAUDE.md pede, e é o único teste que não pode ser desligado.
"""

from datetime import date

import pytest

from app import falsos
from app.contratos import CATEGORIAS, AcuraciaClassificacao, AcuraciaPrevisao
from app.modelos import LIMITE_CONFIANCA, amostras, classificador, previsao

# Doze meses fechados de cinco assuntos em três negócios: a mesma base que a tela usa.
SERIES = tuple(
    (f"{s.categoria} em {c.nome}", s.meses)
    for c in falsos.comercios()
    for s in falsos.series(c.empresa_id)
)


@pytest.fixture(scope="module")
def separadas():
    return amostras.separar()


@pytest.fixture(scope="module")
def modelo(separadas):
    treino, _ = separadas
    return classificador.treinar(treino)


@pytest.fixture(scope="module")
def acerto(modelo, separadas):
    _, teste = separadas
    return classificador.medir(modelo, teste)


@pytest.fixture(scope="module")
def conferida():
    return previsao.validar(SERIES)


# ------------------------------------------------------------ a régua, item por item

def test_o_classificador_ganha_da_regua(acerto):
    """Régua: responder sempre o assunto mais comum."""
    assert isinstance(acerto, AcuraciaClassificacao)
    assert acerto.categoria_regua in CATEGORIAS
    assert acerto.f1_macro > acerto.f1_macro_regua
    assert acerto.acerto_geral > acerto.acerto_regua


def test_a_previsao_ganha_da_regua(conferida):
    """Régua: repetir o número do mês anterior."""
    assert isinstance(conferida, AcuraciaPrevisao)
    assert conferida.erro_medio < conferida.erro_medio_regua


# ------------------------------------------------------------ classificação

def test_sai_um_f1_por_assunto(acerto):
    assert {linha.categoria for linha in acerto.linhas} == set(CATEGORIAS)
    for linha in acerto.linhas:
        assert 0.0 <= linha.precisao <= 1.0
        assert 0.0 <= linha.recall <= 1.0
        assert 0.0 <= linha.f1 <= 1.0
        assert linha.amostra > 0
    assert acerto.amostra == sum(linha.amostra for linha in acerto.linhas)


def test_o_limite_de_confianca_e_o_que_manda_na_abstencao(modelo, separadas):
    _, teste = separadas
    textos = [texto for texto, _ in teste]
    assert all(modelo.prever(t, limite=0.0)[0] is not None for t in textos)
    assert all(modelo.prever(t, limite=1.01)[0] is None for t in textos)


def test_frase_sem_sinal_nenhum_nao_recebe_assunto(modelo):
    """Texto fora do vocabulário não pode sair com assunto: melhor dizer que não sabe."""
    assunto, confianca = modelo.prever("blá blá zzz qqq")
    assert assunto is None
    assert confianca < LIMITE_CONFIANCA


def test_abster_melhora_o_acerto(modelo, separadas):
    """Se abster-se não melhora a precisão do que sobra, a abstenção não serve para nada."""
    _, teste = separadas
    respondidas = [(m, c) for m, c in ((modelo.prever(t), c) for t, c in teste) if m[0]]
    assert respondidas, "o modelo se absteve de tudo"
    acerto_respondidas = sum(1 for (a, _), c in respondidas if a == c) / len(respondidas)
    acerto_geral = sum(1 for t, c in teste if modelo.prever(t)[0] == c) / len(teste)
    assert acerto_respondidas >= acerto_geral


def test_a_frase_vaga_e_o_elogio_tendem_a_abstencao(modelo):
    """Não é reclamação de assunto nenhum: o certo é não forçar um."""
    sem_assunto = amostras.sem_assunto()
    abstidas = sum(1 for texto in sem_assunto if modelo.prever(texto)[0] is None)
    assert abstidas > len(sem_assunto) / 2


# ------------------------------------------------------------ previsão

def test_a_faixa_contem_o_mais_provavel():
    for _, historico in SERIES:
        faixa = previsao.prever(historico)
        assert faixa.p10 <= faixa.p50 <= faixa.p90
        assert faixa.p10 >= 0


def test_a_faixa_abre_quando_o_mes_esta_mais_longe():
    for _, historico in SERIES:
        perto = previsao.prever(historico, passos=1)
        longe = previsao.prever(historico, passos=2)
        assert longe.p90 - longe.p10 >= perto.p90 - perto.p10


def test_a_faixa_cobre_o_que_promete(conferida):
    """A faixa é de 80%: cobrir muito menos que isso é faixa mentirosa."""
    assert 0.7 <= conferida.cobertura <= 1.0


def test_a_conferencia_usa_origem_movel_e_nao_sorteio(conferida):
    """Uma janela por mês conferível de cada série, da mais antiga para a mais nova."""
    por_serie = len(SERIES[0][1]) - previsao.MINIMO_TREINO
    assert conferida.janelas == por_serie * len(SERIES)
    meses = [mes for mes, _, _ in conferida.pontos]
    assert meses == sorted(meses)
    assert len(meses) == por_serie


def test_a_conferencia_nao_ve_o_futuro(conferida):
    """Cada ponto tem de sair do histórico até ali, e de nada depois dele."""
    historico = next(h for nome, h in SERIES if nome == conferida.exemplo)
    datas = [mes for mes, _ in historico]
    for mes, previsto, realizado in conferida.pontos:
        i = datas.index(mes)
        assert i >= previsao.MINIMO_TREINO
        assert previsao.prever(historico[:i]).p50 == previsto
        assert historico[i][1] == realizado


def test_historico_curto_nao_vira_previsao():
    with pytest.raises(ValueError, match="mínimo"):
        previsao.prever([(date(2026, 1, 1), 10), (date(2026, 2, 1), 11)])
