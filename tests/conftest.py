"""Cliente de teste e a lista de telas que todo teste percorre."""

import os
import re

import pytest
from starlette.testclient import TestClient

# A senha de demonstração vem do ambiente. Sem ela, ninguém entra - nem o teste.
SENHA_DEMO = os.environ.setdefault("RADAR_SENHA_DEMO", "admin")
os.environ.setdefault("RADAR_CHAVE", "chave-de-teste-nao-usar-em-producao")

from app.web import app  # noqa: E402  (importa depois de definir as variáveis de ambiente)

# Telas do dono do negócio: valem as regras de linguagem simples.
# A sessão do teste é da Bella Massa, então só as telas dela entram aqui. Pedir
# tela de outra empresa devolve 403 de propósito, e isso é testado à parte, em
# tests/seguranca/test_isolamento.py.
TELAS_DO_DONO = [
    "/", "/entrar", "/resumo", "/comercio/bella-massa", "/previsao/bella-massa",
    "/previsao/bella-massa?categoria=preco", "/avisos", "/investigacao",
    "/investigacao/bella-massa/demora", "/investigacao/bella-massa/ambiente",
    "/simulador", "/simulador/bella-massa", "/simulador/bella-massa?categoria=preco",
    "/experimentos", "/experimentos/exp-bella-entregador",
    "/confianca", "/o-que-falta", "/ajuda",
]
# A área da banca pode ter termo técnico, mas só dentro de "Detalhes técnicos".
TODAS_AS_TELAS = TELAS_DO_DONO + ["/sobre"]


@pytest.fixture(scope="session")
def cliente():
    """Cliente já autenticado: as telas internas agora exigem sessão."""
    with TestClient(app) as sessao:
        pagina = sessao.get("/entrar")
        achado = re.search(r'name="csrf" value="([^"]+)"', pagina.text)
        assert achado, "a tela de entrada precisa trazer o token contra CSRF"
        resposta = sessao.post("/entrar", data={
            "usuario": "bella", "senha": SENHA_DEMO,
            "csrf": achado.group(1), "proximo": "/resumo",
        })
        assert resposta.status_code == 200, f"login falhou: {resposta.status_code}"
        yield sessao
