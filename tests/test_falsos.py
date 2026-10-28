"""Os dados de mentira precisam ter o formato dos contratos e ser sempre iguais."""

import pytest

from app import falsos
from app.contratos import (
    CATEGORIAS,
    Alerta,
    Investigacao,
    PlanoExperimento,
    ResultadoSimulacao,
    ResumoComercio,
    SerieMensal,
)

EMPRESAS = [e[0] for e in falsos.EMPRESAS]


def test_comercios_devolvem_o_tipo_do_contrato():
    for c in falsos.comercios():
        assert isinstance(c, ResumoComercio)
        assert c.estado in ("vai_piorar", "fique_de_olho", "normal")


@pytest.mark.parametrize("empresa", EMPRESAS)
@pytest.mark.parametrize("categoria", CATEGORIAS)
def test_faixa_contem_o_mais_provavel(empresa, categoria):
    serie = falsos.serie(empresa, categoria)
    assert isinstance(serie, SerieMensal)
    for p in serie.previsoes:
        assert p.p10 <= p.p50 <= p.p90


@pytest.mark.parametrize("empresa", EMPRESAS)
def test_faixa_abre_com_o_tempo(empresa):
    for serie in falsos.series(empresa):
        primeira, segunda = serie.previsoes
        assert segunda.p90 - segunda.p10 >= primeira.p90 - primeira.p10


def test_mes_aberto_nao_passa_da_estimativa_do_mes():
    for empresa in EMPRESAS:
        for serie in falsos.series(empresa):
            assert serie.parcial[1] <= serie.previsoes[0].p90


def test_mesma_chamada_mesmo_resultado():
    falsos.serie.cache_clear()
    falsos.comercios.cache_clear()
    falsos.avaliacoes.cache_clear()
    primeira = [falsos.serie(e, c) for e in EMPRESAS for c in CATEGORIAS]
    resumo = falsos.comercios()
    falsos.serie.cache_clear()
    falsos.comercios.cache_clear()
    falsos.avaliacoes.cache_clear()
    assert primeira == [falsos.serie(e, c) for e in EMPRESAS for c in CATEGORIAS]
    assert resumo == falsos.comercios()


def test_as_tres_historias_aparecem_como_aviso():
    avisos = {(a.empresa_id, a.categoria) for a in falsos.alertas()}
    assert ("bella-massa", "demora") in avisos
    assert ("sorriso-claro", "atendimento") in avisos
    assert ("patinhas", "preco") in avisos
    assert all(isinstance(a, Alerta) for a in falsos.alertas())


def test_investigacao_da_pizzaria_aponta_o_entregador():
    resultado = falsos.investigar(None, "bella-massa", "demora")
    assert isinstance(resultado, Investigacao)
    principal = resultado.hipoteses[0]
    assert principal.veredito == "sustentada"
    assert "entregador" in principal.frase


def test_investigacao_sem_ia_nao_traz_ideia_da_ia():
    resultado = falsos.investigar(None, "bella-massa", "demora", usar_ia=False)
    assert all(h.origem != "ia" for h in resultado.hipoteses)
    assert not resultado.usou_ia


def test_pouca_reclamacao_vira_dados_insuficientes():
    resultado = falsos.investigar(None, "patinhas", "ambiente")
    assert resultado.estado == "dados_insuficientes"
    assert resultado.motivo


def test_entregador_a_mais_reduz_demora_e_tem_custo():
    sugestao = falsos.cenario_sugerido(falsos.investigar(None, "bella-massa", "demora"))
    resultado = falsos.simular(None, "bella-massa", sugestao)
    assert isinstance(resultado, ResultadoSimulacao)
    assert resultado.reclamacoes_cenario < resultado.reclamacoes_atual
    assert resultado.minimo <= resultado.reclamacoes_cenario <= resultado.maximo
    assert resultado.custo_extra_mes > 0
    assert resultado.espera_cenario_min < resultado.espera_atual_min


def test_simulador_avisa_quando_o_assunto_nao_depende_da_equipe():
    resultado = falsos.simular(None, "patinhas", falsos.Cenario("x", "preco", ()))
    assert not resultado.confiavel
    assert resultado.motivo


def test_sorteio_balanceia_cada_dia_da_semana():
    for plano in falsos.experimentos():
        assert isinstance(plano, PlanoExperimento)
        for dia_semana in {d.weekday() for d in plano.dias_com_acao + plano.dias_sem_acao}:
            com = sum(1 for d in plano.dias_com_acao if d.weekday() == dia_semana)
            sem = sum(1 for d in plano.dias_sem_acao if d.weekday() == dia_semana)
            assert abs(com - sem) <= 1


def test_teste_em_andamento_ainda_nao_tem_resultado():
    assert falsos.analisar(None, "exp-bella-entregador") is None
    assert falsos.analisar(None, "exp-sorriso-recepcao").veredito == "funcionou"


def test_nenhum_nome_de_pessoa_nas_avaliacoes():
    """O texto chega mascarado: o que seria um nome aparece como [nome]."""
    for empresa in EMPRESAS:
        for avaliacao in falsos.avaliacoes(empresa, limite=0):
            if avaliacao.texto and "[nome]" not in avaliacao.texto:
                assert "Carlos" not in avaliacao.texto and "Maria" not in avaliacao.texto
