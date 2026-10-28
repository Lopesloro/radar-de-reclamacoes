"""Pequenas funções que os testes de segurança repetem."""

import re
import secrets

# Sorteada a cada execução: o teste nunca depende de uma senha conhecida.
SENHA = secrets.token_urlsafe(12)
CHAVE = secrets.token_urlsafe(32)

FORMULARIO_DE_ENTRADA = """
<form method="post" action="/entrar">
  <input type="hidden" name="csrf" value="{{ request.state.csrf }}">
  <input type="hidden" name="proximo" value="{{ request.query_params.get('proximo', '') }}">
</form>
"""


def token_da_pagina(cliente) -> str:
    """Lê o token do formulário de entrada, como o navegador leria."""
    pagina = cliente.get("/entrar").text
    return re.search(r'name="csrf" value="([^"]+)"', pagina).group(1)


def entrar(cliente, usuario: str, senha: str = SENHA, proximo: str = "", token: str | None = None):
    token = token_da_pagina(cliente) if token is None else token
    dados = {"usuario": usuario, "senha": senha, "csrf": token}
    if proximo:
        dados["proximo"] = proximo
    return cliente.post("/entrar", data=dados)


def sair(cliente, token: str):
    return cliente.post("/sair", data={"csrf": token})
