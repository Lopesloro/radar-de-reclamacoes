"""Leitura das avaliações públicas: o que entra no sistema, e de onde.

O formato de entrada é um só, `AvaliacaoBruta`, e cada plataforma tem um módulo
que traduz a resposta dela para esse formato. O resto do sistema não sabe de que
plataforma a avaliação veio — e é isso que deixa somar Google e iFood na mesma
série sem duplicar código de contagem.

As plataformas estão em `docs/fontes-de-avaliacao.md`, com o que cada uma exige
para liberar o acesso.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


class ErroDeFonte(RuntimeError):
    """A fonte não entregou o que prometeu. A mensagem vai para a tela da fonte."""


@dataclass(frozen=True)
class AvaliacaoBruta:
    """Uma avaliação como a plataforma entregou, antes de mascarar e classificar.

    `id_origem` é o identificador que a plataforma deu. É ele, junto com o
    negócio, que impede a mesma avaliação de ser contada duas vezes quando a
    coleta roda de novo — a unicidade está no banco, não na boa vontade do
    código de coleta.
    """

    id_origem: str
    data: date
    estrelas: int
    texto: str | None

    def __post_init__(self) -> None:
        if not self.id_origem:
            raise ValueError("avaliação sem identificador de origem")
        if not 1 <= self.estrelas <= 5:
            raise ValueError(f"estrelas fora de 1 a 5: {self.estrelas}")
