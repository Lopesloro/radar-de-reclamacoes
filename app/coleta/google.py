"""Avaliações do Perfil da Empresa no Google.

Como o dono liga a conta dele, em três passos:

1. O dono clica em "Ligar o Google" na tela de configuração. Vai para a tela de
   consentimento do Google pedindo o escopo
   `https://www.googleapis.com/auth/business.manage`. Quem autoriza é o dono, na
   conta Google dele, e a autorização vale só para os perfis que ele administra.
2. O Google volta com um código, que o sistema troca por um *refresh token*.
3. O refresh token é cifrado (`app/seguranca/cofre.py`) e guardado na linha da
   fonte. A cada coleta ele é trocado por um token de acesso de uma hora.

**O que trava hoje, e é importante dizer antes da banca perguntar:** a API de
avaliações do Google não vem liberada. Todo projeto no Google Cloud começa com
cota zero nessas chamadas e precisa de um pedido de acesso aprovado à mão pelo
Google, que responde por e-mail em até cerca de duas semanas. Enquanto o pedido
não é aprovado, a chamada volta com cota zero e a fonte fica em `pendente` —
por isso existe a fonte de arquivo (`app/coleta/arquivo.py`), que não depende de
liberação nenhuma e é o caminho do primeiro dia de um cliente.

As avaliações ficam no endereço da versão 4 da API, que segue de pé para esse
recurso: `GET https://mybusiness.googleapis.com/v4/{parent}/reviews`, com
`parent` na forma `accounts/{conta}/locations/{local}` e no máximo 50 por página.

Referência: developers.google.com/my-business/reference/rest/v4/accounts.locations.reviews/list
"""

from __future__ import annotations

from datetime import datetime

import httpx

from app.coleta import AvaliacaoBruta, ErroDeFonte

ENDERECO_TOKEN = "https://oauth2.googleapis.com/token"  # nosec B105 - endereço, não senha
ENDERECO_AVALIACOES = "https://mybusiness.googleapis.com/v4/{parent}/reviews"
ESCOPO = "https://www.googleapis.com/auth/business.manage"
ENDERECO_CONSENTIMENTO = "https://accounts.google.com/o/oauth2/v2/auth"

POR_PAGINA = 50
TEMPO_LIMITE = 30.0
MAXIMO_DE_PAGINAS = 40          # 2000 avaliações por coleta: acima disso, o resto vem na próxima

# A nota vem escrita, não como número.
ESTRELAS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}


def endereco_de_consentimento(cliente_id: str, volta_para: str, estado: str) -> str:
    """Para onde mandar o dono. `estado` é o token contra CSRF da própria volta."""
    from urllib.parse import urlencode

    return ENDERECO_CONSENTIMENTO + "?" + urlencode({
        "client_id": cliente_id,
        "redirect_uri": volta_para,
        "response_type": "code",
        "scope": ESCOPO,
        "access_type": "offline",     # é o que faz o Google entregar refresh token
        "prompt": "consent",
        "state": estado,
    })


def trocar_codigo_por_refresh(codigo: str, cliente_id: str, cliente_segredo: str,
                              volta_para: str, cliente: httpx.Client | None = None) -> str:
    """O refresh token, que é o que fica guardado cifrado. O código serve uma vez só."""
    fechar = cliente is None
    cliente = cliente or httpx.Client(timeout=TEMPO_LIMITE)
    try:
        resposta = cliente.post(ENDERECO_TOKEN, data={
            "code": codigo, "client_id": cliente_id, "client_secret": cliente_segredo,
            "redirect_uri": volta_para, "grant_type": "authorization_code",
        })
        if resposta.status_code != 200:
            raise ErroDeFonte(f"o Google recusou a troca do código (HTTP {resposta.status_code}).")
        token = resposta.json().get("refresh_token")
        if not token:
            raise ErroDeFonte(
                "o Google não devolveu refresh token. Isso acontece quando a conta já "
                "autorizou antes: refaça com prompt=consent."
            )
        return token
    finally:
        if fechar:
            cliente.close()


def _token_de_acesso(refresh: str, cliente_id: str, cliente_segredo: str,
                     cliente: httpx.Client) -> str:
    resposta = cliente.post(ENDERECO_TOKEN, data={
        "refresh_token": refresh, "client_id": cliente_id,
        "client_secret": cliente_segredo, "grant_type": "refresh_token",
    })
    if resposta.status_code != 200:
        raise ErroDeFonte(
            f"o Google não renovou o acesso (HTTP {resposta.status_code}). "
            "Em geral é o dono ter retirado a autorização: peça para ligar de novo."
        )
    token = resposta.json().get("access_token")
    if not token:
        raise ErroDeFonte("o Google respondeu sem token de acesso.")
    return token


def _converter(crua: dict) -> AvaliacaoBruta | None:
    identificador = crua.get("reviewId")
    escrita = crua.get("starRating")
    quando = crua.get("createTime") or crua.get("updateTime")
    if not identificador or escrita not in ESTRELAS or not quando:
        return None
    try:
        data = datetime.fromisoformat(str(quando).replace("Z", "+00:00")).date()
    except ValueError:
        return None
    # `reviewer.displayName` existe na resposta e **não** é lido: o nome de quem
    # escreveu não entra no sistema em campo nenhum.
    return AvaliacaoBruta(
        id_origem=str(identificador)[:200],
        data=data,
        estrelas=ESTRELAS[escrita],
        texto=crua.get("comment"),
    )


def ler(refresh_token: str, local: str, cliente_id: str, cliente_segredo: str,
        cliente: httpx.Client | None = None) -> tuple[AvaliacaoBruta, ...]:
    """As avaliações do local. `local` é `accounts/{conta}/locations/{local}`."""
    if not local.startswith("accounts/"):
        raise ErroDeFonte(
            "o identificador do Google tem a forma accounts/{conta}/locations/{local}."
        )
    fechar = cliente is None
    cliente = cliente or httpx.Client(timeout=TEMPO_LIMITE)
    try:
        acesso = _token_de_acesso(refresh_token, cliente_id, cliente_segredo, cliente)
        achadas: list[AvaliacaoBruta] = []
        pagina = None
        for _ in range(MAXIMO_DE_PAGINAS):
            parametros = {"pageSize": POR_PAGINA}
            if pagina:
                parametros["pageToken"] = pagina
            resposta = cliente.get(
                ENDERECO_AVALIACOES.format(parent=local),
                params=parametros, headers={"Authorization": f"Bearer {acesso}"},
            )
            if resposta.status_code == 403:
                raise ErroDeFonte(
                    "o Google respondeu 403. Quase sempre é o acesso à API de avaliações "
                    "ainda não aprovado para o projeto (a cota começa em zero) ou a conta "
                    "não administrar este local."
                )
            if resposta.status_code != 200:
                raise ErroDeFonte(f"o Google respondeu HTTP {resposta.status_code}.")
            corpo = resposta.json()
            for crua in corpo.get("reviews", []):
                convertida = _converter(crua)
                if convertida is not None:
                    achadas.append(convertida)
            pagina = corpo.get("nextPageToken")
            if not pagina:
                break
        return tuple(achadas)
    finally:
        if fechar:
            cliente.close()
