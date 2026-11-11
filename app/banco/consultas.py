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
    EtapaParceiro,
    PrevisaoMes,
    ResumoComercio,
    SerieMensal,
)
from app.modelos import LIMITE_CONFIANCA
from app.modelos.previsao import CRESCIMENTO_QUE_IMPORTA

# As sete etapas do combinado. Cada uma é conferida contra um fato do banco em
# `etapas()`, no fim deste arquivo.
ETAPAS_TOTAL = 7


def _mes_de(dia: date) -> date:
    return date(dia.year, dia.month, 1)


def _fracao_do_mes(hoje: date) -> float:
    return round(hoje.day / calendar.monthrange(hoje.year, hoje.month)[1], 2)


def _faixa(linha: modelo.Previsao) -> PrevisaoMes:
    return PrevisaoMes(mes=linha.mes, p10=linha.p10, p50=linha.p50, p90=linha.p90)


def _estado(ultimo: int, previsto: PrevisaoMes | None) -> Estado:
    """Os três estados que a tela mostra, com a mesma régua que foi medida.

    O limite é `previsao.CRESCIMENTO_QUE_IMPORTA`, importado e não copiado: a
    medição de acerto do aviso em `previsao.avaliar_avisos` usa esse mesmo
    número, e dois números diferentes para a mesma pergunta fariam a tela avisar
    numa régua e o relatório medir em outra.

    - `vai_piorar`: o mínimo esperado já passa do mês fechado. Acerto medido 0,59.
    - `fique_de_olho`: o mais provável sobe o bastante para importar. Acerto 0,43.
    - `normal`: o resto, inclusive subida que cabe no sobe-e-desde normal.
    """
    if previsto is None:
        return "normal"
    if previsto.p10 > ultimo:
        return "vai_piorar"
    if previsto.p50 - ultimo >= CRESCIMENTO_QUE_IMPORTA:
        return "fique_de_olho"
    return "normal"


def _certeza(confianca: float) -> Certeza:
    if confianca >= 0.8:
        return "alta"
    return "media" if confianca >= LIMITE_CONFIANCA else "baixa"


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

        def _quanto_cresce(categoria: str, fechado=fechado,
                           previstas=previstas) -> tuple[int, int, str]:
            """A ordem que escolhe o assunto em alta: cresce mais, e depois o maior.

            O segundo critério não é enfeite. Sem ele o desempate caía na ordem
            alfabética, e um assunto com 1 reclamação que sobe 1 ganhava de um com
            19 que também sobe 1, só porque "qualidade" vem depois de "demora".
            A tela então dizia "a demora é o que mais incomoda" no gráfico e abria
            a estimativa em qualidade. Aconteceu em produção.
            """
            atual = fechado[categoria]
            if categoria not in previstas:
                return (-10**6, atual, categoria)
            return (previstas[categoria].p50 - atual, atual, categoria)

        em_alta = max(fechado, key=_quanto_cresce)
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
            # A contagem sai da mesma função que desenha a tela "O que falta":
            # dois números diferentes para a mesma pergunta já aconteceu aqui.
            etapas_concluidas=sum(
                1 for e in etapas(sessao, empresa_id, comercio.id) if e.estado == "feito"
            ),
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


# ------------------------------------------------------------ o que as telas pedem direto

def ids_de_comercio(sessao: Session, empresa_id: str) -> frozenset[str]:
    """Os negócios da empresa. É o conjunto que a trava de isolamento compara."""
    return frozenset(sessao.scalars(
        select(modelo.Comercio.id).where(modelo.Comercio.empresa_id == empresa_id)
    ).all())


def negocios_cadastrados(sessao: Session, empresa_id: str) -> tuple[tuple[str, str, str], ...]:
    """Todo negócio da empresa, independente de ter histórico."""
    return tuple(
        (linha.id, linha.nome, linha.cidade)
        for linha in sessao.scalars(
            select(modelo.Comercio)
            .where(modelo.Comercio.empresa_id == empresa_id)
            .order_by(modelo.Comercio.nome)
        ).all()
    )


def comercio(sessao: Session, empresa_id: str, comercio_id: str) -> ResumoComercio | None:
    """O cartão de um negócio. None quando não é da empresa ou não tem mês fechado."""
    return next(
        (c for c in comercios(sessao, empresa_id) if c.empresa_id == comercio_id),
        None,
    )


def series(sessao: Session, empresa_id: str, comercio_id: str,
           hoje: date) -> tuple[SerieMensal, ...]:
    """Uma série por assunto que tem histórico neste negócio."""
    assuntos = sessao.scalars(
        select(modelo.SerieMensal.categoria_id)
        .where(modelo.SerieMensal.empresa_id == empresa_id,
               modelo.SerieMensal.comercio_id == comercio_id)
        .distinct()
    ).all()
    achadas = (serie(sessao, empresa_id, comercio_id, assunto, hoje) for assunto in sorted(assuntos))
    return tuple(s for s in achadas if s is not None and s.meses)


