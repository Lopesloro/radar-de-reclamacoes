"""As frases que respondem à pergunta de cada gráfico e de cada cartão.

O título de um gráfico é a conclusão dele, com números, montada a partir dos
dados. Nunca escrita à mão: se o número muda, a frase muda junto.
"""

from __future__ import annotations

from app.conteudo import ARTIGO, NOMES_CATEGORIA
from app.formatos import mes_longo


def nome(categoria: str) -> str:
    return NOMES_CATEGORIA[categoria]


def com_artigo(categoria: str) -> str:
    return f"{ARTIGO[categoria]} {nome(categoria)}"


def _mudanca(valor: int) -> str:
    if valor > 0:
        return f"{valor} a mais"
    if valor < 0:
        return f"{abs(valor)} a menos"
    return "o mesmo número"


def assuntos_do_mes(series, mes_ref) -> str:
    dominante = max(series, key=lambda s: s.ultimo)
    variacao = dominante.variacao
    comparacao = (
        f"{_mudanca(variacao)} que em {mes_longo(dominante.meses[-2][0])}"
        if variacao else f"o mesmo número de {mes_longo(dominante.meses[-2][0])}"
    )
    return (
        f"{com_artigo(dominante.categoria).capitalize()} é o que mais incomoda: "
        f"{dominante.ultimo} reclamações em {mes_longo(mes_ref)}, {comparacao}."
    )


def previsao(serie) -> str:
    corrente = serie.previsoes[0]
    diferenca = corrente.p50 - serie.ultimo
    mes_atual = mes_longo(corrente.mes)
    mes_antes = mes_longo(serie.meses[-1][0])
    if diferenca == 0:
        fim = f"o mesmo número de {mes_antes}"
    else:
        fim = f"{_mudanca(diferenca)} que em {mes_antes}"
    return (
        f"Em {mes_atual} devem chegar cerca de {corrente.p50} reclamações de "
        f"{nome(serie.categoria)}, {fim}."
    )


def cartao(resumo) -> str:
    para = resumo.vai_crescer_para
    if resumo.estado == "normal":
        return (
            f"Nenhum assunto deve crescer em {mes_longo(para.mes)}. "
            f"{com_artigo(resumo.mais_reclamado).capitalize()} continua sendo o que mais aparece."
        )
    return (
        f"{com_artigo(resumo.vai_crescer).capitalize()} deve passar de {resumo.vai_crescer_de} "
        f"para cerca de {para.p50} reclamações em {mes_longo(para.mes)}."
    )


def alerta(item) -> str:
    return (
        f"{com_artigo(item.categoria).capitalize()} teve {item.atual} reclamações no último mês "
        f"fechado. Em {mes_longo(item.previsto.mes)} devem ser cerca de {item.previsto.p50}, "
        f"entre {item.previsto.p10} e {item.previsto.p90}."
    )


def hipotese_grafico(h) -> str:
    return (
        f"Antes: {_numero(h.antes_semana)} reclamações por semana. "
        f"Depois: {_numero(h.depois_semana)} por semana."
    )


def simulacao(resultado) -> str:
    if not resultado.cenario.mudancas:
        return "Mude a equipe de algum turno para ver o que deve acontecer."
    evitadas = round(resultado.reclamacoes_atual - resultado.reclamacoes_cenario)
    assunto = nome(resultado.cenario.categoria)
    if evitadas >= 1:
        return (
            f"Com essa mudança, as reclamações de {assunto} devem cair de "
            f"{round(resultado.reclamacoes_atual)} para cerca de "
            f"{round(resultado.reclamacoes_cenario)} por mês."
        )
    if evitadas <= -1:
        return (
            f"Com essa mudança, as reclamações de {assunto} devem subir de "
            f"{round(resultado.reclamacoes_atual)} para cerca de "
            f"{round(resultado.reclamacoes_cenario)} por mês."
        )
    return f"Essa mudança quase não mexe nas reclamações de {assunto}."


def _numero(valor: float) -> str:
    if float(valor).is_integer():
        return str(int(valor))
    return f"{valor:.1f}".replace(".", ",")
