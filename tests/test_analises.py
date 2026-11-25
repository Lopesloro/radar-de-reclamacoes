"""As contas de "Por quê?", "E se?" e "Testes", sem banco: mesma entrada, mesmo número.

O que estes testes protegem:

1. **Por quê?** acha a causa plantada e descarta a mudança que não mexeu em nada,
   e não testa nada quando há pouca reclamação.
2. **E se?** bate com a fórmula clássica da fila (Erlang C), que é a régua dele,
   e pôr gente a mais nunca aumenta a espera.
3. **Testes** sorteia equilibrado por dia da semana, o selo denuncia plano
   alterado, e o veredito só sai com dado suficiente.
"""

import random
from datetime import date, datetime, timedelta

import pytest

from app.contratos import Cenario, EventoDiario, PlanoExperimento, Turno
from app.modelos import causas, fila
from app.modelos import experimento as teste

HOJE = date(2026, 11, 26)


# ------------------------------------------------------------ Por quê?

def _historico(semente=1, mudanca=date(2026, 9, 1), antes=0.2, depois=0.7):
    """Um ano de avaliações: três por dia sem assunto, e demora que sobe na data da mudança."""
    sorteio = random.Random(semente)
    avaliacoes = []
    for atras in range(365):
        dia = HOJE - timedelta(days=atras)
        avaliacoes += [causas.AvaliacaoClassificada(dia, None, None)] * 3
        if sorteio.random() < (depois if dia >= mudanca else antes):
            avaliacoes.append(causas.AvaliacaoClassificada(dia, "demora", "Demorou demais"))
    return avaliacoes


EVENTOS = (
    EventoDiario("e1", "x", date(2026, 9, 1), "equipe", "Saiu um garçom da noite"),
    EventoDiario("e2", "x", date(2026, 4, 1), "produto", "Cardápio novo"),
)


def test_benjamini_hochberg_confere_com_a_conta_a_mao():
    q = causas.benjamini_hochberg([0.01, 0.04, 0.03, 0.20])
    assert q == pytest.approx([0.04, 0.0533, 0.0533, 0.20], abs=1e-3)
    assert causas.benjamini_hochberg([]) == []


def test_acha_a_causa_plantada_e_descarta_a_que_nao_mexeu():
    resultado = causas.investigar(_historico(), EVENTOS, "demora", HOJE)
    assert resultado.estado == "concluida"
    por_evento = {("garçom" in h.frase, "Cardápio" in h.frase): h for h in resultado.hipoteses
                  if h.origem == "diario"}
    garcom, cardapio = por_evento[(True, False)], por_evento[(False, True)]
    assert garcom.veredito == "sustentada" and garcom.depois_semana > garcom.antes_semana
    assert cardapio.veredito != "sustentada"
    assert resultado.hipoteses[0] is garcom, "a provável causa vem primeiro"
    assert not resultado.usou_ia


def test_com_pouca_reclamacao_nao_testa_nada_e_diz_quanto_falta():
    poucas = [causas.AvaliacaoClassificada(HOJE - timedelta(days=d), "demora", "x") for d in range(3)]
    resultado = causas.investigar(poucas, EVENTOS, "demora", HOJE)
    assert resultado.estado == "dados_insuficientes" and resultado.hipoteses == ()
    assert "3 no total" in resultado.motivo


def test_mudanca_recente_demais_nao_vira_hipotese():
    recente = (EventoDiario("e3", "x", HOJE - timedelta(days=5), "preco", "Subiu o preço"),)
    resultado = causas.investigar(_historico(), recente, "demora", HOJE)
    assert all(h.origem != "diario" for h in resultado.hipoteses)


def test_mesma_entrada_mesmo_resultado():
    assert causas.investigar(_historico(), EVENTOS, "demora", HOJE).hipoteses == \
        causas.investigar(_historico(), EVENTOS, "demora", HOJE).hipoteses


# ------------------------------------------------------------ E se?

def test_a_simulacao_bate_com_a_formula_da_fila():
    """A régua do simulador: num turno estável, a espera simulada fica perto da de Erlang C."""
    simulada = fila.simular_turno(80, 6.0, 3, 11, repeticoes=200).espera_media
    teoria = fila.erlang_c(80 / (fila.HORAS_DO_TURNO * 60), 6.0, 3)
    assert simulada == pytest.approx(teoria, rel=0.15)


