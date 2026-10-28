"""Entrada, sessão e saída."""

from urllib.parse import parse_qs, urlsplit

import pytest
from starlette.testclient import TestClient

from app.seguranca import sessao
from app.seguranca.limite import TENTATIVAS_MAXIMAS
from app.seguranca.sessao import NOME_DO_COOKIE, VALIDADE_SEGUNDOS, Assinador, Sessao
from tests.seguranca.ajudas import CHAVE, SENHA, entrar, sair, token_da_pagina

ROTAS_INTERNAS = [
    "/resumo", "/comercio/bella-massa", "/previsao", "/previsao/bella-massa", "/avisos", "/investigacao",
    "/investigacao/bella-massa/demora", "/simulador", "/simulador/bella-massa", "/experimentos",
    "/experimentos/exp-bella-entregador", "/confianca", "/o-que-falta", "/ajuda", "/sobre",
]


# ------------------------------------------------------------------ quem pode ver o quê

@pytest.mark.parametrize("rota", ROTAS_INTERNAS)
def test_tela_interna_sem_entrada_manda_para_a_entrada(anonimo, rota):
    resposta = anonimo.get(rota)
    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/entrar?proximo=")


def test_endereco_que_nao_existe_tambem_manda_para_a_entrada(anonimo):
    """Quem está de fora não descobre o que existe e o que não existe."""
    assert anonimo.get("/pagina-que-nao-existe").status_code == 303


def test_o_destino_pedido_volta_inteiro_na_entrada(anonimo):
    resposta = anonimo.get("/previsao/patinhas?categoria=preco")
    consulta = parse_qs(urlsplit(resposta.headers["location"]).query)
    assert consulta["proximo"] == ["/previsao/patinhas?categoria=preco"]


@pytest.mark.parametrize("rota", ["/", "/entrar", "/saude", "/static/css/app.css"])
def test_pagina_publica_abre_sem_entrar(anonimo, rota):
    assert anonimo.get(rota).status_code == 200


def test_tela_interna_abre_depois_de_entrar(bella):
    assert bella.get("/resumo").status_code == 200
    assert bella.get("/comercio/bella-massa").status_code == 200


# ------------------------------------------------------------------ a entrada

def test_entrada_leva_ao_destino_pedido(anonimo):
    resposta = entrar(anonimo, "bella", proximo="/previsao/bella-massa")
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/previsao/bella-massa"


def test_entrada_sem_destino_leva_ao_resumo(anonimo):
    assert entrar(anonimo, "bella").headers["location"] == "/resumo"


@pytest.mark.parametrize("destino", [
    "https://exemplo.invalido/roubo", "//exemplo.invalido", "/\\exemplo.invalido",
])
def test_destino_externo_e_ignorado(anonimo, destino):
    assert entrar(anonimo, "bella", proximo=destino).headers["location"] == "/resumo"


def test_senha_errada_nao_entra(anonimo):
    resposta = entrar(anonimo, "bella", senha="errada")
    assert resposta.headers["location"] == "/entrar?erro=credencial"
    assert anonimo.get("/resumo").status_code == 303


def test_usuario_que_nao_existe_recebe_a_mesma_resposta_que_senha_errada(anonimo):
    a = entrar(anonimo, "fantasma")
    b = entrar(anonimo, "bella", senha="errada")
    assert (a.status_code, a.headers["location"]) == (b.status_code, b.headers["location"])


def test_cada_usuario_entra_na_sua_empresa(site):
    esperado = [("bella", "bella-massa"), ("sorriso", "sorriso-claro"), ("patinhas", "patinhas")]
    for usuario, empresa in esperado:
        cliente = TestClient(site, follow_redirects=False)
        entrar(cliente, usuario)
        assert cliente.get("/_teste/quem").json() == {"nome": usuario, "empresa": empresa}


def test_entrada_aceita_texto_com_acento_sem_quebrar(anonimo):
    assert entrar(anonimo, "joão", senha="ação").headers["location"] == "/entrar?erro=credencial"


# ------------------------------------------------------------------ limite de tentativas

def test_tentativas_demais_bloqueiam_a_origem_mesmo_com_a_senha_certa(anonimo):
    token = token_da_pagina(anonimo)
    for _ in range(TENTATIVAS_MAXIMAS):
        entrar(anonimo, "bella", senha="errada", token=token)
    resposta = entrar(anonimo, "bella", token=token)
    assert resposta.headers["location"] == "/entrar?erro=bloqueado"
    assert anonimo.get("/resumo").status_code == 303


def test_o_bloqueio_vale_para_a_origem_e_nao_para_o_site_todo(site):
    agressor = TestClient(site, follow_redirects=False, client=("203.0.113.9", 4000))
    for _ in range(TENTATIVAS_MAXIMAS):
        entrar(agressor, "bella", senha="errada")
    vizinho = TestClient(site, follow_redirects=False, client=("203.0.113.10", 4000))
    assert entrar(vizinho, "bella").headers["location"] == "/resumo"


