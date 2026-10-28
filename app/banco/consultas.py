"""As leituras do banco, no formato que `app/contratos.py` combinou.

Toda função aqui recebe `empresa_id` como primeiro argumento depois da sessão, e
toda consulta filtra por ele. O `empresa_id` vem da sessão do usuário — nunca da
URL nem do formulário. Uma função sem esse filtro é defeito, não estilo.

Atenção ao vocabulário: `empresa` é a parceira (a dona dos dados) e `comercio` é
o negócio dela. No contrato, o campo `empresa_id` carrega o identificador do
*comércio*, que é o que aparece na URL.
"""

from __future__ import annotations

import calendar
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.banco import modelo
from app.contratos import (
    Alerta,
    AvaliacaoTela,
    Certeza,
    Estado,
    PrevisaoMes,
    ResumoComercio,
    SerieMensal,
)
from app.modelos import LIMITE_CONFIANCA

# Três das sete etapas do combinado não dependem do parceiro: histórico, conferência
# da separação por assunto e conferência da estimativa. Ver `app/falsos.etapas`.
ETAPAS_SEM_PARCEIRO = 3
ETAPAS_TOTAL = 7


def _mes_de(dia: date) -> date:
    return date(dia.year, dia.month, 1)


def _fracao_do_mes(hoje: date) -> float:
    return round(hoje.day / calendar.monthrange(hoje.year, hoje.month)[1], 2)


def _faixa(linha: modelo.Previsao) -> PrevisaoMes:
    return PrevisaoMes(mes=linha.mes, p10=linha.p10, p50=linha.p50, p90=linha.p90)


def _estado(ultimo: int, previsto: PrevisaoMes | None) -> Estado:
    """Mesma régua de `app/falsos._estado`: a tela já aprendeu a ler estes três estados."""
    if previsto is None:
        return "normal"
    crescimento = previsto.p50 - ultimo
    if crescimento < 1.5 or crescimento / max(ultimo, 1) < 0.04:
        return "normal"
    return "vai_piorar" if previsto.p10 > ultimo else "fique_de_olho"


def _certeza(confianca: float) -> Certeza:
    if confianca >= 0.8:
        return "alta"
    return "media" if confianca >= LIMITE_CONFIANCA else "baixa"


def _etapas(comercio: modelo.Comercio) -> int:
    combinado = (comercio.tem_termo, comercio.tem_fonte,
                 comercio.categorias_combinadas, comercio.tem_canal)
    return ETAPAS_SEM_PARCEIRO + sum(combinado)


# ------------------------------------------------------------ séries e previsões

def serie(sessao: Session, empresa_id: str, comercio_id: str, categoria: str,
          hoje: date) -> SerieMensal | None:
    """A série de um assunto. Devolve None quando o comércio não é da empresa."""
    linhas = sessao.scalars(
        select(modelo.SerieMensal)
        .where(modelo.SerieMensal.empresa_id == empresa_id,
               modelo.SerieMensal.comercio_id == comercio_id,
               modelo.SerieMensal.categoria_id == categoria)
        .order_by(modelo.SerieMensal.mes)
    ).all()
    if not linhas:
        return None

    mes_corrente = _mes_de(hoje)
    meses = tuple((linha.mes, linha.quantidade) for linha in linhas if linha.mes < mes_corrente)
    aberto = next((linha.quantidade for linha in linhas if linha.mes == mes_corrente), 0)

    previsoes = sessao.scalars(
        select(modelo.Previsao)
        .join(modelo.VersaoModelo, modelo.VersaoModelo.id == modelo.Previsao.versao_modelo_id)
        .where(modelo.Previsao.empresa_id == empresa_id,
               modelo.Previsao.comercio_id == comercio_id,
               modelo.Previsao.categoria_id == categoria,
               modelo.Previsao.mes >= mes_corrente,
               modelo.VersaoModelo.ativa.is_(True))
        .order_by(modelo.Previsao.mes)
        .limit(2)
    ).all()

    return SerieMensal(
        empresa_id=comercio_id,
        categoria=categoria,
        meses=meses,
        parcial=(mes_corrente, aberto),
        parcial_fracao=_fracao_do_mes(hoje),
        previsoes=tuple(_faixa(p) for p in previsoes),
    )


