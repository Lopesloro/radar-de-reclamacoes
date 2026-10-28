"""Resumo, ficha do negócio, estimativa e avisos."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app import formatos, servicos
from app.contratos import CATEGORIAS
from app.formatos import mes_longo
from app.graficos import frases, svg
from app.rotas._telas import tela
from app.seguranca import empresa_do_usuario, exigir_empresa

rotas = APIRouter()


@rotas.get("/resumo")
def resumo(request: Request):
    empresa = empresa_do_usuario(request)
    negocios = servicos.comercios(empresa)
    cartoes = []
    for c in negocios:
        serie = servicos.serie(c.empresa_id, c.vai_crescer)
        cartoes.append({
            "negocio": c,
            "frase": frases.cartao(c),
            "grafico": svg.mini_colunas(
                serie.meses[-6:],
                f"Reclamações de {frases.nome(c.vai_crescer)} nos últimos 6 meses",
            ),
        })
    avisos = servicos.alertas(empresa)
    if not negocios:
        # Empresa recém-conectada, ainda sem um mês fechado: a tela diz isso em
        # vez de estourar. consultas.comercios() pula comércio sem histórico.
        return tela(
            request, "resumo.html", "resumo",
            cartoes=[], mes=None, mes_corrente=None,
            lidas=0, reclamacoes=0, avisos=(), sem_historico=True,
        )
    return tela(
        request, "resumo.html", "resumo",
        cartoes=cartoes,
        mes=negocios[0].mes_referencia,
        mes_corrente=negocios[0].vai_crescer_para.mes,
        lidas=sum(c.avaliacoes_lidas for c in negocios),
        reclamacoes=sum(c.reclamacoes for c in negocios),
        avisos=avisos,
        piorando=sum(1 for c in negocios if c.estado == "vai_piorar"),
    )


@rotas.get("/comercio/{empresa}")
def comercio(request: Request, empresa: str):
    exigir_empresa(request, empresa)
    negocio = servicos.comercio(empresa)
    todas = sorted(servicos.series(empresa), key=lambda s: s.ultimo, reverse=True)
    mes_anterior = mes_longo(todas[0].meses[-2][0])
    itens = [(frases.nome(s.categoria), s.ultimo, s.variacao) for s in todas]
    return tela(
        request, "comercio.html", "resumo",
        negocio=negocio,
        negocios=servicos.comercios(empresa_do_usuario(request)),
        series=todas,
        mes_anterior=mes_anterior,
        frase=frases.assuntos_do_mes(todas, negocio.mes_referencia),
        grafico=svg.barras_assuntos(itens, f"Reclamações por assunto em {negocio.nome}", mes_anterior),
        tabela=[(nome, valor, valor - variacao, formatos.diferenca(variacao))
                for nome, valor, variacao in itens],
        avaliacoes=servicos.avaliacoes(empresa),
    )


@rotas.get("/previsao")
def previsao_inicial(request: Request):
    alerta = next(iter(servicos.alertas(empresa_do_usuario(request))), None)
    destino = f"/previsao/{alerta.empresa_id}?categoria={alerta.categoria}" if alerta else \
        f"/previsao/{empresa_do_usuario(request)}"
    return RedirectResponse(destino, status_code=303)


@rotas.get("/previsao/{empresa}")
def previsao(request: Request, empresa: str, categoria: str | None = None):
    exigir_empresa(request, empresa)
    negocio = servicos.comercio(empresa)
    escolhida = categoria if categoria in CATEGORIAS else negocio.vai_crescer
    serie = servicos.serie(empresa, escolhida)
    alerta = next((a for a in servicos.alertas(empresa_do_usuario(request))
                   if a.empresa_id == empresa and a.categoria == escolhida), None)
    corrente, proximo = serie.previsoes
    tabela = [(formatos.mes_ano(mes), valor, "mês fechado") for mes, valor in serie.meses[-6:]]
    tabela.append((formatos.mes_ano(corrente.mes), f"{serie.parcial[1]} até hoje",
                   f"deve fechar perto de {corrente.p50}, entre {corrente.p10} e {corrente.p90}"))
    tabela.append((formatos.mes_ano(proximo.mes), f"cerca de {proximo.p50}",
                   f"estimativa, entre {proximo.p10} e {proximo.p90}"))
    return tela(
        request, "previsao.html", "resumo",
        negocio=negocio,
        negocios=servicos.comercios(empresa_do_usuario(request)),
        serie=serie,
        escolhida=escolhida,
        categorias_disponiveis=CATEGORIAS,
        alerta=alerta,
        tabela=tabela,
        frase=frases.previsao(serie),
        grafico=svg.colunas_mensais(
            serie, f"Reclamações de {frases.nome(escolhida)} por mês em {negocio.nome}"
        ),
    )


@rotas.get("/avisos")
def avisos(request: Request):
    lista = servicos.alertas(empresa_do_usuario(request))
    return tela(
        request, "avisos.html", "avisos",
        avisos=[{"alerta": a, "frase": frases.alerta(a)} for a in lista],
    )
