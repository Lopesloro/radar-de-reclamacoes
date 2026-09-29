"""Formatação de números e datas no padrão brasileiro."""

from datetime import date

MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def _milhar_br(texto: str) -> str:
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def decimal(valor: float, casas: int = 2) -> str:
    return _milhar_br(f"{valor:,.{casas}f}")


def inteiro(valor: float) -> str:
    return decimal(valor, 0)


def pct(valor: float, casas: int = 0, sinal: bool = True) -> str:
    """0.123 vira '+12%'. Usa o sinal de menos tipográfico."""
    formato = f"{{:+.{casas}f}}" if sinal else f"{{:.{casas}f}}"
    texto = formato.format(valor * 100).replace(".", ",").replace("-", "−")
    return f"{texto}%"


def contagem(valor: int) -> str:
    """Variação em contagem, nunca em porcentagem: é onde o MAPE dividiria por zero."""
    if valor > 0:
        return f"+{valor}"
    if valor < 0:
        return f"−{abs(valor)}"
    return "sem mudança"


def data_curta(dia: date) -> str:
    return dia.strftime("%d/%m")


def data_longa(dia: date) -> str:
    return f"{dia.day} de {MESES[dia.month - 1]} de {dia.year}"


def mes_longo(dia: date) -> str:
    return f"{MESES[dia.month - 1]} de {dia.year}"
