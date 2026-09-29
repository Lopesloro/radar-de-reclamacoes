"""Testes da tela de apresentação do projeto."""

from app.conteudo import INTEGRANTES, PROJETO


def test_home_responde_e_traz_a_ideia(anonimo):
    resposta = anonimo.get("/")
    assert resposta.status_code == 200
    assert "Por que as pessoas estão reclamando" in resposta.text
    assert PROJETO["disciplina"] in resposta.text


def test_home_lista_todos_os_integrantes(anonimo):
    texto = anonimo.get("/").text
    for pessoa in INTEGRANTES:
        assert pessoa in texto


def test_home_mostra_as_tecnologias_e_a_robustez(anonimo):
    texto = anonimo.get("/").text
    assert "FastAPI" in texto and "scikit-learn" in texto
    assert "Situação não prevista" in texto
    assert "sem categoria abaixo do limite de confiança" in texto


def test_home_declara_os_dois_modelos_com_regua(anonimo):
    texto = anonimo.get("/").text
    assert "F1 por categoria e F1 macro" in texto
    assert "repetir o mês anterior" in texto


def test_saude_responde_json(anonimo):
    dados = anonimo.get("/saude").json()
    assert dados["estado"] == "ok"
    assert dados["dados"] == "demonstração"
    assert dados["comercios"] == 3


def test_home_nao_expoe_nome_de_parceiro(anonimo):
    """Dado de parceiro vive atrás do login, inclusive o nome do comércio."""
    from app import demo
    texto = anonimo.get("/").text
    for c in demo.comercios():
        assert c.nome not in texto


def test_home_convida_a_entrar(anonimo):
    assert 'href="/entrar"' in anonimo.get("/").text
