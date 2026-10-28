"""Senha só existe como hash scrypt, e a senha de demonstração vem do ambiente."""

import hashlib
from pathlib import Path

import pytest

from app.seguranca import senha
from app.seguranca.contas import NEGOCIOS_DE_DEMONSTRACAO, VARIAVEL_SENHA_DEMO, Contas

SENHA = "uma senha de teste, com acentuação: ação"


def test_hash_nao_guarda_a_senha_em_texto():
    guardado = senha.gerar_hash(SENHA)
    assert guardado.startswith("scrypt$")
    assert SENHA not in guardado
    assert SENHA.encode().hex() not in guardado


def test_hash_e_o_scrypt_da_biblioteca_padrao():
    _, n, r, p, sal, derivada = senha.gerar_hash(SENHA).split("$")
    esperado = hashlib.scrypt(
        SENHA.encode(), salt=bytes.fromhex(sal), n=int(n), r=int(r), p=int(p),
        maxmem=2 * 128 * int(r) * (int(n) + int(p) + 2), dklen=32,
    )
    assert bytes.fromhex(derivada) == esperado


def test_senha_certa_confere_e_errada_nao():
    guardado = senha.gerar_hash(SENHA)
    assert senha.conferir(SENHA, guardado) is True
    assert senha.conferir(SENHA + " ", guardado) is False
    assert senha.conferir(SENHA.upper(), guardado) is False
    assert senha.conferir("", guardado) is False


def test_mesma_senha_gera_hashes_diferentes_porque_o_sal_e_sorteado():
    assert senha.gerar_hash(SENHA) != senha.gerar_hash(SENHA)


@pytest.mark.parametrize("lixo", ["", "lixo", "scrypt$1$2", "bcrypt$a$b$c$d$e", "scrypt$x$y$z$w$v",
                                  "scrypt$16384$8$1$zz$zz"])
def test_hash_malformado_nao_confere_e_nao_derruba_o_site(lixo):
    assert senha.conferir(SENHA, lixo) is False


def test_confere_com_os_parametros_gravados_no_hash():
    """O custo vem de dentro do hash: dá para aumentá-lo depois sem invalidar quem já existe."""
    antigo = senha._formatar(SENHA, n=2 ** 12, r=8, p=1)
    assert antigo.split("$")[1] == "4096"
    assert senha.conferir(SENHA, antigo) is True


def test_sem_variavel_de_ambiente_ninguem_entra():
    contas = Contas.da_demonstracao({})
    for usuario in NEGOCIOS_DE_DEMONSTRACAO:
        assert contas.autenticar(usuario, "") is None
        assert contas.autenticar(usuario, "qualquer") is None
    assert Contas.da_demonstracao({VARIAVEL_SENHA_DEMO: ""}).autenticar("bella", "") is None


def test_senha_de_demonstracao_vem_do_ambiente():
    contas = Contas.da_demonstracao({VARIAVEL_SENHA_DEMO: "valor-so-deste-teste"})
    assert contas.autenticar("bella", "valor-so-deste-teste") is not None
    assert contas.autenticar("bella", "outro-valor") is None


def test_cada_conta_entra_so_na_sua_empresa():
    contas = Contas.da_demonstracao({VARIAVEL_SENHA_DEMO: "x1"})
    entradas = {u: contas.autenticar(u, "x1").empresa_id for u in NEGOCIOS_DE_DEMONSTRACAO}
    assert entradas == NEGOCIOS_DE_DEMONSTRACAO
    assert len(set(entradas.values())) == len(entradas) >= 2


def test_conta_guarda_hash_e_nunca_a_senha():
    contas = Contas.da_demonstracao({VARIAVEL_SENHA_DEMO: "x1-segredo"})
    conta = contas.autenticar("bella", "x1-segredo")
    assert conta.hash_senha.startswith("scrypt$")
    assert "x1-segredo" not in repr(conta)


def test_usuario_ignora_maiusculas_e_espacos_nas_pontas():
    contas = Contas.da_demonstracao({VARIAVEL_SENHA_DEMO: "x1"})
    assert contas.autenticar("  Bella ", "x1") is not None


def test_usuario_inexistente_e_senha_errada_dao_a_mesma_recusa():
    contas = Contas.da_demonstracao({VARIAVEL_SENHA_DEMO: "x1"})
    assert contas.autenticar("fantasma", "x1") is None
    assert contas.autenticar("bella", "errada") is None


def test_usuario_inexistente_tambem_paga_o_custo_do_hash(monkeypatch):
    """Sem isso, o tempo de resposta contaria quais usuários existem."""
    contas = Contas.da_demonstracao({VARIAVEL_SENHA_DEMO: "x1"})
    contas.autenticar("fantasma", "x1")       # aquece o hash de mentira, que é calculado uma vez só
    calculos = []
    original = senha._derivar
    monkeypatch.setattr(senha, "_derivar", lambda *a: calculos.append(1) or original(*a))
    contas.autenticar("bella", "errada")
    existente = len(calculos)
    contas.autenticar("fantasma", "x1")
    assert existente == 1
    assert len(calculos) == 2


def test_nenhum_arquivo_do_pacote_tem_senha_fixa():
    pacote = Path(__file__).resolve().parents[2] / "app" / "seguranca"
    for arquivo in pacote.glob("*.py"):
        codigo = arquivo.read_text(encoding="utf-8")
        assert '"admin"' not in codigo and "'admin'" not in codigo, arquivo.name
