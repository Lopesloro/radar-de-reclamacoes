"""Testes das telas de dados: painel, comércio, previsão, alertas e acurácia."""

import pytest

from app import demo


@pytest.mark.parametrize("rota", ["/painel", "/alertas", "/acuracia", "/etapas"])
def test_telas_abrem(cliente, rota):
    assert cliente.get(rota).status_code == 200


def test_painel_lista_os_tres_comercios(cliente):
    texto = cliente.get("/painel").text
    for c in demo.comercios():
        assert c.nome in texto


def test_comercio_mostra_categorias_e_avaliacoes(cliente):
    texto = cliente.get("/comercio/bella-massa").text
    for categoria in demo.CATEGORIAS:
        assert categoria in texto
    assert "sem assunto" in texto
    assert "sem texto" in texto


def test_comercio_inexistente_responde_404(cliente):
    assert cliente.get("/comercio/nao-existe").status_code == 404


def test_previsao_sem_comercio_redireciona(cliente):
    resposta = cliente.get("/previsao", follow_redirects=False)
    assert resposta.status_code == 307
    assert resposta.headers["location"].startswith("/previsao/")


def test_previsao_aceita_categoria_e_ignora_invalida(cliente):
    valida = cliente.get("/previsao/bella-massa?categoria=preço")
    assert "Previsão de preço" in valida.text
    invalida = cliente.get("/previsao/bella-massa?categoria=fofoca")
    assert invalida.status_code == 200
    assert "fofoca" not in invalida.text


def test_previsao_marca_o_mes_em_andamento(cliente):
    texto = cliente.get("/previsao/bella-massa").text
    assert "ainda em andamento, não entra na conta" in texto


def test_faixa_prevista_contem_a_mediana(cliente):
    for c in demo.comercios():
        for serie in c.series:
            for ponto in serie.previsao:
                assert ponto.p10 <= ponto.p50 <= ponto.p90


def test_faixa_abre_com_o_horizonte(cliente):
    serie = demo.comercios()[0].series[0]
    primeira = serie.previsao[0].p90 - serie.previsao[0].p10
    ultima = serie.previsao[-1].p90 - serie.previsao[-1].p10
    assert ultima >= primeira


def test_modelo_supera_a_regua_na_previsao(cliente):
    resultado = demo.acuracia_previsao()
    assert resultado["mae"] < resultado["mae_regua"]


def test_cobertura_da_faixa_fica_perto_do_prometido(cliente):
    assert 0.70 <= demo.acuracia_previsao()["cobertura"] <= 0.90


def test_classificacao_supera_a_regua(cliente):
    resultado = demo.acuracia_classificacao()
    assert resultado["macro"] > resultado["macro_regua"]


def test_alerta_confirmado_sai_da_fila_e_volta_ao_reabrir(cliente, csrf):
    alerta = demo.alertas()[0]
    cliente.post(f"/alertas/{alerta.id}", data={"acao": "confirmar", "csrf": csrf})
    assert demo.alertas()[0].estado == "confirmado"
    cliente.post(f"/alertas/{alerta.id}", data={"acao": "reabrir", "csrf": csrf})
    assert demo.alertas()[0].estado == "aberto"


def test_acao_desconhecida_nao_muda_nada(cliente, csrf):
    alerta = demo.alertas()[0]
    cliente.post(f"/alertas/{alerta.id}", data={"acao": "apagar", "csrf": csrf})
    assert demo.alertas()[0].estado == "aberto"


def test_alerta_sem_token_csrf_nao_muda_nada(cliente):
    alerta = demo.alertas()[0]
    cliente.post(f"/alertas/{alerta.id}", data={"acao": "confirmar", "csrf": "inventado"})
    assert demo.alertas()[0].estado == "aberto"


def test_etapas_mostra_o_que_falta(cliente):
    texto = cliente.get("/etapas").text
    assert "Canal de alerta combinado" in texto
    assert "Falta" in texto
    assert "Coleta real das avaliações" in texto


def test_etapas_explica_onde_a_ia_entra_e_onde_erra(cliente):
    texto = cliente.get("/etapas").text
    assert "Onde a inteligência artificial entra" in texto
    assert "Onde melhorar" in texto
    assert "Ironia" in texto


def test_jargao_tecnico_fica_na_area_interna(cliente):
    """O que sumiu da home precisa continuar existindo para a banca ler."""
    texto = cliente.get("/etapas").text
    assert "FastAPI" in texto and "scikit-learn" in texto
    assert "O que pode dar errado" in texto


def test_prontidao_conta_so_etapa_concluida(cliente):
    for c in demo.comercios():
        etapas = demo.etapas(c)
        assert demo.prontidao(c) == sum(1 for e in etapas if e.estado == "feito")
        for etapa in etapas:
            assert (etapa.falta is None) == (etapa.estado == "feito")


def test_avaliacao_sem_texto_nunca_recebe_categoria(cliente):
    for c in demo.comercios():
        for avaliacao in c.avaliacoes:
            if avaliacao.texto is None:
                assert avaliacao.categoria is None


def test_avaliacao_classificada_supera_o_limite_de_confianca(cliente):
    for c in demo.comercios():
        for avaliacao in c.avaliacoes:
            if avaliacao.categoria is not None:
                assert avaliacao.confianca >= demo.LIMITE_CONFIANCA


def test_etapas_registra_quem_construiu(cliente):
    """A autoria do trabalho precisa estar escrita dentro do próprio sistema."""
    texto = cliente.get("/etapas").text
    assert "Quem construiu" in texto
    assert "Nada aqui foi comprado pronto" in texto
    for pessoa in ("Gabriel Lopes Londe Rodrigues", "Nicolas Marques Linares",
                   "Matheus Rocafa Moraes"):
        assert pessoa in texto


def test_entrada_nao_despeja_termo_tecnico_no_cliente(anonimo):
    """Quem só quer entrar não precisa ler sobre cookie, hash e CSRF."""
    texto = anonimo.get("/entrar").text
    for jargao in ("HttpOnly", "hash", "CSRF", "tentativas por origem"):
        assert jargao not in texto
