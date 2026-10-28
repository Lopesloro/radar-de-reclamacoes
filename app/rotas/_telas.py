"""Monta as telas: templates, filtros e o que toda página recebe."""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import conteudo, formatos, servicos
from app.graficos import frases
from app.seguranca import usuario_atual

RAIZ = Path(__file__).resolve().parent.parent


def _impressao_dos_estaticos() -> str:
    """Muda quando o CSS ou o JavaScript mudam, para o navegador não servir o arquivo velho.

    A conta usa o conteúdo, com a quebra de linha normalizada: o git no Windows
    troca LF por CRLF, e o mesmo arquivo daria impressões diferentes por máquina.
    """
    resumo = hashlib.sha256()
    for caminho in sorted((RAIZ / "static").rglob("*")):
        if caminho.is_file():
            resumo.update(caminho.name.encode())
            resumo.update(caminho.read_bytes().replace(b"\r\n", b"\n"))
    return resumo.hexdigest()[:12]


paginas = Jinja2Templates(directory=str(RAIZ / "templates"))
paginas.env.filters.update(
    inteiro=formatos.inteiro,
    decimal=formatos.decimal,
    moeda=formatos.moeda,
    de_cada=formatos.de_cada,
    diferenca=formatos.diferenca,
    mes_longo=formatos.mes_longo,
    mes_ano=formatos.mes_ano,
    mes_curto=formatos.mes_curto,
    data_curta=formatos.data_curta,
    data_longa=formatos.data_longa,
    dia_semana=formatos.dia_semana,
    periodo=formatos.periodo,
    estrelas=formatos.estrelas,
    assunto=frases.nome,
    com_artigo=frases.com_artigo,
)
paginas.env.globals.update(
    projeto=conteudo.PROJETO,
    versao=conteudo.VERSAO,
    menu=conteudo.MENU,
    menu_mais=conteudo.MENU_MAIS,
    glossario=conteudo.GLOSSARIO,
    estados=conteudo.ESTADOS,
    vereditos=conteudo.VEREDITOS,
    forcas=conteudo.FORCAS,
    resultados_teste=conteudo.RESULTADOS_TESTE,
    categorias=conteudo.NOMES_CATEGORIA,
    demonstracao=servicos.DADOS_DE_DEMONSTRACAO,
    impressao=_impressao_dos_estaticos(),
)


def tela(request: Request, nome: str, ativo: str, *, publica: bool = False,
         status_code: int = 200, **contexto) -> HTMLResponse:
    return paginas.TemplateResponse(
        request,
        nome,
        {"ativo": ativo, "usuario": None if publica else usuario_atual(request), **contexto},
        status_code=status_code,
    )
