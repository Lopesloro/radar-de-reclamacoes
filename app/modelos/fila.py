"""E se? Simula a fila de cada turno e estima o que muda nas reclamações de demora.

O que entra é o que o dono cadastrou: em cada turno, quantas pessoas atendem,
quantos clientes chegam e quantos minutos cada atendimento leva. Nada é
inventado aqui; se o dono não cadastrou turno, a tela pede o cadastro.

A conta, em três passos:

1. **A fila de cada turno**, por simulação de eventos discretos (SimPy). Os
   clientes chegam ao acaso ao longo das quatro horas do turno, cada atendimento
   leva um tempo ao acaso em volta da média, e a equipe atende por ordem de
   chegada. Repetido muitas vezes, com semente fixa: mesma entrada, mesmo número.
2. **Espera longa.** Conta quantos clientes por mês esperam mais de
   `ESPERA_LONGA` minutos, hoje e com a mudança.
3. **Reclamações.** Supõe que as reclamações de demora acompanham os clientes
   que esperaram muito: se a mudança corta pela metade quem espera muito, corta
   pela metade as reclamações de demora. Parte das reclamações de hoje (a média
   dos últimos meses fechados) e aplica a proporção. É uma suposição, e a tela a
   diz em uma frase.

A régua deste modelo é a fórmula clássica da fila (Erlang C): para um turno
estável e longo, a simulação tem de chegar perto dela. Um teste confere.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from functools import lru_cache

from app.contratos import Cenario, ResultadoSimulacao, Turno

HORAS_DO_TURNO = 4
SEMANAS_NO_MES = 4.33
ESPERA_LONGA = 15.0         # minutos
REPETICOES = 60
REAMOSTRAS = 400
SEMENTE = 2026
PERIODOS = ("manha", "tarde", "noite")
# Com menos que isto de clientes esperando muito por mês, não há de onde tirar a proporção.
MINIMO_DE_ESPERA_LONGA = 2.0


@dataclass(frozen=True)
class FilaDoTurno:
    espera_media: float                         # minutos, média das repetições
    longas_por_repeticao: tuple[float, ...]     # fração de clientes com espera longa, por repetição
    clientes: float


def _uma_rodada(clientes: float, minutos: float, equipe: int, semente: int) -> tuple[float, float]:
    """Uma simulação do turno. Devolve (espera média, fração com espera longa)."""
    import simpy

    sorteio = random.Random(semente)
    duracao = HORAS_DO_TURNO * 60
    taxa = clientes / duracao
    # Chegadas e atendimentos sorteados antes: o mesmo turno com equipe diferente
    # recebe exatamente os mesmos clientes, e a diferença é só da equipe.
    chegadas, agora = [], 0.0
    while taxa > 0:
        agora += sorteio.expovariate(taxa)
        if agora > duracao:
            break
        chegadas.append((agora, sorteio.expovariate(1 / minutos)))
    if not chegadas:
        return 0.0, 0.0

    ambiente = simpy.Environment()
    balcao = simpy.Resource(ambiente, capacity=max(1, equipe))
    esperas: list[float] = []

    def cliente(chegou: float, atendimento: float):
        with balcao.request() as vez:
            yield vez
            esperas.append(ambiente.now - chegou)
            yield ambiente.timeout(atendimento)

    def chegada(chegou: float, atendimento: float):
        yield ambiente.timeout(chegou)
        ambiente.process(cliente(chegou, atendimento))

    for chegou, atendimento in chegadas:
        ambiente.process(chegada(chegou, atendimento))
    ambiente.run()
    media = sum(esperas) / len(esperas)
    longas = sum(1 for e in esperas if e > ESPERA_LONGA) / len(esperas)
    return media, longas


@lru_cache(maxsize=512)
def simular_turno(clientes: float, minutos: float, equipe: int, semente: int,
                  repeticoes: int = REPETICOES) -> FilaDoTurno:
    if clientes <= 0:
        return FilaDoTurno(0.0, tuple(0.0 for _ in range(repeticoes)), 0.0)
    rodadas = [_uma_rodada(clientes, minutos, equipe, semente + r) for r in range(repeticoes)]
    return FilaDoTurno(
        espera_media=sum(m for m, _ in rodadas) / repeticoes,
        longas_por_repeticao=tuple(longa for _, longa in rodadas),
        clientes=clientes,
    )


def erlang_c(chegadas_por_minuto: float, minutos: float, equipe: int) -> float:
    """Espera média na fila (minutos) pela fórmula de Erlang C. Infinita se a fila não para de crescer."""
    carga = chegadas_por_minuto * minutos
    if equipe <= carga:
        return math.inf
    soma = sum(carga ** k / math.factorial(k) for k in range(equipe))
    topo = carga ** equipe / math.factorial(equipe) * equipe / (equipe - carga)
    prob_esperar = topo / (soma + topo)
    return prob_esperar * minutos / (equipe - carga)


def _semente(turno: Turno) -> int:
    return SEMENTE + turno.dia_semana * 100 + PERIODOS.index(turno.periodo) * 10_000


def _percentil(valores: list[float], fracao: float) -> float:
    ordenados = sorted(valores)
    posicao = fracao * (len(ordenados) - 1)
    baixo = int(posicao)
    alto = min(baixo + 1, len(ordenados) - 1)
    return ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * (posicao - baixo)


def simular(turnos: tuple[Turno, ...], cenario: Cenario, reclamacoes_hoje: float) -> ResultadoSimulacao:
    """Compara os turnos de hoje com os do cenário. `reclamacoes_hoje` é por mês, no assunto."""
    mudancas = {(t.dia_semana, t.periodo): t for t in cenario.mudancas}
    abertos = [t for t in turnos if t.equipe > 0 and t.clientes > 0]
    if not abertos:
        return ResultadoSimulacao(
            cenario=cenario, reclamacoes_atual=reclamacoes_hoje, reclamacoes_cenario=reclamacoes_hoje,
            minimo=reclamacoes_hoje, maximo=reclamacoes_hoje, espera_atual_min=0.0,
            espera_cenario_min=0.0, custo_extra_mes=0.0, custo_por_reclamacao_evitada=None,
            confiavel=False, motivo="Cadastre pelo menos um turno com equipe e clientes.",
        )

    longas_hoje = [0.0] * REPETICOES
    longas_com = [0.0] * REPETICOES
    espera_hoje = espera_com = clientes_total = custo = 0.0
    for turno in abertos:
        novo = mudancas.get((turno.dia_semana, turno.periodo), turno)
        hoje = simular_turno(turno.clientes, turno.minutos_atendimento, turno.equipe, _semente(turno))
        com = hoje if novo.equipe == turno.equipe else simular_turno(
            turno.clientes, turno.minutos_atendimento, novo.equipe, _semente(turno))
        por_mes = turno.clientes * SEMANAS_NO_MES
        for r in range(REPETICOES):
            longas_hoje[r] += hoje.longas_por_repeticao[r] * por_mes
            longas_com[r] += com.longas_por_repeticao[r] * por_mes
        espera_hoje += hoje.espera_media * turno.clientes
        espera_com += com.espera_media * turno.clientes
        clientes_total += turno.clientes
        custo += (novo.equipe - turno.equipe) * turno.custo_hora * HORAS_DO_TURNO * SEMANAS_NO_MES

    media_hoje = sum(longas_hoje) / REPETICOES
    confiavel = media_hoje >= MINIMO_DE_ESPERA_LONGA and reclamacoes_hoje > 0
    if confiavel:
        razao = sum(longas_com) / sum(longas_hoje)
        cenario_reclamacoes = reclamacoes_hoje * razao
        # A faixa: reamostra as repetições (bootstrap, semente fixa) e refaz a razão.
        # Razão por repetição não serve: muita repetição tem zero espera longa hoje.
        sorteio = random.Random(SEMENTE)
        razoes = []
        for _ in range(REAMOSTRAS):
            escolha = [sorteio.randrange(REPETICOES) for _ in range(REPETICOES)]
            hoje_r = sum(longas_hoje[i] for i in escolha)
            razoes.append(sum(longas_com[i] for i in escolha) / hoje_r if hoje_r > 0 else razao)
        minimo = reclamacoes_hoje * _percentil(razoes, 0.10)
        maximo = reclamacoes_hoje * _percentil(razoes, 0.90)
        motivo = None
    else:
        cenario_reclamacoes = minimo = maximo = reclamacoes_hoje
        motivo = ("Com os turnos de hoje quase ninguém espera mais de "
                  f"{int(ESPERA_LONGA)} minutos, então a conta não tem de onde tirar o efeito "
                  "nas reclamações." if reclamacoes_hoje > 0 else
                  "Ainda não há reclamações de demora nos últimos meses para servir de ponto de partida.")
    evitadas = reclamacoes_hoje - cenario_reclamacoes
    return ResultadoSimulacao(
        cenario=cenario,
        reclamacoes_atual=round(reclamacoes_hoje, 1),
        reclamacoes_cenario=round(cenario_reclamacoes, 1),
        minimo=round(min(minimo, maximo, cenario_reclamacoes), 1),
        maximo=round(max(minimo, maximo, cenario_reclamacoes), 1),
        espera_atual_min=round(espera_hoje / clientes_total, 1),
        espera_cenario_min=round(espera_com / clientes_total, 1),
        custo_extra_mes=round(custo, 2),
        custo_por_reclamacao_evitada=(round(custo / evitadas, 2)
                                      if confiavel and evitadas >= 0.5 and custo > 0 else None),
        confiavel=confiavel,
        motivo=motivo,
    )


def com_equipe(turno: Turno, equipe: int) -> Turno:
    return replace(turno, equipe=equipe)
