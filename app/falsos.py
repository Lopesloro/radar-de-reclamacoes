"""Dados de mentira com o formato dos contratos.

Servem para as telas funcionarem antes de o motor ficar pronto. Cada função tem
a mesma assinatura da versão real; quando a real chegar, `app/servicos.py` troca
a chamada e as telas nem percebem.

Tudo aqui é fictício e determinístico: semente fixa e data fixa. Nenhuma
avaliação foi escrita por cliente de verdade, e nenhum nome real aparece.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import replace
from datetime import date, datetime, timedelta
from functools import cache, lru_cache

from app.contratos import (
    CATEGORIAS,
    AcuraciaClassificacao,
    AcuraciaPrevisao,
    Alerta,
    AvaliacaoTela,
    Cenario,
    EtapaParceiro,
    EventoDiario,
    Hipotese,
    Investigacao,
    LinhaAcerto,
    MarcacaoDia,
    PassoInvestigacao,
    PlanoExperimento,
    PrevisaoMes,
    ResultadoExperimento,
    ResultadoLaboratorio,
    ResultadoSimulacao,
    ResumoComercio,
    SerieMensal,
    Turno,
)

# Data fixa: com date.today() os prints e os testes mudariam todo dia.
HOJE = date(2026, 10, 13)
MESES_FECHADOS = 12
HORAS_POR_TURNO = 5
SEMANAS_POR_MES = 4.33

EMPRESAS = (
    # id, nome fictício, ramo, cidade, assunto da história, início da história, semente
    ("bella-massa", "Pizzaria Bella Massa", "Restaurante", "Campinas, SP", "demora", date(2026, 6, 2), 11),
    ("sorriso-claro", "Clínica Sorriso Claro", "Odontologia", "Valinhos, SP", "atendimento",
     date(2026, 5, 5), 23),
    ("patinhas", "Pet Shop Patinhas", "Pet shop", "Campinas, SP", "preco", date(2026, 7, 1), 37),
)

# Quanto o assunto da história cresce a cada mês depois que a causa começa.
CRESCIMENTO = {"bella-massa": 0.16, "sorriso-claro": 0.16, "patinhas": 0.08}

NIVEL = {
    "bella-massa": {"atendimento": 22, "demora": 30, "preco": 15, "qualidade": 17, "ambiente": 9},
    "sorriso-claro": {"atendimento": 26, "demora": 19, "preco": 14, "qualidade": 12, "ambiente": 8},
    # Ambiente quase não aparece no pet shop: serve para mostrar "dados insuficientes".
    "patinhas": {"atendimento": 16, "demora": 13, "preco": 18, "qualidade": 11, "ambiente": 3},
}

FRASES = {
    "atendimento": (
        "Ninguém explicou direito o que ia ser feito.",
        "Fiquei sem resposta no WhatsApp.",
        "Me atenderam com pouca paciência.",
        "Pedi uma informação e me trataram mal.",
    ),
    "demora": (
        "Esperei muito tempo para ser atendido.",
        "Demorou bem mais do que o prometido.",
        "Fila longa e pouca gente atendendo.",
        "Fiquei quase uma hora esperando.",
    ),
    "preco": (
        "Achei o valor alto para o que entregam.",
        "Cobraram uma taxa que ninguém avisou.",
        "O preço subiu e nada melhorou.",
        "Mais caro do que outros da região.",
    ),
    "qualidade": (
        "O serviço precisou ser refeito.",
        "Veio diferente do combinado.",
        "Faltou capricho no resultado.",
        "Veio faltando item no pedido.",
    ),
    "ambiente": (
        "O lugar estava sujo.",
        "Muito barulho, difícil conversar.",
        "Não tinha onde sentar enquanto esperava.",
        "O banheiro estava sem papel.",
    ),
}

# Frases ligadas à causa de cada história. O "[nome]" mostra o mascaramento:
# nome de pessoa nunca chega à tela.
FRASES_DA_HISTORIA = {
    "bella-massa": (
        "O entregador demorou mais de uma hora numa sexta à noite.",
        "A pizza chegou fria, o motoboy se perdeu.",
        "Sábado à noite o pedido atrasou de novo.",
        "O entregador [nome] não achava o endereço.",
    ),
    "sorriso-claro": (
        "A recepcionista nova não sabia marcar o retorno.",
        "Fui mal recebido na recepção de manhã.",
        "Ninguém confirmou a minha consulta.",
        "A moça da recepção, [nome], foi seca comigo.",
    ),
    "patinhas": (
        "O banho ficou bem mais caro de uma hora pra outra.",
        "A tosa ficou cara demais agora.",
        "Subiram o preço sem avisar.",
        "Pelo valor novo, não compensa mais.",
    ),
}

ELOGIOS = (
    "Gostei muito, voltarei.",
    "Atendimento rápido e educado.",
    "Tudo certo, recomendo.",
)

VAGAS = (
    "Passei aqui hoje.",
    "Fui atendido.",
    "Já vim outras vezes.",
)

# O que já está combinado com cada parceiro.
COMBINADO = {
    "bella-massa": {"termo": True, "fonte": True, "categorias": True, "canal": True},
    "sorriso-claro": {"termo": True, "fonte": True, "categorias": True, "canal": False},
    "patinhas": {"termo": True, "fonte": True, "categorias": False, "canal": False},
}


def _mes(deslocamento: int) -> date:
    """Primeiro dia do mês, contado a partir do mês de HOJE (0 = mês corrente)."""
    total = HOJE.year * 12 + (HOJE.month - 1) + deslocamento
    return date(total // 12, total % 12 + 1, 1)


def _dias_no_mes(dia: date) -> int:
    proximo = date(dia.year + dia.month // 12, dia.month % 12 + 1, 1)
    return (proximo - date(dia.year, dia.month, 1)).days


def _historia(empresa_id: str) -> tuple[str, date]:
    for identificador, _, _, _, categoria, inicio, _ in EMPRESAS:
        if identificador == empresa_id:
            return categoria, inicio
    raise KeyError(empresa_id)


def _semente(empresa_id: str, categoria: str) -> int:
    # Nada de hash() de string: ele muda a cada execução do Python.
    base = next(s for i, *_, s in EMPRESAS if i == empresa_id)
    return base * 100 + CATEGORIAS.index(categoria)


def existe(empresa_id: str) -> bool:
    return any(e[0] == empresa_id for e in EMPRESAS)


# ------------------------------------------------------------ séries

@cache
def serie(empresa_id: str, categoria: str) -> SerieMensal:
    sorteio = random.Random(_semente(empresa_id, categoria))
    nivel = NIVEL[empresa_id][categoria]
    categoria_historia, inicio = _historia(empresa_id)

    meses: list[tuple[date, int]] = []
    for i in range(MESES_FECHADOS):
        mes = _mes(i - MESES_FECHADOS)
        sazonal = 1 + 0.05 * math.sin((mes.month + 1) * math.pi / 6)
        alta = 1.0
        if categoria == categoria_historia and mes >= date(inicio.year, inicio.month, 1):
            meses_desde = (mes.year - inicio.year) * 12 + mes.month - inicio.month + 1
            alta = 1 + CRESCIMENTO[empresa_id] * meses_desde
        valor = nivel * sazonal * alta + sorteio.uniform(-1.4, 1.4)
        meses.append((mes, max(0, round(valor))))

    ultimos = [v for _, v in meses[-4:]]
    tendencia = (ultimos[-1] - ultimos[0]) / 3
    if abs(tendencia) < 1:
        tendencia = 0.0
    sigma = max(1.2, 0.045 * ultimos[-1])

    previsoes = []
    for h in (1, 2):
        centro = max(0.0, ultimos[-1] + tendencia * h)
        largura = 1.2816 * sigma * math.sqrt(h)
        previsoes.append(PrevisaoMes(
            mes=_mes(h - 1),
            p10=max(0, round(centro - largura)),
            p50=round(centro),
            p90=round(centro + largura),
        ))

    fracao = round(HOJE.day / _dias_no_mes(HOJE), 2)
    parcial = (_mes(0), max(0, round(previsoes[0].p50 * fracao + sorteio.uniform(-1, 1))))
    return SerieMensal(empresa_id, categoria, tuple(meses), parcial, fracao, tuple(previsoes))


def series(empresa_id: str) -> tuple[SerieMensal, ...]:
    return tuple(serie(empresa_id, c) for c in CATEGORIAS)


def _crescimento(s: SerieMensal) -> float:
    return s.previsoes[0].p50 - s.ultimo


def _estado(s: SerieMensal) -> str:
    crescimento = _crescimento(s)
    if crescimento < 1.5 or crescimento / max(s.ultimo, 1) < 0.04:
        return "normal"
    # "Vai piorar" é quando nem o mínimo esperado volta ao nível de hoje.
    return "vai_piorar" if s.previsoes[0].p10 > s.ultimo else "fique_de_olho"


# ------------------------------------------------------------ avaliações

@cache
def avaliacoes(empresa_id: str, limite: int = 12) -> tuple[AvaliacaoTela, ...]:
    """As avaliações mais recentes do último mês fechado."""
    sorteio = random.Random(_semente(empresa_id, "atendimento") + 7)
    categoria_historia, _ = _historia(empresa_id)
    mes = _mes(-1)
    itens: list[AvaliacaoTela] = []
    sequencia = 0

    def nova(texto, categoria, estrelas, certeza, motivo):
        nonlocal sequencia
        sequencia += 1
        itens.append(AvaliacaoTela(
            id=f"{empresa_id}-{sequencia:03d}",
            data=date(mes.year, mes.month, sorteio.randint(1, _dias_no_mes(mes))),
            estrelas=estrelas,
            texto=texto,
            categoria=categoria,
            certeza=certeza,
            motivo_sem_assunto=motivo,
        ))

    for s in series(empresa_id):
        frases = FRASES[s.categoria]
        if s.categoria == categoria_historia:
            frases = frases + FRASES_DA_HISTORIA[empresa_id] * 2
        for _ in range(s.ultimo):
            nova(sorteio.choice(frases), s.categoria, sorteio.choice((1, 1, 2, 2, 3)),
                 sorteio.choice(("alta", "alta", "media")), None)
    for _ in range(sorteio.randint(10, 15)):
        nova(sorteio.choice(ELOGIOS), None, sorteio.choice((4, 5, 5)), None, "não é reclamação")
    for _ in range(sorteio.randint(3, 6)):
        nova(None, None, sorteio.choice((1, 3, 4, 5)), None, "só tem estrelas")
    for _ in range(sorteio.randint(2, 4)):
        nova(sorteio.choice(VAGAS), None, sorteio.choice((2, 3, 4)), "baixa", "frase vaga demais")

    itens.sort(key=lambda a: (a.data, a.id), reverse=True)
    return tuple(itens[:limite]) if limite else tuple(itens)


# ------------------------------------------------------------ resumo e avisos

@cache
def comercios() -> tuple[ResumoComercio, ...]:
    lista = []
    for identificador, nome, ramo, cidade, *_ in EMPRESAS:
        todas = series(identificador)
        lidas = avaliacoes(identificador, limite=0)
        dominante = max(todas, key=lambda s: s.ultimo)
        em_alta = max(todas, key=_crescimento)
        passos = etapas(identificador)
        lista.append(ResumoComercio(
            empresa_id=identificador,
            nome=nome,
            ramo=ramo,
            cidade=cidade,
            estado=_estado(em_alta),
            mes_referencia=_mes(-1),
            avaliacoes_lidas=len(lidas),
            reclamacoes=sum(s.ultimo for s in todas),
            sem_assunto=sum(1 for a in lidas if a.categoria is None),
            nota_media=round(sum(a.estrelas for a in lidas) / len(lidas), 1),
            mais_reclamado=dominante.categoria,
            mais_reclamado_qtd=dominante.ultimo,
            vai_crescer=em_alta.categoria,
            vai_crescer_de=em_alta.ultimo,
            vai_crescer_para=em_alta.previsoes[0],
            etapas_concluidas=sum(1 for p in passos if p.estado == "feito"),
            etapas_total=len(passos),
        ))
    return tuple(lista)


def comercio(empresa_id: str) -> ResumoComercio | None:
    return next((c for c in comercios() if c.empresa_id == empresa_id), None)


@cache
def alertas() -> tuple[Alerta, ...]:
    gerados = []
    for c in comercios():
        for s in series(c.empresa_id):
            estado = _estado(s)
            if estado == "normal":
                continue
            gerados.append(Alerta(
                id=f"{c.empresa_id}-{s.categoria}",
                empresa_id=c.empresa_id,
                empresa_nome=c.nome,
                categoria=s.categoria,
                estado=estado,
                atual=s.ultimo,
                previsto=s.previsoes[0],
                gerado_em=HOJE,
                situacao="aberto",
            ))
    gerados.sort(key=lambda a: a.previsto.p50 - a.atual, reverse=True)
    return tuple(gerados)


# ------------------------------------------------------------ "Dá para confiar?"

@lru_cache(maxsize=1)
def acuracia_classificacao() -> AcuraciaClassificacao:
    sorteio = random.Random(101)
    amostras = {"atendimento": 210, "demora": 180, "preco": 150, "qualidade": 140, "ambiente": 120}
    linhas = []
    for categoria in CATEGORIAS:
        precisao = round(sorteio.uniform(0.76, 0.91), 2)
        recall = round(sorteio.uniform(0.72, 0.90), 2)
        f1 = round(2 * precisao * recall / (precisao + recall), 2)
        linhas.append(LinhaAcerto(categoria, precisao, recall, f1, amostras[categoria]))
    total = sum(amostras.values())
    maior = max(amostras, key=amostras.get)
    acerto_regua = amostras[maior] / total
    f1_regua = 2 * acerto_regua / (acerto_regua + 1) / len(CATEGORIAS)
    return AcuraciaClassificacao(
        linhas=tuple(linhas),
        acerto_geral=0.82,
        acerto_regua=round(acerto_regua, 2),
        f1_macro=round(sum(linha.f1 for linha in linhas) / len(linhas), 2),
        f1_macro_regua=round(f1_regua, 2),
        amostra=total,
        categoria_regua=maior,
    )


@lru_cache(maxsize=1)
def acuracia_previsao() -> AcuraciaPrevisao:
    s = serie("bella-massa", "demora")
    valores = [v for _, v in s.meses]
    pontos = []
    for i in range(len(valores) - 6, len(valores)):
        anterior = valores[i - 1]
        tendencia = (valores[i - 1] - valores[i - 4]) / 3
        previsto = round(anterior + (tendencia if abs(tendencia) >= 1 else 0))
        pontos.append((s.meses[i][0], previsto, valores[i]))
    return AcuraciaPrevisao(
        erro_medio=2.1,
        erro_medio_regua=2.9,
        cobertura=0.81,
        janelas=90,
        exemplo="demora na Pizzaria Bella Massa",
        pontos=tuple(pontos),
    )


def etapas(empresa_id: str) -> tuple[EtapaParceiro, ...]:
    combinado = COMBINADO[empresa_id]
    itens = (
        ("Autorização assinada",
         "O dono autorizou por escrito a leitura das avaliações, com prazo e direito de cancelar.",
         combinado["termo"], "Falta a assinatura do responsável pela empresa.", False),
        ("Avaliações chegando",
         "As avaliações públicas do negócio são lidas todo dia.",
         combinado["fonte"], "Falta escolher de onde as avaliações vão vir.", False),
        ("Seis meses de histórico",
         "Com seis meses fechados, o sistema já consegue estimar o mês seguinte.",
         True, "Faltam meses de histórico.", True),
        ("Assuntos combinados com o dono",
         "Os cinco assuntos usam as palavras que o dono usa no dia a dia.",
         combinado["categorias"], "Falta uma conversa de meia hora para confirmar os assuntos.", True),
        ("Separação por assunto conferida",
         "O sistema acerta o assunto mais vezes que o chute mais simples.",
         True, "Falta separar mais avaliações à mão para conferir.", True),
        ("Estimativa conferida",
         "A estimativa erra menos que repetir o número do mês passado.",
         True, "Enquanto não errar menos, a tela mostra o mês passado e diz isso.", True),
        ("Aviso chegando ao dono",
         "O aviso de alta chega por e-mail ou WhatsApp, para quem o dono escolheu.",
         combinado["canal"], "Falta escolher entre e-mail e WhatsApp e quem recebe.", False),
    )
    resultado = []
    for numero, (titulo, detalhe, feito, falta, andamento) in enumerate(itens, start=1):
        estado = "feito" if feito else ("andamento" if andamento else "pendente")
        resultado.append(EtapaParceiro(numero, titulo, estado, detalhe, None if feito else falta))
    return tuple(resultado)


# ------------------------------------------------------------ investigação

DIARIO = {
    "bella-massa": (
        (date(2026, 6, 2), "equipe", "Entrou um entregador novo para as noites de sexta e sábado."),
        (date(2026, 7, 15), "produto", "Cardápio de inverno, com três sabores novos."),
        (date(2026, 9, 1), "preco", "Taxa de entrega subiu de R$ 6 para R$ 8."),
    ),
    "sorriso-claro": (
        (date(2026, 5, 5), "equipe", "Recepcionista nova nas manhãs de segunda a quarta."),
        (date(2026, 6, 20), "estrutura", "Pintura da sala de espera."),
    ),
    "patinhas": (
        (date(2026, 7, 1), "preco", "Tabela nova: banho e tosa 18% mais caros."),
        (date(2026, 8, 3), "horario", "Passou a abrir aos domingos de manhã."),
    ),
}


def eventos_diario(empresa_id: str) -> tuple[EventoDiario, ...]:
    return tuple(
        EventoDiario(f"{empresa_id}-ev{i}", empresa_id, data, tipo, descricao)
        for i, (data, tipo, descricao) in enumerate(DIARIO.get(empresa_id, ()), start=1)
    )


def _hipotese(i, origem, frase, categoria, teste, antes, depois, faixa, q, veredito, forca, exemplos):
    efeito = round(depois - antes, 1)
    return Hipotese(
        id=f"h{i}", origem=origem, frase=frase, categoria=categoria, teste=teste,
        antes_semana=antes, depois_semana=depois, efeito_semana=efeito,
        efeito_min=round(efeito - faixa, 1), efeito_max=round(efeito + faixa, 1),
        q_valor=q, veredito=veredito, forca=forca, avaliacoes_exemplo=tuple(exemplos),
    )


HISTORIAS = {
    ("bella-massa", "demora"): (
        (date(2026, 4, 6), date(2026, 6, 1)),
        (date(2026, 6, 2), date(2026, 10, 12)),
        (
            ("dia_turno", "A demora aumentou nas noites de sexta e sábado depois de 2 de junho, "
             "quando entrou o entregador novo.", "antes_depois", 4.1, 7.9, 1.2, 0.001,
             "sustentada", "forte", FRASES_DA_HISTORIA["bella-massa"][:3]),
            ("termo_novo", "Os clientes passaram a falar muito mais em “entregador” "
             "e “motoboy”.", "termos_novos", 1.2, 3.4, 0.9, 0.004,
             "sustentada", "moderada", FRASES_DA_HISTORIA["bella-massa"][1:]),
            ("ia", "Pode ser que a pizza esteja saindo da cozinha mais devagar.",
             "antes_depois", 2.0, 2.4, 1.1, 0.41, "inconclusiva", "fraca",
             ("Demorou bem mais do que o prometido.",)),
            ("clima", "Chove mais nesta época, e chuva atrasa as entregas.", "clima",
             6.2, 6.9, 1.4, 0.38, "inconclusiva", "fraca", ()),
            ("diario", "O cardápio de inverno, de 15 de julho, deixou o preparo mais lento.",
             "antes_depois", 6.6, 6.8, 0.8, 0.83, "descartada", "fraca", ()),
            ("calendario", "Os feriados de junho e julho aumentaram a demora.", "feriado",
             6.4, 6.5, 0.6, 0.91, "descartada", "fraca", ()),
        ),
    ),
    ("sorriso-claro", "atendimento"): (
        (date(2026, 3, 9), date(2026, 5, 4)),
        (date(2026, 5, 5), date(2026, 10, 12)),
        (
            ("dia_turno", "O atendimento piorou nas manhãs de segunda a quarta depois de 5 de "
             "maio, quando entrou a recepcionista nova.", "antes_depois", 2.3, 5.6, 1.0, 0.002,
             "sustentada", "forte", FRASES_DA_HISTORIA["sorriso-claro"][:3]),
            ("diario", "A pintura da sala de espera, em 20 de junho, incomodou os pacientes.",
             "antes_depois", 6.1, 6.3, 0.9, 0.77, "descartada", "fraca", ()),
            ("clima", "Dias de calor deixam os pacientes mais irritados.", "clima",
             5.8, 6.2, 1.2, 0.52, "inconclusiva", "fraca", ()),
        ),
    ),
    ("patinhas", "preco"): (
        (date(2026, 5, 4), date(2026, 6, 30)),
        (date(2026, 7, 1), date(2026, 10, 12)),
        (
            ("diario", "As reclamações de preço subiram depois de 1º de julho, quando banho e "
             "tosa ficaram 18% mais caros.", "antes_depois", 3.9, 6.8, 1.1, 0.003,
             "sustentada", "forte", FRASES_DA_HISTORIA["patinhas"][:3]),
            ("diario", "Abrir aos domingos, desde 3 de agosto, trouxe clientes que acham caro.",
             "antes_depois", 6.5, 6.9, 1.3, 0.61, "inconclusiva", "fraca", ()),
        ),
    ),
}


def investigar(sessao, empresa_id: str, categoria: str, alerta_id: str | None = None,
               usar_ia: bool = True) -> Investigacao:
    momento = datetime(2026, 10, 13, 9, 30)
    s = serie(empresa_id, categoria)
    passos = (
        PassoInvestigacao(1, momento, "separou os períodos",
                          "reclamações por dia", "8 semanas de base e o período da alta"),
        PassoInvestigacao(2, momento + timedelta(seconds=2), "leu o diário do negócio",
                          f"{len(eventos_diario(empresa_id))} mudanças registradas",
                          "cada mudança virou uma possível causa"),
        PassoInvestigacao(3, momento + timedelta(seconds=3), "juntou calendário e clima",
                          "feriados e chuva por dia", "duas possíveis causas"),
        PassoInvestigacao(4, momento + timedelta(seconds=5), "procurou dias e turnos com mais reclamação",
                          "reclamações por dia da semana e turno", "uma concentração encontrada"),
        PassoInvestigacao(5, momento + timedelta(seconds=8), "pediu ideias à IA",
                          "avaliações já sem nomes e telefones", "1 ideia aceita, 0 recusadas"),
        PassoInvestigacao(6, momento + timedelta(seconds=11), "testou cada possível causa",
                          "um teste para cada uma", "conta corrigida para muitas tentativas"),
        PassoInvestigacao(7, momento + timedelta(seconds=12), "ordenou o resultado",
                          "vereditos e força", "da mais provável para a menos provável"),
    )

    if s.ultimo < 8:
        return Investigacao(
            id=f"inv-{empresa_id}-{categoria}", empresa_id=empresa_id, alerta_id=alerta_id,
            categoria=categoria, periodo_alta=(date(2026, 9, 1), date(2026, 10, 12)),
            periodo_base=(date(2026, 7, 7), date(2026, 8, 31)), hipoteses=(), passos=passos[:1],
            usou_ia=False, estado="dados_insuficientes",
            motivo=f"Chegaram só {s.ultimo} reclamações deste assunto no último mês. Com tão "
                   "pouco, qualquer diferença pode ser acaso. Com pelo menos 30 no período, a "
                   "investigação fica possível.",
        )

    historia = HISTORIAS.get((empresa_id, categoria))
    if historia is None:
        base, alta = (date(2026, 7, 7), date(2026, 8, 31)), (date(2026, 9, 1), date(2026, 10, 12))
        nivel = round(s.ultimo / SEMANAS_POR_MES, 1)
        candidatos = (
            ("clima", "Chuva e calor mexem nas reclamações deste assunto.", "clima",
             nivel, round(nivel + 0.3, 1), 1.0, 0.58, "inconclusiva", "fraca", ()),
            ("calendario", "Os feriados mexem nas reclamações deste assunto.", "feriado",
             nivel, round(nivel + 0.1, 1), 0.7, 0.88, "descartada", "fraca", ()),
        )
    else:
        base, alta, candidatos = historia

    if not usar_ia:
        candidatos = tuple(c for c in candidatos if c[0] != "ia")
    hipoteses = tuple(_hipotese(i, *c[:2], categoria, *c[2:])
                      for i, c in enumerate(candidatos, start=1))
    return Investigacao(
        id=f"inv-{empresa_id}-{categoria}", empresa_id=empresa_id, alerta_id=alerta_id,
        categoria=categoria, periodo_alta=alta, periodo_base=base, hipoteses=hipoteses,
        passos=passos if usar_ia else tuple(p for p in passos if p.ordem != 5),
        usou_ia=usar_ia and any(h.origem == "ia" for h in hipoteses),
        estado="concluida", motivo=None,
    )


# ------------------------------------------------------------ simulador "E se?"

OPERACAO = {
    # (dia_semana, período): (equipe, clientes no turno, minutos por atendimento)
    "bella-massa": {
        **{(d, "tarde"): (1, 6, 25) for d in range(7)},
        **{(d, "noite"): (2, 15, 25) for d in (0, 1, 2, 3, 6)},
        # Sexta e sábado à noite a equipe quase não dá conta: é onde a demora nasce.
        (4, "noite"): (2, 22, 25),
        (5, "noite"): (2, 23, 25),
    },
    "sorriso-claro": {
        **{(d, "manha"): (1, 18, 12) for d in (0, 1, 2)},
        **{(d, "manha"): (1, 14, 12) for d in (3, 4)},
        **{(d, "tarde"): (1, 15, 12) for d in range(5)},
        (5, "manha"): (1, 10, 12),
    },
    "patinhas": {
        **{(d, "manha"): (2, 9, 50) for d in range(6)},
        **{(d, "tarde"): (2, 8, 50) for d in range(6)},
        (6, "manha"): (1, 5, 50),
    },
}
CUSTO_HORA = {"bella-massa": 18.0, "sorriso-claro": 22.0, "patinhas": 20.0}
CATEGORIAS_DO_SIMULADOR = ("demora", "atendimento")


def operacao(empresa_id: str) -> tuple[Turno, ...]:
    custo = CUSTO_HORA[empresa_id]
    turnos = []
    for dia in range(7):
        for periodo in ("manha", "tarde", "noite"):
            equipe, clientes, minutos = OPERACAO[empresa_id].get((dia, periodo), (0, 0, 0))
            turnos.append(Turno(dia, periodo, equipe, float(clientes), float(minutos), custo))
    return tuple(turnos)


def _espera_minutos(turno: Turno) -> float:
    """Espera média na fila (Erlang C). Turno sem equipe, ou que não dá conta, tem teto."""
    if turno.equipe <= 0 or turno.clientes <= 0:
        return 0.0
    chegadas_hora = turno.clientes / HORAS_POR_TURNO
    atendimentos_hora = 60 / turno.minutos_atendimento
    carga = chegadas_hora / atendimentos_hora
    ocupacao = carga / turno.equipe
    if ocupacao >= 1:
        return 90.0
    soma = sum(carga ** k / math.factorial(k) for k in range(turno.equipe))
    topo = carga ** turno.equipe / math.factorial(turno.equipe) / (1 - ocupacao)
    chance_esperar = topo / (soma + topo)
    return min(90.0, chance_esperar / (turno.equipe * atendimentos_hora - chegadas_hora) * 60)


def simular(sessao, empresa_id: str, cenario: Cenario) -> ResultadoSimulacao:
    atual = operacao(empresa_id)
    mudancas = {(t.dia_semana, t.periodo): t for t in cenario.mudancas}
    novo = tuple(mudancas.get((t.dia_semana, t.periodo), t) for t in atual)
    reclamacoes_atual = float(serie(empresa_id, cenario.categoria).previsoes[0].p50)

    def espera_media(turnos):
        peso = sum(t.clientes for t in turnos if t.equipe > 0)
        return sum(_espera_minutos(t) * t.clientes for t in turnos if t.equipe > 0) / max(peso, 1)

    espera_atual, espera_nova = espera_media(atual), espera_media(novo)
    custo = sum(
        (n.equipe - a.equipe) * HORAS_POR_TURNO * a.custo_hora * SEMANAS_POR_MES
        for a, n in zip(atual, novo, strict=True)
    )

    if cenario.categoria not in CATEGORIAS_DO_SIMULADOR:
        return ResultadoSimulacao(cenario, reclamacoes_atual, reclamacoes_atual,
                                  reclamacoes_atual, reclamacoes_atual, espera_atual, espera_nova,
                                  round(custo, 2), None, False,
                                  "Por enquanto, o simulador só entende demora e atendimento, "
                                  "que dependem de quantas pessoas trabalham em cada turno.")

    # Só uma parte das reclamações vem da espera; o resto não muda com a equipe.
    parte_da_espera = 0.7
    razao = (espera_nova + 1) / (espera_atual + 1)
    estimativa = reclamacoes_atual * (1 - parte_da_espera + parte_da_espera * razao ** 0.6)
    evitadas = reclamacoes_atual - estimativa
    return ResultadoSimulacao(
        cenario=cenario,
        reclamacoes_atual=reclamacoes_atual,
        reclamacoes_cenario=round(estimativa, 1),
        minimo=round(estimativa * 0.86, 1),
        maximo=round(estimativa * 1.14, 1),
        espera_atual_min=round(espera_atual, 1),
        espera_cenario_min=round(espera_nova, 1),
        custo_extra_mes=round(custo, 2),
        custo_por_reclamacao_evitada=round(custo / evitadas, 2) if evitadas >= 1 and custo > 0 else None,
        confiavel=True,
        motivo=None,
    )


def cenario_sugerido(investigacao: Investigacao) -> Cenario | None:
    turnos = {
        ("bella-massa", "demora"): ((4, "noite"), (5, "noite")),
        ("sorriso-claro", "atendimento"): ((0, "manha"), (1, "manha"), (2, "manha")),
    }.get((investigacao.empresa_id, investigacao.categoria))
    if not turnos:
        return None
    atual = {(t.dia_semana, t.periodo): t for t in operacao(investigacao.empresa_id)}
    mudancas = tuple(replace(atual[chave], equipe=atual[chave].equipe + 1) for chave in turnos)
    return Cenario("Uma pessoa a mais nos turnos da causa provável",
                   investigacao.categoria, mudancas)


# ------------------------------------------------------------ teste na prática

def _sorteio_balanceado(dias: list[date], semente: int) -> tuple[tuple[date, ...], tuple[date, ...]]:
    """Metade dos dias de cada dia da semana recebe a mudança."""
    sorteio = random.Random(semente)
    com, sem = [], []
    for dia_semana in sorted({d.weekday() for d in dias}):
        grupo = [d for d in dias if d.weekday() == dia_semana]
        sorteio.shuffle(grupo)
        metade = len(grupo) // 2
        com += grupo[:metade]
        sem += grupo[metade:]
    return tuple(sorted(com)), tuple(sorted(sem))


def _selo(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()


@lru_cache(maxsize=1)
def _planos() -> tuple[PlanoExperimento, ...]:
    dias_bella = [date(2026, 9, 11) + timedelta(days=d) for d in range(44)]
    dias_bella = [d for d in dias_bella if d.weekday() in (4, 5)]
    com_b, sem_b = _sorteio_balanceado(dias_bella, 501)

    dias_sorriso = [date(2026, 7, 6) + timedelta(days=d) for d in range(40)]
    dias_sorriso = [d for d in dias_sorriso if d.weekday() in (0, 1, 2)]
    com_s, sem_s = _sorteio_balanceado(dias_sorriso, 502)

    return (
        PlanoExperimento(
            id="exp-bella-entregador", empresa_id="bella-massa", categoria="demora",
            acao="Um entregador a mais nas noites de sexta e sábado",
            inicio=dias_bella[0], fim=dias_bella[-1], dias_com_acao=com_b, dias_sem_acao=sem_b,
            menor_efeito_detectavel=8.0, selo=_selo(f"bella|{com_b}|{sem_b}"),
            selado_em=datetime(2026, 9, 10, 18, 4), estado="em_andamento",
        ),
        PlanoExperimento(
            id="exp-sorriso-recepcao", empresa_id="sorriso-claro", categoria="atendimento",
            acao="Recepcionista experiente junto com a nova nas manhãs de segunda a quarta",
            inicio=dias_sorriso[0], fim=dias_sorriso[-1], dias_com_acao=com_s, dias_sem_acao=sem_s,
            menor_efeito_detectavel=6.0, selo=_selo(f"sorriso|{com_s}|{sem_s}"),
            selado_em=datetime(2026, 7, 3, 11, 20), estado="encerrado",
        ),
    )


def experimentos(empresa_id: str | None = None) -> tuple[PlanoExperimento, ...]:
    return tuple(p for p in _planos() if empresa_id is None or p.empresa_id == empresa_id)


def experimento(plano_id: str) -> PlanoExperimento | None:
    return next((p for p in _planos() if p.id == plano_id), None)


def marcacoes(plano_id: str) -> tuple[MarcacaoDia, ...]:
    plano = experimento(plano_id)
    if plano is None:
        return ()
    com = set(plano.dias_com_acao)
    resultado = []
    for dia in sorted(plano.dias_com_acao + plano.dias_sem_acao):
        if dia > HOJE:
            seguiu = None
        else:
            # Um dia em que o dono não conseguiu seguir o sorteio: acontece na vida real.
            seguiu = dia != date(2026, 9, 26)
        resultado.append(MarcacaoDia(dia, dia in com, seguiu))
    return tuple(resultado)


def analisar(sessao, plano_id: str) -> ResultadoExperimento | None:
    plano = experimento(plano_id)
    if plano is None or plano.estado != "encerrado":
        return None
    return ResultadoExperimento(
        plano_id=plano_id,
        dias_observados=len(plano.dias_com_acao) + len(plano.dias_sem_acao),
        adesao=0.94,
        media_com=1.2,
        media_sem=1.9,
        efeito_mes=-9.0,
        efeito_min=-14.0,
        efeito_max=-4.0,
        veredito="funcionou",
        frase="Nas manhãs com a recepcionista experiente, chegaram cerca de 9 reclamações "
              "de atendimento a menos por mês (entre 4 e 14 a menos).",
    )


# ------------------------------------------------------------ laboratório

def laboratorio() -> ResultadoLaboratorio:
    return ResultadoLaboratorio(
        cenarios=200,
        acerto_agente=0.74,
        acerto_agente_top3=0.91,
        acerto_agente_sem_ia=0.70,
        acerto_regua=0.41,
        falso_alarme_agente=0.06,
        cobertura_simulador=0.83,
        falso_positivo_aa=0.05,
        poder_experimento=0.80,
    )
