"""Página pública e a porta de entrada."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app import conteudo, servicos
from app.rotas import acesso_provisorio
from app.rotas._telas import tela

rotas = APIRouter()


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
        usuario_demo=acesso_provisorio.USUARIO_DEMO,
        senha_e_demo=acesso_provisorio.SENHA_E_DEMO,
    )


@rotas.post("/entrar")
def fazer_entrada(usuario: str = Form(""), senha: str = Form("")):
    # PROVISÓRIO: confere a credencial de demonstração e segue para o resumo, sem
    # sessão. A entrada de verdade (sessão, CSRF, limite de tentativas) é do Matheus.
    if acesso_provisorio.credencial_confere(usuario, senha):
        return RedirectResponse("/resumo", status_code=303)
    return RedirectResponse("/entrar?erro=credencial", status_code=303)
