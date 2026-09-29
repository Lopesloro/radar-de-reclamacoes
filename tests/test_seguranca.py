"""Testes da entrada e dos controles de defesa."""

import re

import pytest

from app import seguranca

PROTEGIDAS = ["/painel", "/comercio/bella-massa", "/previsao", "/alertas", "/acuracia", "/etapas"]


@pytest.mark.parametrize("rota", PROTEGIDAS)
def test_rota_protegida_manda_para_a_entrada(anonimo, rota):
    resposta = anonimo.get(rota)
    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/entrar?proximo=")


def test_entrada_e_home_sao_publicas(anonimo):
    assert anonimo.get("/").status_code == 200
    assert anonimo.get("/entrar").status_code == 200
    assert anonimo.get("/saude").status_code == 200


def test_login_leva_de_volta_ao_destino_pedido(anonimo):
    pagina = anonimo.get("/entrar?proximo=/etapas").text
    token = re.search(r'name="csrf" value="([^"]+)"', pagina).group(1)
    resposta = anonimo.post("/entrar", data={
        "usuario": "admin", "senha": "admin", "csrf": token, "proximo": "/etapas",
    })
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/etapas"


def test_senha_errada_nao_entra(anonimo):
    pagina = anonimo.get("/entrar").text
    token = re.search(r'name="csrf" value="([^"]+)"', pagina).group(1)
    resposta = anonimo.post("/entrar", data={
        "usuario": "admin", "senha": "errada", "csrf": token, "proximo": "/painel",
    })
    assert resposta.headers["location"].startswith("/entrar?erro=credencial")
    assert anonimo.get("/painel").status_code == 303


def test_post_sem_token_csrf_nao_entra(anonimo):
    resposta = anonimo.post("/entrar", data={
        "usuario": "admin", "senha": "admin", "csrf": "inventado", "proximo": "/painel",
    })
    assert resposta.headers["location"] == "/entrar?erro=sessao"


def test_destino_externo_e_ignorado(anonimo):
    pagina = anonimo.get("/entrar").text
    token = re.search(r'name="csrf" value="([^"]+)"', pagina).group(1)
    resposta = anonimo.post("/entrar", data={
        "usuario": "admin", "senha": "admin", "csrf": token,
        "proximo": "https://exemplo.invalido/roubo",
    })
    assert resposta.headers["location"] == "/painel"


def test_tentativas_demais_bloqueiam_a_origem(anonimo):
    pagina = anonimo.get("/entrar").text
    token = re.search(r'name="csrf" value="([^"]+)"', pagina).group(1)
    for _ in range(seguranca.TENTATIVAS_MAXIMAS):
        anonimo.post("/entrar", data={
            "usuario": "admin", "senha": "errada", "csrf": token, "proximo": "/painel",
        })
    resposta = anonimo.post("/entrar", data={
        "usuario": "admin", "senha": "admin", "csrf": token, "proximo": "/painel",
    })
    assert resposta.headers["location"].startswith("/entrar?erro=bloqueado")


def test_sair_encerra_a_sessao(cliente, csrf):
    assert cliente.get("/painel").status_code == 200
    cliente.post("/sair", data={"csrf": csrf})
    resposta = cliente.get("/painel", follow_redirects=False)
    assert resposta.status_code == 303


def test_resposta_traz_os_cabecalhos_de_defesa(anonimo):
    cabecalhos = anonimo.get("/").headers
    assert "unsafe-inline" not in cabecalhos["content-security-policy"]
    assert cabecalhos["x-content-type-options"] == "nosniff"
    assert cabecalhos["x-frame-options"] == "DENY"
    assert cabecalhos["referrer-policy"] == "strict-origin-when-cross-origin"


def test_cookie_de_sessao_e_httponly(anonimo):
    pagina = anonimo.get("/entrar").text
    token = re.search(r'name="csrf" value="([^"]+)"', pagina).group(1)
    resposta = anonimo.post("/entrar", data={
        "usuario": "admin", "senha": "admin", "csrf": token, "proximo": "/painel",
    })
    biscoito = resposta.headers["set-cookie"]
    assert "httponly" in biscoito.lower()
    assert "samesite=lax" in biscoito.lower()


def test_senha_nunca_aparece_em_texto_no_modulo():
    assert seguranca._HASH_ESPERADO != seguranca.SENHA.encode()
    assert seguranca.senha_confere("admin", "admin") is True
    assert seguranca.senha_confere("admin", "Admin") is False
