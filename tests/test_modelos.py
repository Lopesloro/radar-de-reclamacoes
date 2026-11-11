"""A régua. Os dois modelos têm de ganhar do palpite mais simples.

Se o classificador perder de "responder sempre o assunto mais comum", ou se a
previsão perder de "repetir o mês anterior", este arquivo quebra a build. É o
que a regra do CLAUDE.md pede, e é o único teste que não pode ser desligado.
"""

from datetime import date

import pytest

from app.banco import consultas
from app.banco import sessao as banco
from app.contratos import CATEGORIAS, AcuraciaClassificacao, AcuraciaPrevisao
from app.modelos import LIMITE_CONFIANCA, amostras, classificador, previsao
from tests import dados


@pytest.fixture(scope="module")
def series(banco_de_teste):
    """Os meses fechados que estão no banco de teste, postos lá pelo motor de coleta.

    Antes isto vinha de um gerador de séries fictícias. Agora vem da mesma
    consulta que a tela usa, o que faz este teste medir a régua no caminho de
    verdade: se o motor contar errado, a medida cai aqui.
    """
    with banco.Sessao() as sessao:
        achadas = tuple(
            serie
            for empresa, *_ in dados.EMPRESAS
            for serie in consultas.series_fechadas(sessao, empresa)
        )
    assert achadas, "o banco de teste precisa ter séries para a régua ser medida"
    return achadas


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
def conferida(series):
    return previsao.validar(series)


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

def test_a_faixa_contem_o_mais_provavel(series):
    for _, historico in series:
        faixa = previsao.prever(historico)
        assert faixa.p10 <= faixa.p50 <= faixa.p90
        assert faixa.p10 >= 0


def test_a_faixa_abre_quando_o_mes_esta_mais_longe(series):
    for _, historico in series:
        perto = previsao.prever(historico, passos=1)
        longe = previsao.prever(historico, passos=2)
        assert longe.p90 - longe.p10 >= perto.p90 - perto.p10


def test_a_faixa_cobre_o_que_promete(conferida):
    """A faixa é de 80%: cobrir muito menos que isso é faixa mentirosa."""
    assert 0.7 <= conferida.cobertura <= 1.0


def test_a_conferencia_usa_origem_movel_e_nao_sorteio(conferida, series):
    """Uma janela por mês conferível de cada série, da mais antiga para a mais nova."""
    esperadas = sum(max(0, len(h) - previsao.MINIMO_TREINO) for _, h in series)
    assert conferida.janelas == esperadas
    meses = [mes for mes, _, _ in conferida.pontos]
    assert meses == sorted(meses)
    assert len(meses) == len(series[0][1]) - previsao.MINIMO_TREINO


def test_a_conferencia_nao_ve_o_futuro(conferida, series):
    """Cada ponto tem de sair do histórico até ali, e de nada depois dele."""
    historico = next(h for nome, h in series if nome == conferida.exemplo)
    datas = [mes for mes, _ in historico]
    for mes, previsto, realizado in conferida.pontos:
        i = datas.index(mes)
        assert i >= previsao.MINIMO_TREINO
        assert previsao.prever(historico[:i]).p50 == previsto
        assert historico[i][1] == realizado


def test_historico_curto_nao_vira_previsao():
    with pytest.raises(ValueError, match="mínimo"):
        previsao.prever([(date(2026, 1, 1), 10), (date(2026, 2, 1), 11)])


# ------------------------------------------------------------ a qualidade do aviso

# O estudo que mediu o aviso em seis formas de série. Ele existe porque o erro
# médio da estimativa empata com a régua, e empatar no número do meio não
# significa avisar igual: o aviso usa a faixa, que a régua não tem. Reproduzir
# este teste é reproduzir a tabela que está na tela "Dá para confiar?".
FORMAS = ("plana", "sobe", "desce", "degrau", "sazonal", "pico")


def _serie_de_forma(forma: str, meses: int, semente: int) -> tuple[tuple[date, int], ...]:
    import math
    import random

    sorteio = random.Random(semente)
    base, valores = 12, []
    for i in range(meses):
        if forma == "plana":
            centro = base
        elif forma == "sobe":
            centro = base + i * 1.2
        elif forma == "desce":
            centro = base + 8 - i * 0.8
        elif forma == "degrau":
            centro = base + (10 if i >= meses - 5 else 0)
        elif forma == "sazonal":
            centro = base + 6 * math.sin(i / 12 * 2 * math.pi)
        else:
            centro = base + (14 if i == meses - 6 else 0)
        valores.append(max(0, round(centro + sorteio.gauss(0, 2.2))))
    return tuple((date(2025 + i // 12, i % 12 + 1, 1), q) for i, q in enumerate(valores))


@pytest.fixture(scope="module")
def estudo_do_aviso():
    series = [
        (f"{forma}-{semente}-{meses}", _serie_de_forma(forma, meses, semente))
        for forma in FORMAS
        for semente in range(1, 13)
        for meses in (18, 30)
    ]
    return previsao.avaliar_avisos(series), previsao.validar(series)


def test_o_aviso_ganha_da_regua_de_alarme(estudo_do_aviso):
    """A régua aqui é "avise sempre que o último mês subiu".

    É o teste que sustenta o que a tela promete. O sistema avisa menos e acerta
    mais: se um dia ele passar a acertar menos que a régua, a tela está mentindo
    e esta linha quebra a build.
    """
    aviso, _ = estudo_do_aviso
    assert aviso["acerto"] > aviso["acerto_regua"] * 2, (
        f"o aviso forte acerta {aviso['acerto']} e a régua {aviso['acerto_regua']}"
    )
    assert aviso["acerto_atento"] > aviso["acerto_regua"] * 1.5
    assert aviso["avisos_atento"] < aviso["avisos_regua"] / 2, (
        "o aviso intermediário precisa falar menos que a régua, não mais"
    )


def test_a_faixa_cobre_oitenta_por_cento_no_estudo(estudo_do_aviso):
    """A faixa promete 80%. Entre 0,78 e 0,90 é promessa cumprida; 0,73 não era."""
    _, acuracia = estudo_do_aviso
    assert 0.78 <= acuracia.cobertura <= 0.90, f"cobertura de {acuracia.cobertura}"


def test_a_estimativa_nao_perde_feio_da_regua(estudo_do_aviso):
    """Empatar é o resultado honesto; perder por muito seria defeito.

    Está escrito como "não perde feio" e não como "ganha" de propósito: medido,
    o erro é 2,66 contra 2,65 da régua. Um teste que exigisse ganhar só poderia
    ser satisfeito mexendo na medida.
    """
    _, acuracia = estudo_do_aviso
    assert acuracia.erro_medio <= acuracia.erro_medio_regua * 1.05
