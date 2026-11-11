"""A trava devolve 403 no acesso direto. Este arquivo cuida do outro caminho:
o nome da outra empresa aparecendo no corpo de uma tela que a pessoa pode abrir.

O 403 protege o endereço. Não protege a listagem: uma tela de índice que monta
a lista sem filtrar entrega o concorrente dentro do HTML, com 200 na resposta.
"""

import pytest

OUTRAS_EMPRESAS = ("Clínica Sorriso Claro", "Pet Shop Patinhas", "sorriso-claro", "patinhas")

TELAS_DE_INDICE = [
    "/resumo", "/avisos", "/configuracao", "/conferir",
    "/o-que-falta", "/comercio/bella-massa", "/previsao/bella-massa",
]


@pytest.mark.parametrize("rota", TELAS_DE_INDICE)
def test_tela_nao_cita_outra_empresa(cliente, rota):
    """A sessão é da Bella Massa. Nenhuma outra empresa pode aparecer no HTML."""
    resposta = cliente.get(rota)
    assert resposta.status_code == 200, f"{rota} devia abrir para a própria empresa"
    vazou = [nome for nome in OUTRAS_EMPRESAS if nome in resposta.text]
    assert not vazou, f"{rota} mostra dado de outra empresa no corpo da página: {vazou}"


def test_avaliacao_de_outra_empresa_nao_pode_ser_conferida(cliente):
    """O campo se chama `avaliacao_id`, então a trava automática não o alcança.

    A trava global de `app/seguranca/isolamento.py` compara nomes conhecidos
    (`empresa`, `comercio`). Um identificador com outro nome passa por ela, e é
    por isso que a rota confere a empresa da avaliação por dentro. Este teste
    existe para essa segunda trava não ser removida por alguém que ache que a
    primeira já resolve.
    """
    import re

    from app.banco import modelo
    from app.banco import sessao as banco

    with banco.Sessao() as sessao:
        de_outra = sessao.scalar(
            modelo.Avaliacao.__table__.select().where(
                modelo.Avaliacao.empresa_id == "patinhas").limit(1)
        )
    assert de_outra is not None, "o banco de teste precisa ter avaliação da outra empresa"
    alheia = de_outra[0]

    token = re.search(r'name="csrf" value="([^"]+)"', cliente.get("/conferir").text).group(1)
    resposta = cliente.post("/conferir", data={
        "csrf": token, "avaliacao_id": alheia, "categoria": "preco",
    }, follow_redirects=False)
    # Volta com recado de recusa, e nada da outra empresa foi gravado.
    assert resposta.status_code == 303
    assert "erro=" in resposta.headers["location"]

    with banco.Sessao() as sessao:
        marcadas = sessao.scalar(
            modelo.Classificacao.__table__.select().where(
                modelo.Classificacao.avaliacao_id == alheia,
                modelo.Classificacao.motivo_sem_assunto == "conferida pelo dono").limit(1)
        )
    assert marcadas is None, "a conferência gravou em avaliação de outra empresa"


def test_resumo_conta_so_o_proprio_negocio(cliente):
    """Somar as duas empresas faria o dono ler um número que não é o dele."""
    from app import servicos

    da_bella = servicos.comercios("bella-massa")
    assert len(da_bella) == 1
    html = cliente.get("/resumo").text
    assert str(da_bella[0].avaliacoes_lidas) in html
