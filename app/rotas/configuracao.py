"""A tela de configuração do cliente: fontes, canal de aviso e conferência dos assuntos.

Três coisas que o dono do negócio faz aqui, e nenhuma delas é de administrador:

1. **Vê de onde o sistema está lendo** e o que falta para a leitura ficar
   automática. Sem segredo nenhum na tela: só a plataforma e o estado.
2. **Diz para onde o aviso vai.** É uma das sete etapas do combinado.
3. **Confere o assunto de uma avaliação.** É a parte mais importante da tela:
   cada conferência vira rótulo de verdade, e a partir de trinta delas a tela
   "Dá para confiar?" passa a medir o acerto nas avaliações do próprio negócio,
   em vez de no corpus escrito pela equipe. É o cliente ensinando o sistema, e é
   também o que faz o número que ele lê ser sobre o negócio dele.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select

from app import auditoria, servicos
from app.banco import modelo
from app.banco import sessao as banco
from app.coleta import fontes
from app.contratos import CATEGORIAS
from app.modelos import conferencia
from app.rotas import formularios
from app.rotas._telas import tela
from app.seguranca import empresa_do_usuario, usuario_atual

rotas = APIRouter()

AVALIACOES_PARA_CONFERIR = 12


def _voltar(destino: str, recado: str = "", erro: str = "") -> RedirectResponse:
    from urllib.parse import urlencode

    partes = {k: v for k, v in (("recado", recado), ("erro", erro)) if v}
    return RedirectResponse(destino + ("?" + urlencode(partes) if partes else ""),
                            status_code=303)


@rotas.get("/configuracao")
def configuracao(request: Request, recado: str = "", erro: str = ""):
    empresa = empresa_do_usuario(request)
    if not banco.usar_banco():
        return tela(request, "configuracao.html", "configuracao",
                    sem_banco=True, negocios=(), fontes_por_negocio={},
                    email_aviso="", conferidas=0, plataformas=fontes.PLATAFORMAS)
    with banco.Sessao() as sessao:
        linha = sessao.get(modelo.Empresa, empresa)
        negocios = tuple(sessao.scalars(select(modelo.Comercio).where(
            modelo.Comercio.empresa_id == empresa).order_by(modelo.Comercio.nome)).all())
        por_negocio = {
            n.id: tuple(sessao.scalars(select(modelo.Fonte).where(
                modelo.Fonte.comercio_id == n.id)).all())
            for n in negocios
        }
        return tela(
            request, "configuracao.html", "configuracao",
            sem_banco=False,
            negocios=negocios, fontes_por_negocio=por_negocio,
            email_aviso=(linha.email_aviso if linha else "") or "",
            conferidas=len(conferencia.conferidas_no_banco()),
            minimo_conferidas=conferencia.MINIMO_CONFERIDAS,
            plataformas=fontes.PLATAFORMAS,
            etapas_por_negocio={n.id: servicos.etapas(empresa, n.id) for n in negocios},
            recado=recado, erro=erro,
        )


@rotas.post("/configuracao/aviso")
def salvar_aviso(request: Request, email_aviso: str = Form(""), csrf: str = Form("")):
    empresa = empresa_do_usuario(request)
    try:
        dados = formularios.CanalDeAviso(email_aviso=email_aviso)
    except ValidationError as erro:
        return _voltar("/configuracao", erro=erro.errors()[0]["msg"])
    with banco.Sessao() as sessao:
        linha = sessao.get(modelo.Empresa, empresa)
        if linha is None:
            return _voltar("/configuracao", erro="não achei a sua empresa.")
        linha.email_aviso = dados.email_aviso or None
        auditoria.registrar(
            sessao, empresa_id=empresa, usuario_id=usuario_atual(request).nome,
            acao="canal_definido", objeto="canal de aviso",
            detalhe="e-mail de aviso definido" if dados.email_aviso else "e-mail de aviso retirado",
        )
        sessao.commit()
    return _voltar("/configuracao", recado="Canal de aviso salvo.")


@rotas.get("/conferir")
def conferir(request: Request, recado: str = "", erro: str = ""):
    """As avaliações mais recentes com o assunto que o modelo deu, para o dono confirmar."""
    empresa = empresa_do_usuario(request)
    negocios = servicos.comercios(empresa)
    if not negocios:
        return tela(request, "conferir.html", "configuracao", itens=(), negocio=None,
                    conferidas=0, minimo=conferencia.MINIMO_CONFERIDAS, categorias=CATEGORIAS)
    negocio = negocios[0]
    with banco.Sessao() as sessao:
        linhas = sessao.execute(
            select(modelo.Avaliacao, modelo.Classificacao)
            .outerjoin(modelo.Classificacao,
                       modelo.Classificacao.avaliacao_id == modelo.Avaliacao.id)
            .where(modelo.Avaliacao.empresa_id == empresa,
                   modelo.Avaliacao.comercio_id == negocio.empresa_id,
                   modelo.Avaliacao.texto.is_not(None))
            .order_by(modelo.Avaliacao.data.desc())
            .limit(AVALIACOES_PARA_CONFERIR)
        ).all()
        itens = tuple(
            {
                "avaliacao": avaliacao,
                "assunto": classificacao.categoria_id if classificacao else None,
                "confirmada": bool(classificacao
                                   and classificacao.motivo_sem_assunto
                                   == conferencia.MARCA_DE_CONFERIDA),
            }
            for avaliacao, classificacao in linhas
        )
        return tela(
            request, "conferir.html", "configuracao",
            itens=itens, negocio=negocio, categorias=CATEGORIAS,
            conferidas=len(conferencia.conferidas_no_banco()),
            minimo=conferencia.MINIMO_CONFERIDAS, recado=recado, erro=erro,
        )


@rotas.post("/conferir")
def salvar_conferencia(request: Request, avaliacao_id: str = Form(""),
                       categoria: str = Form(""), csrf: str = Form("")):
    empresa = empresa_do_usuario(request)
    try:
        dados = formularios.Conferencia(avaliacao_id=avaliacao_id, categoria=categoria)
    except ValidationError as erro:
        return _voltar("/conferir", erro=erro.errors()[0]["msg"])

    with banco.Sessao() as sessao:
        avaliacao = sessao.get(modelo.Avaliacao, dados.avaliacao_id)
        # A trava de empresa de novo, aqui dentro: o identificador da avaliação
        # vem do formulário, e formulário é dado de fora.
        if avaliacao is None or avaliacao.empresa_id != empresa:
            return _voltar("/conferir", erro="essa avaliação não é do seu negócio.")

        versao = sessao.scalar(select(modelo.VersaoModelo).where(
            modelo.VersaoModelo.empresa_id == empresa,
            modelo.VersaoModelo.tipo == "conferencia"))
        if versao is None:
            from datetime import datetime

            versao = modelo.VersaoModelo(
                id=f"conf-{uuid.uuid4().hex[:12]}", empresa_id=empresa, tipo="conferencia",
                nome="conferido pelo dono", treinada_em=datetime.now(), ativa=False,
            )
            sessao.add(versao)
            sessao.flush()

        atual = sessao.scalar(select(modelo.Classificacao).where(
            modelo.Classificacao.avaliacao_id == avaliacao.id,
            modelo.Classificacao.versao_modelo_id == versao.id))
        if atual is None:
            atual = modelo.Classificacao(
                id=f"cf-{uuid.uuid4().hex[:16]}", empresa_id=empresa,
                avaliacao_id=avaliacao.id, confianca=1.0, versao_modelo_id=versao.id,
            )
            sessao.add(atual)
        atual.categoria_id = dados.categoria or None
        atual.motivo_sem_assunto = conferencia.MARCA_DE_CONFERIDA
        auditoria.registrar(
            sessao, empresa_id=empresa, usuario_id=usuario_atual(request).nome,
            acao="assunto_conferido", objeto=avaliacao.id,
            detalhe=f"assunto conferido pelo dono: {dados.categoria or 'nenhum'}",
        )
        sessao.commit()
    return _voltar("/conferir", recado="Conferido. Obrigado: é isso que afina o sistema.")
