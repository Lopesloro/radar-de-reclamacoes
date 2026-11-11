"""Tira dado pessoal do texto da avaliação antes de ele entrar no banco.

Por que antes do banco e não na tela: o que não é gravado não vaza em dump, em
backup, em log de consulta nem em erro de programação futuro. Mascarar na
exibição deixaria o dado cru guardado e dependeria de toda tela lembrar de
mascarar. É a parte de minimização da LGPD aplicada no lugar que dá para
garantir com um teste.

O que sai, com a marca que fica no lugar:

| O que                                   | Vira        |
|-----------------------------------------|-------------|
| e-mail                                  | `[email]`   |
| telefone com DDD, fixo ou celular       | `[telefone]`|
| CPF e CNPJ, com ou sem pontuação        | `[documento]`|
| CEP                                     | `[cep]`     |
| sequência de 13 a 19 dígitos (cartão)   | `[numero]`  |
| endereço de site e `@usuario`           | `[link]`    |
| nome próprio depois de palavra de papel | `[nome]`    |

**Limite honesto:** nome de pessoa só é pego quando vem depois de uma palavra de
papel ("o entregador João", "a atendente Maria", "o Dr. Paulo"). Nome solto no
meio da frase passa. Não existe regra que ache todo nome próprio em português
sem um dicionário de nomes, e um dicionário erraria no outro sentido, apagando
palavra comum. A alternativa de não guardar texto nenhum mataria o produto, que
é justamente ler o texto. Esse limite está escrito no termo que o parceiro
assina, e o nome de quem escreveu a avaliação **nunca** é guardado em campo
nenhum: a avaliação entra com o identificador que a plataforma deu, não com o
autor.
"""

from __future__ import annotations

import re

MARCA_NOME = "[nome]"

_PAPEIS = (
    "entregador", "entregadora", "motoboy", "atendente", "recepcionista",
    "garcom", "garçom", "garconete", "garçonete", "vendedor", "vendedora",
    "gerente", "funcionario", "funcionária", "funcionaria", "moça", "moca",
    "rapaz", "senhor", "senhora", "dona", "doutor", "doutora", "dr", "dra",
    "sr", "sra", "enfermeiro", "enfermeira", "dentista", "medico", "médica",
    "medica", "professor", "professora", "tosador", "tosadora", "cabeleireiro",
    "cabeleireira", "manicure", "barbeiro", "caixa", "cozinheiro", "cozinheira",
)

_REGRAS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[email]"),
    (re.compile(r"\bhttps?://\S+|\bwww\.\S+", re.IGNORECASE), "[link]"),
    (re.compile(r"(?<![\w])@[A-Za-z0-9_.]{3,}"), "[link]"),
    (re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"), "[documento]"),
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[documento]"),
    (re.compile(r"\b\d{5}-?\d{3}\b"), "[cep]"),
    (re.compile(r"(?:\+?55\s?)?\(?\b\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}\b"), "[telefone]"),
    (re.compile(r"\b9?\d{4}[\s.-]\d{4}\b"), "[telefone]"),
    (re.compile(r"\b\d{13,19}\b"), "[numero]"),
)

# "o entregador João", "a Dra. Ana Paula": a palavra de papel, o artigo opcional
# e um ou dois nomes com maiúscula.
#
# A palavra de papel é comparada sem olhar a caixa, pelo grupo `(?i:...)`. O
# nome, não: `re.IGNORECASE` no padrão inteiro faria `[A-Z]` casar com
# minúscula, e o padrão comia a palavra seguinte ao nome ("a atendente Maria
# foi grossa" virava "a atendente [nome] grossa"). O defeito só aparece com uma
# frase em que o nome é seguido de outra palavra, e foi assim que apareceu.
_NOME_COM_PAPEL = re.compile(
    r"\b(?i:(?P<papel>" + "|".join(_PAPEIS) + r"))\.?\s*,?\s*"
    r"(?P<nome>[A-ZÁÂÃÀÉÊÍÓÔÕÚÇ][a-záâãàéêíóôõúç]{2,}"
    r"(?:\s+(?:d[aeo]s?\s+)?[A-ZÁÂÃÀÉÊÍÓÔÕÚÇ][a-záâãàéêíóôõúç]{2,})?)"
)


def _trocar_nome(achado: re.Match[str]) -> str:
    return f"{achado.group('papel')} {MARCA_NOME}"


def aplicar(texto: str | None) -> str | None:
    """O texto pronto para o banco. None continua None; texto só com espaço vira None."""
    if texto is None:
        return None
    limpo = texto.strip()
    if not limpo:
        return None
    limpo = _NOME_COM_PAPEL.sub(_trocar_nome, limpo)
    for regra, marca in _REGRAS:
        limpo = regra.sub(marca, limpo)
    return re.sub(r"\s+", " ", limpo).strip() or None


def tem_dado_pessoal(texto: str | None) -> bool:
    """Para o teste: o texto ainda tem algo que as regras pegariam?"""
    if not texto:
        return False
    return any(regra.search(texto) for regra, _ in _REGRAS) or bool(_NOME_COM_PAPEL.search(texto))
