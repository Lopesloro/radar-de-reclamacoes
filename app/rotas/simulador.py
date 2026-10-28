"""Tela "E se?": muda a equipe dos turnos e mostra o efeito e o custo.

O formulário é um GET comum: funciona sem JavaScript, e o endereço da página
guarda o cenário, então dá para mandar o link para outra pessoa.
"""

from __future__ import annotations

from dataclasses import replace

from fastapi import APIRouter, Request

from app import servicos
from app.contratos import CATEGORIAS, Cenario
from app.graficos import frases, svg
from app.rotas._telas import tela
from app.rotas.acesso_provisorio import empresa_permitida

rotas = APIRouter()
EQUIPE_MAXIMA = 20


def _campo(turno) -> str:
    return f"t-{turno.dia_semana}-{turno.periodo}"


@rotas.get("/simulador")
def indice(request: Request):
    return tela(request, "simulador_indice.html", "simulador", negocios=servicos.comercios())


@rotas.get("/simulador/{empresa}")
def simulador(request: Request, empresa: str, categoria: str | None = None):
    empresa_permitida(empresa)
    negocio = servicos.comercio(empresa)
    escolhida = categoria if categoria in CATEGORIAS else negocio.vai_crescer
    abertos = [t for t in servicos.operacao(empresa) if t.equipe > 0]

    sugestao = servicos.cenario_sugerido(servicos.investigar(empresa, escolhida))
    sugeridos = {(t.dia_semana, t.periodo) for t in sugestao.mudancas} if sugestao else set()

    pedidos = request.query_params
    if any(_campo(t) in pedidos for t in abertos):
        mudancas = []
        for t in abertos:
            try:
                equipe = int(pedidos.get(_campo(t), t.equipe))
            except ValueError:
                equipe = t.equipe
            equipe = max(1, min(EQUIPE_MAXIMA, equipe))
            if equipe != t.equipe:
                mudancas.append(replace(t, equipe=equipe))
        cenario = Cenario("Mudança escolhida na tela", escolhida, tuple(mudancas))
    elif sugestao is not None:
        cenario = sugestao
    else:
        cenario = Cenario("Sem mudança", escolhida, ())

    novos = {(t.dia_semana, t.periodo): t.equipe for t in cenario.mudancas}
    turnos = sorted(
        ({"turno": t, "campo": _campo(t), "valor": novos.get((t.dia_semana, t.periodo), t.equipe),
          "sugerido": (t.dia_semana, t.periodo) in sugeridos} for t in abertos),
        key=lambda item: (not item["sugerido"], item["turno"].dia_semana, item["turno"].periodo),
    )
    resultado = servicos.simular(empresa, cenario)
    return tela(
        request, "simulador.html", "simulador",
        negocio=negocio,
        negocios=servicos.comercios(),
        escolhida=escolhida,
        categorias_disponiveis=CATEGORIAS,
        turnos=turnos,
        tem_sugeridos=bool(sugeridos),
        resultado=resultado,
        frase=frases.simulacao(resultado),
        grafico=svg.comparacao_cenario(
            resultado.reclamacoes_atual, resultado.reclamacoes_cenario,
            resultado.minimo, resultado.maximo, frases.simulacao(resultado),
        ),
        equipe_maxima=EQUIPE_MAXIMA,
    )
