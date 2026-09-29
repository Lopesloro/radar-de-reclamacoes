"""Clientes de teste: um anônimo e um já autenticado."""

import re

import pytest
from starlette.testclient import TestClient

from app import demo, seguranca
from app.web import app


def _token(cliente: TestClient) -> str:
    pagina = cliente.get("/entrar").text
    achado = re.search(r'name="csrf" value="([^"]+)"', pagina)
    assert achado, "a tela de entrada precisa trazer o token contra CSRF"
    return achado.group(1)


@pytest.fixture
def anonimo():
    with TestClient(app, follow_redirects=False) as cliente:
        yield cliente


@pytest.fixture
def cliente():
    with TestClient(app) as sessao:
        resposta = sessao.post("/entrar", data={
            "usuario": "admin", "senha": "admin",
            "csrf": _token(sessao), "proximo": "/painel",
        })
        assert resposta.status_code == 200
        yield sessao


@pytest.fixture
def csrf(cliente):
    return _token(cliente)


@pytest.fixture(autouse=True)
def estado_limpo():
    demo.limpar_estados()
    seguranca.limpar_tentativas()
    yield
    demo.limpar_estados()
    seguranca.limpar_tentativas()
