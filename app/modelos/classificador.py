"""Separa o texto da avaliação em um dos cinco assuntos — ou se abstém.

Abster-se é resposta: quando a confiança fica abaixo de `LIMITE_CONFIANCA`, o
modelo devolve `None` e a tela mostra "sem assunto" com o motivo, em vez de
chutar um assunto errado e o dono tomar decisão em cima disso.

A medida é F1 por assunto e F1 macro, sempre ao lado da régua: responder sempre
o assunto mais comum. A abstenção conta como erro na medida — é o jeito honesto,
senão bastaria abster-se das difíceis para o F1 subir.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_recall_fscore_support

from app.contratos import CATEGORIAS, AcuraciaClassificacao, LinhaAcerto
from app.modelos import LIMITE_CONFIANCA

SEMENTE = 11
# Palavra e par de palavras: "muito tempo" e "mais caro" valem mais que as soltas.
JANELA_DE_PALAVRAS = (1, 2)


@dataclass(frozen=True)
class Classificador:
    """Um modelo treinado. `prever` devolve (assunto ou None, confiança)."""

    vetor: TfidfVectorizer
    regressao: LogisticRegression

    def prever(self, texto: str, limite: float = LIMITE_CONFIANCA) -> tuple[str | None, float]:
        return self.prever_muitos([texto], limite)[0]

    def prever_muitos(self, textos: Sequence[str],
                      limite: float = LIMITE_CONFIANCA) -> list[tuple[str | None, float]]:
        """A decisão de abster-se vive só aqui. `prever` passa por este caminho.

        Era escrita em dois lugares, e a cópia esconde defeito: um teste que
        sabotava `prever` passava porque a medição usava a outra.
        """
        chances = self.regressao.predict_proba(self.vetor.transform(list(textos)))
        respostas = []
        for linha in chances:
            melhor = int(linha.argmax())
            confianca = float(linha[melhor])
            respostas.append(
                (None, confianca) if confianca < limite
                else (str(self.regressao.classes_[melhor]), confianca)
            )
        return respostas


def treinar(amostras: Sequence[tuple[str, str]]) -> Classificador:
    textos = [texto for texto, _ in amostras]
    assuntos = [assunto for _, assunto in amostras]
    vetor = TfidfVectorizer(ngram_range=JANELA_DE_PALAVRAS, sublinear_tf=True, min_df=1)
    matriz = vetor.fit_transform(textos)
    regressao = LogisticRegression(max_iter=2000, C=4.0, random_state=SEMENTE)
    regressao.fit(matriz, assuntos)
    return Classificador(vetor, regressao)


def medir(modelo: Classificador,
          amostras: Sequence[tuple[str, str]]) -> AcuraciaClassificacao:
    """F1 por assunto, F1 macro e o mesmo par para a régua."""
    verdadeiros = [assunto for _, assunto in amostras]
    # Abstenção entra como "" — nunca igual a um assunto, então conta como erro.
    respondidos = [a or "" for a, _ in modelo.prever_muitos([t for t, _ in amostras])]

    precisao, recall, f1, apoio = precision_recall_fscore_support(
        verdadeiros, respondidos, labels=list(CATEGORIAS), zero_division=0
    )
    linhas = tuple(
        LinhaAcerto(categoria, round(float(p), 3), round(float(r), 3), round(float(f), 3), int(n))
        for categoria, p, r, f, n in zip(CATEGORIAS, precisao, recall, f1, apoio, strict=True)
    )

    # A régua: responder sempre o assunto mais comum do conjunto.
    comuns = Counter(verdadeiros)
    categoria_regua = min(comuns, key=lambda c: (-comuns[c], c))
    regua = [categoria_regua] * len(verdadeiros)

    certos = sum(1 for v, r in zip(verdadeiros, respondidos, strict=True) if v == r)
    return AcuraciaClassificacao(
        linhas=linhas,
        acerto_geral=round(certos / len(verdadeiros), 3),
        acerto_regua=round(comuns[categoria_regua] / len(verdadeiros), 3),
        f1_macro=round(float(f1_score(verdadeiros, respondidos, labels=list(CATEGORIAS),
                                      average="macro", zero_division=0)), 3),
        f1_macro_regua=round(float(f1_score(verdadeiros, regua, labels=list(CATEGORIAS),
                                            average="macro", zero_division=0)), 3),
        amostra=len(verdadeiros),
        categoria_regua=categoria_regua,
    )
