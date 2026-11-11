"""Segredo de fonte cifrado em repouso.

O token que a plataforma dá (Google, iFood) é a chave da casa do cliente: com
ele dá para ler as avaliações dele e, no caso do iFood, responder em nome dele.
Guardá-lo em texto no banco significa que qualquer cópia do banco — um dump de
desenvolvimento, um backup, uma consulta de suporte — entrega a conta do cliente.

Duas regras valem aqui, e as duas têm teste:

1. **Sem chave de cofre, o sistema recusa gravar segredo.** Não grava em texto
   "por enquanto": recusa. É o único jeito de a falta de configuração não virar
   vazamento silencioso.
2. **O segredo nunca entra em log nem em tela.** Quem precisa saber se a fonte
   funciona lê `estado`, não o token.

A cifra é Fernet (AES-128-CBC com HMAC-SHA256) da biblioteca `cryptography`:
cifra autenticada, então um segredo adulterado no banco falha ao abrir em vez de
devolver lixo.
"""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken

VARIAVEL_CHAVE = "RADAR_COFRE_CHAVE"


class CofreFechado(RuntimeError):
    """Pediram para cifrar sem chave configurada. Nunca cair para texto puro."""


def gerar_chave() -> str:
    """Uma chave nova, para colar na variável de ambiente do serviço."""
    return Fernet.generate_key().decode()


def chave() -> str | None:
    valor = os.environ.get(VARIAVEL_CHAVE, "").strip()
    return valor or None


def disponivel() -> bool:
    """True quando há chave e ela tem o formato que o Fernet aceita."""
    valor = chave()
    if valor is None:
        return False
    try:
        Fernet(valor.encode())
    except (ValueError, TypeError):
        return False
    return True


def _motor() -> Fernet:
    valor = chave()
    if valor is None:
        raise CofreFechado(
            f"{VARIAVEL_CHAVE} não está configurada: sem ela o segredo da fonte "
            "não é gravado. Gere uma com app.seguranca.cofre.gerar_chave()."
        )
    try:
        return Fernet(valor.encode())
    except (ValueError, TypeError) as erro:
        raise CofreFechado(f"{VARIAVEL_CHAVE} não é uma chave Fernet válida.") from erro


def cifrar(segredo: str) -> str:
    """O segredo pronto para a coluna. Levanta `CofreFechado` sem chave."""
    if not segredo:
        raise ValueError("segredo vazio não precisa de cofre")
    return _motor().encrypt(segredo.encode()).decode()


def decifrar(guardado: str | None) -> str | None:
    """O segredo de volta, ou None se não houver, se a chave for outra ou se o
    valor tiver sido mexido. Nunca levanta para o chamador: fonte que não abre é
    fonte com erro, e o motor de coleta sabe lidar com isso."""
    if not guardado:
        return None
    try:
        return _motor().decrypt(guardado.encode()).decode()
    except (CofreFechado, InvalidToken, ValueError):
        return None