def series_fechadas(sessao: Session, empresa_id: str) -> tuple[tuple[str, tuple[tuple[date, int], ...]], ...]:
    """Os meses fechados de cada (negócio, assunto). É o que a conferência da
    previsão usa para rodar a origem móvel em cima do dado real da empresa."""
    linhas = sessao.execute(
        select(modelo.SerieMensal.comercio_id, modelo.SerieMensal.categoria_id,
               modelo.SerieMensal.mes, modelo.SerieMensal.quantidade)
        .where(modelo.SerieMensal.empresa_id == empresa_id,
               modelo.SerieMensal.fechado.is_(True))
        .order_by(modelo.SerieMensal.comercio_id, modelo.SerieMensal.categoria_id,
                  modelo.SerieMensal.mes)
    ).all()
    agrupadas: dict[tuple[str, str], list[tuple[date, int]]] = {}
    for comercio_id, categoria, mes, quantidade in linhas:
        agrupadas.setdefault((comercio_id, categoria), []).append((mes, quantidade))
    return tuple(
        (f"{comercio_id} / {categoria}", tuple(meses))
        for (comercio_id, categoria), meses in agrupadas.items()
    )


def quantos_negocios(sessao: Session) -> int:
    """A contagem para a página pública: um número, de empresa nenhuma em particular."""
    return sessao.scalar(
        select(func.count(modelo.Comercio.id)).join(
            modelo.Empresa, modelo.Empresa.id == modelo.Comercio.empresa_id
        ).where(modelo.Empresa.ativa.is_(True), modelo.Empresa.plano != "interno")
    ) or 0


def tem_avaliacao(sessao: Session, empresa_id: str) -> bool:
    return sessao.scalar(
        select(func.count(modelo.Avaliacao.id)).where(modelo.Avaliacao.empresa_id == empresa_id)
    ) > 0


# ------------------------------------------------------------ etapas do combinado

_TITULOS_DAS_ETAPAS = (
    (1, "Autorização assinada", "O dono autorizou por escrito a leitura das avaliações públicas dele."),
    (2, "Fonte ligada", "A conta da plataforma está ligada e o sistema consegue ler as avaliações."),
    (3, "Assuntos combinados", "O dono conferiu que os cinco assuntos descrevem o negócio dele."),
    (4, "Canal de aviso", "Para onde o aviso vai quando um assunto deve crescer."),
    (5, "Histórico suficiente", "Seis meses fechados: abaixo disso a estimativa não sai."),
    (6, "Separação conferida", "Uma amostra de avaliações foi conferida à mão para medir o acerto."),
    (7, "Estimativa conferida", "A estimativa foi comparada com o que de fato aconteceu."),
)


def etapas(sessao: Session, empresa_id: str, comercio_id: str) -> tuple[EtapaParceiro, ...]:
    """As sete etapas entre o combinado e o aviso chegando ao dono.

    Cada estado sai de um fato do banco, não de uma marcação à mão: é por isso
    que a tela "O que falta" não mente quando alguém esquece de atualizar algo.
    """
    negocio = sessao.get(modelo.Comercio, comercio_id)
    if negocio is None or negocio.empresa_id != empresa_id:
        return ()
    empresa = sessao.get(modelo.Empresa, empresa_id)

    fonte = sessao.scalar(
        select(modelo.Fonte).where(modelo.Fonte.comercio_id == comercio_id,
                                   modelo.Fonte.estado == "ligada")
    )
    meses = sessao.scalar(
        select(func.count(modelo.SerieMensal.mes)).where(
            modelo.SerieMensal.comercio_id == comercio_id,
            modelo.SerieMensal.fechado.is_(True),
            modelo.SerieMensal.categoria_id == "atendimento",
        )
    ) or 0
    conferidas = sessao.scalar(
        select(func.count(modelo.Classificacao.id))
        .join(modelo.Avaliacao, modelo.Avaliacao.id == modelo.Classificacao.avaliacao_id)
        .where(modelo.Avaliacao.comercio_id == comercio_id,
               modelo.Classificacao.motivo_sem_assunto == "conferida pelo dono")
    ) or 0
    previsoes = sessao.scalar(
        select(func.count(modelo.Previsao.id)).where(modelo.Previsao.comercio_id == comercio_id)
    ) or 0

    fatos = (
        (negocio.tem_termo, "Autorização no arquivo do projeto.", "Falta o dono assinar a autorização."),
        (fonte is not None, f"Lendo de {fonte.plataforma if fonte else ''}.",
         "Falta ligar a conta da plataforma."),
        (negocio.categorias_combinadas, "Os cinco assuntos foram conferidos com o dono.",
         "Falta o dono conferir se os assuntos descrevem o negócio."),
        (bool(empresa and empresa.email_aviso) or negocio.tem_canal,
         "O aviso vai por e-mail.", "Falta dizer para onde o aviso vai."),
        (meses >= 6, f"{meses} meses fechados.", f"Faltam {max(0, 6 - meses)} meses de histórico."),
        (conferidas >= 30, f"{conferidas} avaliações conferidas à mão.",
         f"Faltam {max(0, 30 - conferidas)} avaliações conferidas para medir o acerto."),
        (previsoes > 0, "Estimativa gerada e comparada com o realizado.",
         "Falta a primeira estimativa deste negócio."),
    )
    return tuple(
        EtapaParceiro(
            numero=numero, titulo=titulo,
            estado="feito" if pronto else "pendente",
            detalhe=detalhe if pronto else descricao,
            falta=None if pronto else falta,
        )
        for (numero, titulo, descricao), (pronto, detalhe, falta) in zip(
            _TITULOS_DAS_ETAPAS, fatos, strict=True
        )
    )
