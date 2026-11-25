"""A ficha do cliente, cifrada em repouso.

CNPJ, responsável, telefone, e-mail de contato e onde o negócio está no Google e
no iFood são dados de quem contrata. Eles vão para o banco numa coluna só
(`empresa.ficha_cifrada`), como um JSON cifrado pelo cofre (`app/seguranca/cofre.py`).
Uma cópia do banco — dump, backup, consulta de suporte — não entrega nenhum deles.

A mesma regra do cofre vale aqui: **sem `RADAR_COFRE_CHAVE`, a ficha é recusada**,
nunca gravada em texto. Só a área da equipe abre a ficha; a trilha de auditoria
registra que a ficha mudou, nunca o que está nela.
"""

from __future__ import annotations

import json

from app.seguranca import cofre

CAMPOS = ("cnpj", "responsavel", "telefone", "email_contato", "google_local", "ifood_loja")
ROTULOS = {
    "cnpj": "CNPJ",
    "responsavel": "Responsável",
    "telefone": "Telefone",
    "email_contato": "E-mail de contato",
    "google_local": "Endereço no Google Maps",
    "ifood_loja": "Identificador da loja no iFood",
}


class FichaSemCofre(Exception):
    """Há dado para gravar e não há chave para cifrar."""


def vazia(dados: dict[str, str]) -> bool:
    return not any((dados.get(campo) or "").strip() for campo in CAMPOS)


def cifrar(dados: dict[str, str]) -> str | None:
    """O JSON da ficha cifrado. None quando a ficha está vazia."""
    limpos = {campo: (dados.get(campo) or "").strip() for campo in CAMPOS}
    if vazia(limpos):
        return None
    if not cofre.disponivel():
        raise FichaSemCofre(
            f"{cofre.VARIAVEL_CHAVE} não está configurada: sem ela a ficha do cliente "
            "não é gravada, para não ficar em texto no banco."
        )
    return cofre.cifrar(json.dumps(limpos, ensure_ascii=False))


def abrir(guardada: str | None) -> dict[str, str]:
    """A ficha legível. Vazia se não há ficha ou se a chave do cofre mudou."""
    if not guardada:
        return {}
    texto = cofre.decifrar(guardada)
    if texto is None:
        return {}
    try:
        dados = json.loads(texto)
    except ValueError:
        return {}
    return {campo: str(dados.get(campo) or "") for campo in CAMPOS}
