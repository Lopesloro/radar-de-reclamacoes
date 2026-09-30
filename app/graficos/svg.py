"""Gráficos das telas, gerados em Python como SVG no servidor.

Regras seguidas em todos eles: um eixo só, eixo rotulado com unidade explícita,
linha de 2px, marcador com anel da cor do fundo, grade em filete de 1px, texto
sempre em cor de texto, nunca na cor da série, e dica de valor ao passar o
mouse em cada ponto.
"""

from __future__ import annotations

import math
from datetime import date
from html import escape

from markupsafe import Markup

from app.demo import MESES_CURTOS

ACENTO = "#0F6E7B"
CONTRA = "#B4531F"
TINTA = "#15212B"
MUDO = "#55646E"
TENDENCIA = "#8A939A"
GRADE = "#E3E7EA"
LAVADO = "#F1F3F4"
FUNDO = "#FFFFFF"
FONTE = "Inter, Segoe UI, Helvetica, Arial, sans-serif"


def mes_curto(dia: date) -> str:
    return f"{MESES_CURTOS[dia.month - 1]}/{dia.year % 100:02d}"


def _passo_limpo(amplitude: float, alvo: int) -> float:
    if amplitude <= 0:
        return 1.0
    bruto = amplitude / alvo
    ordem = 10 ** math.floor(math.log10(bruto))
    for m in (1, 2, 2.5, 5, 10):
        if bruto <= m * ordem:
            return m * ordem
    return 10 * ordem


def _eixo(vmin: float, vmax: float, alvo: int = 4) -> tuple[float, float, list[float]]:
    passo = _passo_limpo(vmax - vmin, alvo)
    inicio = math.floor(vmin / passo) * passo
    fim = math.ceil(vmax / passo) * passo
    ticks, valor = [], inicio
    while valor <= fim + passo * 1e-9:
        ticks.append(round(valor, 10))
        valor += passo
    return inicio, fim, ticks


def _texto(x: float, y: float, conteudo: str, *, tamanho: int = 12, cor: str = MUDO,
           ancora: str = "start", peso: int = 400) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONTE}" font-size="{tamanho}" '
        f'font-weight="{peso}" fill="{cor}" text-anchor="{ancora}">{escape(conteudo)}</text>'
    )


def _alvo(x: float, y: float, dica: str) -> str:
    return (
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="transparent">'
        f"<title>{escape(dica)}</title></circle>"
    )


def _svg(largura: int, altura: int, titulo: str, corpo: list[str]) -> Markup:
    return Markup(
        f'<svg class="grafico__svg" viewBox="0 0 {largura} {altura}" role="img" '
        f'aria-label="{escape(titulo)}" xmlns="http://www.w3.org/2000/svg">'
        f"<title>{escape(titulo)}</title>{''.join(corpo)}</svg>"
    )


def sparkline(valores: list[int], titulo: str, largura: int = 112, altura: int = 28) -> Markup:
    if len(valores) < 2:
        return Markup("")
    vmin, vmax = min(valores), max(valores)

    def x(i: int) -> float:
        return 4 + i * (largura - 10) / (len(valores) - 1)

    def y(v: float) -> float:
        return altura - 5 - (v - vmin) * (altura - 10) / ((vmax - vmin) or 1)

    pontos = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(valores))
    return Markup(
        f'<svg class="sparkline" viewBox="0 0 {largura} {altura}" width="{largura}" '
        f'height="{altura}" role="img" aria-label="{escape(titulo)}" '
        f'xmlns="http://www.w3.org/2000/svg"><title>{escape(titulo)}</title>'
        f'<polyline points="{pontos}" fill="none" stroke="{TENDENCIA}" stroke-width="1.5" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{x(len(valores) - 1):.1f}" cy="{y(valores[-1]):.1f}" r="4" '
        f'fill="{ACENTO}" stroke="{FUNDO}" stroke-width="2"/></svg>'
    )