# ------------------------------------------------------------ avaliações

def avaliacoes(sessao: Session, empresa_id: str, comercio_id: str,
               limite: int = 12) -> tuple[AvaliacaoTela, ...]:
    """As avaliações mais recentes, com o assunto do modelo que está no ar."""
    consulta = (
        select(modelo.Avaliacao, modelo.Classificacao)
        .outerjoin(
            modelo.Classificacao,
            (modelo.Classificacao.avaliacao_id == modelo.Avaliacao.id)
            & modelo.Classificacao.versao_modelo_id.in_(
                select(modelo.VersaoModelo.id).where(
                    modelo.VersaoModelo.empresa_id == empresa_id,
                    modelo.VersaoModelo.tipo == "classificacao",
                    modelo.VersaoModelo.ativa.is_(True),
                )
            ),
        )
        .where(modelo.Avaliacao.empresa_id == empresa_id,
               modelo.Avaliacao.comercio_id == comercio_id)
        .order_by(modelo.Avaliacao.data.desc(), modelo.Avaliacao.id.desc())
    )
    if limite:
        consulta = consulta.limit(limite)

    return tuple(
        AvaliacaoTela(
            id=avaliacao.id,
            data=avaliacao.data,
            estrelas=avaliacao.estrelas,
            texto=avaliacao.texto,
            categoria=classificacao.categoria_id if classificacao else None,
            certeza=_certeza(classificacao.confianca) if classificacao else None,
            motivo_sem_assunto=classificacao.motivo_sem_assunto if classificacao else None,
        )
        for avaliacao, classificacao in sessao.execute(consulta).all()
    )


# ------------------------------------------------------------ resumo

def _mes_referencia(sessao: Session, empresa_id: str, comercio_id: str) -> date | None:
    return sessao.scalar(
        select(func.max(modelo.SerieMensal.mes)).where(
            modelo.SerieMensal.empresa_id == empresa_id,
            modelo.SerieMensal.comercio_id == comercio_id,
            modelo.SerieMensal.fechado.is_(True),
        )
    )


