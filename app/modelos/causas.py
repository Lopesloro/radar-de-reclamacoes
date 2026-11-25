"""Por quê? As possíveis causas de um assunto, cada uma testada com estatística.

De onde saem as possíveis causas:

1. **O diário do negócio.** Cada mudança que o dono anotou (entrou alguém na
   equipe, subiu o preço, mudou o horário) vira uma hipótese: as reclamações do
   assunto subiram depois daquela data? Compara oito semanas antes com até oito
   semanas depois.
2. **Os dias da semana.** As reclamações do assunto se concentram de sexta a
   domingo mais do que as avaliações em geral? Não depende do diário, então
   sempre há pelo menos uma hipótese para testar.

Os testes:

- Antes e depois: teste exato da razão de duas taxas de Poisson (binomial
  condicional). Dadas as reclamações das duas janelas somadas, quantas caíram na
  janela de depois, contra o que se esperaria pelo tamanho de cada janela.
- Fim de semana: teste exato de Fisher, comparando o assunto com o resto das
  avaliações. Usar o resto como comparação desconta o movimento: um bar recebe
  mais avaliação no sábado de todo jeito.
- Muitas hipóteses ao mesmo tempo aumentam a chance de uma dar "certo" por
  sorte. A correção de Benjamini-Hochberg (q-valor) cuida disso.

Nada aqui vem de modelo de linguagem: a IA não participa. A frase de cada
hipótese é montada a partir dos números.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.contratos import EventoDiario, Hipotese, Investigacao, PassoInvestigacao

JANELA = timedelta(weeks=8)
# Depois da mudança, quantos dias no mínimo antes de testar: com menos, a janela
# de depois é curta demais e qualquer resultado é sorte.
DIAS_MINIMOS_DEPOIS = 14
# Abaixo disto, no assunto inteiro, o sistema diz que ainda não dá e não testa nada.
MINIMO_DO_ASSUNTO = 8
# Abaixo disto, perto de uma data, aquela hipótese fica "ainda não dá para dizer".
MINIMO_NA_JANELA = 4
JANELA_DIAS_DA_SEMANA = timedelta(weeks=26)
FIM_DE_SEMANA = (4, 5, 6)           # sexta, sábado e domingo
Q_PROVAVEL = 0.05
P_DESCARTA = 0.5
Z_FAIXA = 1.2816                    # faixa de 80%, a mesma das estimativas


@dataclass(frozen=True)
class AvaliacaoClassificada:
    """O mínimo que a investigação precisa de cada avaliação."""

    data: date
    categoria: str | None
    texto: str | None


def benjamini_hochberg(p_valores: Sequence[float]) -> list[float]:
    """q-valores na mesma ordem dos p-valores."""
    n = len(p_valores)
    if n == 0:
        return []
    ordem = sorted(range(n), key=lambda i: p_valores[i])
    q = [0.0] * n
    menor = 1.0
    for posicao in range(n - 1, -1, -1):
        i = ordem[posicao]
        menor = min(menor, p_valores[i] * n / (posicao + 1))
        q[i] = min(1.0, menor)
    return q


def _p_taxa_subiu(k_antes: int, t_antes: float, k_depois: int, t_depois: float) -> float:
    """P-valor de "a taxa de depois é maior que a de antes" (binomial condicional)."""
    from scipy import stats

    total = k_antes + k_depois
    if total == 0:
        return 1.0
    esperado = t_depois / (t_antes + t_depois)
    return float(stats.binomtest(k_depois, total, esperado, alternative="greater").pvalue)


def _faixa_da_diferenca(k_a: int, t_a: float, k_b: int, t_b: float) -> tuple[float, float, float]:
    """Diferença de taxas (b menos a) e a faixa de 80%, pela aproximação normal."""
    diferenca = k_b / t_b - k_a / t_a
    # Meio ponto evita faixa de largura zero quando uma janela não teve reclamação.
    erro = math.sqrt((k_a + 0.5) / t_a ** 2 + (k_b + 0.5) / t_b ** 2)
    return diferenca, diferenca - Z_FAIXA * erro, diferenca + Z_FAIXA * erro


def _semanas(inicio: date, fim: date) -> float:
    return max(1, (fim - inicio).days) / 7


def _veredito(efeito: float, p: float, q: float, poucos: bool) -> tuple[str, str]:
    if poucos:
        return "inconclusiva", "fraca"
    if efeito > 0 and q < Q_PROVAVEL:
        return "sustentada", ("forte" if q < 0.01 else "moderada")
    if efeito <= 0 or p >= P_DESCARTA:
        return "descartada", "fraca"
    return "inconclusiva", "fraca"


def _numero(valor: float) -> str:
    texto = f"{valor:.1f}".replace(".", ",")
    return texto[:-2] if texto.endswith(",0") else texto


def _data(dia: date) -> str:
    from app.formatos import data_longa

    return data_longa(dia)


def _exemplos(avaliacoes, categoria: str, condicao) -> tuple[str, ...]:
    textos = [a.texto for a in sorted(avaliacoes, key=lambda a: a.data, reverse=True)
              if a.categoria == categoria and a.texto and condicao(a.data)]
    return tuple(textos[:3])


def _hipotese_do_diario(i: int, evento: EventoDiario, categoria: str, avaliacoes, hoje: date,
                        nome: str) -> tuple[Hipotese, float, bool, float] | None:
    if (hoje - evento.data).days < DIAS_MINIMOS_DEPOIS:
        return None
    base_ini, base_fim = evento.data - JANELA, evento.data
    alta_ini, alta_fim = evento.data, min(evento.data + JANELA, hoje)
    do_assunto = [a for a in avaliacoes if a.categoria == categoria]
    k_antes = sum(1 for a in do_assunto if base_ini <= a.data < base_fim)
    k_depois = sum(1 for a in do_assunto if alta_ini <= a.data < alta_fim)
    t_antes, t_depois = _semanas(base_ini, base_fim), _semanas(alta_ini, alta_fim)
    p = _p_taxa_subiu(k_antes, t_antes, k_depois, t_depois)
    efeito, minimo, maximo = _faixa_da_diferenca(k_antes, t_antes, k_depois, t_depois)
    antes, depois = k_antes / t_antes, k_depois / t_depois
    poucos = k_antes + k_depois < MINIMO_NA_JANELA
    quando = _data(evento.data)
    o_que = evento.descricao.rstrip(". ")
    if poucos:
        frase = (f"Perto de {quando} ({o_que}) houve poucas reclamações de {nome} "
                 "para comparar antes e depois.")
    elif depois > antes:
        frase = (f"As reclamações de {nome} subiram depois de {quando}, quando: {o_que} "
                 f"(de {_numero(antes)} para {_numero(depois)} por semana).")
    else:
        frase = (f"Depois de {quando} ({o_que}), as reclamações de {nome} não subiram "
                 f"({_numero(antes)} por semana antes, {_numero(depois)} depois).")
    hipotese = Hipotese(
        id=f"h{i}", origem="diario", frase=frase, categoria=categoria,
        teste="razão de taxas de Poisson (binomial condicional), unilateral",
        antes_semana=round(antes, 2), depois_semana=round(depois, 2),
        efeito_semana=round(efeito, 2), efeito_min=round(minimo, 2), efeito_max=round(maximo, 2),
        q_valor=1.0, veredito="inconclusiva", forca="fraca",
        avaliacoes_exemplo=_exemplos(avaliacoes, categoria, lambda d: alta_ini <= d < alta_fim),
    )
    return hipotese, p, poucos, efeito


def _hipotese_fim_de_semana(i: int, categoria: str, avaliacoes, hoje: date,
                            nome: str) -> tuple[Hipotese, float, bool, float] | None:
    from scipy import stats

    # As últimas 26 semanas, se nelas houver reclamação suficiente do assunto. Negócio
    # com pouca avaliação (um bar pequeno recebe poucas por mês) usa o histórico inteiro.
    inicio, periodo = hoje - JANELA_DIAS_DA_SEMANA, "nas últimas 26 semanas"
    if sum(1 for a in avaliacoes if a.categoria == categoria and inicio <= a.data < hoje) < MINIMO_DO_ASSUNTO:
        inicio, periodo = min((a.data for a in avaliacoes), default=hoje), "em todo o histórico"
    recentes = [a for a in avaliacoes if inicio <= a.data < hoje]
    if not recentes:
        return None
    fds = [a for a in recentes if a.data.weekday() in FIM_DE_SEMANA]
    semana = [a for a in recentes if a.data.weekday() not in FIM_DE_SEMANA]
    a_fds = sum(1 for a in fds if a.categoria == categoria)
    a_sem = sum(1 for a in semana if a.categoria == categoria)
    outros_fds, outros_sem = len(fds) - a_fds, len(semana) - a_sem
    if a_fds + a_sem == 0 or outros_fds + outros_sem == 0:
        return None
    _, p = stats.fisher_exact([[a_fds, outros_fds], [a_sem, outros_sem]], alternative="greater")
    dias = [inicio + timedelta(d) for d in range((hoje - inicio).days)]
    dias_fds = sum(1 for d in dias if d.weekday() in FIM_DE_SEMANA)
    dias_sem = (hoje - inicio).days - dias_fds
    # Para a tela: reclamações por dia, de segunda a quinta e de sexta a domingo.
    por_dia_sem, por_dia_fds = a_sem / dias_sem, a_fds / dias_fds
    efeito, minimo, maximo = _faixa_da_diferenca(a_sem, dias_sem, a_fds, dias_fds)
    fatia_assunto = a_fds / (a_fds + a_sem)
    fatia_geral = len(fds) / len(recentes)
    poucos = a_fds + a_sem < MINIMO_NA_JANELA
    if poucos:
        frase = f"Ainda há poucas reclamações de {nome} para saber se elas se concentram em algum dia."
    elif fatia_assunto > fatia_geral:
        frase = (f"As reclamações de {nome} se concentram de sexta a domingo, {periodo}: "
                 f"{round(fatia_assunto * 100)} de cada 100 caem nesses dias, contra "
                 f"{round(fatia_geral * 100)} de cada 100 avaliações em geral.")
    else:
        frase = (f"As reclamações de {nome} não se concentram de sexta a domingo, {periodo}: "
                 f"{round(fatia_assunto * 100)} de cada 100 caem nesses dias, perto das "
                 f"{round(fatia_geral * 100)} de cada 100 avaliações em geral.")
    hipotese = Hipotese(
        id=f"h{i}", origem="dia_turno", frase=frase, categoria=categoria,
        teste="exato de Fisher (assunto × resto das avaliações, sexta a domingo), unilateral",
        antes_semana=round(por_dia_sem, 2), depois_semana=round(por_dia_fds, 2),
        efeito_semana=round(efeito, 2), efeito_min=round(minimo, 2), efeito_max=round(maximo, 2),
        q_valor=1.0, veredito="inconclusiva", forca="fraca",
        avaliacoes_exemplo=_exemplos(avaliacoes, categoria,
                                     lambda d: inicio <= d < hoje and d.weekday() in FIM_DE_SEMANA),
    )
    # O efeito que decide o veredito é a fatia, não a diferença por dia: o
    # movimento do fim de semana já é maior, e isso não é causa de nada.
    return hipotese, float(p), poucos, fatia_assunto - fatia_geral


def investigar(avaliacoes: Sequence[AvaliacaoClassificada], eventos: Sequence[EventoDiario],
               categoria: str, hoje: date, *, empresa_id: str = "",
               alerta_id: str | None = None) -> Investigacao:
    """Testa as possíveis causas e devolve da mais provável para a menos provável."""
    from app.conteudo import NOMES_CATEGORIA

    nome = NOMES_CATEGORIA[categoria]
    agora = datetime.now()
    alta = (hoje - JANELA, hoje)
    base = (hoje - 2 * JANELA, hoje - JANELA - timedelta(days=1))
    total = sum(1 for a in avaliacoes if a.categoria == categoria)
    identificador = f"inv-{empresa_id}-{categoria}"

    passos = [PassoInvestigacao(1, agora, "contou as reclamações",
                                f"{len(avaliacoes)} avaliações do negócio",
                                f"{total} reclamações de {nome}")]
    if total < MINIMO_DO_ASSUNTO:
        return Investigacao(
            id=identificador, empresa_id=empresa_id, alerta_id=alerta_id, categoria=categoria,
            periodo_alta=alta, periodo_base=base, hipoteses=(), passos=tuple(passos),
            usou_ia=False, estado="dados_insuficientes",
            motivo=(f"Ainda há poucas reclamações de {nome} para procurar a causa "
                    f"({total} no total; a conta precisa de pelo menos {MINIMO_DO_ASSUNTO}). "
                    "Quando chegarem mais avaliações, a análise sai sozinha."),
        )

    candidatas: list[tuple[Hipotese, float, bool, float]] = []
    for evento in sorted(eventos, key=lambda e: e.data):
        achada = _hipotese_do_diario(len(candidatas) + 1, evento, categoria, avaliacoes, hoje, nome)
        if achada:
            candidatas.append(achada)
    passos.append(PassoInvestigacao(2, agora, "leu o diário do negócio",
                                    f"{len(eventos)} mudanças anotadas",
                                    f"{len(candidatas)} com tempo suficiente depois para comparar"))
    fds = _hipotese_fim_de_semana(len(candidatas) + 1, categoria, avaliacoes, hoje, nome)
    if fds:
        candidatas.append(fds)
    passos.append(PassoInvestigacao(3, agora, "olhou os dias da semana",
                                    "últimas 26 semanas, ou o histórico inteiro se tiver pouco",
                                    "sexta a domingo contra o resto"))

    q_valores = benjamini_hochberg([p for _, p, _, _ in candidatas])
    hipoteses = []
    for (h, p, poucos, efeito), q in zip(candidatas, q_valores, strict=True):
        veredito, forca = _veredito(efeito, p, q, poucos)
        hipoteses.append(Hipotese(**{**h.__dict__, "q_valor": round(q, 4),
                                     "veredito": veredito, "forca": forca}))
    ordem = {"sustentada": 0, "inconclusiva": 1, "descartada": 2}
    hipoteses.sort(key=lambda h: (ordem[h.veredito], h.q_valor))
    passos.append(PassoInvestigacao(4, agora, "testou cada possível causa",
                                    f"{len(hipoteses)} testes",
                                    "conta corrigida para muitas tentativas (Benjamini-Hochberg)"))
    return Investigacao(
        id=identificador, empresa_id=empresa_id, alerta_id=alerta_id, categoria=categoria,
        periodo_alta=alta, periodo_base=base, hipoteses=tuple(hipoteses), passos=tuple(passos),
        usou_ia=False, estado="concluida", motivo=None,
    )
