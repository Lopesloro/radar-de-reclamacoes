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
    if not serie.previsoes:
        fechados = len(serie.meses)
        faltam = max(0, 6 - fechados)
        return (
            f"Ainda não dá para estimar {com_artigo(serie.categoria)}: a estimativa começa "
            f"com seis meses fechados, e este negócio tem {fechados}. "
            f"{'Falta' if faltam == 1 else 'Faltam'} {faltam}."
        )
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


def ritmo_do_mes(serie) -> str:
    """O que o mês corrente já diz, antes de acabar.

    A estimativa fala do mês fechado, mas o dono abre a tela no dia 10. Se já
    chegaram 22 reclamações num mês cuja estimativa inteira é 19, isso é
    informação, e o sistema estava jogando fora: ele comparava a estimativa com o
    mês ANTERIOR e dizia "variação normal" com o mês corrente já estourado.

    Duas leituras, nesta ordem:

    1. o que já chegou passou do máximo esperado para o mês inteiro;
    2. com uma parte do mês passada, o que já chegou está perto do máximo
       esperado para o mês inteiro.

    A segunda só vale depois do primeiro terço do mês.

    **O que esta função não faz, de propósito: extrapolar.** A tentação é dividir
    o que chegou pela fração do mês e anunciar o total. Com 22 reclamações num
    terço do mês isso dá 67, um número que o sistema não consegue defender —
    avaliação não chega em ritmo constante, e 67 na tela é alarme falso com cara
    de medida. A frase diz o fato (quanto chegou, quanto do mês passou, qual era
    o máximo esperado) e deixa a conta com quem conhece o negócio.
    """
    if not serie.previsoes:
        return ""
    corrente = serie.previsoes[0]
    ja_chegou = serie.parcial[1]
    if ja_chegou > corrente.p90:
        return (
            f"Atenção: já chegaram {ja_chegou} neste mês, e o máximo esperado para o mês "
            f"inteiro era {corrente.p90}. O mês já passou do esperado."
        )
    fracao = serie.parcial_fracao
    if fracao >= 0.33 and ja_chegou >= corrente.p50:
        passou_do_mes = round(fracao * 100)
        return (
            f"Já chegaram {ja_chegou} com {passou_do_mes}% do mês passado, e o esperado para "
            f"o mês inteiro era {corrente.p50}. Vale olhar o que mudou nos últimos dias."
        )
    return ""


def leitura_da_faixa(serie) -> str:
    """O que a faixa quer dizer, em uma frase, sem termo técnico.

    É a frase que explica por que a faixa existe: o número do meio sozinho não
    separa subida de verdade de sobe-e-desce, e o dono decide com a faixa.
    """
    if not serie.previsoes:
        return ""
    corrente = serie.previsoes[0]
    largura = corrente.p90 - corrente.p10
    aviso_do_ritmo = ritmo_do_mes(serie)
    if aviso_do_ritmo:
        return aviso_do_ritmo
    if corrente.p10 > serie.ultimo:
        return (
            f"Mesmo no cenário mais fraco ({corrente.p10}), o mês fecha acima dos "
            f"{serie.ultimo} do mês passado. É por isso que o sistema avisa."
        )
    if corrente.p90 <= serie.ultimo:
        return (
            f"Mesmo no cenário mais forte ({corrente.p90}), o mês fecha igual ou abaixo dos "
            f"{serie.ultimo} do mês passado."
        )
    return (
        f"O mês passado fechou em {serie.ultimo}, e isso cabe dentro da faixa de "
        f"{corrente.p10} a {corrente.p90}. Ou seja: pode subir, pode cair, e por enquanto "
        f"a diferença caberia no sobe-e-desce normal de um mês para o outro "
        f"(a faixa tem {largura} de largura)."
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