def test_acertos_nao_contam_como_tentativa(site):
    for _ in range(TENTATIVAS_MAXIMAS + 2):
        cliente = TestClient(site, follow_redirects=False)
        assert entrar(cliente, "bella").headers["location"] == "/resumo"


# ------------------------------------------------------------------ token contra CSRF

def test_entrada_com_token_inventado_e_recusada(anonimo):
    resposta = entrar(anonimo, "bella", token="inventado")
    assert resposta.headers["location"] == "/entrar?erro=sessao"
    assert anonimo.get("/resumo").status_code == 303


def test_entrada_sem_token_e_recusada(anonimo):
    resposta = anonimo.post("/entrar", data={"usuario": "bella", "senha": SENHA})
    assert resposta.headers["location"] == "/entrar?erro=sessao"


def test_token_de_outra_sessao_nao_vale(site):
    de_outro = token_da_pagina(TestClient(site, follow_redirects=False))
    cliente = TestClient(site, follow_redirects=False)
    token_da_pagina(cliente)
    assert entrar(cliente, "bella", token=de_outro).headers["location"] == "/entrar?erro=sessao"


def test_token_recusado_nao_gasta_tentativa(anonimo):
    for _ in range(TENTATIVAS_MAXIMAS + 2):
        entrar(anonimo, "bella", token="inventado")
    assert entrar(anonimo, "bella").headers["location"] == "/resumo"


def test_todo_post_exige_o_token_ate_o_que_nao_e_de_entrada(bella):
    assert bella.post("/_teste/altera", data={}).status_code == 403
    assert bella.post("/_teste/altera", data={"csrf": "inventado"}).status_code == 403
    assert bella.post("/_teste/altera", json={"csrf": "x"}).status_code == 403


def test_post_passa_com_o_token_no_formulario_ou_no_cabecalho(bella):
    token = token_da_pagina(bella)
    assert bella.post("/_teste/altera", data={"csrf": token}).text == "alterado"
    assert bella.post("/_teste/altera", headers={"X-CSRF-Token": token}).text == "alterado"


def test_corpo_que_nao_e_formulario_chega_intacto_na_rota(bella):
    """O middleware não pode engolir um corpo que não leu."""
    token = token_da_pagina(bella)
    resposta = bella.post("/_teste/eco", json={"a": [1, 2], "b": "ação"}, headers={"X-CSRF-Token": token})
    assert resposta.json() == {"a": [1, 2], "b": "ação"}


def test_token_de_outro_usuario_nao_vale(bella, patinhas):
    assert bella.post("/_teste/altera", data={"csrf": token_da_pagina(patinhas)}).status_code == 403


def test_leitura_nao_pede_token(bella):
    assert bella.get("/resumo").status_code == 200


def test_post_sem_entrar_vai_para_a_entrada_e_nao_le_o_corpo(anonimo):
    resposta = anonimo.post("/_teste/altera", data={"csrf": "x"})
    assert resposta.status_code == 303
    assert resposta.headers["location"].startswith("/entrar")


def test_corpo_enorme_e_recusado(bella):
    resposta = bella.post("/_teste/altera", data={"csrf": token_da_pagina(bella), "lixo": "x" * 200_000})
    assert resposta.status_code == 413


def test_o_formulario_chega_inteiro_na_rota_depois_de_conferido(anonimo):
    """A conferência lê o corpo; a rota precisa receber os mesmos campos."""
    assert entrar(anonimo, "bella", proximo="/avisos").headers["location"] == "/avisos"


# ------------------------------------------------------------------ sair

def test_sair_encerra_a_sessao(bella):
    resposta = sair(bella, token_da_pagina(bella))
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/"
    assert bella.get("/resumo").status_code == 303


def test_sair_manda_o_navegador_apagar_o_cookie(bella):
    cookie = sair(bella, token_da_pagina(bella)).headers["set-cookie"].lower()
    assert f"{NOME_DO_COOKIE}=" in cookie and "max-age=0" in cookie


def test_sair_tambem_exige_o_token(bella):
    assert bella.post("/sair", data={}).status_code == 403
    assert bella.post("/sair", data={"csrf": "inventado"}).status_code == 403
    assert bella.get("/resumo").status_code == 200


def test_sair_por_link_nao_funciona(bella):
    assert bella.get("/sair").status_code == 405
    assert bella.get("/resumo").status_code == 200


# ------------------------------------------------------------------ cookie e validade

def test_cookie_e_httponly_e_samesite_lax(anonimo):
    cookie = entrar(anonimo, "bella").headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie
    assert "secure" not in cookie    # em http de desenvolvimento o navegador descartaria o cookie


def test_cookie_e_secure_quando_o_acesso_e_https(site):
    cliente = TestClient(site, base_url="https://testserver", follow_redirects=False)
    assert "secure" in entrar(cliente, "bella").headers["set-cookie"].lower()