def barras_categorias(itens: list[tuple[str, int, int]], titulo: str) -> Markup:
    """Contagem por categoria no mês fechado. A maior barra leva o acento."""
    largura, esq, dir_, topo, passo, espessura = 720, 150, 96, 18, 46, 24
    altura = topo + passo * len(itens) + 46
    maior = max(v for _, v, _ in itens) or 1
    _, _, ticks = _eixo(0, maior * 1.08)
    escala = (largura - esq - dir_) / (ticks[-1] or 1)

    corpo: list[str] = []
    for t in ticks:
        x = esq + t * escala
        corpo.append(
            f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{topo}" y2="{altura - 42}" '
            f'stroke="{GRADE}" stroke-width="1"/>'
        )
        corpo.append(_texto(x, altura - 24, f"{t:.0f}", ancora="middle", tamanho=11))
    corpo.append(_texto(esq, altura - 6, "reclamações classificadas no mês", tamanho=12))

    for i, (rotulo, valor, variacao) in enumerate(itens):
        y = topo + i * passo
        cor = ACENTO if valor == maior else MUDO
        corpo.append(_texto(esq - 14, y + espessura - 6, rotulo, cor=TINTA, ancora="end", tamanho=14))
        corpo.append(
            f'<rect x="{esq}" y="{y:.1f}" width="{max(valor * escala, 1):.1f}" '
            f'height="{espessura}" rx="4" fill="{cor}">'
            f"<title>{escape(f'{rotulo}: {valor} reclamações')}</title></rect>"
        )
        sinal = "+" if variacao > 0 else ("−" if variacao < 0 else "=")
        nota = f"{valor}   {sinal}{abs(variacao)}" if variacao else f"{valor}   ="
        corpo.append(_texto(esq + valor * escala + 10, y + espessura - 6, nota,
                            cor=TINTA, tamanho=13, peso=600))
    return _svg(largura, int(altura), titulo, corpo)


