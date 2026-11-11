"""Estima quantas reclamações de um assunto chegam nos próximos meses.

Devolve o mais provável e a faixa de mínimo e máximo (p10, p50, p90), que é o
que `app/contratos.PrevisaoMes` combinou com a tela.

A conferência é com **origem móvel**: treina até o mês k, prevê o mês k+1, anda
um mês e repete. Nunca com divisão aleatória dos meses — sortear mês de teste
deixa o modelo ver o futuro e produz um número bonito e falso.

## O resultado honesto da medição, que muda o que a tela promete

Seis métodos foram medidos em seis formas de série (plana, subindo, descendo,
degrau, sazonal, com um pico), em 144 séries, por origem móvel. O erro médio
de todos ficou entre 2,6 e 2,8 reclamações por mês. A régua — responder "o mês
que vem é igual ao mês passado" — ficou em 2,65. Nenhum método ganhou dela de
forma que importe, inclusive um seletor automático que escolhia o método
conferindo os métodos dentro do próprio treino (2,62).

Isso não é defeito do código: numa contagem mensal pequena, o sobe-e-desce
aleatório é maior que a tendência, e nenhum método extrai sinal que não existe.
A conclusão certa não é inventar um método mais complicado para o número ficar
bonito; é parar de prometer o que o número central não entrega e entregar o que
de fato ajuda o dono a decidir:

1. **A faixa.** "Deve fechar entre 20 e 26" é informação que a régua não dá, e
   é o que separa "subiu de verdade" de "subiu por acaso". A largura sai dos
   erros que o próprio método cometeu um mês à frente no histórico, com a
   correção da t de Student para o desvio ter sido estimado de poucos erros. A
   cobertura medida nas 2.592 janelas saiu de **0,73 para 0,82** com essa
   correção, numa faixa que promete 0,80. Sem ela, a tela prometia 80% e
   entregava 73%.
2. **O aviso.** O que o dono faz com a tela é reagir a "este assunto deve
   crescer", e é aí que o sistema ganha da régua de verdade. Medido nas mesmas
   janelas, contando como acerto o mês que de fato subiu duas reclamações ou
   mais:

   | Aviso                               | Acerto | Pega das altas | Quantos avisos |
   |-------------------------------------|--------|----------------|----------------|
   | "Vai piorar" (mínimo acima do mês)  | 0,59   | 0,05           | 70             |
   | "Fique de olho" (mais provável sobe)| 0,43   | 0,25           | 472            |
   | Régua: "o último mês subiu"         | 0,22   | 0,30           | 1.133          |

   Lido em voz alta: a régua grita 1.133 vezes e acerta uma em cinco; o "fique
   de olho" fala 472 vezes e acerta duas em cinco, pegando quase a mesma
   proporção de altas. É por isso que o aviso tem dois níveis e não um.

## O que este arquivo não faz, de propósito

Não tem termo de mês do ano. Na forma de série sazonal o método perde da régua
(erro 3,44 contra 2,84), e isso está medido. Um termo sazonal honesto pede 24
meses de histórico para ser estimado e conferido; nenhum cliente tem isso hoje,
e estimá-lo com 12 meses seria ajustar ruído e piorar o resto. Entra quando
houver dado para medi-lo, com a mesma conferência por origem móvel.

A tendência usa a mediana das inclinações entre todos os pares dos últimos seis
meses (Theil-Sen), amortecida, em vez da diferença entre o primeiro e o último
mês da janela: um único mês fora de série deixava de ser ruído e virava
tendência permanente. Isso aparece nos números: na série com um pico, o erro
caiu de 3,56 (régua) para 3,41.
"""

from __future__ import annotations

import math
import statistics as _st
from collections.abc import Sequence
from datetime import date
from statistics import fmean, stdev

from app.contratos import AcuraciaPrevisao, PrevisaoMes

Historico = Sequence[tuple[date, int]]

# Quatro meses para medir a tendência e dois de sobra para medir o próprio erro.
MINIMO_TREINO = 6
# Janela da tendência. Seis meses: o suficiente para a mediana das inclinações
# ter pares, e curto o bastante para não arrastar um ano velho.
MESES_DA_TENDENCIA = 6
# Quantos meses entram no ponto de partida. Dois, e não um: partir do último mês
# deixa a estimativa refém de um mês atípico (o erro na série plana caiu de 2,23
# para 2,04 com dois).
MESES_DO_CENTRO = 2
# A tendência medida é cortada pela metade e um pouco: alta de reclamação costuma
# voltar, e projetar a inclinação inteira exagera o mês seguinte.
AMORTECIMENTO = 0.6
# Uma inclinação só vira tendência se o movimento dela na janela passar do ruído
# típico da própria série.
RUIDO_PARA_SER_TENDENCIA = 1.0
# A faixa é de 80%. Com erro suficiente medido, usa-se o percentil; sem, a
# aproximação normal (1,2816 desvios para cada lado).
FAIXA = 0.80
DESVIOS_DA_FAIXA = 1.2816
ERROS_PARA_PERCENTIL = 8
# Nenhuma faixa nasce menor que isto, mesmo numa série muito quieta.
DESVIO_MINIMO = 1.0


