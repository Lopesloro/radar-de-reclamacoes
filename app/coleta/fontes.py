"""Qual módulo lê qual fonte, e o que cada fonte precisa para funcionar.

A tela de administração mostra esta tabela. Quem opera precisa saber, antes de
prometer prazo ao cliente, que ligar o Google depende de uma aprovação que não
está na mão da equipe.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.coleta import AvaliacaoBruta, ErroDeFonte
from app.seguranca import cofre

ARQUIVO = "arquivo"
GOOGLE = "google"
IFOOD = "ifood"


@dataclass(frozen=True)
class Plataforma:
    chave: str
    nome: str
    como_liga: str
    o_que_trava: str | None
    automatica: bool


PLATAFORMAS: tuple[Plataforma, ...] = (
    Plataforma(
        chave=ARQUIVO, nome="Arquivo enviado",
        como_liga="O dono exporta as avaliações do painel da plataforma e a equipe envia o arquivo.",
        o_que_trava=None, automatica=False,
    ),
    Plataforma(
        chave=GOOGLE, nome="Perfil da Empresa no Google",
        como_liga="O dono autoriza na conta Google dele, no escopo business.manage.",
        o_que_trava=(
            "O Google precisa aprovar o acesso à API de avaliações do projeto. A cota "
            "começa em zero e a aprovação é manual, com resposta por e-mail em cerca de "
            "duas semanas."
        ),
        automatica=True,
    ),
    Plataforma(
        chave=IFOOD, nome="iFood",
        como_liga="O dono autoriza o aplicativo no Portal do Parceiro e passa o merchantId.",
        o_que_trava="O módulo de avaliações precisa ser liberado para o aplicativo pela distribuição.",
        automatica=True,
    ),
)

POR_CHAVE = {p.chave: p for p in PLATAFORMAS}

# Plataformas sem API pública de avaliação de loja hoje, com o caminho que resta.
# Está no código porque é pergunta que o cliente faz, e a resposta não pode
# depender de alguém lembrar.
SEM_API = (
    ("99Food", "O Portal do Estabelecimento Parceiro mostra as avaliações na tela, sem API "
               "pública documentada. Caminho: exportar do portal e enviar como arquivo."),
    ("Rappi", "Sem documentação pública de avaliações de loja. Mesmo caminho: arquivo."),
    ("Uber Eats", "Saiu da operação de refeições no Brasil; não há integração a fazer."),
    ("Reclame Aqui", "Sem API aberta. O dono exporta do painel dele e envia como arquivo."),
)

PRIMEIRO_HISTORICO_EM_DIAS = 730


def ler_de(sessao: Session, fonte_id: str) -> tuple[AvaliacaoBruta, ...]:
    """Lê a fonte automática. Fonte de arquivo não passa por aqui: quem envia é a tela."""
    import os

    from app.banco import modelo
    from app.coleta import google, ifood

    fonte = sessao.get(modelo.Fonte, fonte_id)
    if fonte is None:
        raise ErroDeFonte("essa fonte não existe.")
    if fonte.plataforma == ARQUIVO:
        raise ErroDeFonte("a fonte de arquivo é alimentada pelo envio, não pela coleta.")

    segredo = cofre.decifrar(fonte.segredo_cifrado)
    if segredo is None:
        raise ErroDeFonte(
            "o segredo desta fonte não abriu. Em geral é a chave do cofre ter mudado: "
            "ligue a fonte de novo."
        )

    desde = (fonte.ultima_coleta.date() - timedelta(days=7)) if fonte.ultima_coleta \
        else date.today() - timedelta(days=PRIMEIRO_HISTORICO_EM_DIAS)

    if fonte.plataforma == GOOGLE:
        cliente_id = os.environ.get("RADAR_GOOGLE_CLIENTE_ID", "")
        cliente_segredo = os.environ.get("RADAR_GOOGLE_CLIENTE_SEGREDO", "")
        if not cliente_id or not cliente_segredo:
            raise ErroDeFonte(
                "faltam RADAR_GOOGLE_CLIENTE_ID e RADAR_GOOGLE_CLIENTE_SEGREDO no serviço."
            )
        return google.ler(segredo, fonte.identificador_externo, cliente_id, cliente_segredo)

    if fonte.plataforma == IFOOD:
        partes = segredo.split(":", 1)
        if len(partes) != 2:
            raise ErroDeFonte("o segredo do iFood é clientId:clientSecret.")
        return ifood.ler(partes[0], partes[1], fonte.identificador_externo, desde)

    raise ErroDeFonte(f"plataforma que o sistema não conhece: {fonte.plataforma!r}")
