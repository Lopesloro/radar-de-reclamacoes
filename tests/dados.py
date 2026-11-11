"""O banco de teste: duas empresas com avaliações, montadas pelo motor de verdade.

Nenhum atalho: o teste não escreve em `serie_mensal` nem em `previsao` à mão. Ele
entrega avaliações ao `app/coleta/motor.py` e deixa o motor classificar, contar
os meses, estimar e gerar aviso. É a única forma de o teste provar que o caminho
inteiro funciona, e não só que as tabelas aceitam escrita.

O texto das avaliações vem do corpus rotulado da equipe (`app/modelos/corpus.py`).
É **dado de teste**, não dado de produto: nenhuma tela do sistema lê daqui.

As duas empresas existem para o teste de isolamento ter de onde tentar vazar. O
identificador da empresa e o do negócio são iguais nos dois casos porque cada uma
tem um negócio só, o que é o caso comum de cliente pequeno.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from app.banco import modelo
from app.banco import sessao as banco
from app.coleta import AvaliacaoBruta, motor
from app.contratos import CATEGORIAS
from app.modelos import corpus

HOJE = date(2026, 11, 10)
MESES = 15

EMPRESAS = (
    # id, nome, negócio, ramo, cidade, assunto que cresce, entrada do dono
    ("bella-massa", "Pizzaria Bella Massa", "Restaurante", "Campinas, SP", "demora", "bella"),
    ("patinhas", "Pet Shop Patinhas", "Pet shop", "Campinas, SP", "preco", "patinhas"),
)

NIVEL = {
    "bella-massa": {"atendimento": 9, "demora": 8, "preco": 6, "qualidade": 5, "ambiente": 3},
    # Ambiente quase não aparece aqui: serve para testar assunto com pouco dado.
    "patinhas": {"atendimento": 6, "demora": 5, "preco": 7, "qualidade": 4, "ambiente": 1},
}


def _avaliacoes(empresa_id: str, cresce: str, semente: int) -> list[AvaliacaoBruta]:
    sorteio = random.Random(semente)
    brutas: list[AvaliacaoBruta] = []
    numero = 0
    for atras in range(MESES, -1, -1):
        base = date(HOJE.year, HOJE.month, 1) - timedelta(days=30 * atras)
        mes = date(base.year, base.month, 1)
        for categoria in CATEGORIAS:
            quantas = NIVEL[empresa_id][categoria]
            if categoria == cresce and atras <= 4:
                quantas += (5 - atras) * 2
            for _ in range(max(0, quantas + sorteio.randint(-1, 1))):
                numero += 1
                brutas.append(AvaliacaoBruta(
                    id_origem=f"{empresa_id}-{numero}",
                    data=date(mes.year, mes.month, sorteio.randint(1, 28)),
                    estrelas=sorteio.choice([1, 1, 2, 2, 3]),
                    texto=sorteio.choice(corpus.FRASES[categoria]),
                ))
        for _ in range(3):
            numero += 1
            brutas.append(AvaliacaoBruta(
                id_origem=f"{empresa_id}-{numero}",
                data=date(mes.year, mes.month, 15), estrelas=5,
                texto=sorteio.choice(corpus.ELOGIOS),
            ))
    return brutas


def montar(senha_hash: str) -> None:
    """Cria as tabelas e põe as duas empresas com histórico. Idempotente."""
    import uuid

    banco.esquecer()
    modelo.Base.metadata.create_all(banco.motor())

    with banco.Sessao() as sessao:
        if sessao.get(modelo.Empresa, "bella-massa") is not None:
            return
        for categoria in CATEGORIAS:
            sessao.add(modelo.Categoria(id=categoria, nome=categoria, ordem=1))
        for identificador, nome, ramo, cidade, _cresce, entrada in EMPRESAS:
            sessao.add(modelo.Empresa(
                id=identificador, nome=nome, plano="piloto",
                email_aviso=f"{entrada}@exemplo.com.br",
            ))
            sessao.flush()
            sessao.add(modelo.Comercio(
                id=identificador, empresa_id=identificador, nome=nome, ramo=ramo,
                cidade=cidade, tem_termo=True, categorias_combinadas=True,
            ))
            sessao.add(modelo.Usuario(
                id=f"u-{identificador}", empresa_id=identificador, email=entrada,
                nome=nome, papel="dono", senha_hash=senha_hash,
            ))
        # A empresa da equipe e a conta de administrador.
        sessao.add(modelo.Empresa(id="radar", nome="Equipe do Radar", plano="interno"))
        sessao.flush()
        sessao.add(modelo.Usuario(
            id="admin", empresa_id="radar", email="admin", nome="Administrador",
            papel="admin", senha_hash=senha_hash,
        ))
        sessao.commit()

    for identificador, _nome, _ramo, _cidade, cresce, _entrada in EMPRESAS:
        with banco.Sessao() as sessao:
            motor.coletar(
                sessao, identificador, identificador,
                _avaliacoes(identificador, cresce, semente=len(identificador)),
                hoje=HOJE,
            )
            sessao.commit()
    assert uuid  # o import existe para o motor; silencia o linter sem mudar o motor
