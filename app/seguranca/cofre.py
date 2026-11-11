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

A chave do Fernet tem um formato próprio (32 bytes em base64 urlsafe), e o
`generateValue` do Render gera um texto aleatório que **não** está nesse
formato. Em vez de pedir para alguém colar a chave na mão (e descobrir o erro
quando o primeiro token não gravar), o valor da variável é passado por SHA-256
para virar a chave: qualquer texto com entropia suficiente serve, e o do Render
serve. O preço é que trocar a variável torna ilegível o que já foi cifrado, o
que é o comportamento correto de uma troca de chave.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets

from cryptography.fernet import Fernet, InvalidToken

VARIAVEL_CHAVE = "RADAR_COFRE_CHAVE"


class CofreFechado(RuntimeError):
    """Pediram para cifrar sem chave configurada. Nunca cair para texto puro."""


# Abaixo disto o valor não tem entropia para virar chave. Vinte e quatro
# caracteres é o tamanho de um `secrets.token_urlsafe(18)`.
TAMANHO_MINIMO = 24


def gerar_chave() -> str:
    """Um valor novo para a variável de ambiente do serviço."""
    return secrets.token_urlsafe(32)


def chave() -> str | None:
    valor = os.environ.get(VARIAVEL_CHAVE, "").strip()
    return valor or None


def _derivar(valor: str) -> bytes:
    """A chave do Fernet a partir do texto da variável de ambiente."""
    resumo = hashlib.sha256(valor.encode()).digest()
    return base64.urlsafe_b64encode(resumo[:32])


def disponivel() -> bool:
    """True quando há valor configurado e ele é longo o bastante."""
    valor = chave()
    return valor is not None and len(valor) >= TAMANHO_MINIMO


def _motor() -> Fernet:
    valor = chave()
    if valor is None:
        raise CofreFechado(
            f"{VARIAVEL_CHAVE} não está configurada: sem ela o segredo da fonte "
            "não é gravado. Gere um valor com app.seguranca.cofre.gerar_chave()."
        )
    if len(valor) < TAMANHO_MINIMO:
        raise CofreFechado(
            f"{VARIAVEL_CHAVE} tem menos de {TAMANHO_MINIMO} caracteres: "
            "curta demais para cifrar segredo de cliente."
        )
    return Fernet(_derivar(valor))


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