def previsao_mensal(serie, titulo: str) -> Markup:
    """Uma coluna por mês: o que já aconteceu, o mês aberto e o que se espera.

    Coluna é mais fácil de ler que linha quando o valor é contagem, e o traço
    vertical em cima da coluna estimada mostra o mínimo e o máximo sem precisar
    de legenda numérica. Nada de P10 e P90 na tela: quem olha quer saber "quanto
    deve dar" e "quanto pode variar".
    """
    largura, altura = 760, 350
    esq, dir_, topo, base = 56, 20, 64, 64

    fechados = serie.pontos[-9:]
    parcial = serie.parcial
    previstos = list(serie.previsao)
    colunas = len(fechados) + 1 + len(previstos)

    faixa_util = largura - esq - dir_
    vao = faixa_util / colunas
    espessura = min(40.0, vao * 0.6)

    def centro(i: int) -> float:
        return esq + vao * (i + 0.5)

    maximo = max([v for _, v in fechados] + [p.p90 for p in previstos] + [parcial[1]])
    _, y1, ticks = _eixo(0, maximo * 1.12)

    def y(v: float) -> float:
        return altura - base - (v - ticks[0]) * (altura - base - topo) / ((y1 - ticks[0]) or 1)

    corpo: list[str] = []

    # Legenda em palavras, no alto.
    corpo.append(f'<rect x="{esq}" y="14" width="13" height="13" rx="2" fill="{MUDO}"/>')
    corpo.append(_texto(esq + 19, 25, "meses que já fecharam", cor=TINTA))
    corpo.append(
        f'<rect x="{esq + 190}" y="14" width="13" height="13" rx="2" fill="none" '
        f'stroke="{MUDO}" stroke-width="1.5" stroke-dasharray="3 2"/>'
    )
    corpo.append(_texto(esq + 209, 25, "mês ainda em andamento", cor=TINTA))
    corpo.append(f'<rect x="{esq + 400}" y="14" width="13" height="13" rx="2" fill="{ACENTO}"/>')
    corpo.append(_texto(esq + 419, 25, "estimativa, com mínimo e máximo", cor=TINTA))

    for t in ticks:
        corpo.append(
            f'<line x1="{esq}" x2="{largura - dir_}" y1="{y(t):.1f}" y2="{y(t):.1f}" '
            f'stroke="{GRADE}" stroke-width="1"/>'
        )
        corpo.append(_texto(esq - 10, y(t) + 4, f"{t:.0f}", ancora="end", tamanho=11))
    corpo.append(_texto(esq - 10, topo - 14, "reclamações no mês", tamanho=12))

    base_y = y(ticks[0])
    indice = 0

    for mes, valor in fechados:
        x = centro(indice) - espessura / 2
        corpo.append(
            f'<rect x="{x:.1f}" y="{y(valor):.1f}" width="{espessura:.1f}" '
            f'height="{max(base_y - y(valor), 1):.1f}" rx="3" fill="{MUDO}">'
            f"<title>{escape(f'{mes_curto(mes)}: {valor} reclamações')}</title></rect>"
        )
        corpo.append(_rotulo_mes(centro(indice), altura - base, mes, indice == 0))
        indice += 1

    mes_aberto, valor_aberto = parcial
    x = centro(indice) - espessura / 2
    corpo.append(
        f'<rect x="{x:.1f}" y="{y(valor_aberto):.1f}" width="{espessura:.1f}" '
        f'height="{max(base_y - y(valor_aberto), 1):.1f}" rx="3" fill="none" '
        f'stroke="{MUDO}" stroke-width="1.5" stroke-dasharray="4 3">'
        f"<title>{escape(f'{mes_curto(mes_aberto)}: {valor_aberto} até agora, o mês ainda não terminou')}</title>"
        f"</rect>"
    )
    corpo.append(_texto(centro(indice), y(valor_aberto) - 9, "parcial", ancora="middle", tamanho=10))
    corpo.append(_rotulo_mes(centro(indice), altura - base, mes_aberto, False))
    indice += 1

    for ponto in previstos:
        cx = centro(indice)
        x = cx - espessura / 2
        corpo.append(
            f'<rect x="{x:.1f}" y="{y(ponto.p50):.1f}" width="{espessura:.1f}" '
            f'height="{max(base_y - y(ponto.p50), 1):.1f}" rx="3" fill="{ACENTO}">'
            f"<title>{escape(f'{mes_curto(ponto.mes)}: estimativa de {ponto.p50:.0f}, entre {ponto.p10:.0f} e {ponto.p90:.0f}')}</title>"
            f"</rect>"
        )
        # Traço do mínimo ao máximo, com as pontas marcadas.
        corpo.append(
            f'<line x1="{cx:.1f}" x2="{cx:.1f}" y1="{y(ponto.p90):.1f}" y2="{y(ponto.p10):.1f}" '
            f'stroke="{TINTA}" stroke-width="1.5"/>'
        )
        for valor in (ponto.p10, ponto.p90):
            corpo.append(
                f'<line x1="{cx - 8:.1f}" x2="{cx + 8:.1f}" y1="{y(valor):.1f}" '
                f'y2="{y(valor):.1f}" stroke="{TINTA}" stroke-width="1.5"/>'
            )
        corpo.append(_texto(cx, y(ponto.p90) - 10, f"{ponto.p50:.0f}", ancora="middle",
                            tamanho=13, cor=TINTA, peso=600))
        corpo.append(_rotulo_mes(cx, altura - base, ponto.mes, False))
        indice += 1

    # Onde o passado acaba e a estimativa começa.
    corte = esq + vao * len(fechados)
    corpo.append(
        f'<line x1="{corte:.1f}" x2="{corte:.1f}" y1="{topo - 6}" y2="{base_y + 10:.1f}" '
        f'stroke="{TENDENCIA}" stroke-width="1" stroke-dasharray="4 4"/>'
    )
    corpo.append(_texto(corte + 6, topo + 4, "daqui para a frente é estimativa",
                        tamanho=11, cor=MUDO))
    corpo.append(
        f'<line x1="{esq}" x2="{largura - dir_}" y1="{base_y:.1f}" y2="{base_y:.1f}" '
        f'stroke="{TINTA}" stroke-width="1"/>'
    )
    return _svg(largura, altura, titulo, corpo)