def test_fila_que_nao_para_de_crescer_tem_espera_infinita_na_formula():
    assert fila.erlang_c(1.0, 6.0, 3) == float("inf")


def _semana(equipe_noite=2):
    return tuple(Turno(d, p, equipe_noite if p == "noite" else 3, 95 if p == "noite" else 40, 6.0, 18.0)
                 for d in range(7) for p in ("tarde", "noite"))


def test_gente_a_mais_nunca_aumenta_a_espera_e_custa_o_que_deve():
    mudancas = tuple(Turno(d, "noite", 3, 95, 6.0, 18.0) for d in range(7))
    resultado = fila.simular(_semana(), Cenario("x", "demora", mudancas), reclamacoes_hoje=15)
    assert resultado.confiavel
    assert resultado.espera_cenario_min < resultado.espera_atual_min
    assert resultado.reclamacoes_cenario < resultado.reclamacoes_atual
    assert resultado.minimo <= resultado.reclamacoes_cenario <= resultado.maximo
    assert resultado.custo_extra_mes == pytest.approx(7 * 18.0 * fila.HORAS_DO_TURNO * fila.SEMANAS_NO_MES)


def test_sem_mudanca_o_cenario_e_igual_a_hoje():
    resultado = fila.simular(_semana(), Cenario("x", "demora", ()), reclamacoes_hoje=15)
    assert resultado.reclamacoes_cenario == resultado.reclamacoes_atual
    assert resultado.custo_extra_mes == 0


def test_sem_turno_cadastrado_nao_inventa():
    resultado = fila.simular((), Cenario("x", "demora", ()), reclamacoes_hoje=15)
    assert not resultado.confiavel and "turno" in resultado.motivo


# ------------------------------------------------------------ Testes

def test_o_sorteio_e_equilibrado_por_dia_da_semana_e_repetivel():
    com, sem = teste.sortear(date(2026, 12, 1), 28, semente=5)
    assert len(com) == len(sem) == 14 and not set(com) & set(sem)
    for dia_da_semana in range(7):
        assert sum(1 for d in com if d.weekday() == dia_da_semana) == 2
    assert teste.sortear(date(2026, 12, 1), 28, semente=5) == (com, sem)


def _plano(inicio=date(2026, 10, 1), dias=28, semente=3):
    com, sem = teste.sortear(inicio, dias, semente=semente)
    fim = inicio + timedelta(days=dias - 1)
    selado = datetime(2026, 9, 30, 20, 0)
    return PlanoExperimento("p1", "x", "demora", "Uma pessoa a mais", inicio, fim, com, sem, 5.0,
                            teste.selar("demora", "Uma pessoa a mais", inicio, fim, com, selado),
                            selado, "em_andamento")


def test_o_selo_denuncia_plano_alterado_depois_do_sorteio():
    plano = _plano()
    assert teste.selo_confere(plano)
    trocado = PlanoExperimento(**{**plano.__dict__, "dias_com_acao": plano.dias_sem_acao,
                                  "dias_sem_acao": plano.dias_com_acao})
    assert not teste.selo_confere(trocado)


def test_mudanca_que_corta_as_reclamacoes_funciona():
    plano = _plano()
    datas = [d for d in plano.dias_sem_acao for _ in range(2)] + list(plano.dias_com_acao[:3])
    resultado = teste.analisar(plano, {d: True for d in plano.dias_com_acao}, datas, HOJE)
    assert resultado.veredito == "funcionou"
    assert resultado.media_com < resultado.media_sem and resultado.efeito_mes < 0
    assert resultado.adesao == 1.0


def test_antes_da_metade_do_teste_ainda_nao_da_para_saber():
    plano = _plano(inicio=HOJE - timedelta(days=5))
    datas = [d for d in plano.dias_sem_acao if d < HOJE for _ in range(3)]
    resultado = teste.analisar(plano, {}, datas, HOJE)
    assert resultado.veredito == "ainda_nao_da_para_saber"


def test_antes_do_primeiro_dia_nao_ha_resultado():
    assert teste.analisar(_plano(inicio=HOJE + timedelta(days=1)), {}, [], HOJE) is None
