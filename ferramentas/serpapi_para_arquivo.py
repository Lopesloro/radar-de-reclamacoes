"""Monta o arquivo de avaliações de um negócio a partir do Google, pela SerpApi.

Não é leitura automática dentro do produto (essa ficou de fora, ver
`app/coleta/fontes.py`). É uma ferramenta da equipe, rodada à mão, para o caso em
que o dono **autorizou** a leitura mas não consegue exportar as avaliações do
painel dele. O resultado é um CSV no formato que `app/coleta/arquivo.py` aceita, e
ele entra no sistema pelo caminho oficial: a tela `/admin/fontes`.

O arquivo sai sem o nome e a foto de quem escreveu, e com o texto já passado pela
mesma máscara que o sistema aplica antes do banco (`app/coleta/mascara.py`). A
chave da SerpApi fica em `SERPAPI_KEY`, no ambiente ou no `.env` (fora do git).
Cada página de avaliações gasta uma busca da cota da SerpApi.

    python -m ferramentas.serpapi_para_arquivo "Poco Loco Bar Campinas" --saida dados_reais/poco-loco.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from app.coleta import AvaliacaoBruta
from app.coleta.mascara import aplicar

ENDERECO = "https://serpapi.com/search.json"
RAIZ = Path(__file__).resolve().parents[1]
# Nomes de coluna que `app/coleta/arquivo.py` reconhece.
COLUNAS = ("id_origem", "data", "estrelas", "texto")


class ErroSerpApi(RuntimeError):
    pass


def ler_chave() -> str:
    chave = os.environ.get("SERPAPI_KEY")
    arquivo = RAIZ / ".env"
    if not chave and arquivo.exists():
        # utf-8-sig: o Bloco de Notas e o PowerShell antigo põem uma marca invisível no começo.
        for linha in arquivo.read_text(encoding="utf-8-sig").splitlines():
            nome, _, valor = linha.partition("=")
            if nome.strip() == "SERPAPI_KEY":
                chave = valor.strip().strip('"').strip("'")
    if not chave:
        raise ErroSerpApi("Falta a chave: crie o arquivo .env com a linha SERPAPI_KEY=sua_chave.")
    return chave


def _pedir(parametros: dict) -> dict:
    """Uma chamada à SerpApi. Separada para os testes trocarem por uma resposta pronta."""
    endereco = f"{ENDERECO}?{urllib.parse.urlencode(parametros)}"
    try:
        with urllib.request.urlopen(endereco, timeout=60) as resposta:
            dados = json.load(resposta)
    except urllib.error.HTTPError as erro:
        try:
            detalhe = json.load(erro).get("error", "")
        except Exception:
            detalhe = ""
        # A mensagem nunca leva o endereço: ele contém a chave.
        raise ErroSerpApi(f"A SerpApi recusou o pedido ({erro.code}). {detalhe}".strip()) from None
    if "error" in dados:
        raise ErroSerpApi(f"A SerpApi respondeu: {dados['error']}")
    return dados


def achar_lugar(busca: str, chave: str) -> tuple[str, str]:
    """(data_id, nome) do primeiro lugar que o Google Maps devolve para a busca."""
    dados = _pedir({"engine": "google_maps", "type": "search", "q": busca, "hl": "pt-br", "api_key": chave})
    lugar = dados.get("place_results") or next(iter(dados.get("local_results") or []), None)
    if not lugar or not lugar.get("data_id"):
        raise ErroSerpApi(f"Nenhum lugar encontrado para “{busca}”.")
    return lugar["data_id"], lugar.get("title", busca)


def _converter(bruta: dict) -> AvaliacaoBruta | None:
    try:
        return AvaliacaoBruta(
            id_origem=bruta["review_id"],
            data=date.fromisoformat((bruta.get("iso_date") or "")[:10]),
            estrelas=int(round(float(bruta["rating"]))),
            texto=aplicar((bruta.get("extracted_snippet") or {}).get("original") or bruta.get("snippet")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def baixar_avaliacoes(data_id: str, chave: str, max_paginas: int = 200) -> list[AvaliacaoBruta]:
    """Todas as avaliações do lugar, das mais novas para as mais antigas, sem repetição."""
    vistas: dict[str, AvaliacaoBruta] = {}
    token = None
    for _ in range(max_paginas):
        parametros = {"engine": "google_maps_reviews", "data_id": data_id, "hl": "pt-br",
                      "sort_by": "newestFirst", "api_key": chave}
        if token:
            # A SerpApi só aceita escolher o tamanho da página depois da primeira.
            parametros.update(next_page_token=token, num=20)
        dados = _pedir(parametros)
        for bruta in dados.get("reviews") or []:
            avaliacao = _converter(bruta)
            if avaliacao:
                vistas.setdefault(avaliacao.id_origem, avaliacao)
        token = (dados.get("serpapi_pagination") or {}).get("next_page_token")
        if not token:
            break
    return list(vistas.values())


def salvar_csv(avaliacoes: list[AvaliacaoBruta], caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(COLUNAS)
        for a in avaliacoes:
            escritor.writerow([a.id_origem, a.data.isoformat(), a.estrelas, a.texto or ""])


def main(argumentos: list[str] | None = None) -> int:
    leitor = argparse.ArgumentParser(
        description="Monta o CSV de avaliações do Google de um negócio autorizado.")
    leitor.add_argument("busca", help="nome do lugar, como no Google Maps")
    leitor.add_argument("--saida", type=Path, default=RAIZ / "dados_reais" / "avaliacoes.csv")
    leitor.add_argument("--max-paginas", type=int, default=200,
                        help="limite de páginas (cada página gasta uma busca da cota)")
    opcoes = leitor.parse_args(argumentos)
    try:
        chave = ler_chave()
        data_id, nome = achar_lugar(opcoes.busca, chave)
        print(f"Lugar encontrado: {nome}")
        avaliacoes = baixar_avaliacoes(data_id, chave, opcoes.max_paginas)
    except ErroSerpApi as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    salvar_csv(avaliacoes, opcoes.saida)
    com_texto = sum(1 for a in avaliacoes if a.texto)
    print(f"{len(avaliacoes)} avaliações salvas em {opcoes.saida} ({com_texto} com texto).")
    print("Para entrar no sistema: área da equipe, tela Fontes, importar este arquivo no negócio certo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
