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


class FichaDoCliente(Estrito):
    """Os dados de quem contrata. Todos opcionais; os que vierem são conferidos."""

    cnpj: str = Field(default="", max_length=20)
    responsavel: str = Field(default="", max_length=160)
    telefone: str = Field(default="", max_length=20)
    email_contato: str = Field(default="", max_length=200)
    google_local: str = Field(default="", max_length=500)
    ifood_loja: str = Field(default="", max_length=120)

    @field_validator("cnpj")
    @classmethod
    def _cnpj(cls, valor: str) -> str:
        if not valor.strip():
            return ""
        digitos = re.sub(r"\D", "", valor)
        if len(digitos) != 14:
            raise ValueError("o CNPJ tem 14 números")
        return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"

    @field_validator("telefone")
    @classmethod
    def _telefone(cls, valor: str) -> str:
        if valor.strip() and len(re.sub(r"\D", "", valor)) not in (10, 11):
            raise ValueError("o telefone tem DDD e 8 ou 9 números")
        return valor.strip()

    @field_validator("email_contato")
    @classmethod
    def _email_contato(cls, valor: str) -> str:
        if valor.strip() and "@" not in valor:
            raise ValueError("o e-mail de contato precisa ter @")
        return valor.strip()


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
