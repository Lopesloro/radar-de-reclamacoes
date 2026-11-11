"""Resumo, ficha do negócio, estimativa e avisos.

Toda tela aqui lê o banco pela porta de `app/servicos.py` e todas tratam o caso
de não haver dado: cliente recém-ligado, fonte que ainda não coletou, negócio
sem mês fechado. A tela diz isso em uma frase e aponta o que fazer, em vez de
mostrar zero como se fosse medida.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app import formatos, servicos
from app.contratos import CATEGORIAS
from app.formatos import mes_longo
from app.graficos import frases, svg
from app.modelos import ativo, leitura
from app.rotas._telas import tela
from app.seguranca import empresa_do_usuario, exigir_comercio

rotas = APIRouter()


def _vazio(request: Request, ativo: str, **contexto):
    """A tela de "ainda não há dado", com o motivo certo.

    `negocios` vem de `negocios_cadastrados` e não de `comercios`: o segundo
    devolve só quem tem mês fechado, e com ele um cliente recém-cadastrado lia
    "você não tem negócio ligado" quando o negócio dele estava ligado e só
    faltavam as avaliações chegarem.
    """
    return tela(
        request, "sem_dados.html", ativo,
        tem_banco=servicos.tem_banco(),
        negocios=servicos.negocios_cadastrados(empresa_do_usuario(request)),
        **contexto,
    )


@rotas.get("/resumo")
def resumo(request: Request):
    empresa = empresa_do_usuario(request)
    negocios = servicos.comercios(empresa)
    if not negocios:
        return _vazio(request, "resumo")

    cartoes = []
    for c in negocios:
        serie = servicos.serie(empresa, c.empresa_id, c.vai_crescer)
        cartoes.append({
            "negocio": c,
            "frase": frases.cartao(c),
            "grafico": svg.mini_colunas(
                serie.meses[-6:] if serie else (),
                f"Reclamações de {frases.nome(c.vai_crescer)} nos últimos 6 meses",
            ),
        })
    return tela(
        request, "resumo.html", "resumo",
        cartoes=cartoes,
        mes=negocios[0].mes_referencia,
        mes_corrente=negocios[0].vai_crescer_para.mes,
        lidas=sum(c.avaliacoes_lidas for c in negocios),
        reclamacoes=sum(c.reclamacoes for c in negocios),
        avisos=servicos.alertas(empresa),
        piorando=sum(1 for c in negocios if c.estado == "vai_piorar"),
    )


@rotas.get("/comercio/{comercio}")
def comercio(request: Request, comercio: str):
    empresa = exigir_comercio(request, comercio)
    negocio = servicos.comercio(empresa, comercio)
    if negocio is None:
        return _vazio(request, "resumo", negocio_sem_mes=comercio)
    todas = sorted(servicos.series(empresa, comercio), key=lambda s: s.ultimo, reverse=True)
    if not todas:
        return _vazio(request, "resumo", negocio_sem_mes=comercio)

    mes_anterior = mes_longo(todas[0].meses[-2][0]) if len(todas[0].meses) > 1 else ""
    itens = [(frases.nome(s.categoria), s.ultimo, s.variacao) for s in todas]
    return tela(
        request, "comercio.html", "resumo",
        negocio=negocio,
        negocios=servicos.comercios(empresa),
        series=todas,
        mes_anterior=mes_anterior,
        frase=frases.assuntos_do_mes(todas, negocio.mes_referencia),
        grafico=svg.barras_assuntos(
            itens, f"Reclamações por assunto em {negocio.nome}", mes_anterior),
        tabela=[(nome, valor, valor - variacao, formatos.diferenca(variacao))
                for nome, valor, variacao in itens],
        avaliacoes=servicos.avaliacoes(empresa, comercio),
    )


@rotas.get("/previsao")
def previsao_inicial(request: Request):
    """Manda para a estimativa que mais importa: a do aviso aberto, se houver."""
    empresa = empresa_do_usuario(request)
    alerta = next(iter(servicos.alertas(empresa)), None)
    if alerta is not None:
        return RedirectResponse(
            f"/previsao/{alerta.empresa_id}?categoria={alerta.categoria}", status_code=303)
    negocios = servicos.comercios(empresa)
    if not negocios:
        return RedirectResponse("/resumo", status_code=303)
    return RedirectResponse(f"/previsao/{negocios[0].empresa_id}", status_code=303)


@rotas.get("/previsao/{comercio}")
def previsao(request: Request, comercio: str, categoria: str | None = None):
    empresa = exigir_comercio(request, comercio)
    negocio = servicos.comercio(empresa, comercio)
    if negocio is None:
        return _vazio(request, "resumo", negocio_sem_mes=comercio)
    escolhida = categoria if categoria in CATEGORIAS else negocio.vai_crescer
    serie = servicos.serie(empresa, comercio, escolhida)
    if serie is None or not serie.meses:
        return _vazio(request, "resumo", negocio_sem_mes=comercio)

    alerta = next((a for a in servicos.alertas(empresa)
                   if a.empresa_id == comercio and a.categoria == escolhida), None)
    tabela = [(formatos.mes_ano(mes), valor, "mês fechado") for mes, valor in serie.meses[-6:]]
    corrente = proximo = None
    if len(serie.previsoes) >= 2:
        corrente, proximo = serie.previsoes[0], serie.previsoes[1]
        tabela.append((
            formatos.mes_ano(corrente.mes), f"{serie.parcial[1]} até hoje",
            f"deve fechar perto de {corrente.p50}, entre {corrente.p10} e {corrente.p90}",
        ))
        tabela.append((
            formatos.mes_ano(proximo.mes), f"cerca de {proximo.p50}",
            f"estimativa, entre {proximo.p10} e {proximo.p90}",
        ))
    else:
        # Menos de seis meses fechados: a estimativa não sai, e a tela diz por quê.
        tabela.append((
            formatos.mes_ano(serie.parcial[0]), f"{serie.parcial[1]} até hoje",
            "a estimativa começa com seis meses fechados",
        ))
    return tela(
        request, "previsao.html", "resumo",
        negocio=negocio,
        negocios=servicos.comercios(empresa),
        serie=serie,
        corrente=corrente,
        proximo=proximo,
        escolhida=escolhida,
        categorias_disponiveis=CATEGORIAS,
        alerta=alerta,
        tabela=tabela,
        frase=frases.previsao(serie),
        leitura=leitura.da_previsao(negocio.nome, serie),
        com_ia=ativo.usando_ia(),
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
        tem_negocio=bool(servicos.comercios(empresa_do_usuario(request))),
    )
