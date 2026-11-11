"""Conferência estrita do que chega em formulário.

Pydantic no modo estrito: campo a mais é erro, campo faltando é erro, texto fora
do tamanho é erro. O motivo de ser estrito e não tolerante: um formulário que
aceita campo desconhecido é a porta para alguém mandar `papel=admin` num
cadastro de cliente e o código, lá na frente, usar o que chegou.

Nada aqui conhece HTML. A rota lê o formulário, passa pelo modelo e só então
toca no banco; erro de conferência volta para a tela como frase em português.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.coleta.fontes import POR_CHAVE
from app.contratos import CATEGORIAS

# Identificador que vai para a URL: só minúscula, número e hífen. Sem isso, um
# identificador com barra ou ponto viraria outro caminho no site.
_IDENTIFICADOR = re.compile(r"^[a-z0-9][a-z0-9-]{1,58}[a-z0-9]$")


class Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _conferir_identificador(valor: str) -> str:
    if not _IDENTIFICADOR.match(valor):
        raise ValueError(
            "o identificador usa só letra minúscula, número e hífen, e tem de 3 a 60 caracteres"
        )
    return valor


class NovoCliente(Estrito):
    identificador: str = Field(min_length=3, max_length=60)
    nome: str = Field(min_length=2, max_length=160)
    plano: str = Field(default="piloto", max_length=30)
    negocio_nome: str = Field(min_length=2, max_length=160)
    ramo: str = Field(min_length=2, max_length=80)
    cidade: str = Field(min_length=2, max_length=120)
    entrada: str = Field(min_length=3, max_length=200)
    email_aviso: str = Field(default="", max_length=200)

    @field_validator("identificador")
    @classmethod
    def _identificador(cls, valor: str) -> str:
        return _conferir_identificador(valor)

    @field_validator("plano")
    @classmethod
    def _plano(cls, valor: str) -> str:
        if valor not in ("piloto", "mensal", "interno"):
            raise ValueError("o plano é piloto, mensal ou interno")
        return valor

    @field_validator("email_aviso")
    @classmethod
    def _email(cls, valor: str) -> str:
        if valor and "@" not in valor:
            raise ValueError("o e-mail de aviso precisa ter @")
        return valor


class NovoNegocio(Estrito):
    identificador: str = Field(min_length=3, max_length=60)
    nome: str = Field(min_length=2, max_length=160)
    ramo: str = Field(min_length=2, max_length=80)
    cidade: str = Field(min_length=2, max_length=120)

    @field_validator("identificador")
    @classmethod
    def _identificador(cls, valor: str) -> str:
        return _conferir_identificador(valor)


class NovoUsuario(Estrito):
    entrada: str = Field(min_length=3, max_length=200)
    nome: str = Field(min_length=2, max_length=160)

    @field_validator("entrada")
    @classmethod
    def _entrada(cls, valor: str) -> str:
        minuscula = valor.lower()
        if " " in minuscula:
            raise ValueError("o nome de entrada não tem espaço")
        return minuscula


class NovaFonte(Estrito):
    comercio_id: str = Field(min_length=3, max_length=60)
    plataforma: str = Field(min_length=3, max_length=30)
    identificador_externo: str = Field(default="", max_length=200)
    segredo: str = Field(default="", max_length=4000)

    @field_validator("plataforma")
    @classmethod
    def _plataforma(cls, valor: str) -> str:
        if valor not in POR_CHAVE:
            raise ValueError(f"plataforma que o sistema não conhece: {valor}")
        return valor


class Importacao(Estrito):
    comercio_id: str = Field(min_length=3, max_length=60)
    conteudo: str = Field(min_length=10, max_length=900_000)


class CanalDeAviso(Estrito):
    email_aviso: str = Field(default="", max_length=200)

    @field_validator("email_aviso")
    @classmethod
    def _email(cls, valor: str) -> str:
        if valor and ("@" not in valor or "." not in valor.split("@")[-1]):
            raise ValueError("escreva um e-mail completo, como nome@empresa.com.br")
        return valor


class Conferencia(Estrito):
    avaliacao_id: str = Field(min_length=3, max_length=80)
    categoria: str = Field(max_length=30)

    @field_validator("categoria")
    @classmethod
    def _categoria(cls, valor: str) -> str:
        if valor and valor not in CATEGORIAS:
            raise ValueError("assunto fora dos cinco combinados")
        return valor
