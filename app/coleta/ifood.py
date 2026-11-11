"""Avaliações do iFood, pela API de parceiro.

Como o dono liga: no Portal do Parceiro ele autoriza o aplicativo do Radar e o
iFood entrega um par `clientId`/`clientSecret` e o `merchantId` da loja. O par
vai cifrado no cofre; a cada coleta ele é trocado por um token de acesso.

**O que trava hoje:** o módulo de avaliações precisa ser liberado para o
aplicativo pela distribuição do iFood. Sem a liberação, a chamada volta com
erro de autorização e a fonte fica em `pendente`.

Detalhes da API que mudam o código, e por isso estão escritos aqui:

- O período padrão da listagem é só os **últimos 7 dias**. Para o histórico que
  a previsão precisa, a coleta pede mês a mês com `dateFrom` e `dateTo`.
- `pageSize` vai até 50.
- Data em ISO 8601.
- Token expirado volta 401, e o certo é renovar e repetir, não desistir.

O prefixo do módulo (`/review/v1.0`) é configurável porque é o que a
documentação do módulo confirma na liberação; o que não muda é a forma do
caminho, `/merchants/{merchantId}/reviews`.

Referência: developer.ifood.com.br/pt-BR/docs/guides/modules/review
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta

import httpx

from app.coleta import AvaliacaoBruta, ErroDeFonte

BASE = "https://merchant-api.ifood.com.br"
CAMINHO_TOKEN = "/authentication/v1.0/oauth/token"
VARIAVEL_PREFIXO = "RADAR_IFOOD_PREFIXO"
PREFIXO_PADRAO = "/review/v1.0"

POR_PAGINA = 50
TEMPO_LIMITE = 30.0
DIAS_POR_PEDIDO = 30
MAXIMO_DE_MESES = 24


def prefixo() -> str:
    return os.environ.get(VARIAVEL_PREFIXO, "").strip() or PREFIXO_PADRAO


def _token(cliente_id: str, cliente_segredo: str, cliente: httpx.Client) -> str:
    resposta = cliente.post(BASE + CAMINHO_TOKEN, data={
        "grantType": "client_credentials",
        "clientId": cliente_id,
        "clientSecret": cliente_segredo,
    })
    if resposta.status_code != 200:
        raise ErroDeFonte(f"o iFood recusou a autenticação (HTTP {resposta.status_code}).")
    token = resposta.json().get("accessToken")
    if not token:
        raise ErroDeFonte("o iFood respondeu sem accessToken.")
    return token


def _converter(crua: dict) -> AvaliacaoBruta | None:
    identificador = crua.get("id") or crua.get("reviewId")
    nota = crua.get("score", crua.get("rating"))
    quando = crua.get("createdAt") or crua.get("publishedAt") or crua.get("orderDate")
    if not identificador or nota is None or not quando:
        return None
    try:
        estrelas = int(round(float(nota)))
        data = datetime.fromisoformat(str(quando).replace("Z", "+00:00")).date()
    except (TypeError, ValueError):
        return None
    if not 1 <= estrelas <= 5:
        return None
    return AvaliacaoBruta(
        id_origem=str(identificador)[:200],
        data=data,
        estrelas=estrelas,
        texto=crua.get("comment") or crua.get("message") or None,
    )


def ler(cliente_id: str, cliente_segredo: str, merchant_id: str, desde: date,
        ate: date | None = None, cliente: httpx.Client | None = None) -> tuple[AvaliacaoBruta, ...]:
    """As avaliações da loja entre as duas datas, em fatias de 30 dias."""
    if not merchant_id:
        raise ErroDeFonte("falta o merchantId da loja no iFood.")
    ate = ate or date.today()
    fechar = cliente is None
    cliente = cliente or httpx.Client(timeout=TEMPO_LIMITE)
    try:
        token = _token(cliente_id, cliente_segredo, cliente)
        cabecalhos = {"Authorization": f"Bearer {token}"}
        caminho = f"{BASE}{prefixo()}/merchants/{merchant_id}/reviews"
        achadas: dict[str, AvaliacaoBruta] = {}

        inicio = desde
        for _ in range(MAXIMO_DE_MESES):
            if inicio > ate:
                break
            fim = min(inicio + timedelta(days=DIAS_POR_PEDIDO), ate)
            pagina = 1
            while True:
                resposta = cliente.get(caminho, params={
                    "page": pagina, "pageSize": POR_PAGINA,
                    "dateFrom": inicio.isoformat(), "dateTo": fim.isoformat(),
                }, headers=cabecalhos)
                if resposta.status_code == 401:
                    token = _token(cliente_id, cliente_segredo, cliente)
                    cabecalhos = {"Authorization": f"Bearer {token}"}
                    continue
                if resposta.status_code == 403:
                    raise ErroDeFonte(
                        "o iFood respondeu 403. Em geral é o módulo de avaliações ainda "
                        "não liberado para o aplicativo pela distribuição."
                    )
                if resposta.status_code != 200:
                    raise ErroDeFonte(f"o iFood respondeu HTTP {resposta.status_code}.")
                corpo = resposta.json()
                lista = corpo.get("reviews", corpo if isinstance(corpo, list) else [])
                for crua in lista:
                    convertida = _converter(crua) if isinstance(crua, dict) else None
                    if convertida is not None:
                        achadas[convertida.id_origem] = convertida
                if len(lista) < POR_PAGINA:
                    break
                pagina += 1
            inicio = fim + timedelta(days=1)
        return tuple(achadas.values())
    finally:
        if fechar:
            cliente.close()
