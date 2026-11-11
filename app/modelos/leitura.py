"""A frase que explica a estimativa, escrita pela IA quando ela está disponível.

Duas regras que fazem isto ser seguro e barato:

1. **A IA não calcula nada.** Ela recebe os números já prontos (mês fechado,
   mais provável, mínimo, máximo) e escreve uma frase sobre eles. Se a IA
   estiver fora, a frase determinística de `app/graficos/frases.py` entra no
   lugar e a tela não muda de forma.
2. **Uma chamada por mês por assunto.** O resultado fica guardado em memória
   com a chave (negócio, assunto, mês): a mesma tela aberta vinte vezes faz uma
   chamada, não vinte. A conta gratuita da IA tem limite por minuto, e tela de
   produto não pode depender de sorte.

Por que vale uma chamada de IA para uma frase: a frase determinística acerta o
conteúdo mas tem sempre a mesma forma, e o dono de negócio pequeno lê melhor uma
frase escrita em linguagem de gente. O conteúdo é o mesmo; o que muda é a chance
de ele ler até o fim.
"""

from __future__ import annotations

import logging
import threading

from app.graficos import frases
from app.investigacao import ia as _ia

_log = logging.getLogger("radar.leitura")
_guardadas: dict[tuple[str, str, str], str] = {}
_trava = threading.Lock()
LIMITE_DE_GUARDADAS = 500


def _pergunta(negocio: str, assunto: str, serie) -> str:
    corrente = serie.previsoes[0]
    fechado = serie.ultimo
    mes_fechado = serie.meses[-1][0]
    return (
        f"Negócio: {negocio}. Assunto da reclamação: {assunto}. "
        f"No último mês fechado ({mes_fechado:%m/%Y}) chegaram {fechado} reclamações desse "
        f"assunto. Para o mês corrente, a estimativa é de {corrente.p50}, podendo ficar entre "
        f"{corrente.p10} e {corrente.p90}. Até hoje já chegaram {serie.parcial[1]}. "
        "Escreva uma frase dizendo ao dono o que isso quer dizer na prática e se ele precisa "
        "agir agora. Se o número do mês passado cabe dentro da faixa, diga que ainda pode ser "
        "variação normal."
    )


def da_previsao(negocio: str, serie) -> str:
    """A leitura da estimativa. Devolve a frase determinística se a IA não ajudar."""
    reserva = frases.leitura_da_faixa(serie)
    if not serie.previsoes or not _ia.disponivel():
        return reserva

    chave = (negocio, serie.categoria, serie.previsoes[0].mes.isoformat())
    with _trava:
        guardada = _guardadas.get(chave)
    if guardada is not None:
        return guardada

    cliente = _ia.do_ambiente()
    try:
        frase = cliente.explicar(_pergunta(negocio, serie.categoria, serie))
    except Exception:       # noqa: BLE001 - tela não cai por causa da IA
        _log.warning("leitura: a IA não respondeu; usando a frase própria")
        frase = None
    escolhida = frase or reserva
    with _trava:
        if len(_guardadas) > LIMITE_DE_GUARDADAS:
            _guardadas.clear()
        _guardadas[chave] = escolhida
    return escolhida


def esquecer() -> None:
    """Descarta o guardado. Serve ao teste e à troca de modelo."""
    with _trava:
        _guardadas.clear()
