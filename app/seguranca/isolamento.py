"""Isolamento entre empresas: a empresa de quem pede vem da sessão e de mais nenhum lugar.

Duas travas. A primeira vale para toda rota (`vigiar_empresa`, ligada por `instalar`): se o endereço,
a consulta ou o formulário citam uma empresa (`empresa` ou `empresa_id`) que não é a da sessão, a
resposta é 403 antes da rota rodar, para uma tela nova não esquecer de conferir. A segunda são as
funções abaixo, para a rota que descobre a empresa por outro caminho (um número de teste, por exemplo):
`empresa_do_usuario` diz qual é, `exigir_empresa` recusa a dos outros.

Empresa que não existe leva o mesmo 403 que empresa dos outros: com 404 de um lado e 403 do outro,
a diferença contaria quais empresas existem.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request
from starlette.requests import HTTPConnection

from app.seguranca import sessao as _sessao

NOMES_DE_EMPRESA = ("empresa", "empresa_id")


@dataclass(frozen=True)
class Usuario:
    nome: str
    empresa_id: str


def usuario_atual(requisicao: HTTPConnection) -> Usuario | None:
    atual = _sessao.da_requisicao(requisicao)
    if atual is None or atual.usuario is None or atual.empresa_id is None:
        return None
    return Usuario(nome=atual.usuario, empresa_id=atual.empresa_id)


def empresa_do_usuario(requisicao: HTTPConnection) -> str:
    """A única fonte aceita para saber de qual empresa filtrar uma consulta."""
    usuario = usuario_atual(requisicao)
    if usuario is None:
        raise HTTPException(status_code=401, detail="É preciso entrar.")
    return usuario.empresa_id


def exigir_empresa(requisicao: HTTPConnection, empresa_id: str) -> str:
    propria = empresa_do_usuario(requisicao)
    if empresa_id != propria:
        raise HTTPException(status_code=403, detail="Esse negócio não é o seu.")
    return propria


def vigiar_empresa(request: Request) -> None:
    """Dependência de todas as rotas: o pedido não pode apontar para outra empresa que não a da sessão."""
    usuario = usuario_atual(request)
    if usuario is None:       # rota pública: não há empresa de onde comparar
        return
    formulario = request.scope.get("state", {}).get("formulario", {})   # lido pelo middleware
    citadas: list[str] = []
    for nome in NOMES_DE_EMPRESA:
        if nome in request.path_params:
            citadas.append(request.path_params[nome])
        citadas += request.query_params.getlist(nome)
        citadas += formulario.get(nome, [])
    if any(empresa != usuario.empresa_id for empresa in citadas):
        raise HTTPException(status_code=403, detail="Esse negócio não é o seu.")
