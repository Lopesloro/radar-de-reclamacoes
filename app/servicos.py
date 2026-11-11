"""A única porta que as telas usam para pedir dados.

Tudo vem do banco. Não existe mais dado de demonstração: a versão anterior do
projeto tinha um gerador de avaliações fictícias (`app/falsos.py`) para as telas
poderem nascer antes do motor, e ele foi removido. O que a tela mostra agora ou
veio de uma avaliação pública lida de uma plataforma, ou não existe — e quando
não existe, a tela diz isso em uma frase, em vez de mostrar número inventado.

Três estados possíveis, e cada tela sabe diferenciá-los:

1. **Sem banco** (`DATABASE_URL` vazia): o sistema está de pé mas não guarda
   nada. `tem_banco()` é falso e toda leitura devolve vazio.
2. **Banco vazio para esta empresa**: cliente recém-cadastrado, fonte ainda não
   coletou. `tem_dados(empresa)` é falso.
3. **Com dados**: o caminho normal.

Toda função recebe `empresa_id` (a empresa dona dos dados, que vem da sessão) e,
quando é sobre um negócio, `comercio_id`. Função sem o filtro de empresa é
defeito, não estilo.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date

from app.banco import consultas
from app.banco import sessao as banco
from app.contratos import (
    AcuraciaClassificacao,
    AcuraciaPrevisao,
    Alerta,
    AvaliacaoTela,
    EtapaParceiro,
    ResumoComercio,
    SerieMensal,
)


def hoje() -> date:
    """O dia de hoje, num lugar só, para o teste poder fixá-lo."""
    return date.today()


def tem_banco() -> bool:
    return banco.usar_banco()


@contextmanager
def _aberta():
    """Uma sessão de leitura. Fora do banco, devolve None e quem chamou responde vazio."""
    if not banco.usar_banco():
        yield None
        return
    with banco.Sessao() as sessao:
        yield sessao


def tem_dados(empresa_id: str) -> bool:
    with _aberta() as sessao:
        return False if sessao is None else consultas.tem_avaliacao(sessao, empresa_id)


def ids_de_comercio(empresa_id: str) -> frozenset[str]:
    with _aberta() as sessao:
        return frozenset() if sessao is None else consultas.ids_de_comercio(sessao, empresa_id)


def quantos_negocios() -> int:
    with _aberta() as sessao:
        return 0 if sessao is None else consultas.quantos_negocios(sessao)


# ------------------------------------------------------------ telas do dono

def comercios(empresa_id: str) -> tuple[ResumoComercio, ...]:
    with _aberta() as sessao:
        return () if sessao is None else consultas.comercios(sessao, empresa_id)


def comercio(empresa_id: str, comercio_id: str) -> ResumoComercio | None:
    with _aberta() as sessao:
        return None if sessao is None else consultas.comercio(sessao, empresa_id, comercio_id)


def series(empresa_id: str, comercio_id: str) -> tuple[SerieMensal, ...]:
    with _aberta() as sessao:
        return () if sessao is None else consultas.series(sessao, empresa_id, comercio_id, hoje())


def serie(empresa_id: str, comercio_id: str, categoria: str) -> SerieMensal | None:
    with _aberta() as sessao:
        if sessao is None:
            return None
        return consultas.serie(sessao, empresa_id, comercio_id, categoria, hoje())


def avaliacoes(empresa_id: str, comercio_id: str, limite: int = 12) -> tuple[AvaliacaoTela, ...]:
    with _aberta() as sessao:
        if sessao is None:
            return ()
        return consultas.avaliacoes(sessao, empresa_id, comercio_id, limite)


def alertas(empresa_id: str) -> tuple[Alerta, ...]:
    with _aberta() as sessao:
        return () if sessao is None else consultas.alertas(sessao, empresa_id)


def etapas(empresa_id: str, comercio_id: str) -> tuple[EtapaParceiro, ...]:
    with _aberta() as sessao:
        return () if sessao is None else consultas.etapas(sessao, empresa_id, comercio_id)


# ------------------------------------------------------------ dá para confiar?

def acuracia_classificacao() -> AcuraciaClassificacao:
    """O acerto do classificador que está no ar, medido agora.

    A medida é do conjunto de conferência; `origem_da_medida` diz qual.
    """
    from app.modelos import conferencia

    return conferencia.acerto_da_separacao()


def origem_da_medida() -> str:
    from app.modelos import conferencia

    return conferencia.origem()


def acuracia_previsao(empresa_id: str) -> AcuraciaPrevisao | None:
    """O acerto da estimativa nas séries reais da empresa, por origem móvel.

    None quando nenhuma série da empresa tem meses suficientes: é o caso do
    cliente novo, e a tela diz isso em vez de mostrar erro zero.
    """
    from app.modelos import conferencia

    with _aberta() as sessao:
        if sessao is None:
            return None
        return conferencia.acerto_da_estimativa(consultas.series_fechadas(sessao, empresa_id))
