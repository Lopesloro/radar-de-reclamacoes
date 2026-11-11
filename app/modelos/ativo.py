"""Qual classificador está no ar, decidido em tempo de execução.

Com chave de IA configurada, a IA classifica e o modelo local fica de reserva
para quando ela não responder. Sem chave, o modelo local classifica sozinho. O
resto do sistema não pergunta qual é: pede `classificador()` e usa.

O modelo local é treinado uma vez por processo (`@cache`): são ~1300 frases e
leva menos de um segundo, mas treinar em cada pedido web seria um segundo por
pedido.
"""

from __future__ import annotations

from functools import cache

from app.investigacao import ia as _ia
from app.modelos import amostras, classificador
from app.modelos.classificador_ia import ClassificadorIA


@cache
def local() -> classificador.Classificador:
    """O modelo local treinado no corpus rotulado."""
    treino, _ = amostras.separar()
    return classificador.treinar(treino)


def classificador_em_uso():
    cliente = _ia.do_ambiente()
    if cliente is None:
        return local()
    return ClassificadorIA(ia=cliente, reserva=local())


def nome_do_modelo() -> str:
    cliente = _ia.do_ambiente()
    return f"ia:{cliente.nome}" if cliente is not None else "local:tfidf+regressao"


def usando_ia() -> bool:
    return _ia.disponivel()
