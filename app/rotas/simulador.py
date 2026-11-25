"""Tela "E se?": o dono cadastra os turnos, muda a equipe e vê o efeito na fila e na demora.

O cenário vai num formulário GET: funciona sem JavaScript, e o endereço guarda o
cenário, então dá para mandar o link para outra pessoa. O cadastro dos turnos
vai por POST, com o token de segurança, como todo formulário que grava.
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
from app.contratos import Cenario
from app.graficos import frases, svg
from app.modelos import fila
from app.rotas import formularios
from app.rotas._telas import tela
from app.seguranca import empresa_do_usuario, exigir_empresa, usuario_atual

rotas = APIRouter()
EQUIPE_MAXIMA = 20
# O "E se?" muda a equipe, e equipe mexe na espera. Por isso o assunto é demora.
ASSUNTO = "demora"


def _voltar(destino: str, recado: str = "", erro: str = "") -> RedirectResponse:
    # A âncora (#diario) vai depois da pergunta: antes, o navegador trataria o
    # recado como parte da âncora e a tela nunca o leria.
    caminho, _, ancora = destino.partition("#")
    partes = {k: v for k, v in (("recado", recado), ("erro", erro)) if v}
    endereco = caminho + ("?" + urlencode(partes) if partes else "") + (f"#{ancora}" if ancora else "")
    return RedirectResponse(endereco, status_code=303)


def _campo(turno) -> str:
    return f"t-{turno.dia_semana}-{turno.periodo}"


@rotas.get("/simulador")
def indice(request: Request):
    return tela(request, "simulador_indice.html", "simulador",
                negocios=servicos.comercios(empresa_do_usuario(request)))


@rotas.get("/simulador/{comercio}")
def simulador(request: Request, comercio: str, recado: str = "", erro: str = ""):
    empresa = exigir_empresa(request, comercio)
    negocio = servicos.comercio(empresa, comercio)
    if negocio is None:
        raise HTTPException(status_code=404)
    cadastrados = servicos.turnos(empresa, comercio)
    abertos = [t for t in cadastrados if t.equipe > 0 and t.clientes > 0]

    pedidos = request.query_params
    mudancas = []
    for t in abertos:
        try:
            equipe = int(pedidos.get(_campo(t), t.equipe))
        except ValueError:
            equipe = t.equipe
        equipe = max(1, min(EQUIPE_MAXIMA, equipe))
        if equipe != t.equipe:
            mudancas.append(fila.com_equipe(t, equipe))
    cenario = Cenario("Mudança escolhida na tela" if mudancas else "Sem mudança", ASSUNTO, tuple(mudancas))
    novos = {(t.dia_semana, t.periodo): t.equipe for t in cenario.mudancas}
    turnos = [{"turno": t, "campo": _campo(t), "valor": novos.get((t.dia_semana, t.periodo), t.equipe)}
              for t in abertos]
    resultado = servicos.simular(empresa, comercio, cenario) if abertos else None
    frase = frases.simulacao(resultado) if resultado else ""
    return tela(
        request, "simulador.html", "simulador",
        negocio=negocio,
        negocios=servicos.comercios(empresa),
        escolhida=ASSUNTO,
        cadastrados=cadastrados,
        turnos=turnos,
        resultado=resultado,
        frase=frase,
        grafico=svg.comparacao_cenario(
            resultado.reclamacoes_atual, resultado.reclamacoes_cenario,
            resultado.minimo, resultado.maximo, frase,
        ) if resultado else None,
        equipe_maxima=EQUIPE_MAXIMA,
        espera_longa=int(fila.ESPERA_LONGA),
        horas_do_turno=fila.HORAS_DO_TURNO,
        recado=recado, erro=erro,
    )


@rotas.post("/simulador/{comercio}/turno")
def salvar_turno(request: Request, comercio: str, dia_semana: str = Form(""), periodo: str = Form(""),
                 equipe: str = Form(""), clientes: str = Form(""), minutos_atendimento: str = Form(""),
                 custo_hora: str = Form("0"), csrf: str = Form("")):
    empresa = exigir_empresa(request, comercio)
    volta = f"/simulador/{comercio}"
    try:
        dados = formularios.TurnoNovo(
            dia_semana=dia_semana, periodo=periodo, equipe=equipe, clientes=clientes.replace(",", "."),
            minutos_atendimento=minutos_atendimento.replace(",", "."),
            custo_hora=(custo_hora or "0").replace(",", "."),
        )
    except ValidationError as erro:
        return _voltar(volta + "#turnos", erro=erro.errors()[0]["msg"].removeprefix("Value error, "))
    usuario = usuario_atual(request)
    with banco.Sessao() as sessao:
        negocio = sessao.get(modelo.Comercio, comercio)
        if negocio is None or negocio.empresa_id != empresa:
            raise HTTPException(status_code=403, detail="Esse negócio não é o seu.")
        linha = sessao.scalar(select(modelo.Turno).where(
            modelo.Turno.empresa_id == empresa, modelo.Turno.comercio_id == comercio,
            modelo.Turno.dia_semana == dados.dia_semana, modelo.Turno.periodo == dados.periodo))
        if linha is None:
            linha = modelo.Turno(id=f"tu-{uuid.uuid4().hex[:16]}", empresa_id=empresa,
                                 comercio_id=comercio, dia_semana=dados.dia_semana, periodo=dados.periodo)
            sessao.add(linha)
        linha.equipe = dados.equipe
        linha.clientes = dados.clientes
        linha.minutos_atendimento = dados.minutos_atendimento
        linha.custo_hora = dados.custo_hora
        auditoria.registrar(sessao, empresa_id=empresa, usuario_id=usuario.identificador,
                            acao="turno_salvo", objeto=comercio,
                            detalhe=f"dia {dados.dia_semana}, {dados.periodo}")
        sessao.commit()
    return _voltar(volta, recado="Turno salvo.")


@rotas.post("/simulador/{comercio}/turno/apagar")
def apagar_turno(request: Request, comercio: str, dia_semana: str = Form(""), periodo: str = Form(""),
                 csrf: str = Form("")):
    empresa = exigir_empresa(request, comercio)
    usuario = usuario_atual(request)
    try:
        dia = int(dia_semana)
    except ValueError:
        return _voltar(f"/simulador/{comercio}#turnos", erro="turno inválido")
    with banco.Sessao() as sessao:
        linha = sessao.scalar(select(modelo.Turno).where(
            modelo.Turno.empresa_id == empresa, modelo.Turno.comercio_id == comercio,
            modelo.Turno.dia_semana == dia, modelo.Turno.periodo == periodo))
        if linha is not None:
            sessao.delete(linha)
            auditoria.registrar(sessao, empresa_id=empresa, usuario_id=usuario.identificador,
                                acao="turno_apagado", objeto=comercio, detalhe=f"dia {dia}, {periodo}")
            sessao.commit()
    return _voltar(f"/simulador/{comercio}#turnos", recado="Turno apagado.")
