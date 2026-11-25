"""Leituras do banco para "Por quê?", "E se?" e "Testes".

Mesma regra de `consultas.py`: toda função recebe `empresa_id`, que vem da
sessão, e filtra por ele. Um negócio de outra empresa devolve vazio, nunca erro
com dado dentro.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.banco import modelo
from app.contratos import EventoDiario, PlanoExperimento, Turno
from app.modelos.causas import AvaliacaoClassificada


def avaliacoes_classificadas(sessao: Session, empresa_id: str,
                             comercio_id: str) -> list[AvaliacaoClassificada]:
    """Todas as avaliações do negócio, com o assunto da versão do modelo que está no ar."""
    ativa = (select(modelo.VersaoModelo.id)
             .where(modelo.VersaoModelo.empresa_id == empresa_id,
                    modelo.VersaoModelo.tipo == "classificacao",
                    modelo.VersaoModelo.ativa.is_(True)))
    linhas = sessao.execute(
        select(modelo.Avaliacao.data, modelo.Classificacao.categoria_id, modelo.Avaliacao.texto)
        .outerjoin(modelo.Classificacao, and_(
            modelo.Classificacao.avaliacao_id == modelo.Avaliacao.id,
            modelo.Classificacao.versao_modelo_id.in_(ativa)))
        .where(modelo.Avaliacao.empresa_id == empresa_id,
               modelo.Avaliacao.comercio_id == comercio_id)
    ).all()
    return [AvaliacaoClassificada(data=d, categoria=c, texto=t) for d, c, t in linhas]


def eventos(sessao: Session, empresa_id: str, comercio_id: str) -> tuple[EventoDiario, ...]:
    linhas = sessao.scalars(
        select(modelo.EventoDiario)
        .where(modelo.EventoDiario.empresa_id == empresa_id,
               modelo.EventoDiario.comercio_id == comercio_id)
        .order_by(modelo.EventoDiario.data.desc())
    ).all()
    return tuple(EventoDiario(e.id, e.empresa_id, e.data, e.tipo, e.descricao) for e in linhas)


def turnos(sessao: Session, empresa_id: str, comercio_id: str) -> tuple[Turno, ...]:
    ordem = {"manha": 0, "tarde": 1, "noite": 2}
    linhas = sessao.scalars(
        select(modelo.Turno)
        .where(modelo.Turno.empresa_id == empresa_id, modelo.Turno.comercio_id == comercio_id)
    ).all()
    return tuple(sorted(
        (Turno(t.dia_semana, t.periodo, t.equipe, t.clientes, t.minutos_atendimento, t.custo_hora)
         for t in linhas),
        key=lambda t: (t.dia_semana, ordem.get(t.periodo, 9)),
    ))


def reclamacoes_por_mes(sessao: Session, empresa_id: str, comercio_id: str, categoria: str,
                        meses: int = 3) -> float:
    """Média das reclamações do assunto nos últimos meses fechados. Zero se não há série."""
    linhas = sessao.scalars(
        select(modelo.SerieMensal.quantidade)
        .where(modelo.SerieMensal.empresa_id == empresa_id,
               modelo.SerieMensal.comercio_id == comercio_id,
               modelo.SerieMensal.categoria_id == categoria,
               modelo.SerieMensal.fechado.is_(True))
        .order_by(modelo.SerieMensal.mes.desc()).limit(meses)
    ).all()
    return sum(linhas) / len(linhas) if linhas else 0.0


def _plano(linha: modelo.Experimento, hoje: date) -> PlanoExperimento:
    com = tuple(sorted(date.fromisoformat(d) for d in linha.dias_com_acao.split(",") if d))
    todos = [linha.inicio + timedelta(days=i) for i in range((linha.fim - linha.inicio).days + 1)]
    sem = tuple(d for d in todos if d not in set(com))
    estado = linha.estado
    if estado == "em_andamento" and hoje > linha.fim:
        estado = "encerrado"
    return PlanoExperimento(
        id=linha.id, empresa_id=linha.empresa_id, categoria=linha.categoria_id, acao=linha.acao,
        inicio=linha.inicio, fim=linha.fim, dias_com_acao=com, dias_sem_acao=sem,
        menor_efeito_detectavel=linha.menor_efeito, selo=linha.selo, selado_em=linha.selado_em,
        estado=estado,
    )


def planos(sessao: Session, empresa_id: str, hoje: date) -> tuple[tuple[PlanoExperimento, str], ...]:
    """Os testes da empresa, com o negócio de cada um. Mais recente primeiro."""
    linhas = sessao.scalars(
        select(modelo.Experimento).where(modelo.Experimento.empresa_id == empresa_id)
        .order_by(modelo.Experimento.inicio.desc())
    ).all()
    return tuple((_plano(linha, hoje), linha.comercio_id) for linha in linhas)


def plano(sessao: Session, empresa_id: str, plano_id: str,
          hoje: date) -> tuple[PlanoExperimento, str] | None:
    linha = sessao.scalar(
        select(modelo.Experimento).where(modelo.Experimento.id == plano_id,
                                         modelo.Experimento.empresa_id == empresa_id)
    )
    return None if linha is None else (_plano(linha, hoje), linha.comercio_id)


def marcadas(sessao: Session, empresa_id: str, plano_id: str) -> dict[date, bool]:
    linhas = sessao.execute(
        select(modelo.MarcacaoDia.data, modelo.MarcacaoDia.seguiu)
        .where(modelo.MarcacaoDia.empresa_id == empresa_id,
               modelo.MarcacaoDia.experimento_id == plano_id)
    ).all()
    return {d: s for d, s in linhas}


def datas_das_reclamacoes(sessao: Session, empresa_id: str, comercio_id: str, categoria: str,
                          inicio: date, fim: date) -> list[date]:
    return [a.data for a in avaliacoes_classificadas(sessao, empresa_id, comercio_id)
            if a.categoria == categoria and inicio <= a.data <= fim]
