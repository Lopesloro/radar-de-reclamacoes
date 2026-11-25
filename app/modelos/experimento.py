"""Testes na prática: sortear os dias, selar o plano e comparar no fim.

O dono escolhe uma mudança (um atendente a mais no almoço, por exemplo) e um
período. O sistema sorteia em quais dias a mudança acontece e em quais não. Como
quem escolhe é o sorteio, os dois grupos de dias são parecidos em tudo, menos na
mudança, e a diferença de reclamações entre eles é efeito dela, não sorte nem
escolha dos dias mais fáceis.

Três cuidados:

1. **Sorteio equilibrado por dia da semana.** Sábado tem mais movimento que
   terça. O sorteio é feito dentro de cada dia da semana, então cada grupo
   recebe a sua parte de sábados.
2. **Plano selado.** Na criação, o plano (assunto, mudança, datas sorteadas)
   vira um SHA-256. Se alguém mexer nas datas depois de ver o resultado, o selo
   deixa de bater e a tela avisa.
3. **Intenção de tratar.** A comparação usa o que o sorteio mandou, não o que o
   dono marcou que fez. Quem marca escolhe, e a escolha estraga a comparação. A
   marcação mostra o quanto o sorteio foi seguido (a adesão).

O teste no fim: dadas as reclamações dos dois grupos somadas, quantas caíram
nos dias com a mudança, contra o que se esperaria pela quantidade de dias de
cada grupo (binomial condicional, bilateral).
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import secrets
from collections.abc import Sequence
from datetime import date, datetime, timedelta

from app.contratos import MarcacaoDia, PlanoExperimento, ResultadoExperimento

DIAS_MINIMO = 14
DIAS_MAXIMO = 56
DIAS_POR_MES = 30
NIVEL = 0.05
Z_FAIXA = 1.2816                    # faixa de 80%, a mesma das estimativas
# Abaixo disto, somando os dois grupos, o teste ainda não diz nada.
MINIMO_DE_RECLAMACOES = 6


def _numero(valor: float) -> str:
    """Número para frase: sem casa decimal acima de 10, com vírgula abaixo."""
    if valor >= 10:
        return str(round(valor))
    return f"{valor:.1f}".replace(".", ",").removesuffix(",0")


def sortear(inicio: date, dias: int, semente: int | None = None) -> tuple[tuple[date, ...], tuple[date, ...]]:
    """(dias com a mudança, dias sem), sorteados dentro de cada dia da semana."""
    sorteio = random.Random(secrets.randbits(64) if semente is None else semente)
    por_dia: dict[int, list[date]] = {}
    for i in range(dias):
        dia = inicio + timedelta(days=i)
        por_dia.setdefault(dia.weekday(), []).append(dia)
    com: list[date] = []
    sem: list[date] = []
    # Quem fica com o dia "a mais" de um dia da semana ímpar alterna, para os
    # grupos terminarem do mesmo tamanho (ou com um de diferença).
    vez_do_com = sorteio.random() < 0.5
    for dia_da_semana in sorted(por_dia):
        lista = por_dia[dia_da_semana]
        sorteio.shuffle(lista)
        metade = len(lista) // 2
        if len(lista) % 2:
            metade += 1 if vez_do_com else 0
            vez_do_com = not vez_do_com
        com += lista[:metade]
        sem += lista[metade:]
    return tuple(sorted(com)), tuple(sorted(sem))


def selar(categoria: str, acao: str, inicio: date, fim: date, dias_com: Sequence[date],
          selado_em: datetime) -> str:
    """SHA-256 do plano. Muda se qualquer data, o assunto ou a mudança mudarem."""
    plano = {
        "categoria": categoria, "acao": acao, "inicio": inicio.isoformat(), "fim": fim.isoformat(),
        "dias_com_acao": [d.isoformat() for d in sorted(dias_com)],
        "selado_em": selado_em.replace(microsecond=0).isoformat(),
    }
    return hashlib.sha256(json.dumps(plano, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def selo_confere(plano: PlanoExperimento) -> bool:
    return selar(plano.categoria, plano.acao, plano.inicio, plano.fim, plano.dias_com_acao,
                 plano.selado_em) == plano.selo


def menor_efeito(reclamacoes_por_dia: float, dias_com: int, dias_sem: int) -> float:
    """A menor mudança, em reclamações por mês, que o teste consegue perceber (95% e 80% de poder)."""
    base = max(reclamacoes_por_dia, 0.05)
    erro = math.sqrt(base / max(dias_com, 1) + base / max(dias_sem, 1))
    return round((1.96 + 0.84) * erro * DIAS_POR_MES, 1)


def marcacoes(plano: PlanoExperimento, marcadas: dict[date, bool]) -> tuple[MarcacaoDia, ...]:
    com = set(plano.dias_com_acao)
    dias = sorted(com | set(plano.dias_sem_acao))
    return tuple(MarcacaoDia(data=d, com_acao=d in com, seguiu=marcadas.get(d)) for d in dias)


def analisar(plano: PlanoExperimento, marcadas: dict[date, bool],
             datas_das_reclamacoes: Sequence[date], hoje: date) -> ResultadoExperimento | None:
    """O resultado até hoje. None se nenhum dia do teste terminou ainda."""
    from scipy import stats

    com = [d for d in plano.dias_com_acao if d < hoje]
    sem = [d for d in plano.dias_sem_acao if d < hoje]
    if not com or not sem:
        return None
    contagem: dict[date, int] = {}
    for d in datas_das_reclamacoes:
        contagem[d] = contagem.get(d, 0) + 1
    k_com = sum(contagem.get(d, 0) for d in com)
    k_sem = sum(contagem.get(d, 0) for d in sem)
    media_com, media_sem = k_com / len(com), k_sem / len(sem)
    efeito_dia = media_com - media_sem
    erro = math.sqrt((k_com + 0.5) / len(com) ** 2 + (k_sem + 0.5) / len(sem) ** 2)
    total = k_com + k_sem
    p = float(stats.binomtest(k_com, total, len(com) / (len(com) + len(sem))).pvalue) if total else 1.0

    marcados = [seguiu for d, seguiu in marcadas.items() if d < hoje]
    adesao = sum(1 for s in marcados if s) / len(marcados) if marcados else 0.0
    observados = len(com) + len(sem)
    terminou = hoje > plano.fim
    por_mes = _numero(abs(efeito_dia) * DIAS_POR_MES)

    dias_do_plano = len(plano.dias_com_acao) + len(plano.dias_sem_acao)
    if total < MINIMO_DE_RECLAMACOES or (not terminou and observados < dias_do_plano / 2):
        veredito = "ainda_nao_da_para_saber"
        frase = (f"Passaram {observados} dos {dias_do_plano} dias, "
                 f"com {total} reclamações no assunto. Ainda é cedo para dizer se a mudança funciona.")
    elif p < NIVEL and efeito_dia < 0:
        veredito = "funcionou"
        frase = (f"Nos dias com a mudança houve cerca de {por_mes} reclamações a menos "
                 "por mês, e a diferença é grande demais para ser sorte.")
    elif p < NIVEL and efeito_dia > 0:
        veredito = "nao_funcionou"
        frase = (f"Piorou: nos dias com a mudança houve cerca de {por_mes} reclamações a mais por mês, "
                 "e a diferença é grande demais para ser sorte.")
    elif terminou:
        veredito = "nao_funcionou"
        frase = ("Não deu para ver diferença entre os dias com e sem a mudança. Se ela ajuda, "
                 f"ajuda menos do que {plano.menor_efeito_detectavel:.0f} reclamações por mês.")
    else:
        veredito = "ainda_nao_da_para_saber"
        frase = (f"Até agora a diferença entre os dias com e sem a mudança pode ser sorte. "
                 f"O teste termina em {plano.fim.day}/{plano.fim.month}.")
    return ResultadoExperimento(
        plano_id=plano.id, dias_observados=observados, adesao=round(adesao, 3),
        media_com=round(media_com, 2), media_sem=round(media_sem, 2),
        efeito_mes=round(efeito_dia * DIAS_POR_MES, 1),
        efeito_min=round((efeito_dia - Z_FAIXA * erro) * DIAS_POR_MES, 1),
        efeito_max=round((efeito_dia + Z_FAIXA * erro) * DIAS_POR_MES, 1),
        veredito=veredito, frase=frase,
    )


def p_valor(plano: PlanoExperimento, datas_das_reclamacoes: Sequence[date], hoje: date) -> float | None:
    """O p-valor do teste, para o bloco técnico. None se ainda não há dias."""
    from scipy import stats

    com = [d for d in plano.dias_com_acao if d < hoje]
    sem = [d for d in plano.dias_sem_acao if d < hoje]
    if not com or not sem:
        return None
    k_com = sum(1 for d in datas_das_reclamacoes if d in set(com))
    k_sem = sum(1 for d in datas_das_reclamacoes if d in set(sem))
    if k_com + k_sem == 0:
        return 1.0
    return float(stats.binomtest(k_com, k_com + k_sem, len(com) / (len(com) + len(sem))).pvalue)
