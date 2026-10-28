"""Limite de tentativas por origem e o destino seguro depois do login."""

import pytest

from app.seguranca.destino import caminho_interno
from app.seguranca.limite import LimiteDeTentativas, origem_de


class Relogio:
    def __init__(self):
        self.agora = 1000.0

    def __call__(self):
        return self.agora


@pytest.fixture
def relogio():
    return Relogio()


def test_bloqueia_ao_chegar_no_maximo_de_falhas(relogio):
    limite = LimiteDeTentativas(maximo=3, janela=60, relogio=relogio)
    for _ in range(2):
        limite.registrar_falha("a")
    assert limite.bloqueada("a") is False
    limite.registrar_falha("a")
    assert limite.bloqueada("a") is True


def test_origens_diferentes_nao_se_misturam(relogio):
    limite = LimiteDeTentativas(maximo=2, janela=60, relogio=relogio)
    limite.registrar_falha("a")
    limite.registrar_falha("a")
    assert limite.bloqueada("a") is True
    assert limite.bloqueada("b") is False


def test_libera_quando_as_falhas_saem_da_janela(relogio):
    limite = LimiteDeTentativas(maximo=2, janela=60, relogio=relogio)
    limite.registrar_falha("a")
    limite.registrar_falha("a")
    relogio.agora += 59
    assert limite.bloqueada("a") is True
    relogio.agora += 2
    assert limite.bloqueada("a") is False


def test_a_janela_desliza_falha_por_falha(relogio):
    limite = LimiteDeTentativas(maximo=2, janela=60, relogio=relogio)
    limite.registrar_falha("a")
    relogio.agora += 40
    limite.registrar_falha("a")
    assert limite.bloqueada("a") is True
    relogio.agora += 25          # a primeira falha (65s atrás) saiu; a segunda (25s) fica
    assert limite.bloqueada("a") is False


def test_origem_desconhecida_nunca_e_liberada_de_graca(relogio):
    limite = LimiteDeTentativas(maximo=1, janela=60, relogio=relogio)
    limite.registrar_falha(origem_de(None))
    assert limite.bloqueada(origem_de(None)) is True


def test_memoria_nao_cresce_sem_limite(relogio):
    limite = LimiteDeTentativas(maximo=3, janela=60, relogio=relogio, origens_guardadas=5)
    for i in range(5):
        limite.registrar_falha(f"antiga-{i}")
    relogio.agora += 120
    limite.registrar_falha("nova")
    assert len(limite) == 1
    assert limite.bloqueada("antiga-0") is False


def test_ipv4_vale_o_endereco_inteiro():
    assert origem_de("203.0.113.7") == "203.0.113.7"


def test_ipv6_vale_o_bloco_de_64_bits():
    """Quem recebe um IPv6 recebe um /64 inteiro: contar o endereço deixaria trocar de origem de graça."""
    assert origem_de("2001:db8:1:2:aaaa:bbbb:cccc:dddd") == origem_de("2001:db8:1:2::1")
    assert origem_de("2001:db8:1:2::1") != origem_de("2001:db8:1:3::1")


@pytest.mark.parametrize("destino", ["/resumo", "/previsao/patinhas?categoria=preco", "/", "/a/b/c"])
def test_caminho_interno_passa(destino):
    assert caminho_interno(destino) == destino


@pytest.mark.parametrize("destino", [
    None, "", "resumo", "https://exemplo.invalido/roubo", "http://exemplo.invalido", "//exemplo.invalido",
    "///exemplo.invalido", "/\\exemplo.invalido", "/..\\exemplo", "javascript:alert(1)", "\\\\exemplo",
    "/ok\r\nSet-Cookie: a=b", "/\t/exemplo.invalido", " //exemplo.invalido", "/resumo\x00",
])
def test_caminho_externo_ou_estranho_cai_no_padrao(destino):
    assert caminho_interno(destino) == "/resumo"


def test_padrao_pode_ser_trocado():
    assert caminho_interno("https://x.invalido", padrao="/inicio") == "/inicio"
