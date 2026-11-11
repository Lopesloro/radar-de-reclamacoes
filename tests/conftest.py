"""O banco de teste, o cliente autenticado e a lista de telas que todo teste percorre.

O banco é um SQLite num arquivo temporário, criado uma vez por sessão de teste e
preenchido pelo motor de coleta de verdade (`tests/dados.py`). Duas decisões aqui
valem explicação:

- **`DATABASE_URL` é definida antes de importar `app.web`.** O sistema decide de
  onde lê na primeira chamada, e não no import; definir antes só evita depender
  dessa ordem.
- **A chave da IA é apagada do ambiente.** Teste não fala com a internet. Com a
  chave presente, a suíte sairia da máquina, demoraria minutos e o resultado
  dependeria da conta de outra pessoa. O caminho da IA é testado à parte, em
  `tests/seguranca/test_ia_segura.py`, com um cliente de mentira.
"""

import os
import re
import tempfile
from pathlib import Path

import pytest
from starlette.testclient import TestClient

SENHA = "senha-de-teste-nao-usar-em-producao"

_pasta = Path(tempfile.mkdtemp(prefix="radar-teste-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_pasta / 'teste.sqlite3'}"
os.environ.setdefault("RADAR_CHAVE", "chave-de-teste-nao-usar-em-producao")
os.environ["RADAR_ADMIN_SENHA"] = SENHA
os.environ.setdefault("RADAR_COFRE_CHAVE", "")
for _variavel in ("RADAR_IA_CHAVE", "GEMINI_API_KEY"):
    os.environ.pop(_variavel, None)

from app.seguranca import senha as _senha  # noqa: E402
from app.web import app  # noqa: E402
from tests import dados  # noqa: E402

# Telas do dono do negócio: valem as regras de linguagem simples.
# A sessão do teste é da Bella Massa, então só as telas dela entram aqui. Pedir
# tela de outra empresa devolve 403 de propósito, e isso é testado à parte, em
# tests/seguranca/test_isolamento.py.
TELAS_DO_DONO = [
    "/", "/entrar", "/resumo", "/comercio/bella-massa", "/previsao/bella-massa",
    "/previsao/bella-massa?categoria=preco", "/avisos",
    "/configuracao", "/conferir", "/confianca", "/o-que-falta", "/ajuda",
]
# A área da equipe pode ter termo técnico: quem lê é quem opera o sistema.
TELAS_DA_EQUIPE = [
    "/admin", "/admin/clientes", "/admin/clientes/bella-massa", "/admin/fontes",
    "/admin/coletas", "/admin/auditoria", "/admin/sistema",
]
TODAS_AS_TELAS = TELAS_DO_DONO


@pytest.fixture(scope="session", autouse=True)
def banco_de_teste():
    """Cria e preenche o banco antes de qualquer teste rodar."""
    dados.montar(_senha.gerar_hash(SENHA))
    yield


def _entrar(sessao: TestClient, usuario: str) -> None:
    pagina = sessao.get("/entrar")
    achado = re.search(r'name="csrf" value="([^"]+)"', pagina.text)
    assert achado, "a tela de entrada precisa trazer o token contra CSRF"
    resposta = sessao.post("/entrar", data={
        "usuario": usuario, "senha": SENHA,
        "csrf": achado.group(1), "proximo": "/resumo",
    })
    assert resposta.status_code == 200, f"entrada de {usuario} falhou: {resposta.status_code}"


@pytest.fixture(scope="session")
def cliente(banco_de_teste):
    """O dono da Bella Massa, já autenticado."""
    with TestClient(app) as sessao:
        _entrar(sessao, "bella")
        yield sessao


@pytest.fixture(scope="session")
def equipe(banco_de_teste):
    """A conta de administrador, para as telas de `/admin`."""
    with TestClient(app) as sessao:
        _entrar(sessao, "admin")
        yield sessao


@pytest.fixture
def anonimo(banco_de_teste):
    with TestClient(app, follow_redirects=False) as sessao:
        yield sessao


def token_de(sessao: TestClient, caminho: str = "/configuracao") -> str:
    """O token contra CSRF lido de uma tela, como o navegador leria."""
    achado = re.search(r'name="csrf" value="([^"]+)"', sessao.get(caminho).text)
    assert achado, f"a tela {caminho} precisa trazer o token contra CSRF"
    return achado.group(1)
