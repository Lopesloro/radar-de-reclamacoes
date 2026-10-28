"""Cria o site e liga as rotas de cada área.

Tudo é montado no servidor: a página chega pronta, e o JavaScript só melhora
(fecha o balão de ajuda, faz o tour). Sem JavaScript, tudo continua funcionando.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.conteudo import PROJETO, VERSAO
from app.rotas import experimentos, investigacao, paginas, painel, publico, simulador
from app.rotas._telas import RAIZ, tela

app = FastAPI(title=PROJETO["nome"], version=VERSAO, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=RAIZ / "static"), name="static")

for modulo in (publico, painel, investigacao, simulador, experimentos, paginas):
    app.include_router(modulo.rotas)


@app.get("/saude")
def saude() -> JSONResponse:
    # Só o estado e a versão: nada sobre usuário, senha ou configuração.
    return JSONResponse({"estado": "ok", "versao": VERSAO})


@app.exception_handler(StarletteHTTPException)
async def erro_http(request: Request, erro: StarletteHTTPException):
    if erro.status_code == 404:
        return tela(request, "nao_encontrado.html", "", status_code=404)
    return JSONResponse({"erro": erro.detail}, status_code=erro.status_code)
