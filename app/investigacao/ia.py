"""O cliente da IA (Gemini), com rédea curta.

O que a IA faz neste projeto, e só isto:

1. **Separa a avaliação por assunto.** É onde ela ganha do modelo local com
   folga: o modelo local aprende de um corpus escrito à mão e tropeça em gíria,
   erro de digitação e frase com dois assuntos; a IA lê isso como gente.
2. **Escreve a frase de leitura da estimativa.** Uma frase, em português
   simples, sobre números que **ela não calculou**.

O que a IA nunca faz: calcular número. A estimativa, a faixa e o erro saem de
`app/modelos/previsao.py`, que é estatística conferida por origem móvel. Pedir
número a um modelo de linguagem é pedir um número plausível, não um número
medido — e a banca pergunta de onde veio o número.

Regras de operação:

- **Chave fora do repositório.** `RADAR_IA_CHAVE` (ou `GEMINI_API_KEY`) no
  ambiente. Sem chave, `disponivel()` é falso e o sistema usa o modelo local;
  nada quebra.
- **Limite de chamadas.** Um balde por minuto (`POR_MINUTO`), porque a conta
  gratuita corta em poucas chamadas por minuto e porque uma coleta grande não
  pode virar uma conta grande.
- **Nada de texto em log.** Em erro, o log leva o código HTTP e o tamanho do
  lote. Nunca a avaliação, nunca a chave, nunca a resposta.
- **Tempo limite.** Vinte segundos. A tela do dono não espera a IA: a coleta
  roda fora do pedido web.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Sequence

import httpx

from app.investigacao import protecao
from app.investigacao.protecao import RespostaIA

VARIAVEL_CHAVE = "RADAR_IA_CHAVE"
VARIAVEL_CHAVE_ALTERNATIVA = "GEMINI_API_KEY"
VARIAVEL_MODELO = "RADAR_IA_MODELO"

# O mais barato que resolve a tarefa. O "latest" acompanha a versão corrente da
# família sem o código precisar mudar de nome a cada lançamento.
MODELO_PADRAO = "gemini-flash-lite-latest"
ENDERECO = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"

POR_MINUTO = 12
TEMPO_LIMITE = 20.0
TENTATIVAS = 3
# Espera base entre tentativas, dobrando a cada uma. O teste passa zero: dormir
# seis segundos por caso de erro deixaria a suíte lenta sem medir nada a mais.
ESPERA_BASE = 2.0
# Quantas avaliações vão num pedido. Oito é um meio: uma por pedido gastaria o
# limite da conta em uma coleta pequena, e um lote grande deixa uma avaliação
# com texto estranho perto de muitas outras. O índice de cada item é conferido
# na volta, e lote com contagem diferente da enviada é descartado inteiro.
TAMANHO_DO_LOTE = 8

_log = logging.getLogger("radar.ia")


def chave() -> str | None:
    for variavel in (VARIAVEL_CHAVE, VARIAVEL_CHAVE_ALTERNATIVA):
        valor = os.environ.get(variavel, "").strip()
        if valor:
            return valor
    return None


def modelo() -> str:
    return os.environ.get(VARIAVEL_MODELO, "").strip() or MODELO_PADRAO


def disponivel() -> bool:
    return chave() is not None


class _Balde:
    """Limite de chamadas por minuto, numa janela que desliza."""

    def __init__(self, por_minuto: int = POR_MINUTO):
        self._por_minuto = por_minuto
        self._marcas: list[float] = []
        self._trava = threading.Lock()

    def esperar(self) -> float:
        """Segura a vez até caber no limite. Devolve quanto esperou, para o teste ver."""
        with self._trava:
            agora = time.monotonic()
            self._marcas = [m for m in self._marcas if agora - m < 60]
            if len(self._marcas) < self._por_minuto:
                self._marcas.append(agora)
                return 0.0
            espera = 60 - (agora - self._marcas[0])
        time.sleep(max(0.0, espera))
        with self._trava:
            self._marcas = [m for m in self._marcas if time.monotonic() - m < 60]
            self._marcas.append(time.monotonic())
        return espera


class IA:
    def __init__(self, chave_de_acesso: str, nome_do_modelo: str | None = None,
                 por_minuto: int = POR_MINUTO, cliente: httpx.Client | None = None,
                 espera_base: float = ESPERA_BASE):
        self._chave = chave_de_acesso
        self._modelo = nome_do_modelo or modelo()
        self._balde = _Balde(por_minuto)
        self._cliente = cliente
        self._espera_base = espera_base

    @property
    def nome(self) -> str:
        return self._modelo

    # ------------------------------------------------------------ transporte

    def _pedir(self, corpo: dict) -> dict | None:
        endereco = ENDERECO.format(modelo=self._modelo)
        cliente = self._cliente or httpx.Client(timeout=TEMPO_LIMITE)
        try:
            for tentativa in range(TENTATIVAS):
                self._balde.esperar()
                try:
                    resposta = cliente.post(
                        endereco, params={"key": self._chave}, json=corpo,
                        headers={"content-type": "application/json"},
                    )
                except httpx.HTTPError as erro:
                    _log.warning("ia: falha de rede (%s), tentativa %d", type(erro).__name__, tentativa + 1)
                    continue
                if resposta.status_code == 200:
                    return resposta.json()
                # 429 é limite da conta e 5xx é problema do outro lado: os dois
                # passam com uma espera. 400 e 403 são pedido ou chave errados,
                # e repetir não conserta.
                if resposta.status_code in (429, 500, 502, 503, 504):
                    _log.warning("ia: HTTP %d, tentativa %d", resposta.status_code, tentativa + 1)
                    time.sleep(self._espera_base * (2 ** tentativa))
                    continue
                _log.error("ia: HTTP %d, desistindo", resposta.status_code)
                return None
            return None
        finally:
            if self._cliente is None:
                cliente.close()

    @staticmethod
    def _texto_da_resposta(dados: dict | None) -> str | None:
        if not dados:
            return None
        for candidato in dados.get("candidates", []):
            for parte in candidato.get("content", {}).get("parts", []):
                if isinstance(parte.get("text"), str):
                    return parte["text"]
        return None

    # ------------------------------------------------------------ separar por assunto

    def classificar(self, textos: Sequence[str]) -> list[RespostaIA | None]:
        """Um item por texto, na mesma ordem. None onde a IA não respondeu direito."""
        respostas: list[RespostaIA | None] = []
        for inicio in range(0, len(textos), TAMANHO_DO_LOTE):
            lote = list(textos[inicio:inicio + TAMANHO_DO_LOTE])
            respostas += self._classificar_lote(lote)
        return respostas

    def _classificar_lote(self, lote: Sequence[str]) -> list[RespostaIA | None]:
        vazio: list[RespostaIA | None] = [None] * len(lote)
        if not lote:
            return []
        envelopes = "\n".join(
            f"{i}. {protecao.envelopar(texto)}" for i, texto in enumerate(lote)
        )
        corpo = {
            "systemInstruction": {"parts": [{"text": protecao.INSTRUCAO}]},
            "contents": [{"role": "user", "parts": [{"text":
                f"Classifique as {len(lote)} avaliações numeradas abaixo. "
                f"Devolva uma lista com exatamente {len(lote)} itens, na mesma ordem, "
                "cada um com indice, assunto, confianca e motivo.\n" + envelopes
            }]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseJsonSchema": {
                    "type": "object",
                    "properties": {"itens": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "indice": {"type": "integer"},
                                **protecao.ESQUEMA["properties"],
                            },
                            "required": ["indice", *protecao.ESQUEMA["required"]],
                        },
                    }},
                    "required": ["itens"],
                },
            },
        }
        import json

        bruta = self._texto_da_resposta(self._pedir(corpo))
        if not bruta:
            return vazio
        try:
            itens = json.loads(bruta).get("itens")
        except (ValueError, TypeError, AttributeError):
            return vazio
        if not isinstance(itens, list) or len(itens) != len(lote):
            # Contagem diferente da enviada: não há como saber qual resposta é de
            # qual avaliação. Descarta o lote inteiro e deixa o modelo local decidir.
            _log.warning("ia: lote veio com %s itens para %d avaliações", type(itens), len(lote))
            return vazio

        resultado: list[RespostaIA | None] = list(vazio)
        for item in itens:
            if not isinstance(item, dict):
                continue
            indice = item.get("indice")
            if not isinstance(indice, int) or isinstance(indice, bool):
                continue
            if not 0 <= indice < len(lote):
                continue
            resultado[indice] = protecao.ler_resposta(json.dumps(item))
        return resultado

    # ------------------------------------------------------------ frase da estimativa

    def explicar(self, pergunta: str, limite_de_palavras: int = 45) -> str | None:
        """Uma frase sobre números que já existem. Devolve None se a IA não responder.

        `pergunta` é montada pelo sistema com números do próprio banco, nunca com
        texto de avaliação. O que volta é texto puro, cortado, e vai para a tela
        escapado pelo Jinja: não vira consulta, comando nem redirecionamento.
        """
        corpo = {
            "systemInstruction": {"parts": [{"text":
                "Você explica número de relatório para dono de comércio pequeno, "
                "em português do Brasil simples, sem termo técnico e sem travessão. "
                f"No máximo {limite_de_palavras} palavras. "
                "Não invente número nenhum: use só os números que receber."
            }]},
            "contents": [{"role": "user", "parts": [{"text": pergunta}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4000},
        }
        bruta = self._texto_da_resposta(self._pedir(corpo))
        if not bruta:
            return None
        frase = protecao.limpar(bruta).replace("—", ",").replace("–", ",")
        palavras = frase.split()
        if len(palavras) > limite_de_palavras + 15:
            frase = " ".join(palavras[:limite_de_palavras]) + "."
        return frase[:400] or None


def do_ambiente() -> IA | None:
    """A IA configurada, ou None. Quem chama decide o que fazer sem ela."""
    valor = chave()
    return None if valor is None else IA(valor)
