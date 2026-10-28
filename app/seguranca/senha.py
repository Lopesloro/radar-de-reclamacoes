"""Senha guardada como hash scrypt da biblioteca padrão, nunca em texto.

O hash carrega o próprio custo (`scrypt$n$r$p$sal$derivada`). Assim dá para
aumentar o custo no futuro sem invalidar quem já tem senha guardada.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

# Custo de memória de 16 MiB por conferência: cabe no plano gratuito e já torna cara a força bruta.
_N, _R, _P = 2 ** 14, 8, 1
_TAMANHO_DO_SAL = 16
_TAMANHO_DA_DERIVADA = 32


def _derivar(senha: str, sal: bytes, n: int, r: int, p: int) -> bytes:
    # maxmem acompanha o custo gravado no hash; o padrão da biblioteca (32 MiB) travaria custos maiores.
    return hashlib.scrypt(
        senha.encode(), salt=sal, n=n, r=r, p=p,
        maxmem=2 * 128 * r * (n + p + 2), dklen=_TAMANHO_DA_DERIVADA,
    )


def _formatar(senha: str, n: int, r: int, p: int) -> str:
    sal = secrets.token_bytes(_TAMANHO_DO_SAL)
    return "$".join(["scrypt", str(n), str(r), str(p), sal.hex(), _derivar(senha, sal, n, r, p).hex()])


def gerar_hash(senha: str) -> str:
    return _formatar(senha, _N, _R, _P)


def conferir(senha: str, guardado: str) -> bool:
    """Compara em tempo constante. Hash malformado confere como falso, nunca como erro."""
    try:
        algoritmo, n, r, p, sal, esperado = guardado.split("$")
        if algoritmo != "scrypt":
            return False
        derivada = _derivar(senha, bytes.fromhex(sal), int(n), int(r), int(p))
        return hmac.compare_digest(derivada, bytes.fromhex(esperado))
    except ValueError:
        return False
