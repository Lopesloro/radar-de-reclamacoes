"""Cria o site e liga as rotas de cada área.

Tudo é montado no servidor: a página chega pronta, e o JavaScript só melhora
(fecha o balão de ajuda, faz o tour). Sem JavaScript, tudo continua funcionando.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.conteudo import PROJETO, VERSAO
from app.rotas import admin, configuracao, paginas, painel, publico
from app.rotas._telas import RAIZ, tela
from app.seguranca import instalar


@asynccontextmanager
async def partida(_app: FastAPI):
    """Na partida: sobe o banco para a última migração e cria a conta do administrador.

    Sem isto, um serviço novo com banco vazio não tem por onde entrar, e a única
    alternativa seria senha escrita no código. É idempotente e não sobrescreve
    conta que já exista, para uma variável esquecida no painel não reabrir uma
    conta fechada.
    """
    from app.banco import migracao
    from app.banco import sessao as banco
    from app.seguranca.contas import garantir_administrador

    if banco.usar_banco():
        # Nesta ordem: a migração cria as tabelas, e só então a conta pode ser
        # gravada. Ao contrário, o primeiro arranque falharia.
        migracao.subir()
        with banco.Sessao() as sessao:
            garantir_administrador(sessao)
    yield


app = FastAPI(
    title=PROJETO["nome"], version=VERSAO, lifespan=partida,
    docs_url=None, redoc_url=None, openapi_url=None,
)
app.mount("/static", StaticFiles(directory=RAIZ / "static"), name="static")

# Antes do include_router: com este FastAPI a trava de empresa é fixada no
# registro da rota. Depois, ela levanta na partida em vez de falhar calada.
instalar(app)

for modulo in (publico, painel, configuracao, paginas, admin):
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
