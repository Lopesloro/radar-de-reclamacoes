"""A conta de demonstração: avaliações e cadastros simulados, com semente fixa.

Existe para a banca e para quem quer ver o sistema funcionando com volume. Duas
regras a seguram:

1. **Só entra em empresa marcada como demonstração** (plano "demonstracao"), e
   toda tela dessa empresa avisa, numa faixa no topo, que os dados são simulados.
2. **Entra pelo mesmo caminho do dado real.** As avaliações simuladas vão para
   `motor.coletar`, que mascara, classifica, conta, estima e avisa como faz com
   as do Google. O diário, os turnos e o teste são gravados nas mesmas tabelas
   em que o dono grava. Nenhuma tela tem caminho especial para a demonstração.

A história simulada (uma cantina), para as três telas terem o que mostrar:

- Há 120 dias saiu um garçom da noite e ninguém entrou no lugar. As reclamações
  de demora mais que dobram depois disso, e se concentram de sexta a domingo.
- Há 60 dias a taxa de serviço subiu. As reclamações de preço sobem.
- Há 300 dias entrou o cardápio de inverno. Nada muda: é a hipótese que o
  "Por quê?" deve descartar.
- Nas noites de sexta a domingo a equipe não dá conta da fila (o "E se?" mostra).
- Um teste de 42 dias, já terminado, com uma pessoa a mais no salão à noite nos
  dias sorteados. Nesses dias a demora cai a menos de um terço.
"""

from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.banco import modelo
from app.coleta import AvaliacaoBruta, motor
from app.modelos import corpus
from app.modelos import experimento as teste

SEMENTE = 2027
DIAS_DE_HISTORICO = 450
# Reclamações por dia, de cada assunto, antes de qualquer mudança.
BASE = {"atendimento": 0.22, "demora": 0.3, "preco": 0.2, "qualidade": 0.14, "ambiente": 0.07}
ELOGIOS_POR_DIA = 0.8
SO_ESTRELAS_POR_DIA = 0.5

EVENTOS = (
    # dias atrás, tipo, descrição
    (300, "produto", "Entrou o cardápio de inverno, com quatro pratos novos."),
    (120, "equipe", "Saiu um garçom do turno da noite e ninguém entrou no lugar."),
    (60, "preco", "A taxa de serviço passou de 10% para 12%."),
)
TESTE = {"acao": "Uma pessoa a mais no salão à noite", "categoria": "demora",
         "comeca_dias_atras": 50, "dias": 42}


class JaTemDados(Exception):
    pass


def _poisson(sorteio: random.Random, media: float) -> int:
    """Quantos eventos num dia, pelo método de Knuth (médias pequenas)."""
    limite, k, p = pow(2.718281828459045, -media), 0, 1.0
    while True:
        p *= sorteio.random()
        if p <= limite:
            return k
        k += 1


def _taxa(categoria: str, dia: date, hoje: date, dias_com_teste: set[date]) -> float:
    taxa = BASE[categoria]
    fim_de_semana = dia.weekday() >= 4
    if categoria == "demora" and dia >= hoje - timedelta(days=120):
        taxa *= 5.0 if fim_de_semana else 1.2
        if dia in dias_com_teste:
            taxa *= 0.2
    if categoria == "preco" and dia >= hoje - timedelta(days=60):
        taxa *= 4.0
    return taxa


def avaliacoes(hoje: date, dias_com_teste: set[date]) -> list[AvaliacaoBruta]:
    sorteio = random.Random(SEMENTE)
    brutas: list[AvaliacaoBruta] = []
    numero = 0
    for atras in range(DIAS_DE_HISTORICO, 0, -1):
        dia = hoje - timedelta(days=atras)
        movimento = 1.3 if dia.weekday() >= 4 else 1.0
        for categoria in BASE:
            for _ in range(_poisson(sorteio, _taxa(categoria, dia, hoje, dias_com_teste))):
                numero += 1
                brutas.append(AvaliacaoBruta(f"sim-{numero}", dia, sorteio.choice((1, 1, 2, 2, 3)),
                                             sorteio.choice(corpus.FRASES[categoria])))
        for _ in range(_poisson(sorteio, ELOGIOS_POR_DIA * movimento)):
            numero += 1
            brutas.append(AvaliacaoBruta(f"sim-{numero}", dia, sorteio.choice((4, 5, 5)),
                                         sorteio.choice(corpus.ELOGIOS)))
        for _ in range(_poisson(sorteio, SO_ESTRELAS_POR_DIA * movimento)):
            numero += 1
            brutas.append(AvaliacaoBruta(f"sim-{numero}", dia, sorteio.choice((3, 4, 5, 5)), None))
    return brutas


