"""Autenticação, sessão e os controles de defesa do site.

O recorte de cibersegurança do projeto é **defesa**: nada aqui ataca nada. O que
existe é o mínimo que um painel com dado de terceiro precisa ter — senha
guardada como hash, sessão assinada em cookie HttpOnly, token contra CSRF em
todo formulário, limite de tentativas de login e cabeçalhos de resposta.

A senha de demonstração é `admin`. Em produção ela vem de `RADAR_SENHA`, e o
site avisa na tela de entrada enquanto estiver usando a senha de demonstração.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time

USUARIO = os.environ.get("RADAR_USUARIO", "admin")
SENHA = os.environ.get("RADAR_SENHA", "admin")
SENHA_E_DEMONSTRACAO = SENHA == "admin"

CHAVE_SESSAO = os.environ.get("RADAR_CHAVE") or secrets.token_urlsafe(48)

_SAL = os.environ.get("RADAR_SAL", "radar-de-reclamacoes").encode()
TENTATIVAS_MAXIMAS = 8
JANELA_SEGUNDOS = 300

# Contagem de tentativas por origem. Em memória: o dado não sobrevive ao
# reinício, e é justamente isso que se espera de um bloqueio temporário.
_tentativas: dict[str, list[float]] = {}


def _hash(senha: str) -> bytes:
    """scrypt da biblioteca padrão: sem dependência nova e com custo de memória."""
    return hashlib.scrypt(senha.encode(), salt=_SAL, n=2 ** 14, r=8, p=1, dklen=32)


_HASH_ESPERADO = _hash(SENHA)


def senha_confere(usuario: str, senha: str) -> bool:
    """Compara em tempo constante e sempre calcula o hash, mesmo com usuário errado."""
    calculado = _hash(senha)
    usuario_ok = hmac.compare_digest(usuario.strip().lower(), USUARIO.lower())
    senha_ok = hmac.compare_digest(calculado, _HASH_ESPERADO)
    return usuario_ok and senha_ok


def pode_tentar(origem: str) -> bool:
    agora = time.monotonic()
    marcas = [t for t in _tentativas.get(origem, []) if agora - t < JANELA_SEGUNDOS]
    _tentativas[origem] = marcas
    return len(marcas) < TENTATIVAS_MAXIMAS


def registrar_tentativa(origem: str) -> None:
    _tentativas.setdefault(origem, []).append(time.monotonic())


def limpar_tentativas(origem: str | None = None) -> None:
    if origem is None:
        _tentativas.clear()
    else:
        _tentativas.pop(origem, None)


def segundos_restantes(origem: str) -> int:
    marcas = _tentativas.get(origem, [])
    if not marcas:
        return 0
    return max(0, int(JANELA_SEGUNDOS - (time.monotonic() - marcas[0])))


def token_csrf(sessao) -> str:
    token = sessao.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        sessao["csrf"] = token
    return token


def csrf_confere(sessao, enviado: str | None) -> bool:
    guardado = sessao.get("csrf")
    return bool(guardado and enviado and hmac.compare_digest(guardado, enviado))


CABECALHOS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'none'; "
        "object-src 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}
