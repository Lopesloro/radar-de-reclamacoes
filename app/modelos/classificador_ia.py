"""O classificador que usa a IA, com a mesma interface do modelo local.

Serve para `app/coleta/motor.py` e para a conferência não precisarem saber qual
dos dois está no ar: os dois respondem `prever_muitos(textos)` e devolvem
`(assunto ou None, confiança)`.

Uma ressalva que vale dizer na tela e na banca: **a confiança que a IA declara
não é probabilidade calibrada**. Nos testes ela responde 1.0 em quase tudo,
inclusive quando erra. Então a abstenção da IA não vem de um limiar de
confiança (como no modelo local) e sim da própria resposta `nenhum`. O número
que diz se dá para confiar é o acerto medido no conjunto de conferência, em
`app/modelos/conferencia.py`, e é esse que aparece em "Dá para confiar?".
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.investigacao.ia import IA
from app.investigacao.protecao import RespostaIA


@dataclass(frozen=True)
class ClassificadorIA:
    ia: IA
    # Quando a IA não responde (rede, limite da conta, formato errado), quem
    # decide é este. Sem reserva, a avaliação fica sem assunto.
    reserva: object | None = None

    @property
    def nome(self) -> str:
        return f"ia:{self.ia.nome}"

    def prever(self, texto: str, limite: float | None = None) -> tuple[str | None, float]:
        return self.prever_muitos([texto], limite)[0]

    def prever_muitos(self, textos: Sequence[str],
                      limite: float | None = None) -> list[tuple[str | None, float]]:
        respostas = self.ia.classificar(list(textos))
        if self.reserva is None:
            return [self._achatar(r) for r in respostas]

        faltando = [i for i, r in enumerate(respostas) if r is None]
        if not faltando:
            return [self._achatar(r) for r in respostas]
        do_local = self.reserva.prever_muitos([textos[i] for i in faltando])
        saida = [self._achatar(r) for r in respostas]
        for posicao, resposta_local in zip(faltando, do_local, strict=True):
            saida[posicao] = resposta_local
        return saida

    def motivos(self, textos: Sequence[str]) -> list[RespostaIA | None]:
        """As respostas inteiras, com o motivo em português. O motor guarda isso."""
        return self.ia.classificar(list(textos))

    @staticmethod
    def _achatar(resposta: RespostaIA | None) -> tuple[str | None, float]:
        if resposta is None:
            return (None, 0.0)
        return (resposta.assunto, resposta.confianca)
