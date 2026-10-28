"""A trava devolve 403 no acesso direto. Este arquivo cuida do outro caminho:
o nome da outra empresa aparecendo no corpo de uma tela que a pessoa pode abrir.

O 403 protege o endereço. Não protege a listagem: uma tela de índice que monta
a lista sem filtrar entrega o concorrente dentro do HTML, com 200 na resposta.
"""

import pytest

OUTRAS_EMPRESAS = ("Clínica Sorriso Claro", "Pet Shop Patinhas", "sorriso-claro", "patinhas")

TELAS_DE_INDICE = [
    "/resumo", "/avisos", "/investigacao", "/simulador", "/experimentos",
    "/o-que-falta", "/comercio/bella-massa", "/previsao/bella-massa",
]


@pytest.mark.parametrize("rota", TELAS_DE_INDICE)
def test_tela_nao_cita_outra_empresa(cliente, rota):
    """A sessão é da Bella Massa. Nenhuma outra empresa pode aparecer no HTML."""
    resposta = cliente.get(rota)
    assert resposta.status_code == 200, f"{rota} devia abrir para a própria empresa"
    vazou = [nome for nome in OUTRAS_EMPRESAS if nome in resposta.text]
    assert not vazou, f"{rota} mostra dado de outra empresa no corpo da página: {vazou}"


def test_experimento_de_outra_empresa_e_recusado(cliente):
    """O parâmetro se chama plano_id, então a trava automática não o alcança."""
    resposta = cliente.get("/experimentos/exp-sorriso-recepcao")
    assert resposta.status_code == 403
    assert "Sorriso" not in resposta.text


def test_resumo_conta_so_o_proprio_negocio(cliente):
    """Somar as três empresas faria o dono ler um número que não é o dele."""
    from app import servicos

    da_bella = servicos.comercios("bella-massa")
    assert len(da_bella) == 1
    html = cliente.get("/resumo").text
    assert str(da_bella[0].avaliacoes_lidas) in html
