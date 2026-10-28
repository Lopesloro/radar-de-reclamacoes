"""Sobe o site de verdade numa porta livre e abre o navegador em 390px e 1280px.

Rodar: `python -m playwright install chromium` uma vez, depois `pytest -m e2e`.
Sem baixar o Chromium, dá para usar o Edge do Windows: `pytest -m e2e --browser-channel msedge`.
"""

from __future__ import annotations

import os
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn

from app.web import app

LARGURAS = (390, 1280)
EVIDENCIAS = Path(__file__).resolve().parents[2] / "docs" / "evidencias" / "telas"


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def endereco():
    """O endereço do site rodando. Hoje a demonstração abre sem senha; quando a entrada
    do Matheus ficar pronta, a fixture `pagina` passa a entrar com o usuário demo."""
    porta = _porta_livre()
    servidor = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=porta, log_level="warning"))
    linha = threading.Thread(target=servidor.run, daemon=True)
    linha.start()
    limite = time.monotonic() + 15
    while not servidor.started:
        if time.monotonic() > limite:
            raise RuntimeError("o servidor de teste não subiu")
        time.sleep(0.05)
    yield f"http://127.0.0.1:{porta}"
    servidor.should_exit = True
    linha.join(timeout=5)


# A conta de demonstração. As telas internas exigem sessão desde que a entrada
# de verdade entrou; sem isto, todo teste de botão cairia na tela de login.
USUARIO_DEMO = "bella"
SENHA_DEMO = os.environ.setdefault("RADAR_SENHA_DEMO", "admin")
os.environ.setdefault("RADAR_CHAVE", "chave-de-teste-nao-usar-em-producao")


def _entrar(pagina) -> None:
    """Entra pelo formulário, como uma pessoa faria. O token vem do próprio HTML."""
    pagina.ir("/entrar")
    pagina.fill('input[name="usuario"]', USUARIO_DEMO)
    pagina.fill('input[name="senha"]', SENHA_DEMO)
    pagina.click('form.formulario button[type="submit"]')
    pagina.wait_for_url(lambda u: "/entrar" not in u, timeout=10_000)


@pytest.fixture
def abrir(browser, endereco):
    """Abre uma aba com a largura pedida e junta os erros do console."""
    contextos = []

    def _abrir(largura: int):
        contexto = browser.new_context(viewport={"width": largura, "height": 900})
        contextos.append(contexto)
        pagina = contexto.new_page()
        pagina.erros = []
        pagina.on("console", lambda m: pagina.erros.append(m.text) if m.type == "error" else None)
        pagina.on("pageerror", lambda e: pagina.erros.append(str(e)))
        pagina.ir = lambda rota: pagina.goto(endereco + rota, wait_until="networkidle")
        _entrar(pagina)
        return pagina

    yield _abrir
    for contexto in contextos:
        contexto.close()


@pytest.fixture(scope="session")
def pasta_evidencias() -> Path:
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    return EVIDENCIAS