def test_cookie_dura_no_maximo_oito_horas(anonimo):
    cookie = entrar(anonimo, "bella").headers["set-cookie"].lower()
    segundos = int(cookie.split("max-age=")[1].split(";")[0])
    assert VALIDADE_SEGUNDOS == 8 * 60 * 60
    assert VALIDADE_SEGUNDOS - 5 <= segundos <= VALIDADE_SEGUNDOS


def test_pagina_publica_cria_sessao_mas_saude_e_estatico_nao(anonimo):
    assert NOME_DO_COOKIE in anonimo.get("/entrar").headers["set-cookie"]
    novo = TestClient(anonimo.app, follow_redirects=False)
    assert "set-cookie" not in novo.get("/saude").headers
    assert "set-cookie" not in novo.get("/static/css/app.css").headers


def test_sessao_vence_em_oito_horas_mesmo_com_uso(monkeypatch, site):
    hora = [1_000_000.0]
    monkeypatch.setattr(sessao, "_agora", lambda: hora[0])
    cliente = TestClient(site, follow_redirects=False)
    entrar(cliente, "bella")
    hora[0] += VALIDADE_SEGUNDOS - 3600
    assert cliente.get("/resumo").status_code == 200       # usar a sessão...
    hora[0] += 3600 - 1
    assert cliente.get("/resumo").status_code == 200
    hora[0] += 2
    assert cliente.get("/resumo").status_code == 303       # ...não adia o fim: o prazo conta da entrada


def test_cookie_adulterado_nao_vale(bella):
    valor = bella.cookies[NOME_DO_COOKIE]
    bella.cookies.clear()
    bella.cookies.set(NOME_DO_COOKIE, valor[:-6] + ("AAAAAA" if not valor.endswith("AAAAAA") else "BBBBBB"))
    assert bella.get("/resumo").status_code == 303


def test_cookie_assinado_com_outra_chave_nao_vale(site):
    falso = Assinador("chave-do-atacante").assinar(
        Sessao(csrf="x", inicio=sessao._agora(), usuario="bella", empresa_id="bella-massa"))
    cliente = TestClient(site, follow_redirects=False)
    cliente.cookies.set(NOME_DO_COOKIE, falso)
    assert cliente.get("/resumo").status_code == 303


def test_cookie_assinado_com_a_chave_certa_vale(site):
    """Contraprova do teste de cima: o que falha lá é a chave, não o formato do cookie."""
    verdadeiro = Assinador(CHAVE).assinar(
        Sessao(csrf="x", inicio=sessao._agora(), usuario="bella", empresa_id="bella-massa"))
    cliente = TestClient(site, follow_redirects=False)
    cliente.cookies.set(NOME_DO_COOKIE, verdadeiro)
    assert cliente.get("/resumo").status_code == 200


def test_entrar_troca_o_cookie_e_o_token(site):
    cliente = TestClient(site, follow_redirects=False)
    token_antes = token_da_pagina(cliente)
    cookie_antes = cliente.cookies[NOME_DO_COOKIE]
    entrar(cliente, "bella", token=token_antes)
    assert cliente.cookies[NOME_DO_COOKIE] != cookie_antes
    assert token_da_pagina(cliente) != token_antes
    intruso = TestClient(site, follow_redirects=False)
    intruso.cookies.set(NOME_DO_COOKIE, cookie_antes)
    assert intruso.get("/resumo").status_code == 303


def _app_vazio(contas):
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse

    from app.seguranca import instalar
    app = FastAPI()
    instalar(app, contas=contas)       # sem `chave`: a chave vem do ambiente

    @app.get("/privado")
    def privado():
        return PlainTextResponse("segredo")

    return app


def _cookie_com(chave: str) -> str:
    quem = Sessao(csrf="x", inicio=sessao._agora(), usuario="bella", empresa_id="bella-massa")
    return Assinador(chave).assinar(quem)


def test_a_chave_da_sessao_vem_do_ambiente(contas, monkeypatch):
    monkeypatch.setenv("RADAR_CHAVE", "chave-so-deste-teste")
    cliente = TestClient(_app_vazio(contas), follow_redirects=False)
    cliente.cookies.set(NOME_DO_COOKIE, _cookie_com("chave-so-deste-teste"))
    assert cliente.get("/privado").text == "segredo"


def test_sem_chave_no_ambiente_o_servidor_sorteia_uma_que_ninguem_conhece(contas, monkeypatch):
    monkeypatch.delenv("RADAR_CHAVE", raising=False)
    cliente = TestClient(_app_vazio(contas), follow_redirects=False)
    for palpite in ("", "radar", "chave-so-deste-teste", "admin"):
        cliente.cookies.set(NOME_DO_COOKIE, _cookie_com(palpite or "vazia"))
        assert cliente.get("/privado").status_code == 303
