"""A política de cabeçalhos existe, não afrouxa a CSP e não quebra as páginas do site."""

import re
from pathlib import Path

from app.seguranca.cabecalhos import CABECALHOS

TEMPLATES = Path(__file__).resolve().parents[2] / "app" / "templates"


def _diretivas(csp: str) -> dict[str, list[str]]:
    partes = (p.strip() for p in csp.split(";") if p.strip())
    return {p.split()[0]: p.split()[1:] for p in partes}


def test_csp_nao_tem_unsafe_inline_nem_unsafe_eval():
    csp = CABECALHOS["Content-Security-Policy"]
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp


def test_csp_so_deixa_script_do_proprio_site():
    diretivas = _diretivas(CABECALHOS["Content-Security-Policy"])
    assert diretivas["script-src"] == ["'self'"]
    assert diretivas["default-src"] == ["'self'"]
    assert diretivas["object-src"] == ["'none'"]
    assert diretivas["frame-ancestors"] == ["'none'"]
    assert diretivas["form-action"] == ["'self'"]


def test_csp_libera_todo_endereco_externo_que_os_templates_usam():
    """Se alguém puser outra fonte ou CDN no HTML, este teste lembra de decidir sobre ela."""
    csp = CABECALHOS["Content-Security-Policy"]
    externos = set()
    for arquivo in TEMPLATES.glob("*.html"):
        externos |= set(re.findall(r"https://([a-z0-9.-]+)", arquivo.read_text(encoding="utf-8")))
    assert externos, "os templates deveriam carregar a fonte do Google"
    for host in externos:
        assert host in csp, f"{host} é usado nos templates e a CSP bloquearia"


def test_demais_cabecalhos_de_defesa():
    assert CABECALHOS["X-Frame-Options"] == "DENY"
    assert CABECALHOS["X-Content-Type-Options"] == "nosniff"
    assert CABECALHOS["Referrer-Policy"] == "strict-origin-when-cross-origin"
    hsts = CABECALHOS["Strict-Transport-Security"]
    segundos = int(re.search(r"max-age=(\d+)", hsts).group(1))
    assert segundos >= 31536000
