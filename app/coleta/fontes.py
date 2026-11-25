"""De onde as avaliações entram hoje, e o que falta para as outras plataformas.

Hoje só existe uma fonte: o **arquivo** (CSV ou JSON) que o dono exporta do
painel da plataforma e a equipe envia pela tela `/admin/fontes`.

A leitura automática do Google e do iFood **não entra no produto**. As duas têm
API, mas as duas dependem de uma autorização que não está na mão da equipe. Elas
ficam descritas aqui, com o que cada uma exige, para a tela dizer isso ao
operador antes de ele prometer prazo a um cliente.
"""

from __future__ import annotations

from dataclasses import dataclass

ARQUIVO = "arquivo"


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
)

POR_CHAVE = {p.chave: p for p in PLATAFORMAS}

# Leitura automática que fica para depois: cada uma precisa de autorização de fora.
FUTURAS: tuple[Plataforma, ...] = (
    Plataforma(
        chave="google", nome="Perfil da Empresa no Google",
        como_liga="O dono autorizaria na conta Google dele a leitura das avaliações.",
        o_que_trava=(
            "O Google precisa aprovar o acesso do projeto à API de avaliações. A "
            "aprovação é manual e leva cerca de duas semanas."
        ),
        automatica=True,
    ),
    Plataforma(
        chave="ifood", nome="iFood",
        como_liga="O dono autorizaria o aplicativo do Radar no Portal do Parceiro.",
        o_que_trava="O iFood precisa liberar o módulo de avaliações para o aplicativo.",
        automatica=True,
    ),
)

# Plataformas sem API pública de avaliação de loja hoje, com o caminho que resta.
SEM_API = (
    ("99Food", "Sem API pública de avaliações. Caminho: exportar do portal e enviar como arquivo."),
    ("Rappi", "Sem documentação pública de avaliações de loja. Mesmo caminho: arquivo."),
    ("Reclame Aqui", "Sem API aberta. O dono exporta do painel dele e envia como arquivo."),
)
