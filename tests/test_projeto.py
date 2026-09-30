"""Testes da tela de apresentação do projeto."""

from app.conteudo import INTEGRANTES, PROJETO


def test_home_responde_e_vende_o_resultado(anonimo):
    """A home fala do que o dono do negócio ganha, não de como o modelo funciona."""
    resposta = anonimo.get("/")
    assert resposta.status_code == 200
    assert "Você sabe a sua nota" in resposta.text
    assert "A lista do que mais incomoda" in resposta.text


def test_home_nao_traz_identificacao_academica(anonimo):
    """A página pública é comercial. Disciplina, instituição e equipe vivem dentro."""
    texto = anonimo.get("/").text
    for termo in (PROJETO["disciplina"], PROJETO["instituicao"], PROJETO["orientadora"]):
        assert termo not in texto
    for pessoa in INTEGRANTES:
        assert pessoa not in texto


def test_home_nao_tem_travessao(anonimo):
    texto = anonimo.get("/").text
    assert "\u2014" not in texto and "\u2013" not in texto


def test_home_so_tem_uma_acao(anonimo):
    """Um site B2B abre com uma porta só: entrar."""
    texto = anonimo.get("/").text
    assert "O projeto" not in texto
    assert texto.count('href="/entrar"') >= 1


def test_home_nao_tem_jargao_tecnico(anonimo):
    """Nome de biblioteca e sigla de métrica vivem na área interna, não na home."""
    texto = anonimo.get("/").text
    for jargao in ("FastAPI", "scikit-learn", "PostgreSQL", "F1", "P10", "CSRF"):
        assert jargao not in texto


def test_home_diz_o_que_o_cliente_nao_precisa_fazer(anonimo):
    texto = anonimo.get("/").text
    assert "vai precisar fazer" in texto
    assert "Instalar programa" in texto


def test_home_mostra_a_comparacao_com_o_palpite_simples(anonimo):
    texto = anonimo.get("/").text
    assert "repetir o número do mês passado" in texto
    assert "chutar sempre o assunto mais comum" in texto


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