def _rotulo_mes(x: float, y_base: float, mes: date, com_ano: bool) -> str:
    """Mês em três letras; o ano só aparece quando vira."""
    saida = _texto(x, y_base + 20, MESES_CURTOS[mes.month - 1], ancora="middle", tamanho=11)
    if com_ano or mes.month == 1:
        saida += _texto(x, y_base + 36, str(mes.year), ancora="middle", tamanho=10)
    return saida


def variacao(itens: list[tuple[str, int]], titulo: str) -> Markup:
    """Quanto cada categoria subiu ou caiu em relação ao mês anterior, em contagem."""
    largura, esq, dir_, topo, passo, espessura = 720, 150, 70, 46, 44, 22
    altura = topo + passo * len(itens) + 14
    maior = max(abs(v) for _, v in itens) or 1
    zero = esq + (largura - esq - dir_) / 2
    escala = (largura - esq - dir_) / 2 / maior

    corpo = [
        f'<rect x="{esq}" y="12" width="12" height="12" rx="2" fill="{CONTRA}"/>',
        _texto(esq + 18, 22, "Cresceu", cor=TINTA),
        f'<rect x="{esq + 110}" y="12" width="12" height="12" rx="2" fill="{ACENTO}"/>',
        _texto(esq + 128, 22, "Caiu", cor=TINTA),
        _texto(largura - dir_, 22, "variação em número de reclamações", ancora="end"),
        f'<line x1="{zero:.1f}" x2="{zero:.1f}" y1="{topo - 10}" y2="{altura - 10}" '
        f'stroke="{GRADE}" stroke-width="1"/>',
    ]
    for i, (rotulo, valor) in enumerate(itens):
        centro = topo + i * passo + passo / 2
        corpo.append(_texto(esq - 14, centro + 4, rotulo, cor=TINTA, ancora="end", tamanho=14))
        x1 = zero + valor * escala
        x0, x1 = (zero, x1) if valor >= 0 else (x1, zero)
        corpo.append(
            f'<rect x="{min(x0, x1):.1f}" y="{centro - espessura / 2:.1f}" '
            f'width="{max(abs(x1 - x0), 1):.1f}" height="{espessura}" rx="4" '
            f'fill="{CONTRA if valor > 0 else ACENTO}"/>'
        )
        rotulo_valor = f"+{valor}" if valor > 0 else (f"−{abs(valor)}" if valor < 0 else "0")
        if valor >= 0:
            corpo.append(_texto(zero + abs(valor) * escala + 10, centro + 4, rotulo_valor,
                                cor=TINTA, peso=600))
        else:
            corpo.append(_texto(zero - abs(valor) * escala - 10, centro + 4, rotulo_valor,
                                cor=TINTA, peso=600, ancora="end"))
    return _svg(largura, int(altura), titulo, corpo)


