"""Os cabecalhos de defesa saem em toda resposta, não só nas páginas que deram certo."""

from starlette.testclient import TestClient

from tests.seguranca.ajudas import entrar, sair, token_da_pagina


def _confere(resposta, onde: str) -> None:
    cabecalhos = resposta.headers
    assert "unsafe-inline" not in cabecalhos["content-security-policy"], onde
    assert "script-src 'self'" in cabecalhos["content-security-policy"], onde
    assert cabecalhos["x-frame-options"] == "DENY", onde
    assert cabecalhos["x-content-type-options"] == "nosniff", onde
    assert cabecalhos["referrer-policy"] == "strict-origin-when-cross-origin", onde
    assert "max-age=" in cabecalhos["strict-transport-security"], onde


def test_cabecalhos_na_pagina_publica(anonimo):
    resposta = anonimo.get("/")
    assert resposta.status_code == 200
    _confere(resposta, "/")


def test_cabecalhos_no_arquivo_estatico(anonimo):
    _confere(anonimo.get("/static/css/app.css"), "estático")


def test_cabecalhos_no_redirecionamento_para_a_entrada(anonimo):
    resposta = anonimo.get("/resumo")
    assert resposta.status_code == 303
    _confere(resposta, "redirecionamento")


def test_cabecalhos_na_tela_interna(bella):
    _confere(bella.get("/resumo"), "/resumo")


def test_cabecalhos_na_pagina_nao_encontrada(bella):
    resposta = bella.get("/pagina-que-nao-existe")
    assert resposta.status_code == 404
    _confere(resposta, "404")


def test_cabecalhos_na_recusa_por_empresa(bella):
    resposta = bella.get("/comercio/patinhas")
    assert resposta.status_code == 403
    _confere(resposta, "403 de empresa")


def test_cabecalhos_na_recusa_por_token(bella):
    resposta = bella.post("/_teste/altera", data={})
    assert resposta.status_code == 403
    _confere(resposta, "403 de token")


def test_cabecalhos_no_metodo_nao_permitido(bella):
    resposta = bella.get("/sair")
    assert resposta.status_code == 405
    _confere(resposta, "405")


def test_cabecalhos_no_corpo_grande_demais(bella):
    resposta = bella.post("/_teste/altera", data={"csrf": token_da_pagina(bella), "x": "y" * 200_000})
    assert resposta.status_code == 413
    _confere(resposta, "413")


def test_cabecalhos_na_entrada_e_na_saida(anonimo):
    _confere(entrar(anonimo, "bella"), "POST /entrar")
    _confere(sair(anonimo, token_da_pagina(anonimo)), "POST /sair")


def test_cabecalhos_ate_quando_a_rota_quebra(site):
    cliente = TestClient(site, raise_server_exceptions=False, follow_redirects=False)
    entrar(cliente, "bella")
    resposta = cliente.get("/_teste/quebra")
    assert resposta.status_code == 500
    _confere(resposta, "500")
    assert "defeito de teste" not in resposta.text      # o erro fica no log, nunca na tela


def test_nome_de_negocio_com_marcacao_nao_vira_marcacao_na_tela(cliente):
    """O nome do negócio é texto livre do cadastro e vai para dentro do SVG.

    O bandit aponta todo `Markup(...)` como possível XSS, e aqui a defesa é o
    `html.escape` em cada texto que vem de fora. Este teste é o que sustenta
    essa resposta: muda o nome do negócio para uma marcação e confere que ela
    sai escapada, não executável.
    """
    from app.banco import modelo
    from app.banco import sessao as banco

    venenoso = '</title><script>alert("xss")</script>'
    with banco.Sessao() as sessao:
        negocio = sessao.get(modelo.Comercio, "bella-massa")
        original = negocio.nome
        negocio.nome = venenoso
        sessao.commit()
    try:
        for rota in ("/resumo", "/comercio/bella-massa", "/previsao/bella-massa"):
            html = cliente.get(rota).text
            assert "<script>alert" not in html, f"{rota} deixou a marcação passar"
            assert "&lt;script&gt;" in html or "&lt;/title&gt;" in html, rota
    finally:
        with banco.Sessao() as sessao:
            sessao.get(modelo.Comercio, "bella-massa").nome = original
            sessao.commit()
