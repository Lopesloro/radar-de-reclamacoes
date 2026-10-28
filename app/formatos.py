"""Número, dinheiro e data do jeito brasileiro."""

from __future__ import annotations

from datetime import date

MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)
MESES_CURTOS = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
DIAS_SEMANA = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")
DIAS_CURTOS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")
PERIODOS = {"manha": "manhã", "tarde": "tarde", "noite": "noite"}


def _milhar(texto: str) -> str:
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def decimal(valor: float, casas: int = 1) -> str:
    return _milhar(f"{valor:,.{casas}f}")


def inteiro(valor: float) -> str:
    return _milhar(f"{round(valor):,}")


def moeda(valor: float) -> str:
    return f"R$ {_milhar(f'{valor:,.0f}')}"


def de_cada(fracao: float, base: int = 10) -> str:
    """0,82 vira '8 de cada 10'."""
    return f"{round(fracao * base)} de cada {base}"


def diferenca(valor: float, referencia: str = "") -> str:
    """Diferença em palavras, sempre com seta: '▲ 4 a mais', '▼ 2 a menos', '= igual'."""
    numero = round(valor)
    sufixo = f" que {referencia}" if referencia else ""
    if numero > 0:
        return f"▲ {numero} a mais{sufixo}"
    if numero < 0:
        return f"▼ {abs(numero)} a menos{sufixo}"
    return "= igual" + (f" a {referencia}" if referencia else "")


def mes_longo(dia: date) -> str:
    return MESES[dia.month - 1]


def mes_ano(dia: date) -> str:
    return f"{MESES[dia.month - 1]} de {dia.year}"


def mes_curto(dia: date) -> str:
    return MESES_CURTOS[dia.month - 1]


def data_curta(dia: date) -> str:
    return f"{dia.day:02d}/{dia.month:02d}"


def data_longa(dia: date) -> str:
    return f"{dia.day} de {MESES[dia.month - 1]}"


def dia_semana(numero: int) -> str:
    return DIAS_SEMANA[numero]


def periodo(chave: str) -> str:
    return PERIODOS[chave]


def estrelas(quantidade: int) -> str:
    return "★" * quantidade + "☆" * (5 - quantidade)