def _turnos(empresa_id: str, comercio_id: str) -> list[modelo.Turno]:
    linhas = []
    for dia in range(7):
        fim_de_semana = dia >= 4
        for periodo, equipe, clientes in (
            ("manha", 2 if dia >= 5 else 0, 35 if dia >= 5 else 0),
            ("tarde", 3, 85 if fim_de_semana else 60),
            ("noite", 2, 95 if fim_de_semana else 45),
        ):
            linhas.append(modelo.Turno(
                id=f"tu-{uuid.uuid4().hex[:16]}", empresa_id=empresa_id, comercio_id=comercio_id,
                dia_semana=dia, periodo=periodo, equipe=equipe, clientes=clientes,
                minutos_atendimento=6.0, custo_hora=18.0,
            ))
    return linhas


def preencher(sessao: Session, empresa_id: str, comercio_id: str, *, usuario_id: str | None = None,
              hoje: date | None = None) -> motor.Resultado:
    """Grava a demonstração inteira num negócio vazio de uma empresa de demonstração."""
    hoje = hoje or date.today()
    empresa = sessao.get(modelo.Empresa, empresa_id)
    negocio = sessao.get(modelo.Comercio, comercio_id)
    if empresa is None or negocio is None or negocio.empresa_id != empresa_id:
        raise ValueError("negócio não encontrado nessa empresa")
    if empresa.plano != "demonstracao":
        raise ValueError("dado simulado só entra em cliente com o plano demonstração")
    ja_tem = sessao.scalar(select(func.count(modelo.Avaliacao.id)).where(
        modelo.Avaliacao.comercio_id == comercio_id)) or 0
    if ja_tem:
        raise JaTemDados(f"esse negócio já tem {ja_tem} avaliações; a demonstração entra só em negócio vazio")

    inicio = hoje - timedelta(days=TESTE["comeca_dias_atras"])
    com, sem = teste.sortear(inicio, TESTE["dias"], semente=SEMENTE)
    resultado = motor.coletar(sessao, empresa_id, comercio_id, avaliacoes(hoje, set(com)),
                              usuario_id=usuario_id, hoje=hoje)

    for atras, tipo, descricao in EVENTOS:
        sessao.add(modelo.EventoDiario(
            id=f"ev-{uuid.uuid4().hex[:16]}", empresa_id=empresa_id, comercio_id=comercio_id,
            data=hoje - timedelta(days=atras), tipo=tipo, descricao=descricao,
        ))
    sessao.add_all(_turnos(empresa_id, comercio_id))

    fim = inicio + timedelta(days=TESTE["dias"] - 1)
    selado_em = datetime.combine(inicio - timedelta(days=1), datetime.min.time()).replace(hour=20)
    plano_id = f"tp-{uuid.uuid4().hex[:16]}"
    sessao.add(modelo.Experimento(
        id=plano_id, empresa_id=empresa_id, comercio_id=comercio_id, categoria_id=TESTE["categoria"],
        acao=TESTE["acao"], inicio=inicio, fim=fim, dias_com_acao=",".join(d.isoformat() for d in com),
        menor_efeito=teste.menor_efeito(BASE["demora"] * 2.3, len(com), len(sem)),
        selo=teste.selar(TESTE["categoria"], TESTE["acao"], inicio, fim, com, selado_em),
        selado_em=selado_em, estado="em_andamento",
    ))
    sessao.flush()      # a marcação aponta para o plano: ele precisa existir antes
    sorteio = random.Random(SEMENTE + 1)
    for dia in sorted(set(com) | set(sem)):
        if dia < hoje:
            sessao.add(modelo.MarcacaoDia(empresa_id=empresa_id, experimento_id=plano_id, data=dia,
                                          seguiu=sorteio.random() > 0.07))
    sessao.flush()
    return resultado
