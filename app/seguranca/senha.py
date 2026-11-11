"""Senha guardada como hash Argon2id, nunca em texto.

Argon2id ganhou a Password Hashing Competition e é a recomendação atual da
OWASP para senha nova. Os parâmetros abaixo são os mínimos que a OWASP publica
(m=19 MiB, t=2, p=1) e existe um motivo concreto para não subir: o serviço roda
num plano de 512 MB de memória, e cada conferência reserva o `m` inteiro. Com
19 MiB e o portão de duas conferências simultâneas de `app/seguranca/rotas.py`,
o pico fica em ~40 MiB. Com os 64 MiB que a biblioteca usa por padrão, duas
conferências já custariam 128 MiB e um pico de entradas derrubaria o site —
foi medido, não suposto.

O hash do Argon2 carrega os próprios parâmetros
(`$argon2id$v=19$m=19456,t=2,p=1$sal$derivada`), então subir o custo no futuro
não invalida senha já guardada: `precisa_regerar` avisa, e quem entra recebe um
hash novo na hora.

Hash scrypt antigo continua sendo conferido (era o formato da primeira versão),
e é trocado por Argon2id no primeiro acerto de senha. Nenhuma conta precisa
trocar de senha por causa da migração.
"""

from __future__ import annotations

import hashlib
import hmac

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

# OWASP: m=19456 KiB, t=2, p=1 para Argon2id. Ver a justificativa de memória acima.
MEMORIA_KIB = 19456
PASSAGENS = 2
PARALELISMO = 1
TAMANHO_DO_SAL = 16
TAMANHO_DA_DERIVADA = 32

_cozinheiro = PasswordHasher(
    time_cost=PASSAGENS,
    memory_cost=MEMORIA_KIB,
    parallelism=PARALELISMO,
    hash_len=TAMANHO_DA_DERIVADA,
    salt_len=TAMANHO_DO_SAL,
    type=Type.ID,
)

PREFIXO_ARGON = "$argon2id$"
PREFIXO_SCRYPT = "scrypt$"


def gerar_hash(senha: str) -> str:
    return _cozinheiro.hash(senha)


# ------------------------------------------------------------ formato antigo

def _derivar_scrypt(senha: str, sal: bytes, n: int, r: int, p: int) -> bytes:
    # maxmem acompanha o custo gravado no hash; o padrão da biblioteca (32 MiB) travaria custos maiores.
    return hashlib.scrypt(
        senha.encode(), salt=sal, n=n, r=r, p=p,
        maxmem=2 * 128 * r * (n + p + 2), dklen=TAMANHO_DA_DERIVADA,
    )


def _conferir_scrypt(senha: str, guardado: str) -> bool:
    try:
        algoritmo, n, r, p, sal, esperado = guardado.split("$")
        if algoritmo != "scrypt":
            return False
        derivada = _derivar_scrypt(senha, bytes.fromhex(sal), int(n), int(r), int(p))
        return hmac.compare_digest(derivada, bytes.fromhex(esperado))
    except ValueError:
        return False


# ------------------------------------------------------------ o que as rotas usam

def conferir(senha: str, guardado: str) -> bool:
    """Confere nos dois formatos. Hash malformado confere como falso, nunca como erro."""
    if not guardado:
        return False
    if guardado.startswith(PREFIXO_SCRYPT):
        return _conferir_scrypt(senha, guardado)
    try:
        return _cozinheiro.verify(guardado, senha)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def precisa_regerar(guardado: str) -> bool:
    """True quando o hash é do formato antigo ou de um custo menor que o de hoje."""
    if not guardado or guardado.startswith(PREFIXO_SCRYPT):
        return True
    try:
        return _cozinheiro.check_needs_rehash(guardado)
    except InvalidHashError:
        return True
