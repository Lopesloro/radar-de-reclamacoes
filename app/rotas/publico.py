"""Página pública e a porta de entrada."""

from __future__ import annotations

import os

from fastapi import APIRouter, Request

from app import conteudo, servicos
from app.rotas._telas import tela

rotas = APIRouter()

# A conta de demonstração mostrada na tela de entrada. As contas nascem em
# app/seguranca/contas.py, a partir de RADAR_SENHA_DEMO.
USUARIO_DEMO = "bella"


@rotas.get("/")
def inicio(request: Request):
    return tela(
        request, "inicio.html", "inicio", publica=True,
        entregas=conteudo.ENTREGAS,
        passos=conteudo.PASSOS,
        dispensado=conteudo.DISPENSADO,
        total_negocios=len(servicos.comercios()),
    )


@rotas.get("/entrar")
def entrar(request: Request, erro: str | None = None):
    return tela(
        request, "entrar.html", "entrar", publica=True,
        erro=erro,
        usuario_demo=USUARIO_DEMO,
        senha_e_demo=os.environ.get("RADAR_SENHA_DEMO") == "admin",
    )

