"""Avaliações rotuladas para treinar e conferir o classificador.

As frases saem de `app/falsos.py` — a especificação viva do que a tela já
consome — e passam por uma bagunça determinística: tira uma palavra, embaralha,
mistura enchimento. Sem isso o teste mediria um problema mais fácil que o real,
porque cada assunto teria um punhado de frases sempre idênticas.

Determinístico de propósito: mesma semente, mesmos números, teste sem sorte.
"""

from __future__ import annotations

import random

from app import falsos
from app.contratos import CATEGORIAS

SEMENTE = 7
VARIACOES = 20

# Palavras que aparecem em qualquer assunto: servem para o modelo não poder se
# apoiar em "a frase tem tamanho X".
ENCHIMENTO = (
    "olha", "pra ser sincero", "fui hoje", "enfim", "no fim das contas",
    "já é a segunda vez", "fica a dica",
)


def _frases_por_assunto() -> dict[str, tuple[str, ...]]:
    """As frases base de cada assunto, com as da história de cada negócio."""
    por_assunto = {categoria: falsos.FRASES[categoria] for categoria in CATEGORIAS}
    for identificador, *_, categoria, _, _ in falsos.EMPRESAS:
        por_assunto[categoria] += falsos.FRASES_DA_HISTORIA[identificador]
    return por_assunto


def _variar(texto: str, sorteio: random.Random) -> str:
    palavras = texto.rstrip(".").split()
    if len(palavras) > 4 and sorteio.random() < 0.5:
        palavras.pop(sorteio.randrange(len(palavras)))
    if sorteio.random() < 0.5:
        palavras.insert(sorteio.choice((0, len(palavras))), sorteio.choice(ENCHIMENTO))
    return " ".join(palavras) + "."


def _variacoes(frase: str, categoria: str,
               sorteio: random.Random) -> list[tuple[str, str]]:
    return [(_variar(frase, sorteio), categoria) for _ in range(VARIACOES)]


def rotuladas() -> tuple[tuple[str, str], ...]:
    """(texto, assunto), o corpo inteiro. Desbalanceado: é como o dado real chega."""
    sorteio = random.Random(SEMENTE)
    return tuple(
        item
        for categoria, frases in _frases_por_assunto().items()
        for frase in frases
        for item in _variacoes(frase, categoria, sorteio)
    )


def separar() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Treino e teste separados por FRASE BASE, nunca por variação.

    Separar por variação deixaria quase a mesma frase dos dois lados e o F1 sairia
    perto de 1 sem o modelo ter aprendido nada: a mesma armadilha de sortear o mês
    de teste na previsão. Aqui uma frase base inteira, com todas as suas variações,
    fica só de um lado. Uma de cada quatro frases de cada assunto vai para o teste.
    """
    sorteio = random.Random(SEMENTE)
    treino: list[tuple[str, str]] = []
    teste: list[tuple[str, str]] = []
    for categoria, frases in _frases_por_assunto().items():
        for posicao, frase in enumerate(frases):
            destino = teste if posicao % 4 == 0 else treino
            destino += _variacoes(frase, categoria, sorteio)
    return treino, teste


def sem_assunto() -> tuple[str, ...]:
    """Elogio e frase vaga: não é reclamação de assunto nenhum, o certo é abster-se."""
    sorteio = random.Random(SEMENTE + 1)
    return tuple(
        _variar(frase, sorteio)
        for frase in falsos.ELOGIOS + falsos.VAGAS
        for _ in range(10)
    )
