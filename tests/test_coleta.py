"""O caminho da avaliação: entra, é mascarada, classificada, contada e estimada.

O que estes testes protegem, em ordem de importância:

1. **Não contar duas vezes.** Rodar a coleta de novo não pode dobrar número.
2. **Não guardar dado pessoal.** A máscara roda antes do banco, não na tela.
3. **Não inventar estimativa.** Com menos de seis meses fechados, não sai
   estimativa nenhuma, e a tela diz isso.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.banco import modelo
from app.banco import sessao as banco
from app.coleta import AvaliacaoBruta, ErroDeFonte, arquivo, motor
from app.coleta.mascara import aplicar, tem_dado_pessoal

HOJE = date(2026, 11, 10)


@pytest.fixture
def negocio_vazio(banco_de_teste):
    """Uma empresa nova, com negócio e nenhuma avaliação."""
    identificador = f"teste-{date.today().toordinal()}"
    with banco.Sessao() as sessao:
        if sessao.get(modelo.Empresa, identificador) is None:
            sessao.add(modelo.Empresa(id=identificador, nome="Empresa de Teste"))
            sessao.flush()
            sessao.add(modelo.Comercio(
                id=identificador, empresa_id=identificador, nome="Negócio de Teste",
                ramo="Teste", cidade="Campinas, SP",
            ))
            sessao.commit()
    yield identificador
    with banco.Sessao() as sessao:
        for tabela in (modelo.Alerta, modelo.Previsao, modelo.SerieMensal,
                       modelo.Classificacao, modelo.Avaliacao, modelo.ExecucaoColeta,
                       modelo.Fonte, modelo.Auditoria, modelo.VersaoModelo):
            sessao.query(tabela).filter(tabela.empresa_id == identificador).delete()
        sessao.query(modelo.Comercio).filter(modelo.Comercio.id == identificador).delete()
        sessao.query(modelo.Empresa).filter(modelo.Empresa.id == identificador).delete()
        sessao.commit()


def _brutas(quantas: int, inicio: int = 1) -> list[AvaliacaoBruta]:
    return [
        AvaliacaoBruta(
            id_origem=f"a{i}", data=HOJE - timedelta(days=i),
            estrelas=1 + i % 5, texto="Esperei quase uma hora para ser atendido.",
        )
        for i in range(inicio, inicio + quantas)
    ]


def test_a_segunda_coleta_nao_conta_a_mesma_avaliacao_de_novo(negocio_vazio):
    """A chave única está no banco, não na memória do programa."""
    with banco.Sessao() as sessao:
        primeira = motor.coletar(sessao, negocio_vazio, negocio_vazio, _brutas(20), hoje=HOJE)
        sessao.commit()
    with banco.Sessao() as sessao:
        segunda = motor.coletar(sessao, negocio_vazio, negocio_vazio, _brutas(20), hoje=HOJE)
        sessao.commit()
    assert primeira.novas == 20
    assert segunda.novas == 0 and segunda.repetidas == 20
    with banco.Sessao() as sessao:
        total = sessao.scalar(select(func.count(modelo.Avaliacao.id)).where(
            modelo.Avaliacao.empresa_id == negocio_vazio))
    assert total == 20


def test_o_texto_chega_ao_banco_sem_dado_pessoal(negocio_vazio):
    bruta = AvaliacaoBruta(
        id_origem="p1", data=HOJE, estrelas=1,
        texto="O entregador João Pedro ligou do 19 99123-4567 e meu cpf 123.456.789-00",
    )
    with banco.Sessao() as sessao:
        motor.coletar(sessao, negocio_vazio, negocio_vazio, [bruta], hoje=HOJE)
        sessao.commit()
    with banco.Sessao() as sessao:
        guardado = sessao.scalar(select(modelo.Avaliacao.texto).where(
            modelo.Avaliacao.id_origem == "p1"))
    assert guardado is not None
    assert "João Pedro" not in guardado
    assert "99123-4567" not in guardado
    assert "123.456.789-00" not in guardado
    assert tem_dado_pessoal(guardado) is False


def test_com_historico_curto_nao_sai_estimativa(negocio_vazio):
    """Três meses de avaliação não dão estimativa: a conta pede seis meses fechados."""
    brutas = [
        AvaliacaoBruta(id_origem=f"c{i}", data=date(2026, 9 + i // 10, 1 + i % 28),
                       estrelas=2, texto="Demorou demais para me atender.")
        for i in range(30)
    ]
    with banco.Sessao() as sessao:
        resultado = motor.coletar(sessao, negocio_vazio, negocio_vazio, brutas, hoje=HOJE)
        sessao.commit()
    assert resultado.novas == 30
    assert resultado.previsoes == 0
    assert resultado.avisos == 0


def test_a_abstencao_e_gravada_com_o_motivo(negocio_vazio):
    """Avaliação só com nota entra com assunto nulo e o motivo, não sem linha."""
    brutas = [AvaliacaoBruta(id_origem="s1", data=HOJE, estrelas=5, texto=None)]
    with banco.Sessao() as sessao:
        resultado = motor.coletar(sessao, negocio_vazio, negocio_vazio, brutas, hoje=HOJE)
        sessao.commit()
    assert resultado.sem_assunto == 1
    with banco.Sessao() as sessao:
        linha = sessao.scalar(select(modelo.Classificacao).join(
            modelo.Avaliacao, modelo.Avaliacao.id == modelo.Classificacao.avaliacao_id
        ).where(modelo.Avaliacao.id_origem == "s1"))
    assert linha.categoria_id is None
    assert linha.motivo_sem_assunto == motor.MOTIVO_SEM_TEXTO


def test_a_coleta_grava_na_trilha_de_auditoria(negocio_vazio):
    with banco.Sessao() as sessao:
        motor.coletar(sessao, negocio_vazio, negocio_vazio, _brutas(3), hoje=HOJE)
        sessao.commit()
    with banco.Sessao() as sessao:
        linha = sessao.scalar(select(modelo.Auditoria).where(
            modelo.Auditoria.empresa_id == negocio_vazio,
            modelo.Auditoria.acao == "coleta_rodada"))
    assert linha is not None and "avaliações novas" in (linha.detalhe or "")


def test_coletar_em_negocio_de_outra_empresa_e_erro(negocio_vazio):
    """O motor também confere: é a terceira trava, depois da tela e da rota."""
    with banco.Sessao() as sessao, pytest.raises(ValueError, match="não é da empresa"):
        motor.coletar(sessao, negocio_vazio, "bella-massa", _brutas(1), hoje=HOJE)


# ------------------------------------------------------------ importação de arquivo

def test_csv_do_painel_brasileiro_e_lido():
    lido = arquivo.ler(
        "id;data;nota;comentario\n"
        "g1;13/10/2026;1;Esperei 50 minutos\n"
        "g2;2026-10-12;2;Caro demais\n"
    )
    assert len(lido.avaliacoes) == 2 and lido.recusadas == 0
    assert lido.avaliacoes[0].data == date(2026, 10, 13)


def test_json_do_google_com_nota_escrita_e_lido():
    lido = arquivo.ler(
        '{"reviews":[{"reviewId":"x1","createTime":"2026-10-01T10:00:00Z",'
        '"starRating":"FIVE","comment":"otimo"}]}'
    )
    assert lido.avaliacoes[0].estrelas == 5


def test_linha_ruim_e_recusada_sozinha_e_o_resto_entra():
    """Um arquivo de 300 linhas com 2 erros de data é um arquivo útil."""
    lido = arquivo.ler(
        "id;data;nota\n"
        "b1;data-ruim;5\n"
        "b2;01/10/2026;3\n"
        "b2;02/10/2026;3\n"
    )
    assert len(lido.avaliacoes) == 1
    assert lido.recusadas == 2
    assert any("data" in m for m in lido.motivos)
    assert any("repetido" in m for m in lido.motivos)


def test_arquivo_sem_nenhuma_linha_util_e_recusado_inteiro():
    with pytest.raises(ErroDeFonte, match="nenhuma linha"):
        arquivo.ler("id;data;nota\nx;nao-e-data;abc\n")


def test_nota_fora_de_um_a_cinco_nao_entra():
    with pytest.raises(ValueError, match="estrelas fora"):
        AvaliacaoBruta(id_origem="x", data=HOJE, estrelas=9, texto=None)


@pytest.mark.parametrize("texto,fora", [
    ("Falei com a atendente Maria e ela foi grossa", "Maria"),
    ("manda no zap 19 99123-4567", "99123-4567"),
    ("escreve pra contato@loja.com.br", "contato@loja.com.br"),
    ("meu cnpj 12.345.678/0001-99 ta no cadastro", "12.345.678/0001-99"),
])
def test_a_mascara_tira_o_que_promete(texto, fora):
    limpo = aplicar(texto)
    assert fora not in limpo
    assert tem_dado_pessoal(limpo) is False


def test_a_mascara_nao_come_palavra_depois_do_nome():
    """Defeito real: `re.IGNORECASE` no padrão inteiro fazia [A-Z] casar com
    minúscula, e "a atendente Maria foi grossa" virava "a atendente [nome] grossa"."""
    assert aplicar("A atendente Maria foi grossa") == "A atendente [nome] foi grossa"
