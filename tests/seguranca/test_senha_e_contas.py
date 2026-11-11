"""Senha só existe como hash Argon2id, e nenhuma senha mora no código.

O formato mudou de scrypt para Argon2id nesta versão. Os dois primeiros testes
provam o formato novo; o terceiro prova que quem tinha hash scrypt continua
entrando, porque uma migração que obriga todo cliente a trocar de senha não é
migração, é reinício.
"""

import re
from pathlib import Path

import pytest

from app.seguranca import senha
from app.seguranca.contas import (
    ADMIN_PADRAO,
    VARIAVEL_ADMIN,
    VARIAVEL_ADMIN_USUARIO,
    Conta,
    Contas,
)

SENHA = "uma senha de teste, com acentuação: ação"


def test_hash_nao_guarda_a_senha_em_texto():
    guardado = senha.gerar_hash(SENHA)
    assert guardado.startswith("$argon2id$")
    assert SENHA not in guardado
    assert SENHA.encode().hex() not in guardado


def test_hash_carrega_os_parametros_que_a_owasp_recomenda():
    """m=19 MiB, t=2, p=1. O número está no hash, então dá para subi-lo depois."""
    guardado = senha.gerar_hash(SENHA)
    assert f"m={senha.MEMORIA_KIB}" in guardado
    assert f"t={senha.PASSAGENS}" in guardado
    assert f"p={senha.PARALELISMO}" in guardado
    assert senha.MEMORIA_KIB == 19456


def test_hash_antigo_de_scrypt_continua_conferindo():
    """Quem já tinha senha guardada não precisa trocar por causa da migração."""
    antigo = _hash_scrypt_antigo(SENHA)
    assert antigo.startswith("scrypt$")
    assert senha.conferir(SENHA, antigo) is True
    assert senha.conferir(SENHA + "x", antigo) is False
    assert senha.precisa_regerar(antigo) is True


def test_hash_de_hoje_nao_precisa_ser_regerado():
    assert senha.precisa_regerar(senha.gerar_hash(SENHA)) is False


def _hash_scrypt_antigo(valor: str) -> str:
    """Monta um hash no formato da primeira versão, para o teste de migração."""
    import hashlib
    import secrets

    sal = secrets.token_bytes(16)
    n, r, p = 2 ** 14, 8, 1
    derivada = hashlib.scrypt(
        valor.encode(), salt=sal, n=n, r=r, p=p,
        maxmem=2 * 128 * r * (n + p + 2), dklen=32,
    )
    return "$".join(["scrypt", str(n), str(r), str(p), sal.hex(), derivada.hex()])


def test_senha_certa_confere_e_errada_nao():
    guardado = senha.gerar_hash(SENHA)
    assert senha.conferir(SENHA, guardado) is True
    assert senha.conferir(SENHA + " ", guardado) is False
    assert senha.conferir(SENHA.upper(), guardado) is False
    assert senha.conferir("", guardado) is False


def test_mesma_senha_gera_hashes_diferentes_porque_o_sal_e_sorteado():
    assert senha.gerar_hash(SENHA) != senha.gerar_hash(SENHA)


@pytest.mark.parametrize("lixo", [
    "", "lixo", "scrypt$1$2", "bcrypt$a$b$c$d$e", "scrypt$x$y$z$w$v",
    "scrypt$16384$8$1$zz$zz", "$argon2id$v=19$m=19456,t=2,p=1$abc",
])
def test_hash_malformado_nao_confere_e_nao_derruba_o_site(lixo):
    assert senha.conferir(SENHA, lixo) is False


# ------------------------------------------------------------ contas

def test_sem_variavel_de_ambiente_ninguem_entra():
    """O padrão é fechado: sem RADAR_ADMIN_SENHA, zero contas."""
    contas = Contas.so_o_administrador({})
    assert len(contas) == 0
    assert contas.autenticar(ADMIN_PADRAO, "") is None
    assert contas.autenticar(ADMIN_PADRAO, "qualquer") is None
    assert len(Contas.so_o_administrador({VARIAVEL_ADMIN: ""})) == 0


