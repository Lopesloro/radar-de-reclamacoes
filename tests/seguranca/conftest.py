"""O site de verdade com a camada de segurança por cima.

Os roteadores vêm de `app.web` (nenhuma rota é copiada), então um teste aqui anda pelas mesmas telas que
o dono do negócio abriria. A diferença é só a linha que falta em `app/web.py`: `instalar(app)`, antes
dos roteadores. As rotas `/entrar` (GET) e `/_teste/*` existem só aqui.
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from starlette.testclient import TestClient

from app.rotas._telas import paginas
from app.seguranca import empresa_do_usuario, exigir_empresa, instalar, usuario_atual
from app.seguranca.contas import VARIAVEL_SENHA_DEMO, Contas
from app.web import app as site_de_verdade
from tests.seguranca.ajudas import CHAVE, FORMULARIO_DE_ENTRADA, SENHA, entrar, token_da_pagina


@pytest.fixture(scope="module")
def contas():
    return Contas.da_demonstracao({VARIAVEL_SENHA_DEMO: SENHA})


def montar_site(contas: Contas) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    instalar(app, contas=contas, chave=CHAVE)

    @app.get("/entrar")
    def formulario_de_entrada(request: Request):
        # No site, quem carrega `{{ request.state.csrf }}` é o entrar.html; aqui, em miniatura.
        return HTMLResponse(paginas.env.from_string(FORMULARIO_DE_ENTRADA).render(request=request))

    @app.post("/_teste/altera")
    def altera():
        return PlainTextResponse("alterado")

    @app.post("/_teste/eco")
    async def eco(request: Request):
        return JSONResponse(await request.json())

    @app.get("/_teste/quem")
    def quem(request: Request):
        usuario = usuario_atual(request)
        if usuario is None:
            return JSONResponse(None)
        return JSONResponse({"nome": usuario.nome, "empresa": usuario.empresa_id})

    @app.get("/_teste/minha-empresa")
    def minha_empresa(request: Request):
        return PlainTextResponse(empresa_do_usuario(request))

    @app.get("/_teste/exigir/{alvo}")
    def exigir(request: Request, alvo: str):
        return PlainTextResponse(exigir_empresa(request, alvo))

    @app.get("/_teste/quebra")
    def quebra():
        raise RuntimeError("defeito de teste")

    # O que `app/web.py` faz com `include_router` e `mount`, depois do `instalar`.
    for rota in site_de_verdade.router.routes:
        if hasattr(rota, "original_router"):
            app.include_router(rota.original_router)
        else:
            app.router.routes.append(rota)
    app.exception_handlers.update(site_de_verdade.exception_handlers)
    return app


@pytest.fixture
def site(contas):
    return montar_site(contas)


@pytest.fixture
def anonimo(site):
    return TestClient(site, follow_redirects=False)


def _logado_como(site, usuario: str) -> TestClient:
    cliente = TestClient(site, follow_redirects=False)
    assert entrar(cliente, usuario).status_code == 303
    return cliente


@pytest.fixture
def bella(site):
    return _logado_como(site, "bella")


@pytest.fixture
def patinhas(site):
    return _logado_como(site, "patinhas")


@pytest.fixture
def token(anonimo):
    return token_da_pagina(anonimo)
