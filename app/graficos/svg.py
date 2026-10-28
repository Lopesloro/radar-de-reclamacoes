"""Gráficos desenhados no servidor, em SVG.

As regras valem para todos (plano/03-nicolas.md, "Regras dos gráficos"):
- o rótulo fica em cima da coisa: todo valor está escrito, sem eixo para decifrar;
- uma cor, um significado: laranja piorou, azul-petróleo é estimativa ou
  melhora, cinza é passado; e a cor nunca vem sozinha, sempre com ▲ ▼ e palavra;
- a incerteza é escrita ("entre 51 e 58") e aparece como uma faixa clara;
- gráfico largo tem uma versão estreita para o celular, trocada pelo CSS, e
  nenhum texto fica abaixo de 12px no tamanho em que aparece na tela.

Nada de atributo `style`: a política de segurança do site não permite.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from html import escape

from markupsafe import Markup

from app.formatos import MESES_CURTOS

ACENTO = "#0F6E7B"
ACENTO_CLARO = "#CFE5E7"
LARANJA = "#B4531F"
PASSADO = "#7A8790"
PASSADO_CLARO = "#DDE2E5"
TINTA = "#16232C"
MUDO = "#46535C"
FUNDO = "#FFFFFF"
FONTE = "Inter, Segoe UI, Helvetica, Arial, sans-serif"


def _texto(x: float, y: float, conteudo: str, *, tamanho: int = 14, cor: str = TINTA,
           ancora: str = "middle", peso: int = 400) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONTE}" font-size="{tamanho}" '
        f'font-weight="{peso}" fill="{cor}" text-anchor="{ancora}">{escape(conteudo)}</text>'
    )


def _retangulo(x: float, y: float, largura: float, altura: float, cor: str, *,
               dica: str | None = None, raio: float = 3, contorno: str | None = None,
               tracejado: bool = False) -> str:
    extra = ""
    if contorno:
        extra = f' stroke="{contorno}" stroke-width="1.5"'
        if tracejado:
            extra += ' stroke-dasharray="4 3"'
    corpo = f"<title>{escape(dica)}</title>" if dica else ""
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(largura, 0):.1f}" '
        f'height="{max(altura, 0):.1f}" rx="{raio}" fill="{cor}"{extra}>{corpo}</rect>'
    )


def _svg(largura: int, altura: int, titulo: str, corpo: list[str], classe: str) -> Markup:
    return Markup(
        f'<svg class="{classe}" viewBox="0 0 {largura} {altura}" role="img" '
        f'aria-label="{escape(titulo)}" xmlns="http://www.w3.org/2000/svg">'
        f"<title>{escape(titulo)}</title>{''.join(corpo)}</svg>"
    )


def _duas_versoes(largo: Markup, estreito: Markup) -> Markup:
    return Markup(f'<div class="grafico__versoes">{largo}{estreito}</div>')


# ------------------------------------------------------------ colunas por mês

def colunas_mensais(serie, titulo: str) -> Markup:
    """Meses fechados em cinza, o mês corrente (o que já chegou mais o que falta) e o seguinte."""
    return _duas_versoes(
        _colunas_mensais(serie, titulo, fechados=6, largura=720, altura=330, fonte=13,
                         classe="grafico__svg grafico__svg--largo"),
        _colunas_mensais(serie, titulo, fechados=3, largura=360, altura=330, fonte=15,
                         classe="grafico__svg grafico__svg--estreito"),
    )


def _colunas_mensais(serie, titulo, *, fechados, largura, altura, fonte, classe) -> Markup:
    meses = list(serie.meses[-fechados:])
    corrente, proximo = serie.previsoes[0], serie.previsoes[1]
    mes_aberto, ja_chegou = serie.parcial
    colunas = len(meses) + 2
    esq, dir_, topo, base = 8, 8, 78, 54
    vao = (largura - esq - dir_) / colunas
    espessura = vao * 0.58
    chao = altura - base
    maximo = max([v for _, v in meses] + [corrente.p90, proximo.p90, ja_chegou]) or 1

    def y(valor: float) -> float:
        return chao - valor * (chao - topo) / maximo

    def centro(i: int) -> float:
        return esq + vao * (i + 0.5)

    corpo: list[str] = []
    for i, (mes, valor) in enumerate(meses):
        cx = centro(i)
        corpo.append(_retangulo(cx - espessura / 2, y(valor), espessura, chao - y(valor), PASSADO,
                                dica=f"{_nome_mes(mes)}: {valor} reclamações"))
        corpo.append(_texto(cx, y(valor) - 8, str(valor), tamanho=fonte, peso=600))
        corpo.append(_texto(cx, chao + 20, MESES_CURTOS[mes.month - 1], tamanho=fonte, cor=MUDO))
        if i == 0 or mes.month == 1:
            corpo.append(_texto(cx, chao + 38, str(mes.year), tamanho=fonte - 1, cor=MUDO))

    for indice, (previsao, parcial) in enumerate(((corrente, ja_chegou), (proximo, None))):
        i = len(meses) + indice
        cx = centro(i)
        # Faixa clara do mínimo ao máximo, um pouco mais larga que a coluna.
        corpo.append(_retangulo(cx - espessura / 2 - 6, y(previsao.p90), espessura + 12,
                                y(previsao.p10) - y(previsao.p90), ACENTO_CLARO, raio=4))
        if parcial is not None:
            corpo.append(_retangulo(cx - espessura / 2, y(previsao.p50), espessura,
                                    y(parcial) - y(previsao.p50), FUNDO, contorno=ACENTO,
                                    tracejado=True,
                                    dica=f"Devem chegar mais {previsao.p50 - parcial} até o fim do mês"))
            corpo.append(_retangulo(cx - espessura / 2, y(parcial), espessura, chao - y(parcial),
                                    PASSADO, dica=f"Chegaram {parcial} até hoje"))
        else:
            corpo.append(_retangulo(cx - espessura / 2, y(previsao.p50), espessura,
                                    chao - y(previsao.p50), ACENTO,
                                    dica=f"Cerca de {previsao.p50}, entre {previsao.p10} e {previsao.p90}"))
        corpo.append(_texto(cx, y(previsao.p90) - 26, f"≈ {previsao.p50}", tamanho=fonte + 1, peso=700))
        corpo.append(_texto(cx, y(previsao.p90) - 8, f"{previsao.p10} a {previsao.p90}", tamanho=fonte,
                            cor=MUDO))
        corpo.append(_texto(cx, chao + 20, MESES_CURTOS[previsao.mes.month - 1], tamanho=fonte,
                            cor=MUDO))
        if parcial is not None:
            corpo.append(_texto(cx, chao + 38, f"até hoje {parcial}", tamanho=fonte - 1, cor=MUDO))
        elif previsao.mes.month == 1:
            corpo.append(_texto(cx, chao + 38, str(previsao.mes.year), tamanho=fonte - 1, cor=MUDO))

    # Onde o passado acaba e a estimativa começa.
    corte = esq + vao * len(meses)
    corpo.append(f'<line x1="{corte:.1f}" x2="{corte:.1f}" y1="14" y2="{chao:.1f}" '
                 f'stroke="{PASSADO}" stroke-width="1" stroke-dasharray="4 4"/>')
    corpo.append(_texto(corte + vao, 22, "estimativa", tamanho=fonte, cor=ACENTO, peso=600))
    corpo.append(f'<line x1="{8:.1f}" x2="{largura - 8:.1f}" y1="{chao:.1f}" y2="{chao:.1f}" '
                 f'stroke="{TINTA}" stroke-width="1"/>')
    return _svg(largura, altura, titulo, corpo, classe)


def _nome_mes(mes: date) -> str:
    return f"{MESES_CURTOS[mes.month - 1]}/{mes.year}"


# ------------------------------------------------------------ assuntos do mês

def barras_assuntos(itens: Sequence[tuple[str, int, int]], titulo: str, mes_anterior: str) -> Markup:
    """Uma barra por assunto. Cada item: (nome, quantidade, diferença para o mês anterior)."""
    return _duas_versoes(
        _barras_assuntos_largo(itens, titulo, mes_anterior),
        _barras_assuntos_estreito(itens, titulo),
    )


def _diferenca_curta(diferenca: int) -> str:
    if diferenca > 0:
        return f"▲ {diferenca} a mais"
    if diferenca < 0:
        return f"▼ {abs(diferenca)} a menos"
    return "= igual"


def _barras_assuntos_largo(itens, titulo, mes_anterior) -> Markup:
    largura, esq, dir_, passo, espessura = 720, 130, 250, 46, 26
    altura = passo * len(itens) + 12
    maior = max(v for _, v, _ in itens) or 1
    escala = (largura - esq - dir_) / maior
    corpo = []
    for i, (nome, valor, diferenca) in enumerate(itens):
        y = 8 + i * passo
        cor = LARANJA if diferenca > 0 else PASSADO
        corpo.append(_texto(esq - 14, y + espessura - 7, nome, tamanho=15, ancora="end"))
        corpo.append(_retangulo(esq, y, max(valor * escala, 2), espessura, cor,
                                dica=f"{nome}: {valor} reclamações"))
        texto = f"{valor} · {_diferenca_curta(diferenca)} que {mes_anterior}"
        corpo.append(_texto(esq + valor * escala + 10, y + espessura - 7, texto, tamanho=14,
                            ancora="start", peso=600))
    return _svg(largura, int(altura), titulo, corpo, "grafico__svg grafico__svg--largo")


def _barras_assuntos_estreito(itens, titulo) -> Markup:
    largura, esq, passo, espessura = 360, 8, 62, 22
    altura = passo * len(itens) + 6
    maior = max(v for _, v, _ in itens) or 1
    escala = (largura - 2 * esq) / maior
    corpo = []
    for i, (nome, valor, diferenca) in enumerate(itens):
        y = 6 + i * passo
        cor = LARANJA if diferenca > 0 else PASSADO
        corpo.append(_texto(esq, y + 16, nome, tamanho=16, ancora="start", peso=600))
        corpo.append(_texto(largura - esq, y + 16, f"{valor} · {_diferenca_curta(diferenca)}",
                            tamanho=15, ancora="end"))
        corpo.append(_retangulo(esq, y + 26, max(valor * escala, 2), espessura, cor,
                                dica=f"{nome}: {valor} reclamações"))
    return _svg(largura, int(altura), titulo, corpo, "grafico__svg grafico__svg--estreito")


# ------------------------------------------------------------ duas colunas

def duas_colunas(rotulo_a: str, valor_a: float, rotulo_b: str, valor_b: float, unidade: str,
                 titulo: str, sentido: str = "neutro") -> Markup:
    """Compara dois números: antes e depois, ou dias sem e dias com a mudança.

    `sentido` diz se o segundo número é ruim ("piorou", laranja) ou bom
    ("melhorou", azul-petróleo). O primeiro é sempre cinza.
    """
    largura, altura, chao, topo = 360, 230, 168, 56
    maior = max(valor_a, valor_b) or 1
    cor_b = {"piorou": LARANJA, "melhorou": ACENTO}.get(sentido, ACENTO)
    corpo = []
    for i, (rotulo, valor, cor) in enumerate(((rotulo_a, valor_a, PASSADO), (rotulo_b, valor_b, cor_b))):
        cx = 90 + i * 180
        topo_barra = chao - valor * (chao - topo) / maior
        corpo.append(_retangulo(cx - 45, topo_barra, 90, chao - topo_barra, cor,
                                dica=f"{rotulo}: {_numero(valor)} {unidade}"))
        corpo.append(_texto(cx, topo_barra - 26, _numero(valor), tamanho=20, peso=700))
        corpo.append(_texto(cx, topo_barra - 8, unidade, tamanho=15, cor=MUDO))
        corpo.append(_texto(cx, chao + 24, rotulo, tamanho=15, cor=MUDO))
    corpo.append(f'<line x1="10" x2="350" y1="{chao}" y2="{chao}" stroke="{TINTA}" stroke-width="1"/>')
    return _svg(largura, altura, titulo, corpo, "grafico__svg grafico__svg--pequeno")


def _numero(valor: float) -> str:
    if float(valor).is_integer():
        return str(int(valor))
    return f"{valor:.1f}".replace(".", ",")


# ------------------------------------------------------------ simulador

def comparacao_cenario(atual: float, cenario: float, minimo: float, maximo: float, titulo: str) -> Markup:
    """Hoje contra a mudança, com a faixa do mínimo ao máximo em volta da estimativa."""
    largura, altura, chao, topo = 360, 250, 186, 66
    maior = max(atual, maximo) or 1

    def y(valor: float) -> float:
        return chao - valor * (chao - topo) / maior

    corpo = [
        _retangulo(45, y(atual), 90, chao - y(atual), PASSADO, dica=f"Hoje: {round(atual)} por mês"),
        _texto(90, y(atual) - 26, str(round(atual)), tamanho=20, peso=700),
        _texto(90, y(atual) - 8, "por mês", tamanho=15, cor=MUDO),
        _texto(90, chao + 24, "hoje", tamanho=15, cor=MUDO),
        _retangulo(219, y(maximo), 102, y(minimo) - y(maximo), ACENTO_CLARO, raio=4),
        _retangulo(225, y(cenario), 90, chao - y(cenario), ACENTO,
                   dica=f"Com a mudança: cerca de {round(cenario)}, entre {round(minimo)} e {round(maximo)}"),
        _texto(270, y(maximo) - 26, f"≈ {round(cenario)}", tamanho=20, peso=700),
        _texto(270, y(maximo) - 8, f"{round(minimo)} a {round(maximo)}", tamanho=15, cor=MUDO),
        _texto(270, chao + 24, "com a mudança", tamanho=15, cor=MUDO),
        f'<line x1="10" x2="350" y1="{chao}" y2="{chao}" stroke="{TINTA}" stroke-width="1"/>',
    ]
    return _svg(largura, altura, titulo, corpo, "grafico__svg grafico__svg--pequeno")


# ------------------------------------------------------------ "Dá para confiar?"

def _boneco(x: float, cheio: bool) -> str:
    cor = ACENTO if cheio else FUNDO
    contorno = ACENTO if cheio else PASSADO
    return (
        f'<circle cx="{x + 14:.1f}" cy="14" r="7" fill="{cor}" stroke="{contorno}" stroke-width="2"/>'
        f'<path d="M{x + 2:.1f},44 Q{x + 2:.1f},25 {x + 14:.1f},25 Q{x + 26:.1f},25 {x + 26:.1f},44 Z" '
        f'fill="{cor}" stroke="{contorno}" stroke-width="2"/>'
    )


def pictograma(acertos: int, titulo: str, total: int = 10) -> Markup:
    """Dez bonecos: os cheios são os acertos."""
    largura, altura = 350, 50
    corpo = [_boneco(i * 35, i < acertos) for i in range(total)]
    return _svg(largura, altura, titulo, corpo, "grafico__svg grafico__svg--pictograma")


def barras_acerto(itens: Sequence[tuple[str, int]], titulo: str) -> Markup:
    """Por assunto: de cada 100 vezes que o sistema diz esse assunto, quantas acerta."""
    largura, esq, passo, espessura = 360, 8, 58, 18
    altura = passo * len(itens) + 6
    corpo = []
    for i, (nome, de_cada_cem) in enumerate(itens):
        y = 6 + i * passo
        util = largura - 2 * esq
        corpo.append(_texto(esq, y + 16, nome, tamanho=16, ancora="start", peso=600))
        corpo.append(_texto(largura - esq, y + 16, f"acerta {de_cada_cem} de cada 100", tamanho=15,
                            ancora="end"))
        corpo.append(_retangulo(esq, y + 26, util, espessura, PASSADO_CLARO, raio=4))
        corpo.append(_retangulo(esq, y + 26, util * de_cada_cem / 100, espessura, ACENTO, raio=4,
                                dica=f"{nome}: acerta {de_cada_cem} de cada 100"))
    return _svg(largura, int(altura), titulo, corpo, "grafico__svg grafico__svg--medio")


def previsto_realizado(pontos: Sequence[tuple[date, int, int]], titulo: str) -> Markup:
    """Mês a mês: o que o sistema disse antes (azul-petróleo) e o que aconteceu (cinza)."""
    return _duas_versoes(
        _previsto_realizado(pontos, titulo, 720, 13, "grafico__svg grafico__svg--largo"),
        _previsto_realizado(pontos, titulo, 360, 14, "grafico__svg grafico__svg--estreito"),
    )


def _previsto_realizado(pontos, titulo, largura, fonte, classe) -> Markup:
    estreito = largura <= 400
    # No celular a identificação vai em duas linhas, para não encavalar.
    altura, chao, topo, esq = (300, 230, 74, 8) if estreito else (280, 210, 52, 8)
    vao = (largura - 2 * esq) / len(pontos)
    barra = min(30.0, vao * 0.36)
    maior = max(max(p, r) for _, p, r in pontos) or 1

    def y(valor: float) -> float:
        return chao - valor * (chao - topo) / maior

    # Duas colunas por mês pedem uma identificação; ela fica escrita no topo, colada no desenho.
    x2, y2 = (esq, 30) if estreito else (esq + 210, 6)
    corpo = [
        _retangulo(esq, 6, 14, 14, ACENTO, raio=2),
        _texto(esq + 20, 18, "o que o sistema disse antes", tamanho=fonte, ancora="start"),
        _retangulo(x2, y2, 14, 14, PASSADO, raio=2),
        _texto(x2 + 20, y2 + 12, "o que aconteceu", tamanho=fonte, ancora="start"),
    ]
    for i, (mes, previsto, realizado) in enumerate(pontos):
        cx = esq + vao * (i + 0.5)
        for deslocamento, valor, cor, nome in ((-barra / 2 - 1, previsto, ACENTO, "disse"),
                                               (barra / 2 + 1, realizado, PASSADO, "aconteceu")):
            x = cx + deslocamento
            corpo.append(_retangulo(x - barra / 2, y(valor), barra, chao - y(valor), cor,
                                    dica=f"{_nome_mes(mes)}: {nome} {valor}"))
            corpo.append(_texto(x, y(valor) - 7, str(valor), tamanho=fonte, peso=600))
        corpo.append(_texto(cx, chao + 20, MESES_CURTOS[mes.month - 1], tamanho=fonte, cor=MUDO))
        erro = abs(previsto - realizado)
        corpo.append(_texto(cx, chao + 40, "acertou" if erro == 0 else f"errou {erro}",
                            tamanho=fonte, cor=MUDO))
    corpo.append(f'<line x1="{esq}" x2="{largura - esq}" y1="{chao}" y2="{chao}" '
                 f'stroke="{TINTA}" stroke-width="1"/>')
    return _svg(largura, altura, titulo, corpo, classe)


# ------------------------------------------------------------ cartão do Resumo

def mini_colunas(pontos: Sequence[tuple[date, int]], titulo: str) -> Markup:
    """Seis colunas pequenas, com o primeiro e o último mês escritos. Tamanho fixo."""
    largura, altura, chao = 240, 74, 50
    vao = largura / len(pontos)
    maior = max(v for _, v in pontos) or 1
    corpo = []
    for i, (mes, valor) in enumerate(pontos):
        topo = chao - valor * 34 / maior
        ultimo = i == len(pontos) - 1
        corpo.append(_retangulo(i * vao + vao * 0.2, topo, vao * 0.6, chao - topo,
                                TINTA if ultimo else PASSADO, raio=2,
                                dica=f"{_nome_mes(mes)}: {valor}"))
        if i in (0, len(pontos) - 1):
            corpo.append(_texto(i * vao + vao / 2, altura - 6, MESES_CURTOS[mes.month - 1],
                                tamanho=12, cor=MUDO))
    return Markup(
        f'<svg class="mini-colunas" width="{largura}" height="{altura}" viewBox="0 0 {largura} {altura}" '
        f'role="img" aria-label="{escape(titulo)}" xmlns="http://www.w3.org/2000/svg">'
        f"<title>{escape(titulo)}</title>{''.join(corpo)}</svg>"
    )
