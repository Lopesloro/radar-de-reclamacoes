"""Para onde mandar depois do login: só caminho interno do próprio site."""

from __future__ import annotations

from urllib.parse import urlsplit


def caminho_interno(destino: str | None, padrao: str = "/resumo") -> str:
    """Devolve `destino` se for um caminho do próprio site e `padrao` em qualquer outro caso.

    Barra endereço externo, `//host` (que o navegador lê como outro site), barra invertida (que
    alguns navegadores tratam como `/`) e caracteres de controle (quebra de linha em cabeçalho).
    """
    if not destino or not destino.startswith("/") or destino.startswith("//"):
        return padrao
    if "\\" in destino or any(ord(c) < 32 or ord(c) == 127 for c in destino):
        return padrao
    partes = urlsplit(destino)
    if partes.scheme or partes.netloc:
        return padrao
    return destino