def test_a_senha_do_administrador_vem_do_ambiente():
    contas = Contas.so_o_administrador({VARIAVEL_ADMIN: "valor-so-deste-teste"})
    conta = contas.autenticar(ADMIN_PADRAO, "valor-so-deste-teste")
    assert conta is not None and conta.papel == "admin" and conta.e_admin
    assert contas.autenticar(ADMIN_PADRAO, "outro-valor") is None


def test_o_nome_do_administrador_tambem_vem_do_ambiente():
    contas = Contas.so_o_administrador({VARIAVEL_ADMIN: "x1", VARIAVEL_ADMIN_USUARIO: "chefia"})
    assert contas.autenticar("chefia", "x1") is not None
    assert contas.autenticar(ADMIN_PADRAO, "x1") is None


def test_conta_guarda_hash_e_nunca_a_senha():
    contas = Contas.so_o_administrador({VARIAVEL_ADMIN: "x1-segredo"})
    conta = contas.autenticar(ADMIN_PADRAO, "x1-segredo")
    assert conta.hash_senha.startswith("$argon2id$")
    assert "x1-segredo" not in repr(conta)


def test_usuario_ignora_maiusculas_e_espacos_nas_pontas():
    contas = Contas.so_o_administrador({VARIAVEL_ADMIN: "x1"})
    assert contas.autenticar(f"  {ADMIN_PADRAO.upper()} ", "x1") is not None


def test_cada_conta_entra_so_na_sua_empresa():
    guardada = senha.gerar_hash("x1")
    contas = Contas([
        Conta(usuario="a", empresa_id="empresa-a", hash_senha=guardada),
        Conta(usuario="b", empresa_id="empresa-b", hash_senha=guardada),
    ])
    assert contas.autenticar("a", "x1").empresa_id == "empresa-a"
    assert contas.autenticar("b", "x1").empresa_id == "empresa-b"


def test_papel_padrao_e_dono_nunca_admin():
    """Conta nasce sem poder de administração: o papel precisa ser dito."""
    conta = Conta(usuario="a", empresa_id="a", hash_senha="x")
    assert conta.papel == "dono" and conta.e_admin is False


def test_usuario_inexistente_e_senha_errada_dao_a_mesma_recusa():
    contas = Contas.so_o_administrador({VARIAVEL_ADMIN: "x1"})
    assert contas.autenticar("fantasma", "x1") is None
    assert contas.autenticar(ADMIN_PADRAO, "errada") is None


def test_usuario_inexistente_tambem_paga_o_custo_do_hash(monkeypatch):
    """Sem isso, o tempo de resposta contaria quais usuários existem."""
    contas = Contas.so_o_administrador({VARIAVEL_ADMIN: "x1"})
    contas.autenticar("fantasma", "x1")       # aquece o hash de mentira, calculado uma vez só
    conferencias = []
    original = senha.conferir
    monkeypatch.setattr(senha, "conferir",
                        lambda *a: conferencias.append(1) or original(*a))
    contas.autenticar(ADMIN_PADRAO, "errada")
    assert len(conferencias) == 1
    contas.autenticar("fantasma", "x1")
    assert len(conferencias) == 2


# O que este teste procura são atribuições de senha, não a palavra "admin" em
# qualquer posição: `ADMIN_PADRAO = "admin"` é o **nome de usuário** padrão do
# administrador, e nome de usuário não é segredo. A versão anterior deste teste
# proibia a palavra inteira e passaria a reprovar essa linha sem motivo.
_ATRIBUICAO_DE_SENHA = re.compile(
    r"(senha|password|hash_senha|segredo|token|chave)\w*\s*[:=]\s*['\"][^'\"]{3,}['\"]",
    re.IGNORECASE,
)
# Nome de variável de ambiente e mensagem de erro citam essas palavras sem guardar segredo.
_PERMITIDO = re.compile(r"RADAR_|VARIAVEL_|GEMINI_|scrypt|argon2|\$argon2id\$|sqlite|postgres")


def test_nenhum_arquivo_do_pacote_tem_senha_fixa():
    pacote = Path(__file__).resolve().parents[2] / "app" / "seguranca"
    achados = []
    for arquivo in sorted(pacote.glob("*.py")):
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            if _ATRIBUICAO_DE_SENHA.search(linha) and not _PERMITIDO.search(linha):
                achados.append(f"{arquivo.name}: {linha.strip()}")
    assert not achados, "senha ou segredo escrito no código: " + "; ".join(achados)
