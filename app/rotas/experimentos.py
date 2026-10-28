"""Tela "Testes": o teste na prática, com o sorteio dos dias e o resultado."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app import servicos
from app.graficos import svg
from app.rotas._telas import tela
from app.seguranca import empresa_do_usuario, exigir_empresa

rotas = APIRouter()


def codigo_do_plano(selo: str) -> str:
    """O selo inteiro é longo demais para anotar; o código curto são os 8 primeiros sinais."""
    return f"{selo[:4]}-{selo[4:8]}".upper()


def _progresso(marcacoes) -> tuple[int, int]:
    return sum(1 for m in marcacoes if m.seguiu is not None), len(marcacoes)


@rotas.get("/experimentos")
def lista(request: Request):
    itens = []
    for plano in servicos.experimentos(empresa_do_usuario(request)):
        marcados, total = _progresso(servicos.marcacoes(plano.id))
        itens.append({
            "plano": plano,
            "negocio": servicos.comercio(plano.empresa_id),
            "marcados": marcados,
            "total": total,
        })
    return tela(request, "experimentos.html", "experimentos", itens=itens)


@rotas.get("/experimentos/{plano_id}")
def detalhe(request: Request, plano_id: str):
    plano = servicos.experimento(plano_id)
    if plano is None:
        # Recusa igual à de empresa alheia: 404 aqui contaria quais planos existem.
        raise HTTPException(status_code=403, detail="Esse plano não é o seu.")
    # O parâmetro se chama plano_id, então a trava automática não o cobre.
    exigir_empresa(request, plano.empresa_id)
    marcacoes = servicos.marcacoes(plano_id)
    marcados, total = _progresso(marcacoes)
    resultado = servicos.analisar(plano_id)
    grafico = None
    if resultado is not None:
        grafico = svg.duas_colunas(
            "dias sem", resultado.media_sem, "dias com", resultado.media_com, "por dia",
            resultado.frase,
            sentido="melhorou" if resultado.media_com < resultado.media_sem else "piorou",
        )
    seguiu = sum(1 for m in marcacoes if m.seguiu)
    return tela(
        request, "experimento.html", "experimentos",
        plano=plano,
        negocio=servicos.comercio(plano.empresa_id),
        codigo=codigo_do_plano(plano.selo),
        marcacoes=marcacoes,
        marcados=marcados,
        total=total,
        seguiu=seguiu,
        hoje=servicos.HOJE,
        resultado=resultado,
        grafico=grafico,
    )
