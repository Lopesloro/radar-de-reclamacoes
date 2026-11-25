"""A ficha do cliente (CNPJ, responsável, contato e onde ele está no Google e no
iFood) é gravada cifrada, ou não é gravada.

Quem pediu: a equipe cadastra cliente novo na frente da banca, e os dados de
quem contrata não podem ficar em texto no banco. Mesma regra do cofre: sem
`RADAR_COFRE_CHAVE`, o sistema recusa em vez de gravar em texto.
"""

import re
import uuid

import pytest
from sqlalchemy import select, text

from app.banco import modelo
from app.banco import sessao as banco
from app.seguranca import cofre

CNPJ = "12.345.678/0001-95"


@pytest.fixture
def com_chave(monkeypatch):
    monkeypatch.setenv(cofre.VARIAVEL_CHAVE, cofre.gerar_chave())


def _token(sessao, caminho="/admin/clientes") -> str:
    return re.search(r'name="csrf" value="([^"]+)"', sessao.get(caminho).text).group(1)


def _cadastrar(equipe, **extra):
    identificador = f"ficha-{uuid.uuid4().hex[:6]}"
    dados = {
        "csrf": _token(equipe), "identificador": identificador, "nome": "Bar de Teste",
        "negocio_nome": "Bar de Teste", "ramo": "Bar", "cidade": "Campinas, SP",
        "entrada": identificador, "cnpj": CNPJ, "responsavel": "Dona do Bar",
        "telefone": "(19) 99999-0000", "email_contato": "dona@exemplo.com.br",
        "google_local": "https://maps.google.com/?cid=123", "ifood_loja": "loja-42",
    }
    dados.update(extra)
    return identificador, equipe.post("/admin/clientes", data=dados, follow_redirects=False)


def test_a_ficha_vai_cifrada_para_o_banco_e_volta_legivel_na_tela_da_equipe(equipe, com_chave):
    identificador, resposta = _cadastrar(equipe)
    assert resposta.status_code == 200, resposta.text[:300]
    with banco.Sessao() as sessao:
        bruta = sessao.execute(text("SELECT ficha_cifrada FROM empresa WHERE id = :i"),
                               {"i": identificador}).scalar()
    assert bruta, "a ficha precisa estar gravada"
    for dado in ("12345678000195", CNPJ, "Dona do Bar", "99999", "dona@exemplo", "loja-42"):
        assert dado not in bruta, f"{dado} está em texto no banco"
    pagina = equipe.get(f"/admin/clientes/{identificador}").text
    assert "12.345.678/0001-95" in pagina
    assert "Dona do Bar" in pagina


def test_sem_chave_de_cofre_a_ficha_e_recusada_e_nada_e_criado(equipe, monkeypatch):
    monkeypatch.setenv(cofre.VARIAVEL_CHAVE, "")
    identificador, resposta = _cadastrar(equipe)
    assert "erro=" in resposta.headers.get("location", "")
    with banco.Sessao() as sessao:
        assert sessao.get(modelo.Empresa, identificador) is None


def test_cnpj_invalido_e_recusado(equipe, com_chave):
    _, resposta = _cadastrar(equipe, cnpj="123")
    assert "erro=" in resposta.headers.get("location", "")


def test_cada_cliente_ganha_as_proprias_fontes_aguardando(equipe, com_chave):
    """Google e iFood ficam registrados por cliente, prontos para quando a
    plataforma autorizar. A leitura automática não roda: a tela diz o que falta."""
    identificador, _ = _cadastrar(equipe)
    with banco.Sessao() as sessao:
        fontes = sessao.scalars(select(modelo.Fonte).where(
            modelo.Fonte.empresa_id == identificador)).all()
        assert {f.plataforma for f in fontes} == {"google", "ifood"}
        assert {f.estado for f in fontes} == {"aguardando"}
        # O identificador na plataforma é dado do cliente: vai na ficha cifrada, não aqui.
        assert all(not f.identificador_externo for f in fontes)
    pagina = equipe.get(f"/admin/clientes/{identificador}").text
    assert "aguardando autorização" in pagina


def test_a_equipe_corrige_a_ficha_depois(equipe, com_chave):
    identificador, _ = _cadastrar(equipe)
    resposta = equipe.post(f"/admin/clientes/{identificador}/ficha", data={
        "csrf": _token(equipe, f"/admin/clientes/{identificador}"),
        "cnpj": CNPJ, "responsavel": "Novo Responsável", "telefone": "",
        "email_contato": "", "google_local": "", "ifood_loja": "",
    }, follow_redirects=False)
    assert resposta.status_code == 303
    assert "Novo Responsável" in equipe.get(f"/admin/clientes/{identificador}").text


def test_o_cliente_nao_le_a_propria_ficha_pela_area_da_equipe(cliente):
    assert cliente.get("/admin/clientes/bella-massa", follow_redirects=False).status_code == 403
