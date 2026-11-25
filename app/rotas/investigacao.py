"""Tela "Por quê?": as possíveis causas de um assunto, e o diário onde o dono anota as mudanças.

As causas saem de `app/modelos/causas.py`, que testa cada mudança do diário e a
concentração no fim de semana com estatística de verdade. Sem mudança anotada,
a tela pede uma: é o diário que alimenta a maior parte das hipóteses.
"""

from __future__ import annotations

import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select

from app import auditoria, servicos
from app.banco import modelo
from app.banco import sessao as banco
from app.contratos import CATEGORIAS
from app.graficos import frases, svg
from app.rotas import formularios
from app.rotas._telas import tela
from app.seguranca import empresa_do_usuario, exigir_empresa, usuario_atual

rotas = APIRouter()

ORIGENS = {
    "diario": "Veio do diário do negócio",
    "dia_turno": "Veio dos dias da semana com mais reclamação",
}
# O que cada coluna do gráfico mostra, por origem da hipótese.
ROTULOS = {
    "diario": ("antes", "depois", "por semana"),
    "dia_turno": ("seg a qui", "sex a dom", "por dia"),
}


def _voltar(destino: str, recado: str = "", erro: str = "") -> RedirectResponse:
    # A âncora (#diario) vai depois da pergunta: antes, o navegador trataria o
    # recado como parte da âncora e a tela nunca o leria.
    caminho, _, ancora = destino.partition("#")
    partes = {k: v for k, v in (("recado", recado), ("erro", erro)) if v}
    endereco = caminho + ("?" + urlencode(partes) if partes else "") + (f"#{ancora}" if ancora else "")
    return RedirectResponse(endereco, status_code=303)


def _frase_grafico(h, rotulos) -> str:
    antes, depois, unidade = rotulos
    return (f"{antes.capitalize()}: {frases._numero(h.antes_semana)} reclamações {unidade}. "
            f"{depois.capitalize()}: {frases._numero(h.depois_semana)} {unidade}.")


@rotas.get("/investigacao")
def indice(request: Request):
    empresa = empresa_do_usuario(request)
    return tela(
        request, "investigacao_indice.html", "investigacao",
        avisos=[{"alerta": a, "frase": frases.alerta(a)} for a in servicos.alertas(empresa)],
        negocios=servicos.comercios(empresa),
        categorias_disponiveis=CATEGORIAS,
    )


@rotas.get("/investigacao/{comercio}/{categoria}")
def investigar(request: Request, comercio: str, categoria: str, recado: str = "", erro: str = ""):
    empresa = exigir_empresa(request, comercio)
    if categoria not in CATEGORIAS:
        raise HTTPException(status_code=404)
    negocio = servicos.comercio(empresa, comercio)
    if negocio is None:
        raise HTTPException(status_code=404)
    resultado = servicos.investigar(empresa, comercio, categoria)
    hipoteses = []
    for h in resultado.hipoteses:
        rotulos = ROTULOS[h.origem]
        frase = _frase_grafico(h, rotulos)
        hipoteses.append({
            "h": h,
            "origem": ORIGENS[h.origem],
            "frase_grafico": frase,
            "grafico": svg.duas_colunas(
                rotulos[0], h.antes_semana, rotulos[1], h.depois_semana, rotulos[2], frase,
                sentido="piorou" if h.depois_semana > h.antes_semana else "melhorou",
            ),
        })
    return tela(
        request, "investigacao.html", "investigacao",
        negocio=negocio,
        negocios=servicos.comercios(empresa),
        categoria=categoria,
        categorias_disponiveis=CATEGORIAS,
        investigacao=resultado,
        hipoteses=hipoteses,
        provaveis=sum(1 for h in resultado.hipoteses if h.veredito == "sustentada"),
        eventos=servicos.eventos_diario(empresa, comercio),
        hoje=servicos.hoje(),
        recado=recado, erro=erro,
    )


@rotas.post("/investigacao/{comercio}/diario")
def anotar(request: Request, comercio: str, data: str = Form(""), tipo: str = Form(""),
           descricao: str = Form(""), categoria: str = Form("demora"), csrf: str = Form("")):
    empresa = exigir_empresa(request, comercio)
    volta = f"/investigacao/{comercio}/{categoria if categoria in CATEGORIAS else 'demora'}"
    try:
        dados = formularios.EventoNovo(data=data, tipo=tipo, descricao=descricao)
    except ValidationError as erro:
        return _voltar(volta + "#diario", erro=erro.errors()[0]["msg"].removeprefix("Value error, "))
    usuario = usuario_atual(request)
    with banco.Sessao() as sessao:
        negocio = sessao.get(modelo.Comercio, comercio)
        if negocio is None or negocio.empresa_id != empresa:
            raise HTTPException(status_code=403, detail="Esse negócio não é o seu.")
        sessao.add(modelo.EventoDiario(
            id=f"ev-{uuid.uuid4().hex[:16]}", empresa_id=empresa, comercio_id=comercio,
            data=dados.data, tipo=dados.tipo, descricao=dados.descricao,
        ))
        auditoria.registrar(sessao, empresa_id=empresa, usuario_id=usuario.identificador,
                            acao="diario_anotado", objeto=comercio, detalhe=dados.data.isoformat())
        sessao.commit()
    return _voltar(volta, recado="Mudança anotada no diário. Ela já entrou como possível causa.")


@rotas.post("/investigacao/{comercio}/diario/apagar")
def apagar(request: Request, comercio: str, evento_id: str = Form(""),
           categoria: str = Form("demora"), csrf: str = Form("")):
    empresa = exigir_empresa(request, comercio)
    usuario = usuario_atual(request)
    with banco.Sessao() as sessao:
        evento = sessao.scalar(select(modelo.EventoDiario).where(
            modelo.EventoDiario.id == evento_id, modelo.EventoDiario.empresa_id == empresa,
            modelo.EventoDiario.comercio_id == comercio))
        if evento is not None:
            sessao.delete(evento)
            auditoria.registrar(sessao, empresa_id=empresa, usuario_id=usuario.identificador,
                                acao="diario_apagado", objeto=comercio, detalhe=evento_id)
            sessao.commit()
    volta = f"/investigacao/{comercio}/{categoria if categoria in CATEGORIAS else 'demora'}"
    return _voltar(volta + "#diario", recado="Mudança apagada do diário.")
