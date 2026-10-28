"""Estima quantas reclamações de um assunto chegam no mês seguinte.

Devolve o mais provável e a faixa de mínimo e máximo (p10, p50, p90), que é o
que `app/contratos.PrevisaoMes` combinou com a tela.

A conferência é com **origem móvel**: treina até o mês k, prevê o mês k+1, anda
um mês e repete. Nunca com divisão aleatória dos meses — sortear mês de teste
deixa o modelo ver o futuro e produz um número bonito e falso.

A medida é o erro médio absoluto e a cobertura da faixa, sempre ao lado da
régua: repetir o número do mês anterior.
"""

from __future__ import annotations

import math
from datetime import date
from statistics import fmean, stdev
from typing import Sequence

from app.contratos import AcuraciaPrevisao, PrevisaoMes

Historico = Sequence[tuple[date, int]]

# Quatro meses para medir a tendência e dois de sobra para medir o próprio erro.
MINIMO_TREINO = 6
MESES_DA_TENDENCIA = 4
# A faixa é de 80%: 1,2816 desvio para cada lado de uma normal.
DESVIOS_DA_FAIXA = 1.2816
# Uma subida só vira tendência se passar de três desvios do ruído da própria série.
# Três desvios é a régua de sempre para "isto não é ruído", e medir o desvio na
# série (em vez de fixar um número) é o que faz a regra valer para um negócio
# grande e para um pequeno. Com 1,0 fixo, a curva do ano era projetada como se
# fosse alta permanente e a previsão ficava pior que repetir o mês anterior.
DESVIOS_PARA_SER_TENDENCIA = 3.0
# Nenhuma faixa nasce menor que isto, mesmo numa série muito quieta.
DESVIO_MINIMO = 1.0


def _mes_adiante(ultimo: date, passos: int) -> date:
    total = ultimo.year * 12 + (ultimo.month - 1) + passos
    return date(total // 12, total % 12 + 1, 1)


def _ruido(valores: Sequence[int]) -> float:
    """O tamanho típico do sobe-e-desce de um mês para o outro nesta série."""
    diferencas = [valores[i] - valores[i - 1] for i in range(1, len(valores))]
    return stdev(diferencas) if len(diferencas) > 1 else float(DESVIO_MINIMO)


def _tendencia(valores: Sequence[int]) -> float:
    """Quanto o assunto sobe por mês. Zero quando o movimento cabe no ruído."""
    recorte = valores[-MESES_DA_TENDENCIA:]
    movimento = recorte[-1] - recorte[0]
    if abs(movimento) <= DESVIOS_PARA_SER_TENDENCIA * _ruido(valores):
        return 0.0
    return movimento / (len(recorte) - 1)


def _desvio(valores: Sequence[int]) -> float:
    """O erro que o próprio modelo cometeu dentro do histórico, um mês à frente."""
    erros = [
        valores[i] - (valores[i - 1] + _tendencia(valores[:i]))
        for i in range(MESES_DA_TENDENCIA, len(valores))
    ]
    if len(erros) < 2:
        return max(DESVIO_MINIMO, 0.05 * valores[-1])
    return max(DESVIO_MINIMO, stdev(erros))


def prever(historico: Historico, passos: int = 1) -> PrevisaoMes:
    """A estimativa de `passos` meses à frente do último mês do histórico."""
    if len(historico) < MINIMO_TREINO:
        raise ValueError(
            f"a previsão pede no mínimo {MINIMO_TREINO} meses fechados; "
            f"chegaram {len(historico)}"
        )
    valores = [quantidade for _, quantidade in historico]
    centro = max(0.0, valores[-1] + _tendencia(valores) * passos)
    largura = DESVIOS_DA_FAIXA * _desvio(valores) * math.sqrt(passos)
    return PrevisaoMes(
        mes=_mes_adiante(historico[-1][0], passos),
        p10=max(0, round(centro - largura)),
        p50=round(centro),
        p90=round(centro + largura),
    )


def regua(historico: Historico) -> int:
    """A régua: o mês que vem é igual ao mês passado."""
    return historico[-1][1]


def validar(series: Sequence[tuple[str, Historico]],
            minimo_treino: int = MINIMO_TREINO) -> AcuraciaPrevisao:
    """Conferência com origem móvel em todas as séries.

    `pontos` traz só a primeira série, que é a que a tela desenha; as medidas
    valem para todas.
    """
    erros, erros_regua, cobertos = [], [], []
    pontos: list[tuple[date, int, int]] = []

    for posicao, (_, historico) in enumerate(series):
        for i in range(minimo_treino, len(historico)):
            treino, (mes, realizado) = historico[:i], historico[i]
            faixa = prever(treino)
            erros.append(abs(faixa.p50 - realizado))
            erros_regua.append(abs(regua(treino) - realizado))
            cobertos.append(faixa.p10 <= realizado <= faixa.p90)
            if posicao == 0:
                pontos.append((mes, faixa.p50, realizado))

    if not erros:
        raise ValueError(f"nenhuma série tem mais de {minimo_treino} meses fechados")

    return AcuraciaPrevisao(
        erro_medio=round(fmean(erros), 2),
        erro_medio_regua=round(fmean(erros_regua), 2),
        cobertura=round(fmean(cobertos), 2),
        janelas=len(erros),
        exemplo=series[0][0],
        pontos=tuple(pontos),
    )
