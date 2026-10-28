"""Uma empresa nunca vê o que é de outra. A empresa vem da sessão; a URL e o formulário só podem concordar."""

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.testclient import TestClient

from app.seguranca import empresa_do_usuario, exigir_empresa, usuario_atual
from tests.seguranca.ajudas import entrar, token_da_pagina

# Cada molde é uma tela de verdade do site que traz a empresa no endereço.
TELAS_POR_EMPRESA = [
    "/comercio/{}", "/previsao/{}", "/previsao/{}?categoria=preco", "/simulador/{}",
    "/investigacao/{}/demora",
]


@pytest.mark.parametrize("molde", TELAS_POR_EMPRESA)
def test_empresa_a_pede_dado_da_empresa_b_e_e_recusada(bella, molde):
    """A prova pedida pela banca: entra como Bella Massa e pede os dados da Patinhas."""
    resposta = bella.get(molde.format("patinhas"))
    assert resposta.status_code == 403
    assert "Patinhas" not in resposta.text


@pytest.mark.parametrize("molde", TELAS_POR_EMPRESA)
def test_e_o_contrario_tambem(patinhas, molde):
    resposta = patinhas.get(molde.format("bella-massa"))
    assert resposta.status_code == 403
    assert "Bella Massa" not in resposta.text


@pytest.mark.parametrize("molde", TELAS_POR_EMPRESA)
def test_cada_empresa_abre_a_sua_propria_tela(bella, patinhas, molde):
    assert bella.get(molde.format("bella-massa")).status_code == 200
    assert patinhas.get(molde.format("patinhas")).status_code == 200


def test_empresa_que_nao_existe_e_recusada_como_a_dos_outros(bella):
    """Se desse 404 aqui e 403 ali, a diferença contaria quais empresas existem."""
    assert bella.get("/comercio/nao-existe").status_code == 403
    assert bella.get("/comercio/patinhas").status_code == bella.get("/comercio/nao-existe").status_code


def test_empresa_no_endereco_com_outra_grafia_tambem_e_recusada(bella):
    assert bella.get("/comercio/BELLA-MASSA").status_code == 403
    assert bella.get("/comercio/bella-massa%2F..%2Fpatinhas").status_code in (403, 404)


@pytest.mark.parametrize("parametro", ["empresa", "empresa_id"])
def test_empresa_de_outro_na_consulta_do_endereco_e_recusada(bella, parametro):
    assert bella.get(f"/resumo?{parametro}=patinhas").status_code == 403
    assert bella.get(f"/resumo?{parametro}=bella-massa").status_code == 200


@pytest.mark.parametrize("campo", ["empresa", "empresa_id"])
def test_empresa_de_outro_no_formulario_e_recusada(bella, campo):
    token = token_da_pagina(bella)
    assert bella.post("/_teste/altera", data={"csrf": token, campo: "patinhas"}).status_code == 403
    assert bella.post("/_teste/altera", data={"csrf": token, campo: "bella-massa"}).status_code == 200


def test_uma_empresa_de_cada_vez_sem_misturar_as_sessoes(site):
    a, b = TestClient(site, follow_redirects=False), TestClient(site, follow_redirects=False)
    entrar(a, "bella")
    entrar(b, "patinhas")
    assert a.get("/_teste/minha-empresa").text == "bella-massa"
    assert b.get("/_teste/minha-empresa").text == "patinhas"


def test_a_empresa_do_usuario_vem_da_sessao_e_nao_do_pedido(bella):
    resposta = bella.get("/_teste/minha-empresa?empresa=patinhas")
    assert resposta.status_code == 403            # a tentativa de apontar outra empresa já é recusada
    assert bella.get("/_teste/minha-empresa", headers={"X-Empresa": "patinhas"}).text == "bella-massa"


def test_exigir_empresa_dentro_da_rota_recusa_a_de_outro(bella):
    """Segunda trava, para telas que descobrem a empresa de outro jeito (ex.: pelo número de um teste)."""
    assert bella.get("/_teste/exigir/bella-massa").text == "bella-massa"
    assert bella.get("/_teste/exigir/patinhas").status_code == 403
    assert bella.get("/_teste/exigir/nao-existe").status_code == 403


def test_usuario_atual_conhece_o_nome_e_a_empresa(bella, anonimo):
    assert bella.get("/_teste/quem").json() == {"nome": "bella", "empresa": "bella-massa"}
    assert usuario_atual(_pedido_sem_sessao()) is None


def test_sem_sessao_nao_existe_empresa_do_usuario():
    with pytest.raises(HTTPException) as erro:
        empresa_do_usuario(_pedido_sem_sessao())
    assert erro.value.status_code == 401
    with pytest.raises(HTTPException) as erro:
        exigir_empresa(_pedido_sem_sessao(), "bella-massa")
    assert erro.value.status_code == 401


def _pedido_sem_sessao() -> Request:
    escopo = {"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b"", "state": {}}
    return Request(escopo)


def test_instalar_depois_das_rotas_e_recusado_em_voz_alta(contas):
    """Com a ordem errada a trava de empresa não vale nas rotas já incluídas: melhor quebrar na partida."""
    from fastapi import APIRouter, FastAPI

    from app.seguranca import instalar
    rotas = APIRouter()
    rotas.add_api_route("/algo", lambda: "x")
    app = FastAPI()
    app.include_router(rotas)
    with pytest.raises(RuntimeError, match="antes de qualquer rota"):
        instalar(app, contas=contas)
    outro = FastAPI()
    outro.add_api_route("/algo", lambda: "x")
    with pytest.raises(RuntimeError, match="antes de qualquer rota"):
        instalar(outro, contas=contas)
