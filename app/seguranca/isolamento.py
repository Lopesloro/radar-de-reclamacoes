"""Isolamento entre empresas: a empresa de quem pede vem da sessão e de mais nenhum lugar.

Três travas, da mais ampla para a mais estreita:

1. `vigiar_empresa` vale para **toda** rota (ligada por `instalar`). Se o
   endereço, a consulta ou o formulário citam um negócio que não é da empresa da
   sessão, a resposta é 403 antes de a rota rodar. Assim uma tela nova já nasce
   protegida, sem ninguém lembrar de conferir.
2. `exigir_comercio` para a rota que descobre o negócio por outro caminho.
3. `exigir_admin` para a área de administração, que não é de cliente nenhum.

Negócio que não existe leva o mesmo 403 que negócio dos outros: com 404 de um
lado e 403 do outro, a diferença contaria quais negócios existem.

O administrador atravessa a trava 1 de propósito — é a equipe do Radar operando
o sistema, e sem isso não há como cadastrar cliente. Em troca, toda ação dele
que muda algo passa pela trilha de auditoria (`app/auditoria.py`), com empresa,
usuário e hora.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request
from starlette.requests import HTTPConnection

from app.seguranca import sessao as _sessao

NOMES_DE_EMPRESA = ("empresa", "empresa_id", "comercio", "comercio_id")
NOME_NO_ESTADO = "comercios_permitidos"


@dataclass(frozen=True)
class Usuario:
    nome: str
    empresa_id: str
    papel: str = "dono"
    # O identificador na tabela `usuario`. É ele que a auditoria grava, e não
    # `nome`, que é o que a pessoa digita para entrar.
    identificador: str | None = None

    @property
    def e_admin(self) -> bool:
        return self.papel == "admin"


def usuario_atual(requisicao: HTTPConnection) -> Usuario | None:
    atual = _sessao.da_requisicao(requisicao)
    if atual is None or atual.usuario is None or atual.empresa_id is None:
        return None
    return Usuario(nome=atual.usuario, empresa_id=atual.empresa_id,
                   papel=atual.papel or "dono", identificador=atual.usuario_id)


def empresa_do_usuario(requisicao: HTTPConnection) -> str:
    """A única fonte aceita para saber de qual empresa filtrar uma consulta."""
    usuario = usuario_atual(requisicao)
    if usuario is None:
        raise HTTPException(status_code=401, detail="É preciso entrar.")
    return usuario.empresa_id


def exigir_admin(requisicao: HTTPConnection) -> Usuario:
    usuario = usuario_atual(requisicao)
    if usuario is None:
        raise HTTPException(status_code=401, detail="É preciso entrar.")
    if not usuario.e_admin:
        raise HTTPException(status_code=403, detail="Essa área é da equipe do Radar.")
    return usuario


def permitidos(requisicao: HTTPConnection) -> frozenset[str]:
    """Os identificadores que a sessão pode citar: a empresa dela e os negócios dela.

    Guardado no estado do pedido: a trava global e a rota perguntam a mesma coisa,
    e sem a memória seriam duas consultas por pedido.
    """
    usuario = usuario_atual(requisicao)
    if usuario is None:
        return frozenset()
    estado = requisicao.scope.setdefault("state", {})
    guardado = estado.get(NOME_NO_ESTADO)
    if guardado is not None:
        return guardado
    from app import servicos

    conjunto = frozenset({usuario.empresa_id, *servicos.ids_de_comercio(usuario.empresa_id)})
    estado[NOME_NO_ESTADO] = conjunto
    return conjunto


def exigir_comercio(requisicao: HTTPConnection, comercio_id: str) -> str:
    """Recusa com 403 o negócio que não é da empresa da sessão. Devolve a empresa."""
    empresa = empresa_do_usuario(requisicao)
    if usuario_atual(requisicao).e_admin:
        return empresa
    if comercio_id not in permitidos(requisicao):
        raise HTTPException(status_code=403, detail="Esse negócio não é o seu.")
    return empresa


# Nome antigo, mantido porque as rotas e os testes de isolamento chamam assim.
exigir_empresa = exigir_comercio


def vigiar_empresa(request: Request) -> None:
    """Dependência de todas as rotas: o pedido não pode apontar para um negócio de outra empresa."""
    usuario = usuario_atual(request)
    if usuario is None:       # rota pública: não há empresa de onde comparar
        return
    if usuario.e_admin:       # a equipe do Radar opera o sistema; a auditoria registra
        return
    formulario = request.scope.get("state", {}).get("formulario", {})   # lido pelo middleware
    citadas: list[str] = []
    for nome in NOMES_DE_EMPRESA:
        if nome in request.path_params:
            citadas.append(request.path_params[nome])
        citadas += request.query_params.getlist(nome)
        citadas += formulario.get(nome, [])
    if not citadas:
        return
    meus = permitidos(request)
    if any(citada not in meus for citada in citadas):
        raise HTTPException(status_code=403, detail="Esse negócio não é o seu.")
