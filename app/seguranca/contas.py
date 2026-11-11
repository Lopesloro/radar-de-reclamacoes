"""Quem pode entrar, em qual empresa e com qual papel.

Duas implementações, a mesma interface:

- `ContasNoBanco` é a de produção: a conta vem da tabela `usuario`, criada pela
  equipe do Radar na área de administração. É o que faz o sistema atender vinte
  clientes sem mexer no código.
- `Contas` guarda em memória. Serve ao teste e ao primeiro arranque, quando
  ainda não existe banco nenhum e só o administrador precisa entrar para
  cadastrar o primeiro cliente.

Nenhuma das duas tem senha escrita no código. A do administrador vem de
`RADAR_ADMIN_SENHA`; sem a variável, **ninguém entra** — o padrão é fechado.

Decisão de identificador: a coluna se chama `email` por história, mas o que se
digita na entrada é um identificador livre (`admin`, `bella`, ou o e-mail do
dono). Quem cadastra escolhe; a unicidade é garantida pelo banco.
"""

from __future__ import annotations

import functools
import os
import secrets
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.seguranca import senha as _senha

VARIAVEL_ADMIN = "RADAR_ADMIN_SENHA"
VARIAVEL_ADMIN_USUARIO = "RADAR_ADMIN_USUARIO"
ADMIN_PADRAO = "admin"
# A empresa da própria equipe do Radar. O administrador precisa de uma linha em
# `empresa` porque toda conta aponta para uma, e é esta.
EMPRESA_DO_RADAR = "radar"
NOME_DA_EMPRESA_DO_RADAR = "Equipe do Radar"


@dataclass(frozen=True)
class Conta:
    usuario: str
    empresa_id: str
    hash_senha: str = field(repr=False)
    papel: str = "dono"
    usuario_id: str = ""

    @property
    def e_admin(self) -> bool:
        return self.papel == "admin"


@functools.cache
def _hash_de_mentira() -> str:
    """Hash de uma senha sorteada. Conferir contra ele custa o mesmo que conferir
    contra um hash real, e é isso que impede o tempo de resposta de dizer quais
    usuários existem."""
    return _senha.gerar_hash(secrets.token_urlsafe(16))


class Contas:
    """Contas em memória."""

    def __init__(self, contas: Iterable[Conta] = ()):
        self._por_usuario = {c.usuario: c for c in contas}

    def __len__(self) -> int:
        return len(self._por_usuario)

    @classmethod
    def so_o_administrador(cls, ambiente: Mapping[str, str] | None = None) -> Contas:
        """O administrador do arranque, quando não há banco. Sem senha na variável,
        devolve zero contas: melhor um sistema em que ninguém entra que um com
        senha conhecida."""
        ambiente = os.environ if ambiente is None else ambiente
        valor = ambiente.get(VARIAVEL_ADMIN, "")
        if not valor:
            return cls()
        nome = ambiente.get(VARIAVEL_ADMIN_USUARIO, ADMIN_PADRAO).strip().lower() or ADMIN_PADRAO
        return cls([Conta(
            usuario=nome, empresa_id=EMPRESA_DO_RADAR, hash_senha=_senha.gerar_hash(valor),
            papel="admin", usuario_id=nome,
        )])

    def autenticar(self, usuario: str, chave: str) -> Conta | None:
        conta = self._por_usuario.get(usuario.strip().lower())
        confere = _senha.conferir(chave, conta.hash_senha if conta else _hash_de_mentira())
        return conta if conta and confere else None


class ContasNoBanco:
    """Contas lidas da tabela `usuario`.

    Faz três coisas no acerto de senha, todas de uma vez e dentro da mesma
    transação: devolve a conta, troca o hash antigo (scrypt) pelo de hoje
    (Argon2id) e grava `ultimo_acesso`. Trocar o hash na entrada é o único
    momento em que o sistema tem a senha em mãos; deixar para depois seria
    nunca.
    """

    def __init__(self, abrir_sessao):
        self._abrir_sessao = abrir_sessao

    def autenticar(self, usuario: str, chave: str) -> Conta | None:
        from app.banco import modelo

        procurado = usuario.strip().lower()
        with self._abrir_sessao() as sessao:
            linha = sessao.scalar(
                select(modelo.Usuario).where(
                    modelo.Usuario.email == procurado,
                    modelo.Usuario.ativo.is_(True),
                )
            )
            guardado = linha.senha_hash if linha and linha.senha_hash else _hash_de_mentira()
            if not _senha.conferir(chave, guardado):
                return None
            if linha is None or not linha.senha_hash:
                return None
            if _senha.precisa_regerar(linha.senha_hash):
                linha.senha_hash = _senha.gerar_hash(chave)
            linha.ultimo_acesso = datetime.now()
            conta = Conta(
                usuario=linha.email, empresa_id=linha.empresa_id,
                hash_senha="", papel=linha.papel, usuario_id=linha.id,
            )
            sessao.commit()
            return conta


# ------------------------------------------------------------ primeiro arranque

def garantir_administrador(sessao: Session, ambiente: Mapping[str, str] | None = None) -> str | None:
    """Cria a conta do administrador se nenhuma existir. Devolve o identificador criado.

    Roda na partida do serviço. É idempotente: com administrador já no banco, não
    faz nada — em particular, **não** sobrescreve a senha de quem já existe, para
    uma variável de ambiente esquecida no painel não reabrir uma conta fechada.
    """
    from app.banco import modelo

    ambiente = os.environ if ambiente is None else ambiente
    valor = ambiente.get(VARIAVEL_ADMIN, "")
    if not valor:
        return None
    nome = ambiente.get(VARIAVEL_ADMIN_USUARIO, ADMIN_PADRAO).strip().lower() or ADMIN_PADRAO

    if sessao.scalar(select(modelo.Usuario).where(modelo.Usuario.papel == "admin")) is not None:
        return None

    if sessao.get(modelo.Empresa, EMPRESA_DO_RADAR) is None:
        sessao.add(modelo.Empresa(
            id=EMPRESA_DO_RADAR, nome=NOME_DA_EMPRESA_DO_RADAR, plano="interno",
        ))
        sessao.flush()
    sessao.add(modelo.Usuario(
        id=nome, empresa_id=EMPRESA_DO_RADAR, email=nome, nome="Administrador",
        papel="admin", senha_hash=_senha.gerar_hash(valor),
    ))
    sessao.commit()
    return nome


def do_sistema():
    """A implementação que vale neste arranque: banco se houver, memória se não."""
    from app.banco import sessao as banco

    if banco.usar_banco():
        return ContasNoBanco(banco.Sessao)
    return Contas.so_o_administrador()
