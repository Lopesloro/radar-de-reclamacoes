"""Dá para confiar?, O que falta, Ajuda e Sobre o sistema."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app import conteudo, formatos, servicos
from app.graficos import frases, svg
from app.rotas._telas import tela
from app.seguranca import empresa_do_usuario

rotas = APIRouter()


@rotas.get("/confianca")
def confianca(request: Request):
    classificacao = servicos.acuracia_classificacao()
    previsao = servicos.acuracia_previsao()
    laboratorio = servicos.laboratorio()
    acerto = round(classificacao.acerto_geral * 10)
    acerto_chute = round(classificacao.acerto_regua * 10)
    linhas_assuntos = [(frases.nome(linha.categoria), round(linha.precisao * 100), linha.amostra)
                       for linha in classificacao.linhas]
    linhas_previsao = [(formatos.mes_ano(mes), previsto, realizado, abs(previsto - realizado))
                       for mes, previsto, realizado in previsao.pontos]
    return tela(
        request, "confianca.html", "confianca",
        linhas_assuntos=linhas_assuntos,
        linhas_previsao=linhas_previsao,
        classificacao=classificacao,
        previsao=previsao,
        laboratorio=laboratorio,
        acerto=acerto,
        acerto_chute=acerto_chute,
        picto_sistema=svg.pictograma(acerto, f"O sistema acerta {acerto} de cada 10"),
        picto_chute=svg.pictograma(acerto_chute, f"O chute mais simples acerta {acerto_chute} de cada 10"),
        grafico_assuntos=svg.barras_acerto(
            [(frases.nome(linha.categoria), round(linha.precisao * 100)) for linha in classificacao.linhas],
            "Quando o sistema diz um assunto, quantas vezes acerta",
        ),
        grafico_previsao=svg.previsto_realizado(
            previsao.pontos, f"O que o sistema disse e o que aconteceu: {previsao.exemplo}",
        ),
        picto_agente=svg.pictograma(round(laboratorio.acerto_agente * 10),
                                    "O agente acha a causa certa"),
        picto_agente_chute=svg.pictograma(round(laboratorio.acerto_regua * 10),
                                          "O chute mais simples acha a causa certa"),
    )


@rotas.get("/o-que-falta")
def o_que_falta(request: Request):
    return tela(
        request, "o_que_falta.html", "o-que-falta",
        blocos=[{"negocio": c, "etapas": servicos.etapas(c.empresa_id)}
                for c in servicos.comercios(empresa_do_usuario(request))],
    )


@rotas.get("/ajuda")
def ajuda(request: Request):
    termos = sorted(conteudo.GLOSSARIO.items(), key=lambda item: item[1]["rotulo"].lower())
    return tela(request, "ajuda.html", "ajuda", termos=termos, perguntas=conteudo.FAQ)


@rotas.get("/sobre")
def sobre(request: Request):
    return tela(
        request, "sobre.html", "sobre",
        autoria=conteudo.AUTORIA,
        tecnologias=conteudo.TECNOLOGIAS,
    )
