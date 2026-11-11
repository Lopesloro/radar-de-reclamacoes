"""Avaliações enviadas em arquivo: CSV ou JSON.

É a fonte que funciona no primeiro dia de um cliente, sem depender de liberação
de API nenhuma. O dono exporta as avaliações do painel da plataforma dele (Google
e iFood permitem exportar) ou a equipe do Radar monta o arquivo, e a área de
administração envia.

Formato aceito, CSV com cabeçalho ou JSON (lista de objetos). Os nomes das
colunas aceitam variação porque nenhum painel exporta com o mesmo nome:

| Campo       | Nomes aceitos                                  | Obrigatório |
|-------------|------------------------------------------------|-------------|
| id_origem   | id_origem, id, review_id, identificador        | sim         |
| data        | data, date, createTime, criada_em              | sim         |
| estrelas    | estrelas, nota, rating, starRating, score      | sim         |
| texto       | texto, comment, comentario, review, descricao  | não         |

Linha inválida não derruba o arquivo inteiro: ela é contada e descrita no
relatório da importação, e as válidas entram. Um arquivo de 300 linhas com 2
erros de data é um arquivo útil, e recusar tudo faria o operador editar CSV à
mão sem saber onde.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import date, datetime

from app.coleta import AvaliacaoBruta, ErroDeFonte

LIMITE_DE_LINHAS = 20_000

_NOMES = {
    "id_origem": ("id_origem", "id", "review_id", "reviewid", "identificador", "codigo"),
    "data": ("data", "date", "createtime", "criada_em", "created_at", "data_avaliacao"),
    "estrelas": ("estrelas", "nota", "rating", "starrating", "score", "stars"),
    "texto": ("texto", "comment", "comentario", "comentário", "review", "descricao", "descrição"),
}

_ESTRELAS_ESCRITAS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "star_rating_one": 1, "star_rating_two": 2, "star_rating_three": 3,
    "star_rating_four": 4, "star_rating_five": 5,
}


@dataclass(frozen=True)
class Importacao:
    avaliacoes: tuple[AvaliacaoBruta, ...]
    recusadas: int
    motivos: tuple[str, ...]

    @property
    def total(self) -> int:
        return len(self.avaliacoes) + self.recusadas


def _achar(linha: dict, campo: str) -> str | None:
    minusculas = {str(c).strip().lower(): v for c, v in linha.items() if c is not None}
    for nome in _NOMES[campo]:
        if nome in minusculas and minusculas[nome] not in (None, ""):
            return str(minusculas[nome]).strip()
    return None


def _data(bruta: str) -> date:
    texto = bruta.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(texto).date()
    except ValueError:
        pass
    for formato in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(bruta.strip(), formato).date()
        except ValueError:
            continue
    raise ValueError(f"data que não dá para ler: {bruta!r}")


def _estrelas(bruta: str) -> int:
    chave = bruta.strip().lower()
    if chave in _ESTRELAS_ESCRITAS:
        return _ESTRELAS_ESCRITAS[chave]
    try:
        return int(round(float(chave.replace(",", "."))))
    except ValueError:
        raise ValueError(f"nota que não dá para ler: {bruta!r}") from None


def _linhas(conteudo: str) -> list[dict]:
    texto = conteudo.lstrip("\ufeff").strip()
    if texto.startswith(("[", "{")):
        dados = json.loads(texto)
        if isinstance(dados, dict):
            for chave in ("reviews", "itens", "items", "data"):
                if isinstance(dados.get(chave), list):
                    dados = dados[chave]
                    break
        if not isinstance(dados, list):
            raise ErroDeFonte("o JSON precisa ser uma lista de avaliações.")
        return [d for d in dados if isinstance(d, dict)]

    # O separador varia entre painel brasileiro (;) e exportação em inglês (,).
    amostra = texto[:4000]
    try:
        dialeto = csv.Sniffer().sniff(amostra, delimiters=",;\t")
    except csv.Error:
        dialeto = csv.excel
    return list(csv.DictReader(io.StringIO(texto), dialect=dialeto))


def ler(conteudo: str) -> Importacao:
    """Lê o arquivo e separa o que serve do que não serve."""
    try:
        cruas = _linhas(conteudo)
    except (ValueError, json.JSONDecodeError) as erro:
        raise ErroDeFonte(f"não deu para ler o arquivo: {erro}") from erro
    if not cruas:
        raise ErroDeFonte("o arquivo não tem nenhuma linha de avaliação.")
    if len(cruas) > LIMITE_DE_LINHAS:
        raise ErroDeFonte(f"o arquivo passa de {LIMITE_DE_LINHAS} linhas; divida em partes.")

    boas: list[AvaliacaoBruta] = []
    motivos: list[str] = []
    vistos: set[str] = set()
    for numero, linha in enumerate(cruas, start=2):
        try:
            identificador = _achar(linha, "id_origem")
            bruta_data = _achar(linha, "data")
            bruta_nota = _achar(linha, "estrelas")
            if not identificador or not bruta_data or not bruta_nota:
                raise ValueError("falta identificador, data ou nota")
            if identificador in vistos:
                raise ValueError(f"identificador repetido no próprio arquivo: {identificador}")
            avaliacao = AvaliacaoBruta(
                id_origem=identificador[:200],
                data=_data(bruta_data),
                estrelas=_estrelas(bruta_nota),
                texto=_achar(linha, "texto"),
            )
        except ValueError as erro:
            if len(motivos) < 20:
                motivos.append(f"linha {numero}: {erro}")
            continue
        vistos.add(avaliacao.id_origem)
        boas.append(avaliacao)

    if not boas:
        raise ErroDeFonte(
            "nenhuma linha do arquivo serviu. Primeiros motivos: " + "; ".join(motivos[:3])
        )
    return Importacao(
        avaliacoes=tuple(boas),
        recusadas=len(cruas) - len(boas),
        motivos=tuple(motivos),
    )
