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
from app.seguranca import instalar

app = FastAPI(title=PROJETO["nome"], version=VERSAO, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=RAIZ / "static"), name="static")

# Antes do include_router: com este FastAPI a trava de empresa é fixada no
# registro da rota. Depois, ela levanta na partida em vez de falhar calada.
instalar(app)

for modulo in (publico, painel, investigacao, simulador, experimentos, paginas):
    app.include_router(modulo.rotas)


@app.get("/saude")
def saude() -> JSONResponse:
    # Só o estado e a versão: nada sobre usuário, senha ou configuração.
    return JSONResponse({"estado": "ok", "versao": VERSAO})


@app.exception_handler(StarletteHTTPException)
async def erro_http(request: Request, erro: StarletteHTTPException):
    if erro.status_code in (403, 404):
        # O 403 do isolamento é a recusa que o dono do negócio mais encontra.
        # Devolver JSON cru no navegador fere "a tela fala a língua do dono".
        return tela(request, "nao_encontrado.html", "", status_code=erro.status_code)
    return JSONResponse({"erro": erro.detail}, status_code=erro.status_code)
