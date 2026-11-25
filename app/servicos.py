"""A única porta que as telas usam para pedir dados.

Tudo vem do banco. A versão anterior do projeto tinha um gerador de avaliações
fictícias (`app/falsos.py`) que as telas liam direto, e ele foi removido. O que a
tela mostra agora veio de uma avaliação pública lida de uma plataforma, do que o
dono cadastrou, ou não existe — e quando não existe, a tela diz isso em uma
frase. A única exceção é a conta de demonstração: o banco dela é preenchido por
`app/coleta/simulado.py`, pelo mesmo motor, e toda tela dela avisa.

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
    """Os cartões do Resumo. Só negócio com pelo menos um mês fechado entra aqui."""
    with _aberta() as sessao:
        return () if sessao is None else consultas.comercios(sessao, empresa_id)


def negocios_cadastrados(empresa_id: str) -> tuple[tuple[str, str, str], ...]:
    """(id, nome, cidade) de todo negócio da empresa, com dado ou sem.

    Existe porque `comercios()` devolve só quem tem mês fechado, e a tela do vazio
    precisa saber a diferença entre "você não tem negócio ligado" e "o seu negócio
    está ligado e as avaliações ainda não chegaram". Com uma função só, um cliente
    recém-cadastrado lia na tela que não tinha negócio nenhum, o que era falso."""
    with _aberta() as sessao:
        return () if sessao is None else consultas.negocios_cadastrados(sessao, empresa_id)


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


# ------------------------------------------------------------ Por quê?, E se? e Testes
#
# As três telas que saíram com o gerador de dados fictícios e voltaram com motor
# de verdade. O que elas leem é o que o dono cadastrou (diário, turnos, plano do
# teste) e as avaliações já classificadas. As contas estão em app/modelos/.

def e_demonstracao(empresa_id: str) -> bool:
    """Conta de demonstração: as avaliações e os cadastros dela foram simulados."""
    from app.banco import modelo

    with _aberta() as sessao:
        if sessao is None:
            return False
        empresa = sessao.get(modelo.Empresa, empresa_id)
        return bool(empresa and empresa.plano == "demonstracao")


def eventos_diario(empresa_id: str, comercio_id: str):
    from app.banco import analises

    with _aberta() as sessao:
        return () if sessao is None else analises.eventos(sessao, empresa_id, comercio_id)


def investigar(empresa_id: str, comercio_id: str, categoria: str):
    from app.banco import analises
    from app.modelos import causas

    with _aberta() as sessao:
        avaliacoes = ([] if sessao is None
                      else analises.avaliacoes_classificadas(sessao, empresa_id, comercio_id))
        eventos = () if sessao is None else analises.eventos(sessao, empresa_id, comercio_id)
    return causas.investigar(avaliacoes, eventos, categoria, hoje(), empresa_id=empresa_id)


def turnos(empresa_id: str, comercio_id: str):
    from app.banco import analises

    with _aberta() as sessao:
        return () if sessao is None else analises.turnos(sessao, empresa_id, comercio_id)


def simular(empresa_id: str, comercio_id: str, cenario):
    from app.banco import analises
    from app.modelos import fila

    with _aberta() as sessao:
        lista = () if sessao is None else analises.turnos(sessao, empresa_id, comercio_id)
        reclamacoes = 0.0 if sessao is None else analises.reclamacoes_por_mes(
            sessao, empresa_id, comercio_id, cenario.categoria)
    return fila.simular(lista, cenario, reclamacoes)


def experimentos(empresa_id: str):
    """Os testes da empresa: tuplas (plano, negócio)."""
    from app.banco import analises

    with _aberta() as sessao:
        return () if sessao is None else analises.planos(sessao, empresa_id, hoje())


def experimento(empresa_id: str, plano_id: str):
    """(plano, negócio) ou None. Plano de outra empresa também é None."""
    from app.banco import analises

    with _aberta() as sessao:
        return None if sessao is None else analises.plano(sessao, empresa_id, plano_id, hoje())


def marcacoes(empresa_id: str, plano_id: str):
    from app.banco import analises
    from app.modelos import experimento as teste

    with _aberta() as sessao:
        if sessao is None:
            return ()
        achado = analises.plano(sessao, empresa_id, plano_id, hoje())
        if achado is None:
            return ()
        return teste.marcacoes(achado[0], analises.marcadas(sessao, empresa_id, plano_id))


def analisar(empresa_id: str, plano_id: str):
    """O resultado do teste até hoje, e o p-valor para o bloco técnico. (None, None) se ainda não há dias."""
    from app.banco import analises
    from app.modelos import experimento as teste

    with _aberta() as sessao:
        if sessao is None:
            return None, None
        achado = analises.plano(sessao, empresa_id, plano_id, hoje())
        if achado is None:
            return None, None
        plano, comercio_id = achado
        datas = analises.datas_das_reclamacoes(sessao, empresa_id, comercio_id, plano.categoria,
                                               plano.inicio, plano.fim)
        marcadas = analises.marcadas(sessao, empresa_id, plano_id)
    return (teste.analisar(plano, marcadas, datas, hoje()), teste.p_valor(plano, datas, hoje()))


def reclamacoes_por_dia(empresa_id: str, comercio_id: str, categoria: str) -> float:
    """Média de reclamações do assunto por dia nos últimos três meses fechados."""
    from app.banco import analises

    with _aberta() as sessao:
        if sessao is None:
            return 0.0
        return analises.reclamacoes_por_mes(sessao, empresa_id, comercio_id, categoria) / 30