def _mes_adiante(ultimo: date, passos: int) -> date:
    total = ultimo.year * 12 + (ultimo.month - 1) + passos
    return date(total // 12, total % 12 + 1, 1)


def _ruido(valores: Sequence[int]) -> float:
    """O tamanho típico do sobe-e-desce de um mês para o outro nesta série."""
    diferencas = [valores[i] - valores[i - 1] for i in range(1, len(valores))]
    return stdev(diferencas) if len(diferencas) > 1 else float(DESVIO_MINIMO)


def _inclinacao_robusta(valores: Sequence[int]) -> float:
    """Mediana das inclinações entre todos os pares (Theil-Sen).

    Com a diferença entre o primeiro e o último mês da janela, um mês fora de
    série virava tendência. A mediana dos pares ignora o ponto solto.
    """
    pares = [
        (valores[j] - valores[i]) / (j - i)
        for i in range(len(valores))
        for j in range(i + 1, len(valores))
    ]
    return _st.median(pares) if pares else 0.0


def _tendencia(valores: Sequence[int]) -> float:
    """Quanto o assunto sobe por mês. Zero quando o movimento cabe no ruído."""
    recorte = valores[-MESES_DA_TENDENCIA:]
    if len(recorte) < 3:
        return 0.0
    inclinacao = _inclinacao_robusta(recorte)
    movimento = abs(inclinacao) * (len(recorte) - 1)
    if movimento <= RUIDO_PARA_SER_TENDENCIA * _ruido(valores):
        return 0.0
    return inclinacao * AMORTECIMENTO


def _centro(valores: Sequence[int]) -> float:
    return fmean(valores[-MESES_DO_CENTRO:])


def _ponto(valores: Sequence[int], passos: int = 1) -> float:
    return max(0.0, _centro(valores) + _tendencia(valores) * passos)


def _erros_internos(valores: Sequence[int]) -> list[float]:
    """O erro, com sinal, que o próprio método cometeu um mês à frente no histórico."""
    return [
        valores[i] - _ponto(valores[:i])
        for i in range(MESES_DA_TENDENCIA, len(valores))
    ]


def _fator_de_poucos_erros(quantos: int) -> float:
    """Quantos desvios abrem 80% quando o desvio foi estimado de `quantos` erros.

    Com o desvio verdadeiro conhecido seriam 1,2816 desvios (normal). Mas aqui o
    desvio é estimado de oito a doze erros, e um desvio estimado de poucos
    pontos sai pequeno com mais frequência do que grande. A distribuição t de
    Student é exatamente a correção para isso, e é a diferença entre prometer
    uma faixa de 80% e entregar uma de 73% — foi o que a medição por origem
    móvel mostrou antes desta correção.
    """
    if quantos < 2:
        return DESVIOS_DA_FAIXA
    from scipy import stats

    return float(stats.t.ppf(1 - (1 - FAIXA) / 2, df=quantos - 1))


def _faixa_do_erro(valores: Sequence[int], passos: int) -> tuple[float, float]:
    """Quanto tirar e quanto somar ao centro, para a faixa de 80%.

    Os erros usados aqui são de verdade de um mês à frente: cada um foi calculado
    prevendo o mês i com os dados até i-1. Não são resíduos de ajuste.

    A largura é a maior entre duas contas, e ficar com a maior é de propósito —
    faixa estreita demais é promessa quebrada, faixa larga demais é só menos
    informação:

    - o desvio dos erros vezes o fator da t de Student, corrigido pela incerteza
      da própria média (o `1 + 1/n`);
    - os percentis 10 e 90 dos erros, que pegam a assimetria quando a série erra
      mais para um lado.
    """
    erros = _erros_internos(valores)
    escala = math.sqrt(passos)
    if len(erros) < 2:
        largura = DESVIOS_DA_FAIXA * max(DESVIO_MINIMO, 0.05 * valores[-1])
        return (largura * escala, largura * escala)

    desvio = max(DESVIO_MINIMO, stdev(erros))
    pela_t = _fator_de_poucos_erros(len(erros)) * desvio * math.sqrt(1 + 1 / len(erros))
    abaixo = acima = pela_t

    if len(erros) >= ERROS_PARA_PERCENTIL:
        ordenados = sorted(erros)
        abaixo = max(abaixo, -_percentil(ordenados, (1 - FAIXA) / 2))
        acima = max(acima, _percentil(ordenados, 1 - (1 - FAIXA) / 2))

    return (max(DESVIO_MINIMO, abaixo) * escala, max(DESVIO_MINIMO, acima) * escala)


def _percentil(ordenados: Sequence[float], fracao: float) -> float:
    """Percentil por interpolação linear. `statistics.quantiles` precisa de n>=2
    e de um número de cortes fixo; aqui o n varia a cada série."""
    if not ordenados:
        return 0.0
    posicao = fracao * (len(ordenados) - 1)
    baixo = int(math.floor(posicao))
    alto = min(baixo + 1, len(ordenados) - 1)
    peso = posicao - baixo
    return ordenados[baixo] * (1 - peso) + ordenados[alto] * peso


def prever(historico: Historico, passos: int = 1) -> PrevisaoMes:
    """A estimativa de `passos` meses à frente do último mês do histórico."""
    if len(historico) < MINIMO_TREINO:
        raise ValueError(
            f"a previsão pede no mínimo {MINIMO_TREINO} meses fechados; "
            f"chegaram {len(historico)}"
        )
    valores = [quantidade for _, quantidade in historico]
    centro = _ponto(valores, passos)
    abaixo, acima = _faixa_do_erro(valores, passos)
    return PrevisaoMes(
        mes=_mes_adiante(historico[-1][0], passos),
        p10=max(0, round(centro - abaixo)),
        p50=round(centro),
        p90=round(centro + acima),
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


# ------------------------------------------------------------ a qualidade do aviso

CRESCIMENTO_QUE_IMPORTA = 2
"""Quantas reclamações a mais num mês já valem a atenção do dono. Dois: abaixo
disso, numa contagem pequena, é sobe-e-desce normal."""


# O resultado do estudo que mediu o aviso em 2.592 janelas de origem móvel, em
# seis formas de série. Fica aqui, com o código que o produziu, para a tela "Dá
# para confiar?" poder mostrar o número de referência quando o cliente ainda não
# tem histórico próprio. Reproduzir: `pytest tests/test_modelos.py -k aviso`.
MEDIDA_DE_REFERENCIA = {
    "janelas": 2592,
    "erro_medio": 2.66,
    "erro_medio_regua": 2.65,
    "cobertura": 0.82,
    "acerto_vai_piorar": 0.59,
    "acerto_fique_de_olho": 0.43,
    "cobertura_fique_de_olho": 0.25,
    "acerto_regua": 0.22,
    "cobertura_regua": 0.30,
}


def avaliar_avisos(series: Sequence[tuple[str, Historico]],
                   minimo_treino: int = MINIMO_TREINO) -> dict[str, float]:
    """Acerto e cobertura do aviso, contra a régua de alarme.

    É a medida que diz se a tela está pedindo atenção na hora certa, e é
    diferente do erro médio: uma estimativa com erro igual ao da régua pode
    avisar muito melhor, porque o aviso usa a faixa e não só o número central.

    - `acerto`: das vezes que o sistema avisou, quantas o assunto de fato subiu.
    - `cobertura`: das vezes que o assunto subiu, quantas o sistema avisou.
    - `acerto_regua` / `cobertura_regua`: o mesmo para "avise sempre que o
      último mês subiu em relação ao anterior".
    """
    forte_certo = forte = 0
    atento_certo = atento = 0
    regua_certo = regua_avisou = 0
    subiu = 0

    for _, historico in series:
        for i in range(minimo_treino, len(historico)):
            treino, (_, realizado) = historico[:i], historico[i]
            ultimo = treino[-1][1]
            faixa = prever(treino)
            de_fato_subiu = realizado - ultimo >= CRESCIMENTO_QUE_IMPORTA
            subiu += de_fato_subiu

            # Dois níveis, que é o que a tela mostra. "Vai piorar" só quando o
            # mínimo esperado já passa do mês fechado: é o aviso que interrompe o
            # dono, e por isso precisa de acerto alto. "Fique de olho" aceita o
            # mais provável acima do mês fechado: pega mais altas, erra mais, e
            # aparece como lista, não como alarme.
            aviso_forte = faixa.p10 > ultimo
            aviso_atento = aviso_forte or (faixa.p50 - ultimo) >= CRESCIMENTO_QUE_IMPORTA
            alarme_regua = len(treino) >= 2 and ultimo > treino[-2][1]

            forte += aviso_forte
            atento += aviso_atento
            regua_avisou += alarme_regua
            forte_certo += aviso_forte and de_fato_subiu
            atento_certo += aviso_atento and de_fato_subiu
            regua_certo += alarme_regua and de_fato_subiu

    def divide(a: int, b: int) -> float:
        return round(a / b, 3) if b else 0.0

    return {
        "acerto": divide(forte_certo, forte),
        "cobertura": divide(forte_certo, subiu),
        "avisos": float(forte),
        "acerto_atento": divide(atento_certo, atento),
        "cobertura_atento": divide(atento_certo, subiu),
        "avisos_atento": float(atento),
        "acerto_regua": divide(regua_certo, regua_avisou),
        "cobertura_regua": divide(regua_certo, subiu),
        "avisos_regua": float(regua_avisou),
        "oportunidades": float(subiu),
    }