def previsto_realizado(pontos: list[tuple[date, float, float]], titulo: str) -> Markup:
    """Duas séries na mesma unidade: o que o modelo previu e o que aconteceu."""
    largura, altura = 760, 300
    esq, dir_, topo, base = 60, 24, 52, 44
    n = len(pontos)

    def x(i: int) -> float:
        return esq + i * (largura - esq - dir_) / max(n - 1, 1)

    maximo = max(max(p, r) for _, p, r in pontos)
    _, y1, ticks = _eixo(0, maximo * 1.1)

    def y(v: float) -> float:
        return altura - base - (v - ticks[0]) * (altura - base - topo) / ((y1 - ticks[0]) or 1)

    corpo = [
        f'<line x1="{esq}" x2="{esq + 22}" y1="22" y2="22" stroke="{ACENTO}" stroke-width="2"/>',
        _texto(esq + 30, 26, "Previsto um mês antes", cor=TINTA),
        f'<line x1="{esq + 210}" x2="{esq + 232}" y1="22" y2="22" stroke="{CONTRA}" stroke-width="2"/>',
        _texto(esq + 240, 26, "Realizado", cor=TINTA),
        _texto(largura - dir_, 26, "reclamações por mês", ancora="end"),
    ]
    for t in ticks:
        corpo.append(
            f'<line x1="{esq}" x2="{largura - dir_}" y1="{y(t):.1f}" y2="{y(t):.1f}" '
            f'stroke="{GRADE}" stroke-width="1"/>'
        )
        corpo.append(_texto(esq - 10, y(t) + 4, f"{t:.0f}", ancora="end", tamanho=11))
    for indice, cor in ((1, ACENTO), (2, CONTRA)):
        linha = " ".join(f"{x(i):.1f},{y(p[indice]):.1f}" for i, p in enumerate(pontos))
        corpo.append(
            f'<polyline points="{linha}" fill="none" stroke="{cor}" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        corpo.append(
            f'<circle cx="{x(n - 1):.1f}" cy="{y(pontos[-1][indice]):.1f}" r="4.5" fill="{cor}" '
            f'stroke="{FUNDO}" stroke-width="2"/>'
        )
    for i, (mes, previsto, realizado) in enumerate(pontos):
        corpo.append(_texto(x(i), altura - base + 20, mes_curto(mes), ancora="middle", tamanho=11))
        corpo.append(_alvo(x(i), (y(previsto) + y(realizado)) / 2,
                           f"{mes_curto(mes)}: previsto {previsto:.0f}, realizado {realizado:.0f}"))
    return _svg(largura, altura, titulo, corpo)


def barras_f1(linhas, macro: float, regua: float, titulo: str) -> Markup:
    """F1 por categoria, com o macro do modelo e o da régua marcados no eixo."""
    largura, esq, dir_, topo, passo, espessura = 720, 150, 90, 56, 44, 22
    altura = topo + passo * len(linhas) + 48
    escala = (largura - esq - dir_)

    corpo = [
        _texto(esq, 24, "F1 por categoria", cor=TINTA, tamanho=13, peso=600),
        _texto(largura - dir_, 24, "0 a 1, quanto maior melhor", ancora="end"),
    ]
    for t in (0, 0.25, 0.5, 0.75, 1.0):
        x = esq + t * escala
        corpo.append(
            f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{topo - 8}" y2="{altura - 44}" '
            f'stroke="{GRADE}" stroke-width="1"/>'
        )
        corpo.append(_texto(x, altura - 26, f"{t:.2f}".replace(".", ","), ancora="middle", tamanho=11))

    for i, linha in enumerate(linhas):
        y = topo + i * passo
        corpo.append(_texto(esq - 14, y + espessura - 5, linha.categoria, cor=TINTA,
                            ancora="end", tamanho=14))
        corpo.append(
            f'<rect x="{esq}" y="{y:.1f}" width="{linha.f1 * escala:.1f}" height="{espessura}" '
            f'rx="4" fill="{ACENTO}"><title>'
            f"{escape(f'{linha.categoria}: F1 {linha.f1}, {linha.apoio} avaliações na amostra')}"
            f"</title></rect>"
        )
        corpo.append(_texto(esq + linha.f1 * escala + 10, y + espessura - 5,
                            f"{linha.f1:.2f}".replace(".", ","), cor=TINTA, tamanho=13, peso=600))

    # O texto usa a tinta; quem carrega a diferença é o traço, não a cor da letra.
    for valor, rotulo, cor, tracejado in (
        (regua, "régua", CONTRA, "3 3"), (macro, "macro do modelo", TINTA, "8 4"),
    ):
        x = esq + valor * escala
        corpo.append(
            f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{topo - 14}" y2="{altura - 44}" '
            f'stroke="{cor}" stroke-width="2" stroke-dasharray="{tracejado}"/>'
        )
        texto = f"{rotulo} {valor:.2f}".replace(".", ",")
        corpo.append(_texto(x, altura - 6, texto, ancora="middle", cor=TINTA, tamanho=12, peso=600))
    return _svg(largura, int(altura), titulo, corpo)
