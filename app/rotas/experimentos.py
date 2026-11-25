"""Tela "Testes": criar o teste, ver os dias sorteados, marcar cada dia e ler o resultado.

O sorteio, o selo e a comparação estão em `app/modelos/experimento.py`. Aqui só
se grava o que o dono decidiu (o plano) e o que ele marcou (cada dia).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select

from app import auditoria, servicos
from app.banco import modelo
from app.banco import sessao as banco
from app.contratos import CATEGORIAS
from app.graficos import svg
from app.modelos import experimento as teste
from app.rotas import formularios
from app.rotas._telas import tela
from app.seguranca import empresa_do_usuario, exigir_empresa, usuario_atual

rotas = APIRouter()


def _voltar(destino: str, recado: str = "", erro: str = "") -> RedirectResponse:
    # A âncora (#diario) vai depois da pergunta: antes, o navegador trataria o
    # recado como parte da âncora e a tela nunca o leria.
    caminho, _, ancora = destino.partition("#")
    partes = {k: v for k, v in (("recado", recado), ("erro", erro)) if v}
    endereco = caminho + ("?" + urlencode(partes) if partes else "") + (f"#{ancora}" if ancora else "")
    return RedirectResponse(endereco, status_code=303)


def codigo_do_plano(selo: str) -> str:
    """O selo inteiro é longo demais para anotar; o código curto são os 8 primeiros sinais."""
    return f"{selo[:4]}-{selo[4:8]}".upper()


def _progresso(marcacoes) -> tuple[int, int]:
    return sum(1 for m in marcacoes if m.seguiu is not None), len(marcacoes)


@rotas.get("/experimentos")
def lista(request: Request, recado: str = "", erro: str = ""):
    empresa = empresa_do_usuario(request)
    negocios = {n.empresa_id: n for n in servicos.comercios(empresa)}
    itens = []
    for plano, comercio_id in servicos.experimentos(empresa):
        marcados, total = _progresso(servicos.marcacoes(empresa, plano.id))
        itens.append({"plano": plano, "negocio": negocios.get(comercio_id),
                      "marcados": marcados, "total": total})
    hoje = servicos.hoje()
    return tela(request, "experimentos.html", "experimentos", itens=itens,
                negocios=tuple(negocios.values()), categorias_disponiveis=CATEGORIAS,
                amanha=hoje + timedelta(days=1), hoje=hoje,
                dias_minimo=teste.DIAS_MINIMO, dias_maximo=teste.DIAS_MAXIMO,
                recado=recado, erro=erro)


@rotas.post("/experimentos")
def criar(request: Request, comercio_id: str = Form(""), categoria: str = Form(""), acao: str = Form(""),
          inicio: str = Form(""), dias: str = Form("28"), csrf: str = Form("")):
    try:
        dados = formularios.ExperimentoNovo(comercio_id=comercio_id, categoria=categoria, acao=acao,
                                            inicio=inicio, dias=dias)
    except ValidationError as erro:
        return _voltar("/experimentos#novo", erro=erro.errors()[0]["msg"].removeprefix("Value error, "))
    empresa = exigir_empresa(request, dados.comercio_id)
    usuario = usuario_atual(request)
    com, sem = teste.sortear(dados.inicio, dados.dias)
    fim = dados.inicio + timedelta(days=dados.dias - 1)
    selado_em = datetime.now().replace(microsecond=0)
    base = servicos.reclamacoes_por_dia(empresa, dados.comercio_id, dados.categoria)
    plano_id = f"tp-{uuid.uuid4().hex[:16]}"
    with banco.Sessao() as sessao:
        negocio = sessao.get(modelo.Comercio, dados.comercio_id)
        if negocio is None or negocio.empresa_id != empresa:
            raise HTTPException(status_code=403, detail="Esse negócio não é o seu.")
        sessao.add(modelo.Experimento(
            id=plano_id, empresa_id=empresa, comercio_id=dados.comercio_id,
            categoria_id=dados.categoria, acao=dados.acao, inicio=dados.inicio, fim=fim,
            dias_com_acao=",".join(d.isoformat() for d in com),
            menor_efeito=teste.menor_efeito(base, len(com), len(sem)),
            selo=teste.selar(dados.categoria, dados.acao, dados.inicio, fim, com, selado_em),
            selado_em=selado_em, estado="em_andamento",
        ))
        auditoria.registrar(sessao, empresa_id=empresa, usuario_id=usuario.identificador,
                            acao="teste_criado", objeto=dados.comercio_id, detalhe=dados.acao[:120])
        sessao.commit()
    return _voltar(f"/experimentos/{plano_id}",
                   recado="Teste criado e dias sorteados. Anote o código do plano.")


@rotas.get("/experimentos/{plano_id}")
def detalhe(request: Request, plano_id: str, recado: str = "", erro: str = ""):
    empresa = empresa_do_usuario(request)
    achado = servicos.experimento(empresa, plano_id)
    if achado is None:
        # Recusa igual à de empresa alheia: 404 aqui contaria quais planos existem.
        raise HTTPException(status_code=403, detail="Esse plano não é o seu.")
    plano, comercio_id = achado
    exigir_empresa(request, comercio_id)
    marcacoes = servicos.marcacoes(empresa, plano_id)
    marcados, total = _progresso(marcacoes)
    resultado, p = servicos.analisar(empresa, plano_id)
    grafico = None
    if resultado is not None:
        grafico = svg.duas_colunas(
            "dias sem", resultado.media_sem, "dias com", resultado.media_com, "por dia",
            resultado.frase,
            sentido="melhorou" if resultado.media_com < resultado.media_sem else "piorou",
        )
    return tela(
        request, "experimento.html", "experimentos",
        plano=plano,
        negocio=servicos.comercio(empresa, comercio_id),
        codigo=codigo_do_plano(plano.selo),
        selo_confere=teste.selo_confere(plano),
        marcacoes=marcacoes,
        marcados=marcados,
        total=total,
        seguiu=sum(1 for m in marcacoes if m.seguiu),
        hoje=servicos.hoje(),
        resultado=resultado,
        p_valor=p,
        grafico=grafico,
        recado=recado, erro=erro,
    )


@rotas.post("/experimentos/{plano_id}/marcar")
def marcar(request: Request, plano_id: str, data: str = Form(""), seguiu: str = Form(""),
           csrf: str = Form("")):
    empresa = empresa_do_usuario(request)
    achado = servicos.experimento(empresa, plano_id)
    if achado is None:
        raise HTTPException(status_code=403, detail="Esse plano não é o seu.")
    plano, comercio_id = achado
    exigir_empresa(request, comercio_id)
    volta = f"/experimentos/{plano_id}"
    try:
        dados = formularios.Marcacao(data=data, seguiu=seguiu)
    except ValidationError:
        return _voltar(volta + "#dias", erro="marcação inválida")
    if dados.data not in set(plano.dias_com_acao) | set(plano.dias_sem_acao):
        return _voltar(volta + "#dias", erro="esse dia não faz parte do teste")
    if dados.data > servicos.hoje():
        return _voltar(volta + "#dias", erro="esse dia ainda não chegou")
    usuario = usuario_atual(request)
    with banco.Sessao() as sessao:
        linha = sessao.scalar(select(modelo.MarcacaoDia).where(
            modelo.MarcacaoDia.empresa_id == empresa, modelo.MarcacaoDia.experimento_id == plano_id,
            modelo.MarcacaoDia.data == dados.data))
        if linha is None:
            linha = modelo.MarcacaoDia(empresa_id=empresa, experimento_id=plano_id, data=dados.data,
                                       seguiu=dados.seguiu)
            sessao.add(linha)
        else:
            linha.seguiu = dados.seguiu
            linha.marcado_em = datetime.now()
        auditoria.registrar(sessao, empresa_id=empresa, usuario_id=usuario.identificador,
                            acao="dia_marcado", objeto=plano_id,
                            detalhe=f"{dados.data.isoformat()}: {'seguiu' if dados.seguiu else 'não seguiu'}")
        sessao.commit()
    return _voltar(volta + "#dias", recado="Dia marcado.")
