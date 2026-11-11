"""Quanto o sistema acerta, medido agora e sempre ao lado da régua.

Duas medidas, e as duas comparam com o chute mais simples que existe:

- **Separação por assunto**: F1 macro contra a régua "responder sempre o assunto
  mais comum". A abstenção conta como erro, senão bastaria o modelo abster-se
  das difíceis para o número subir.
- **Estimativa do mês**: erro médio absoluto e cobertura da faixa, por origem
  móvel (treina até o mês k, prevê k+1, anda um mês), contra a régua "o mês que
  vem é igual ao mês passado".

De onde vem o conjunto de conferência da separação, em ordem de preferência:

1. As avaliações que o dono conferiu à mão no sistema (é o rótulo que vale).
   `origem()` devolve "avaliações conferidas pelo dono".
2. Se ainda não houver o mínimo, o conjunto de teste do corpus rotulado da
   equipe. `origem()` devolve "corpus da equipe".

A diferença é importante e a tela mostra qual foi usada: medir no corpus da
equipe mede um problema mais fácil que o real, porque as frases foram escritas
por quem conhece os cinco assuntos.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from functools import lru_cache

from sqlalchemy import select

from app.contratos import AcuraciaClassificacao, AcuraciaPrevisao
from app.modelos import amostras, ativo, classificador, previsao

MINIMO_CONFERIDAS = 30
MARCA_DE_CONFERIDA = "conferida pelo dono"

# Teto de avaliações conferidas que entram numa medida. Com a IA ligada, cada 8
# viram uma chamada de rede, e a medida roda dentro de um pedido web: 60 são 8
# chamadas, que cabem no balde de 12 por minuto e levam poucos segundos, uma vez
# por processo. Duzentas levariam mais de dois minutos e a tela não carregaria.
#
# O preço é uma amostra pequena, e a tela diz o tamanho dela ao lado do número.
# Amostra pequena e dita é honesto; tela que não carrega não é.
MAXIMO_CONFERIDAS_NA_MEDIDA = 60

ORIGEM_DO_DONO = "avaliações conferidas pelo dono"
ORIGEM_DO_CORPUS = "corpus da equipe, medindo o modelo próprio"

_origem = ORIGEM_DO_CORPUS


def origem() -> str:
    """Qual conjunto a última medida usou. A tela mostra esta frase."""
    return _origem


def conferidas_no_banco() -> tuple[tuple[str, str], ...]:
    """(texto, assunto) das avaliações que algum dono conferiu à mão."""
    from app.banco import modelo
    from app.banco import sessao as banco

    if not banco.usar_banco():
        return ()
    with banco.Sessao() as sessao:
        linhas = sessao.execute(
            select(modelo.Avaliacao.texto, modelo.Classificacao.categoria_id)
            .join(modelo.Classificacao,
                  modelo.Classificacao.avaliacao_id == modelo.Avaliacao.id)
            .where(modelo.Classificacao.motivo_sem_assunto == MARCA_DE_CONFERIDA,
                   modelo.Classificacao.categoria_id.is_not(None),
                   modelo.Avaliacao.texto.is_not(None))
        ).all()
    return tuple((texto, categoria) for texto, categoria in linhas if texto)


def acerto_da_separacao() -> AcuraciaClassificacao:
    """Mede o classificador no melhor conjunto disponível, sem derrubar a tela.

    Duas regras de tamanho, e as duas existem porque a medida roda **dentro de um
    pedido web**:

    - No corpus da equipe, a medida é sempre do **modelo local**, nunca da IA. São
      500 frases, que com a IA viram 63 chamadas de rede e mais de cinco minutos:
      a tela estourava o tempo em produção, e o cliente via a página não carregar.
      Medir a IA no corpus também não diria muito, porque o corpus é o conjunto de
      teste do modelo local.
    - Nas avaliações conferidas pelo dono, a medida é do modelo que está no ar,
      porque é a medida que interessa a ele. O teto de
      `MAXIMO_CONFERIDAS_NA_MEDIDA` existe para a tela não ficar mais lenta a cada
      conferência que o dono faz.
    """
    global _origem

    conferidas = conferidas_no_banco()
    if len(conferidas) >= MINIMO_CONFERIDAS:
        _origem = ORIGEM_DO_DONO
        return _medir_nas_conferidas(conferidas[:MAXIMO_CONFERIDAS_NA_MEDIDA])
    _origem = ORIGEM_DO_CORPUS
    return _medir_no_corpus()


@lru_cache(maxsize=4)
def _medir_nas_conferidas(conferidas: tuple[tuple[str, str], ...]) -> AcuraciaClassificacao:
    """Guardada em memória pela própria amostra: conferência nova muda a chave."""
    return classificador.medir(ativo.classificador_em_uso(), conferidas)


@lru_cache(maxsize=1)
def _medir_no_corpus() -> AcuraciaClassificacao:
    """Medida do modelo local no corpus da equipe. Nunca da IA: ver acima."""
    _, teste = amostras.separar()
    return classificador.medir(ativo.local(), teste)


def acerto_da_estimativa(
    series: Sequence[tuple[str, Sequence[tuple[date, int]]]],
) -> AcuraciaPrevisao | None:
    """Origem móvel nas séries reais. None quando nenhuma tem meses suficientes."""
    uteis = [(nome, meses) for nome, meses in series if len(meses) > previsao.MINIMO_TREINO]
    if not uteis:
        return None
    # A mais longa primeiro: é dela que saem os pontos que a tela desenha.
    uteis.sort(key=lambda item: len(item[1]), reverse=True)
    try:
        return previsao.validar(uteis)
    except ValueError:
        return None
