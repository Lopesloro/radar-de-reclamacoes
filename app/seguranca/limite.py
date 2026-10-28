"""Limite de tentativas de entrada por origem, numa janela de tempo que desliza."""

from __future__ import annotations

import ipaddress
import threading
import time
from collections.abc import Callable

TENTATIVAS_MAXIMAS = 8
JANELA_SEGUNDOS = 300


def origem_de(host: str | None) -> str:
    """IPv6 conta pelo bloco /64: quem recebe um IPv6 recebe milhões de endereços e trocaria de origem."""
    if not host:
        return "desconhecida"
    try:
        endereco = ipaddress.ip_address(host)
    except ValueError:
        return host
    if endereco.version == 6:
        return str(ipaddress.ip_network(f"{endereco}/64", strict=False))
    return str(endereco)


class LimiteDeTentativas:
    """Guarda em memória: reiniciar o servidor zera a contagem, o que serve a um bloqueio temporário."""

    def __init__(
        self,
        maximo: int = TENTATIVAS_MAXIMAS,
        janela: float = JANELA_SEGUNDOS,
        relogio: Callable[[], float] = time.monotonic,
        origens_guardadas: int = 10_000,
    ):
        self._maximo = maximo
        self._janela = janela
        self._relogio = relogio
        self._origens_guardadas = origens_guardadas
        self._falhas: dict[str, list[float]] = {}
        self._trava = threading.Lock()

    def __len__(self) -> int:
        return len(self._falhas)

    def _recentes(self, origem: str) -> list[float]:
        corte = self._relogio() - self._janela
        return [t for t in self._falhas.get(origem, []) if t > corte]

    def bloqueada(self, origem: str) -> bool:
        with self._trava:
            return len(self._recentes(origem)) >= self._maximo

    def registrar_falha(self, origem: str) -> None:
        with self._trava:
            if len(self._falhas) >= self._origens_guardadas:
                self._varrer()
            self._falhas[origem] = [*self._recentes(origem), self._relogio()]

    def _varrer(self) -> None:
        """Esquece quem já saiu da janela, para um enxame de origens não encher a memória."""
        vivas = {o: r for o in self._falhas if (r := self._recentes(o))}
        self._falhas = vivas