def comercios(sessao: Session, empresa_id: str) -> tuple[ResumoComercio, ...]:
    """Os cartões do Resumo. Só os negócios da empresa da sessão."""
    negocios = sessao.scalars(
        select(modelo.Comercio)
        .where(modelo.Comercio.empresa_id == empresa_id)
        .order_by(modelo.Comercio.nome)
    ).all()

    cartoes = []
    for comercio in negocios:
        referencia = _mes_referencia(sessao, empresa_id, comercio.id)
        if referencia is None:
            continue

        fechado = dict(sessao.execute(
            select(modelo.SerieMensal.categoria_id, modelo.SerieMensal.quantidade).where(
                modelo.SerieMensal.empresa_id == empresa_id,
                modelo.SerieMensal.comercio_id == comercio.id,
                modelo.SerieMensal.mes == referencia,
            )
        ).all())
        if not fechado:
            continue

        # Em ordem de mês: o setdefault guarda a previsão do mês mais próximo de cada assunto.
        previstas: dict[str, PrevisaoMes] = {}
        for linha in sessao.scalars(
            select(modelo.Previsao)
            .join(modelo.VersaoModelo,
                  modelo.VersaoModelo.id == modelo.Previsao.versao_modelo_id)
            .where(modelo.Previsao.empresa_id == empresa_id,
                   modelo.Previsao.comercio_id == comercio.id,
                   modelo.Previsao.mes > referencia,
                   modelo.VersaoModelo.ativa.is_(True))
            .order_by(modelo.Previsao.mes)
        ).all():
            previstas.setdefault(linha.categoria_id, _faixa(linha))

        lidas, nota = sessao.execute(
            select(func.count(modelo.Avaliacao.id), func.avg(modelo.Avaliacao.estrelas)).where(
                modelo.Avaliacao.empresa_id == empresa_id,
                modelo.Avaliacao.comercio_id == comercio.id,
                modelo.Avaliacao.data >= referencia,
                modelo.Avaliacao.data < _proximo_mes(referencia),
            )
        ).one()
        sem_assunto = sessao.scalar(
            select(func.count(modelo.Avaliacao.id))
            .join(modelo.Classificacao,
                  modelo.Classificacao.avaliacao_id == modelo.Avaliacao.id)
            .where(modelo.Avaliacao.empresa_id == empresa_id,
                   modelo.Avaliacao.comercio_id == comercio.id,
                   modelo.Avaliacao.data >= referencia,
                   modelo.Avaliacao.data < _proximo_mes(referencia),
                   modelo.Classificacao.categoria_id.is_(None))
        ) or 0

        mais_reclamado = max(fechado, key=lambda c: (fechado[c], c))
        em_alta = max(
            fechado,
            key=lambda c: ((previstas[c].p50 - fechado[c]) if c in previstas else -10**6, c),
        )
        cartoes.append(ResumoComercio(
            empresa_id=comercio.id,
            nome=comercio.nome,
            ramo=comercio.ramo,
            cidade=comercio.cidade,
            estado=_estado(fechado[em_alta], previstas.get(em_alta)),
            mes_referencia=referencia,
            avaliacoes_lidas=lidas,
            reclamacoes=sum(fechado.values()),
            sem_assunto=sem_assunto,
            nota_media=round(nota, 1) if nota is not None else 0.0,
            mais_reclamado=mais_reclamado,
            mais_reclamado_qtd=fechado[mais_reclamado],
            vai_crescer=em_alta,
            vai_crescer_de=fechado[em_alta],
            vai_crescer_para=previstas.get(
                em_alta, PrevisaoMes(referencia, fechado[em_alta], fechado[em_alta],
                                     fechado[em_alta])
            ),
            etapas_concluidas=_etapas(comercio),
            etapas_total=ETAPAS_TOTAL,
        ))
    return tuple(cartoes)


def _proximo_mes(mes: date) -> date:
    return date(mes.year + mes.month // 12, mes.month % 12 + 1, 1)


# ------------------------------------------------------------ avisos

def alertas(sessao: Session, empresa_id: str) -> tuple[Alerta, ...]:
    """Os avisos abertos da empresa, do que mais deve crescer para o que menos."""
    linhas = sessao.execute(
        select(modelo.Alerta, modelo.Previsao, modelo.Comercio)
        .join(modelo.Previsao, modelo.Previsao.id == modelo.Alerta.previsao_id)
        .join(modelo.Comercio, modelo.Comercio.id == modelo.Alerta.comercio_id)
        .where(modelo.Alerta.empresa_id == empresa_id)
        # A docstring promete "os avisos abertos". Sem esta linha, aviso já
        # confirmado ou descartado volta na lista e entra na contagem.
        .where(modelo.Alerta.situacao == "aberto")
    ).all()

    avisos = [
        Alerta(
            id=alerta.id,
            empresa_id=alerta.comercio_id,
            empresa_nome=comercio.nome,
            categoria=alerta.categoria_id,
            estado=alerta.estado,
            atual=alerta.atual,
            previsto=_faixa(previsao),
            gerado_em=alerta.gerado_em,
            situacao=alerta.situacao,
        )
        for alerta, previsao, comercio in linhas
    ]
    avisos.sort(key=lambda a: (a.previsto.p50 - a.atual, a.id), reverse=True)
    return tuple(avisos)
