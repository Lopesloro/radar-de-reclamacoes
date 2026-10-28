"""Tela "Por quê?": as possíveis causas de um assunto que está crescendo."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app import servicos
from app.contratos import CATEGORIAS
from app.graficos import frases, svg
from app.rotas._telas import tela
from app.rotas.acesso_provisorio import empresa_permitida

rotas = APIRouter()

ORIGENS = {
    "diario": "Veio do diário do negócio",
    "calendario": "Veio do calendário",
    "clima": "Veio do clima",
    "dia_turno": "Veio dos dias e turnos com mais reclamação",
    "termo_novo": "Veio das palavras que os clientes usam",
    "ia": "Ideia da inteligência artificial",
}


@rotas.get("/investigacao")
def indice(request: Request):
    return tela(
        request, "investigacao_indice.html", "investigacao",
        avisos=[{"alerta": a, "frase": frases.alerta(a)} for a in servicos.alertas()],
        negocios=servicos.comercios(),
        categorias_disponiveis=CATEGORIAS,
    )


@rotas.get("/investigacao/{empresa}/{categoria}")
def investigar(request: Request, empresa: str, categoria: str):
    empresa_permitida(empresa)
    if categoria not in CATEGORIAS:
        raise HTTPException(status_code=404)
    negocio = servicos.comercio(empresa)
    resultado = servicos.investigar(empresa, categoria)
    hipoteses = [{
        "h": h,
        "origem": ORIGENS[h.origem],
        "grafico": svg.duas_colunas(
            "antes", h.antes_semana, "depois", h.depois_semana, "por semana",
            frases.hipotese_grafico(h),
            sentido="piorou" if h.depois_semana > h.antes_semana else "melhorou",
        ),
        "frase_grafico": frases.hipotese_grafico(h),
    } for h in resultado.hipoteses]
    return tela(
        request, "investigacao.html", "investigacao",
        negocio=negocio,
        negocios=servicos.comercios(),
        categoria=categoria,
        categorias_disponiveis=CATEGORIAS,
        investigacao=resultado,
        hipoteses=hipoteses,
        provaveis=sum(1 for h in resultado.hipoteses if h.veredito == "sustentada"),
        eventos=servicos.eventos_diario(empresa),
        tem_sugestao=servicos.cenario_sugerido(resultado) is not None,
    )
