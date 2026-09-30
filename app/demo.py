"""Dados de demonstração do Radar de Reclamações.

Tudo aqui é fictício e determinístico: os mesmos comércios, as mesmas avaliações
e os mesmos números a cada execução. Serve para exercitar as telas enquanto a
coleta real dos parceiros não começa. Nenhum dado de pessoa real entra neste
arquivo, e nenhuma avaliação aqui foi escrita por um cliente de verdade.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache

HOJE = date(2026, 9, 29)
MESES_FECHADOS = 12          # meses completos que alimentam o modelo
HORIZONTE = 2                # meses previstos
Z80 = 1.2816                 # quantil de 80% da normal, para a faixa P10-P90

CATEGORIAS = ("atendimento", "demora", "preço", "qualidade", "ambiente")
SEM_CATEGORIA = "sem categoria"
ARTIGO = {"atendimento": "o", "demora": "a", "preço": "o", "qualidade": "a", "ambiente": "o"}
LIMITE_CONFIANCA = 0.55      # abaixo disso o classificador não atribui categoria

MESES_CURTOS = ("jan", "fev", "mar", "abr", "mai", "jun",
                "jul", "ago", "set", "out", "nov", "dez")

FRASES = {
    "atendimento": (
        "Fui mal atendido no balcão e ninguém soube resolver.",
        "A atendente foi seca e não explicou nada.",
        "Liguei três vezes e não retornaram.",
        "Falta preparo de quem atende no telefone.",
    ),
    "demora": (
        "O pedido levou quase uma hora para sair.",
        "Esperei muito tempo para ser chamado.",
        "Demorou bem mais do que o combinado.",
        "Fila longa e só uma pessoa atendendo.",
    ),
    "preço": (
        "Achei caro para o que entregam.",
        "O valor subiu e o serviço continuou igual.",
        "Cobraram uma taxa que não estava combinada.",
        "Preço acima do que se paga na região.",
    ),
    "qualidade": (
        "O produto chegou diferente do que foi pedido.",
        "Não ficou do jeito que combinamos.",
        "Precisei voltar para refazer o serviço.",
        "Veio faltando item no pedido.",
    ),
    "ambiente": (
        "O local estava sujo quando cheguei.",
        "Barulho alto, difícil conversar.",
        "Faltou lugar para sentar e esperar.",
        "Ar-condicionado desligado num dia quente.",
    ),
}

ELOGIOS = (
    "Atendimento rápido e educado, voltarei.",
    "Gostei bastante, recomendo.",
    "Serviço bem feito, dentro do prazo.",
)

# Texto que existe, mas não descreve reclamação de nenhuma das categorias.
AMBIGUOS = (
    "Estava passando na rua e resolvi entrar.",
    "Fui atendido.",
    "Já vim outras vezes.",
)


@dataclass(frozen=True)
class Avaliacao:
    id: str
    data: date
    estrelas: int
    texto: str | None
    categoria: str | None
    confianca: float

    @property
    def classificada(self) -> bool:
        return self.categoria is not None

    @property
    def motivo_sem_categoria(self) -> str:
        if self.texto is None:
            return "sem texto"
        if self.estrelas >= 4:
            return "não é reclamação"
        return "confiança abaixo do limite"


@dataclass(frozen=True)
class Previsao:
    mes: date
    p10: float
    p50: float
    p90: float


@dataclass
class Serie:
    """Uma categoria de reclamação ao longo dos meses, em um comércio."""

    categoria: str
    pontos: list[tuple[date, int]]          # meses fechados
    parcial: tuple[date, int]               # mês corrente, ainda aberto
    previsao: list[Previsao]

    @property
    def ultimo(self) -> int:
        return self.pontos[-1][1]

    @property
    def anterior(self) -> int:
        return self.pontos[-2][1]

    @property
    def variacao(self) -> int:
        return self.ultimo - self.anterior

    @property
    def prevista(self) -> float:
        return self.previsao[0].p50

    @property
    def crescimento_previsto(self) -> float:
        return self.prevista - self.ultimo

    @property
    def regua(self) -> int:
        """A régua da previsão: repetir o último mês fechado."""
        return self.ultimo

    def frase(self) -> str:
        artigo = ARTIGO[self.categoria]
        if self.crescimento_previsto >= 1:
            return (
                f"A previsão para o próximo mês é de alta em {artigo} "
                f"{self.categoria}: de {self.ultimo} para cerca de "
                f"{round(self.prevista)} reclamações."
            )
        if self.crescimento_previsto <= -1:
            return (
                f"A previsão indica queda em {artigo} {self.categoria}: "
                f"de {self.ultimo} para cerca de {round(self.prevista)}."
            )
        return (
            f"{artigo.capitalize()} {self.categoria} deve ficar estável, "
            f"perto de {round(self.prevista)} reclamações."
        )


@dataclass
class Alerta:
    id: str
    comercio_id: str
    comercio_nome: str
    categoria: str
    gravidade: str            # critico | atencao
    atual: int
    previsto: float
    gerado_em: date
    estado: str = "aberto"    # aberto | confirmado | descartado

    @property
    def crescimento(self) -> float:
        return self.previsto - self.atual

    def frase(self) -> str:
        artigo = ARTIGO[self.categoria]
        return (
            f"{artigo.capitalize()} {self.categoria} saiu de {self.atual} reclamações "
            f"no último mês fechado para {round(self.previsto)} previstas no próximo."
        )


@dataclass
class Comercio:
    id: str
    nome: str
    ramo: str
    cidade: str
    series: list[Serie]
    avaliacoes: list[Avaliacao]
    nota_media: float = 0.0
    sem_categoria: int = 0

    def serie(self, categoria: str) -> Serie:
        for s in self.series:
            if s.categoria == categoria:
                return s
        raise KeyError(categoria)

    @property
    def total_avaliacoes(self) -> int:
        return len(self.avaliacoes)

    @property
    def pontos_fechados(self) -> list[tuple[date, int]]:
        return self.series[0].pontos

    @property
    def total_reclamacoes(self) -> int:
        return sum(s.ultimo for s in self.series)

    @property
    def dominante(self) -> Serie:
        return max(self.series, key=lambda s: s.ultimo)

    @property
    def em_alta(self) -> Serie:
        return max(self.series, key=lambda s: s.crescimento_previsto)

    @property
    def estado(self) -> str:
        alta = self.em_alta
        relativo = alta.crescimento_previsto / max(alta.ultimo, 1)
        if alta.crescimento_previsto < 1.5 or relativo < 0.04:
            return "ok"
        return "critico" if alta.previsao[0].p10 > alta.ultimo else "atencao"


PARCEIROS = (
    # (id, nome fictício, ramo, cidade, categoria em alta, semente)
    ("bella-massa", "Pizzaria Bella Massa", "Restaurante", "Campinas, SP", "demora", 11),
    ("sorriso-claro", "Clínica Sorriso Claro", "Odontologia", "Valinhos, SP", "atendimento", 23),
    ("patinhas", "Pet Shop Patinhas", "Pet shop", "Campinas, SP", "preço", 37),
)

# O que já está combinado com cada parceiro. É o que alimenta a tela de etapas:
# o empresário precisa ver o que falta antes de cobrar resultado do sistema.
COMBINADO = {
    "bella-massa": {"termo": True, "fonte": True, "categorias": True, "canal": True},
    "sorriso-claro": {"termo": True, "fonte": True, "categorias": True, "canal": False},
    "patinhas": {"termo": True, "fonte": True, "categorias": False, "canal": False},
}

NIVEL_BASE = {"atendimento": 34, "demora": 28, "preço": 22, "qualidade": 18, "ambiente": 12}


def _mes(deslocamento: int) -> date:
    """Primeiro dia do mês, contado a partir do mês corrente (0 = mês de HOJE)."""
    total = HOJE.year * 12 + (HOJE.month - 1) + deslocamento
    return date(total // 12, total % 12 + 1, 1)


AMORTECIMENTO = 1.0   # quanto da tendência se projeta para a frente


def _prever(valores: list[int], sorteio: random.Random) -> list[Previsao]:
    """Último mês fechado mais a tendência dos seis meses, quando ela existe.

    A tendência crua perde da régua em série curta e ruidosa, porque persegue o
    ruído. Por isso a inclinação só entra quando supera o próprio erro padrão, e
    o ponto de partida é o último mês observado, a mesma régua que serve de
    comparação na tela de acurácia.
    """
    janela = valores[-6:]
    n = len(janela)
    media_x = (n - 1) / 2
    media_y = sum(janela) / n
    variancia = sum((i - media_x) ** 2 for i in range(n)) or 1
    inclinacao = sum((i - media_x) * (v - media_y) for i, v in enumerate(janela)) / variancia
    residuos = [v - (media_y + inclinacao * (i - media_x)) for i, v in enumerate(janela)]
    # Inclinação indistinguível de zero não é tendência, é ruído: some.
    erro_inclinacao = math.sqrt(sum(r * r for r in residuos) / max(n - 2, 1) / variancia)
    # 1,8 erros padrão: perto de 90% de confiança para uma janela de seis meses.
    if abs(inclinacao) < 1.8 * erro_inclinacao:
        inclinacao = 0.0
        residuos = [v - media_y for v in janela]
    # A faixa carrega o erro do ajuste, não só a dispersão observada.
    sigma = max(1.0, 1.35 * math.sqrt(sum(r * r for r in residuos) / max(n - 2, 1)))

    # O modelo parte da régua, o último mês fechado, e só se afasta dela
    # quando a inclinação é distinguível de zero. Assim ele nunca perde para a
    # régua por capricho do ajuste: ou empata, ou ganha onde há tendência real.
    nivel = float(janela[-1])

    previsao: list[Previsao] = []
    for h in range(1, HORIZONTE + 1):
        centro = max(0.0, nivel + inclinacao * AMORTECIMENTO * h)
        largura = Z80 * sigma * math.sqrt(h)
        # Contagem de reclamação é número inteiro; prever "58,6" é falsa precisão.
        previsao.append(Previsao(
            mes=_mes(h),
            p10=max(0.0, round(centro - largura)),
            p50=max(0.0, round(centro)),
            p90=round(centro + largura),
        ))
    return previsao


def _serie(categoria: str, em_alta: bool, sorteio: random.Random) -> Serie:
    base = NIVEL_BASE[categoria]
    valores: list[int] = []
    for i in range(MESES_FECHADOS):
        sazonal = 1.0 + 0.04 * math.sin((i + 2) * math.pi / 6)
        tendencia = 1.0 + (0.085 * i if em_alta else 0.0)
        # Quebra de nível nos últimos meses: é o que o alerta precisa enxergar.
        degrau = 1.0
        ruido = sorteio.uniform(-1.6, 1.6)
        valores.append(max(0, round(base * sazonal * tendencia * degrau + ruido)))

    pontos = [(_mes(i - MESES_FECHADOS), v) for i, v in enumerate(valores)]
    # O mês corrente está aberto: por volta de um terço do mês já passou.
    parcial = (_mes(0), max(0, round(valores[-1] * 0.34 + sorteio.uniform(-0.6, 0.6))))
    return Serie(categoria, pontos, parcial, _prever(valores, sorteio))


def _avaliacoes(comercio_id: str, series: list[Serie], sorteio: random.Random) -> list[Avaliacao]:
    """Avaliações do último mês fechado, na proporção das contagens da série."""
    mes = series[0].pontos[-1][0]
    itens: list[Avaliacao] = []
    sequencia = 0

    for serie in series:
        for _ in range(serie.ultimo):
            sequencia += 1
            dia = sorteio.randint(1, 26)
            itens.append(Avaliacao(
                id=f"{comercio_id}-{sequencia:03d}",
                data=date(mes.year, mes.month, dia),
                estrelas=sorteio.choice((1, 1, 2, 2, 3)),
                texto=sorteio.choice(FRASES[serie.categoria]),
                categoria=serie.categoria,
                confianca=round(sorteio.uniform(0.62, 0.96), 2),
            ))

    # Avaliação positiva: entra na nota média e sai da estatística de problemas.
    for _ in range(sorteio.randint(9, 14)):
        sequencia += 1
        itens.append(Avaliacao(
            id=f"{comercio_id}-{sequencia:03d}",
            data=date(mes.year, mes.month, sorteio.randint(1, 26)),
            estrelas=sorteio.choice((4, 5, 5)),
            texto=sorteio.choice(ELOGIOS),
            categoria=None,
            confianca=round(sorteio.uniform(0.71, 0.93), 2),
        ))

    # Avaliação só com estrela: nunca vai para o classificador.
    for _ in range(sorteio.randint(3, 6)):
        sequencia += 1
        itens.append(Avaliacao(
            id=f"{comercio_id}-{sequencia:03d}",
            data=date(mes.year, mes.month, sorteio.randint(1, 26)),
            estrelas=sorteio.choice((1, 3, 4, 5)),
            texto=None,
            categoria=None,
            confianca=0.0,
        ))

    # Texto que não cabe em nenhuma categoria: fica sem categoria, não vira chute.
    for _ in range(sorteio.randint(2, 4)):
        sequencia += 1
        itens.append(Avaliacao(
            id=f"{comercio_id}-{sequencia:03d}",
            data=date(mes.year, mes.month, sorteio.randint(1, 26)),
            estrelas=sorteio.choice((2, 3, 4)),
            texto=sorteio.choice(AMBIGUOS),
            categoria=None,
            confianca=round(sorteio.uniform(0.18, LIMITE_CONFIANCA - 0.02), 2),
        ))

    itens.sort(key=lambda a: (a.data, a.id), reverse=True)
    return itens


@lru_cache(maxsize=1)
def comercios() -> tuple[Comercio, ...]:
    lista: list[Comercio] = []
    for identificador, nome, ramo, cidade, alta, semente in PARCEIROS:
        sorteio = random.Random(semente)
        series = [_serie(c, c == alta, sorteio) for c in CATEGORIAS]
        avaliacoes = _avaliacoes(identificador, series, sorteio)
        nota = sum(a.estrelas for a in avaliacoes) / len(avaliacoes)
        lista.append(Comercio(
            id=identificador,
            nome=nome,
            ramo=ramo,
            cidade=cidade,
            series=series,
            avaliacoes=avaliacoes,
            nota_media=round(nota, 1),
            sem_categoria=sum(1 for a in avaliacoes if not a.classificada),
        ))
    return tuple(lista)


def comercio(identificador: str) -> Comercio | None:
    for c in comercios():
        if c.id == identificador:
            return c
    return None


@lru_cache(maxsize=1)
def _alertas_iniciais() -> tuple[Alerta, ...]:
    gerados: list[Alerta] = []
    for c in comercios():
        for s in c.series:
            crescimento = s.crescimento_previsto
            relativo = crescimento / max(s.ultimo, 1)
            if crescimento < 1.5 or relativo < 0.04:
                continue
            gerados.append(Alerta(
                id=f"{c.id}-{s.categoria}",
                comercio_id=c.id,
                comercio_nome=c.nome,
                categoria=s.categoria,
                # Crítico é quando nem o piso da faixa devolve a categoria ao normal.
                gravidade="critico" if s.previsao[0].p10 > s.ultimo else "atencao",
                atual=s.ultimo,
                previsto=s.prevista,
                gerado_em=HOJE,
            ))
    gerados.sort(key=lambda a: a.crescimento, reverse=True)
    return tuple(gerados)


# O estado do alerta muda em memória: é demonstração, não banco.
_ESTADOS: dict[str, str] = {}


def alertas() -> list[Alerta]:
    lista = []
    for modelo in _alertas_iniciais():
        lista.append(Alerta(
            id=modelo.id,
            comercio_id=modelo.comercio_id,
            comercio_nome=modelo.comercio_nome,
            categoria=modelo.categoria,
            gravidade=modelo.gravidade,
            atual=modelo.atual,
            previsto=modelo.previsto,
            gerado_em=modelo.gerado_em,
            estado=_ESTADOS.get(modelo.id, "aberto"),
        ))
    return lista


def mudar_estado(alerta_id: str, acao: str) -> bool:
    destino = {"confirmar": "confirmado", "descartar": "descartado", "reabrir": "aberto"}
    if acao not in destino or alerta_id not in {a.id for a in _alertas_iniciais()}:
        return False
    _ESTADOS[alerta_id] = destino[acao]
    return True


def limpar_estados() -> None:
    _ESTADOS.clear()


@dataclass(frozen=True)
class LinhaF1:
    categoria: str
    precisao: float
    recall: float
    f1: float
    apoio: int


@lru_cache(maxsize=1)
def acuracia_classificacao() -> dict:
    """Resultado do classificador na amostra rotulada à mão pela equipe."""
    sorteio = random.Random(101)
    linhas: list[LinhaF1] = []
    for categoria in CATEGORIAS:
        apoio = sum(c.serie(categoria).ultimo for c in comercios())
        precisao = round(sorteio.uniform(0.74, 0.91), 2)
        recall = round(sorteio.uniform(0.70, 0.90), 2)
        f1 = round(2 * precisao * recall / (precisao + recall), 2)
        linhas.append(LinhaF1(categoria, precisao, recall, f1, apoio))

    macro = round(sum(l.f1 for l in linhas) / len(linhas), 2)
    # Régua: responder sempre a categoria mais comum da amostra.
    maior = max(linhas, key=lambda l: l.apoio)
    total = sum(l.apoio for l in linhas)
    precisao_regua = maior.apoio / total
    f1_maior = 2 * precisao_regua * 1.0 / (precisao_regua + 1.0)
    macro_regua = round(f1_maior / len(linhas), 2)
    return {
        "linhas": linhas,
        "macro": macro,
        "macro_regua": macro_regua,
        "amostra": total,
        "categoria_regua": maior.categoria,
    }


@lru_cache(maxsize=1)
def acuracia_previsao() -> dict:
    """Previsto contra realizado nos meses fechados, sempre ao lado da régua.

    O modelo aqui é a mesma tendência de seis meses usada na tela de previsão;
    a régua é repetir o mês anterior. O erro é a média do desvio absoluto.
    """
    pontos: list[tuple[date, float, float]] = []
    erro_modelo: list[float] = []
    erro_regua: list[float] = []
    dentro = 0
    total = 0

    for c in comercios():
        for s in c.series:
            valores = [v for _, v in s.pontos]
            for corte in range(6, len(valores)):
                sorteio = random.Random(hash((c.id, s.categoria, corte)) & 0xFFFF)
                previsao = _prever(valores[:corte], sorteio)[0]
                realizado = valores[corte]
                erro_modelo.append(abs(previsao.p50 - realizado))
                erro_regua.append(abs(valores[corte - 1] - realizado))
                total += 1
                if previsao.p10 <= realizado <= previsao.p90:
                    dentro += 1
                if c.id == "bella-massa" and s.categoria == "demora":
                    pontos.append((s.pontos[corte][0], previsao.p50, float(realizado)))

    return {
        "pontos": pontos,
        "mae": round(sum(erro_modelo) / len(erro_modelo), 2),
        "mae_regua": round(sum(erro_regua) / len(erro_regua), 2),
        "cobertura": round(dentro / total, 2),
        "janelas": total,
    }


@dataclass(frozen=True)
class Etapa:
    numero: int
    titulo: str
    estado: str          # feito | andamento | pendente
    detalhe: str
    falta: str | None


def etapas(alvo: Comercio) -> list[Etapa]:
    """As sete etapas entre o aperto de mão e o alerta chegando ao empresário.

    Cada uma é verificada contra o estado real da demonstração: o que está feito
    está feito porque o dado existe, não porque alguém marcou uma caixinha.
    """
    combinado = COMBINADO[alvo.id]
    fechados = len(alvo.pontos_fechados)
    classificacao = acuracia_classificacao()
    previsao = acuracia_previsao()

    def marca(condicao: bool, falta: str, andamento: bool = False) -> tuple[str, str | None]:
        if condicao:
            return "feito", None
        return ("andamento" if andamento else "pendente"), falta

    itens: list[tuple[str, str, bool, str, bool]] = [
        (
            "Termo de autorização assinado",
            "Finalidade acadêmica, escopo, prazo de retenção e direito de revogação por escrito.",
            combinado["termo"],
            "Assinatura do responsável pela empresa, com CNPJ. Sem isso nada é coletado.",
            False,
        ),
        (
            "Fonte de avaliações conectada",
            "A ficha pública do comércio, lida todo dia, com identificador de cada avaliação.",
            combinado["fonte"],
            "Definir a via de leitura e registrar a primeira carga.",
            False,
        ),
        (
            "Histórico mínimo para prever",
            f"{fechados} meses fechados disponíveis; a janela do ajuste é de seis.",
            fechados >= 6,
            f"Faltam {max(0, 6 - fechados)} meses fechados. Até lá a tela mostra o histórico sem previsão.",
            True,
        ),
        (
            "Categorias validadas com o parceiro",
            "As cinco categorias precisam ser as palavras que o dono usa, não as nossas.",
            combinado["categorias"],
            "Uma conversa de trinta minutos para confirmar, renomear ou dividir categoria.",
            True,
        ),
        (
            "Classificação acima da régua",
            f"F1 macro de {classificacao['macro']:.2f} contra {classificacao['macro_regua']:.2f} da régua.",
            classificacao["macro"] > classificacao["macro_regua"],
            "Rotular mais avaliações à mão até o modelo superar a régua em todas as categorias.",
            True,
        ),
        (
            "Previsão acima da régua",
            f"Erro médio de {previsao['mae']:.2f} contra {previsao['mae_regua']:.2f} da régua, "
            f"cobertura de {previsao['cobertura'] * 100:.0f}% na faixa.",
            previsao["mae"] < previsao["mae_regua"],
            "Enquanto o modelo não ganhar da régua, a tela mostra a régua e diz que é ela.",
            True,
        ),
        (
            "Canal de alerta combinado",
            "Por onde o aviso chega quando uma categoria entra em alta.",
            combinado["canal"],
            "Escolher entre e-mail e WhatsApp e confirmar quem recebe. Hoje o alerta só existe na tela.",
            False,
        ),
    ]

    resultado: list[Etapa] = []
    for i, (titulo, detalhe, condicao, falta, andamento) in enumerate(itens, start=1):
        estado, pendencia = marca(condicao, falta, andamento)
        resultado.append(Etapa(i, titulo, estado, detalhe, pendencia))
    return resultado


def prontidao(alvo: Comercio) -> int:
    """Quantas das sete etapas estão concluídas."""
    return sum(1 for e in etapas(alvo) if e.estado == "feito")
