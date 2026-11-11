"""Dá para confiar?, O que falta e Ajuda.

A ficha técnica do sistema saiu daqui e foi para `/admin/sistema`: quem contrata
quer saber se o sistema acerta, não com o que ele foi feito.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app import conteudo, formatos, servicos
from app.graficos import frases, svg
from app.modelos import ativo, previsao
from app.rotas._telas import tela
from app.seguranca import empresa_do_usuario

rotas = APIRouter()


@rotas.get("/confianca")
def confianca(request: Request):
    """Os números do sistema, cada um ao lado do chute mais simples.

    A ordem da tela segue o que de fato ajuda o dono a decidir: primeiro o
    acerto do aviso, depois a separação por assunto, depois o erro da
    estimativa. O erro da estimativa vem por último de propósito, porque é o
    número em que o sistema empata com a régua, e a tela diz isso com essas
    palavras em vez de escondê-lo.
    """
    empresa = empresa_do_usuario(request)
    classificacao = servicos.acuracia_classificacao()
    da_previsao = servicos.acuracia_previsao(empresa)

    acerto = round(classificacao.acerto_geral * 10)
    acerto_chute = round(classificacao.acerto_regua * 10)
    linhas_assuntos = [
        (frases.nome(linha.categoria), round(linha.precisao * 100), linha.amostra)
        for linha in classificacao.linhas
    ]
    linhas_previsao = [
        (formatos.mes_ano(mes), previsto, realizado, abs(previsto - realizado))
        for mes, previsto, realizado in (da_previsao.pontos if da_previsao else ())
    ]
    return tela(
        request, "confianca.html", "confianca",
        classificacao=classificacao,
        origem_da_medida=servicos.origem_da_medida(),
        modelo_no_ar="inteligência artificial" if ativo.usando_ia() else "modelo próprio",
        previsao=da_previsao,
        referencia=previsao.MEDIDA_DE_REFERENCIA,
        linhas_assuntos=linhas_assuntos,
        linhas_previsao=linhas_previsao,
        acerto=acerto,
        acerto_chute=acerto_chute,
        picto_sistema=svg.pictograma(acerto, f"O sistema acerta {acerto} de cada 10"),
        picto_chute=svg.pictograma(
            acerto_chute, f"O chute mais simples acerta {acerto_chute} de cada 10"),
        grafico_assuntos=svg.barras_acerto(
            [(frases.nome(linha.categoria), round(linha.precisao * 100))
             for linha in classificacao.linhas],
            "Quando o sistema diz um assunto, quantas vezes acerta",
        ),
        grafico_previsao=svg.previsto_realizado(
            da_previsao.pontos,
            f"O que o sistema disse e o que aconteceu: {da_previsao.exemplo}",
        ) if da_previsao else "",
    )


@rotas.get("/o-que-falta")
def o_que_falta(request: Request):
    empresa = empresa_do_usuario(request)
    return tela(
        request, "o_que_falta.html", "o-que-falta",
        blocos=[{"negocio": c, "etapas": servicos.etapas(empresa, c.empresa_id)}
                for c in servicos.comercios(empresa)],
        proximas=conteudo.PROXIMAS_ETAPAS,
    )


@rotas.get("/ajuda")
def ajuda(request: Request):
    termos = sorted(conteudo.GLOSSARIO.items(), key=lambda item: item[1]["rotulo"].lower())
    return tela(request, "ajuda.html", "ajuda", termos=termos, perguntas=conteudo.FAQ)
