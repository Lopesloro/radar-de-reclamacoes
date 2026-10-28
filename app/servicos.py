"""A única porta que as telas usam para pedir dados.

Hoje tudo vem de `app.falsos`. Quando uma parte real ficar pronta, troque só a
linha da função correspondente; as rotas e os templates não mudam. Exemplo: o
Gabriel termina o motor e `investigar` passa a chamar
`app.investigacao.motor.investigar(sessao, ...)`.
"""

from __future__ import annotations

from app import falsos
from app.contratos import (
    AcuraciaClassificacao,
    AcuraciaPrevisao,
    Alerta,
    AvaliacaoTela,
    Cenario,
    EtapaParceiro,
    EventoDiario,
    Investigacao,
    MarcacaoDia,
    PlanoExperimento,
    ResultadoExperimento,
    ResultadoLaboratorio,
    ResultadoSimulacao,
    ResumoComercio,
    SerieMensal,
    Turno,
)

# Dados de demonstração: enquanto for verdade, a faixa de aviso aparece em toda tela.
DADOS_DE_DEMONSTRACAO = True
HOJE = falsos.HOJE


def existe(empresa_id: str) -> bool:
    return falsos.existe(empresa_id)


def comercios(empresa_id: str) -> tuple[ResumoComercio, ...]:
    """Os negócios da empresa. O parâmetro é obrigatório de propósito: sem ele,
    a tela lista o negócio dos outros, e já listou."""
    return tuple(c for c in falsos.comercios() if c.empresa_id == empresa_id)


def quantos_negocios() -> int:
    """Só a contagem, para a página pública, que não tem sessão nem dado de ninguém."""
    return len(falsos.comercios())


def comercio(empresa_id: str) -> ResumoComercio | None:
    return falsos.comercio(empresa_id)


def series(empresa_id: str) -> tuple[SerieMensal, ...]:
    return falsos.series(empresa_id)


def serie(empresa_id: str, categoria: str) -> SerieMensal:
    return falsos.serie(empresa_id, categoria)


def avaliacoes(empresa_id: str, limite: int = 12) -> tuple[AvaliacaoTela, ...]:
    return falsos.avaliacoes(empresa_id, limite)


def alertas(empresa_id: str) -> tuple[Alerta, ...]:
    return tuple(a for a in falsos.alertas() if a.empresa_id == empresa_id)


def acuracia_classificacao() -> AcuraciaClassificacao:
    return falsos.acuracia_classificacao()


def acuracia_previsao() -> AcuraciaPrevisao:
    return falsos.acuracia_previsao()


def etapas(empresa_id: str) -> tuple[EtapaParceiro, ...]:
    return falsos.etapas(empresa_id)


def investigar(empresa_id: str, categoria: str, alerta_id: str | None = None) -> Investigacao:
    return falsos.investigar(None, empresa_id, categoria, alerta_id)


def eventos_diario(empresa_id: str) -> tuple[EventoDiario, ...]:
    return falsos.eventos_diario(empresa_id)


def operacao(empresa_id: str) -> tuple[Turno, ...]:
    return falsos.operacao(empresa_id)


def simular(empresa_id: str, cenario: Cenario) -> ResultadoSimulacao:
    return falsos.simular(None, empresa_id, cenario)


def cenario_sugerido(investigacao: Investigacao) -> Cenario | None:
    return falsos.cenario_sugerido(investigacao)


def experimentos(empresa_id: str) -> tuple[PlanoExperimento, ...]:
    return falsos.experimentos(empresa_id)


def experimento(plano_id: str) -> PlanoExperimento | None:
    return falsos.experimento(plano_id)


def marcacoes(plano_id: str) -> tuple[MarcacaoDia, ...]:
    return falsos.marcacoes(plano_id)


def analisar(plano_id: str) -> ResultadoExperimento | None:
    return falsos.analisar(None, plano_id)


def laboratorio() -> ResultadoLaboratorio:
    return falsos.laboratorio()
