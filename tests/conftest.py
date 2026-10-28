"""Cliente de teste e a lista de telas que todo teste percorre."""

import pytest
from starlette.testclient import TestClient

from app.web import app

# Telas do dono do negócio: valem as regras de linguagem simples.
TELAS_DO_DONO = [
    "/", "/entrar", "/resumo", "/comercio/bella-massa", "/previsao/bella-massa",
    "/previsao/patinhas?categoria=preco", "/avisos", "/investigacao",
    "/investigacao/bella-massa/demora", "/investigacao/patinhas/ambiente",
    "/simulador", "/simulador/bella-massa", "/simulador/patinhas?categoria=preco",
    "/experimentos", "/experimentos/exp-bella-entregador", "/experimentos/exp-sorriso-recepcao",
    "/confianca", "/o-que-falta", "/ajuda",
]
# A área da banca pode ter termo técnico, mas só dentro de "Detalhes técnicos".
TODAS_AS_TELAS = TELAS_DO_DONO + ["/sobre"]


@pytest.fixture(scope="session")
def cliente():
    with TestClient(app) as sessao:
        yield sessao
