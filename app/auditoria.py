"""Trilha de auditoria: quem fez o quê, em qual empresa e quando.

Decisão que vale explicar: a linha de auditoria é gravada **dentro da mesma
transação** da ação. Um interceptador global, que registrasse depois da resposta
sair, teria dois defeitos: ação que falha no meio deixaria registro de algo que
não aconteceu, e ação que acontece com a resposta quebrada não deixaria registro
nenhum. Na mesma transação, ou as duas coisas existem ou nenhuma existe.

O que nunca entra em `detalhe`: senha, token de fonte, texto de avaliação. A
trilha diz que alguém leu os dados de uma empresa, não repete os dados.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.banco import modelo

# As ações que o sistema registra. Lista fechada de propósito: ação nova entra
# aqui junto com o teste que prova que a rota dela registra.
ACOES = (
    "entrou",
    "saiu",
    "empresa_criada",
    "comercio_criado",
    "usuario_criado",
    "usuario_desligado",
    "senha_trocada",
    "fonte_ligada",
    "fonte_desligada",
    "canal_definido",
    "assunto_conferido",
    "combinado_atualizado",
    "coleta_rodada",
    "ia_consultada",
    "dados_exportados",
)

TAMANHO_MAXIMO_DO_DETALHE = 500


def registrar(sessao: Session, *, empresa_id: str, acao: str, objeto: str,
              usuario_id: str | None = None, detalhe: str | None = None) -> None:
    """Põe uma linha na trilha. Não dá commit: quem chamou fecha a transação."""
    if acao not in ACOES:
        raise ValueError(f"ação fora da lista de auditoria: {acao!r}")
    sessao.add(modelo.Auditoria(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        acao=acao,
        objeto=objeto[:120],
        detalhe=(detalhe or "")[:TAMANHO_MAXIMO_DO_DETALHE] or None,
    ))


def ultimas(sessao: Session, limite: int = 100,
            empresa_id: str | None = None) -> tuple[modelo.Auditoria, ...]:
    """As linhas mais recentes. Sem `empresa_id`, todas — só a área de administração lê assim."""
    consulta = select(modelo.Auditoria).order_by(modelo.Auditoria.quando.desc()).limit(limite)
    if empresa_id is not None:
        consulta = consulta.where(modelo.Auditoria.empresa_id == empresa_id)
    return tuple(sessao.scalars(consulta).all())
