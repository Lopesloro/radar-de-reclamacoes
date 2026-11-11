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
    ja_chegou = serie.parcial[1]
    # A conclusão não é da IA: ela é a MESMA que a frase determinística usa, e a
    # IA só a reescreve em linguagem de gente. Sem isso as duas discordavam na
    # mesma tela: a frase própria dizia "acima do esperado" e a IA dizia "ainda é
    # normal". Duas conclusões opostas são piores que nenhuma frase, e a saída
    # certa não é afinar o texto do pedido, é tirar a decisão da mão do modelo.
    conclusao = frases.leitura_da_faixa(serie)
    return (
        f"Negócio: {negocio}. Assunto da reclamação: {assunto}. "
        f"No último mês fechado ({mes_fechado:%m/%Y}) chegaram {fechado} reclamações desse "
        f"assunto. Para o mês corrente, a estimativa é de {corrente.p50}, podendo ficar entre "
        f"{corrente.p10} e {corrente.p90}. Até hoje já chegaram {ja_chegou}, e já passou "
        f"{round(serie.parcial_fracao * 100)}% do mês.\n\n"
        f"A conclusão, que você deve manter sem mudar o sentido: {conclusao}\n\n"
        "Reescreva isso em UMA frase, em linguagem de dono de comércio pequeno. "
        "Escreva os números em algarismos, nunca por extenso, e não troque número por "
        "palavra como \"dezenas\". Não acrescente conclusão nenhuma que não esteja acima."
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
