"""O caminho que uma avaliação percorre, do que a plataforma entregou até o aviso.

    plataforma -> AvaliacaoBruta -> máscara -> avaliacao
                                            -> classificacao (assunto ou abstenção)
                                            -> serie_mensal (contagem por mês)
                                            -> previsao (mês corrente e o seguinte)
                                            -> alerta (quando o assunto deve crescer)

Três decisões que valem explicar:

**Idempotente.** Rodar a coleta duas vezes no mesmo dia não dobra número nenhum.
A avaliação é reconhecida por `(comercio_id, id_origem)`, que é chave única no
banco: a segunda vinda da mesma avaliação é descartada pelo próprio banco, não
pela memória do programa. Série, previsão e aviso são refeitos do zero a partir
das classificações, em vez de incrementados.

**A máscara vem antes do banco.** O texto é limpo em `app/coleta/mascara.py` e
só então gravado. O que não foi gravado não vaza depois.

**A abstenção é gravada.** Avaliação que o modelo não soube classificar entra com
`categoria_id` nulo e o motivo. É o que faz a tela poder dizer "32 avaliações
sem assunto" em vez de somar tudo em algum assunto e inflar uma contagem.
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import auditoria
from app.banco import modelo
from app.coleta import AvaliacaoBruta
from app.coleta.mascara import aplicar as mascarar
from app.contratos import CATEGORIAS
from app.modelos import LIMITE_CONFIANCA, ativo, previsao

MOTIVO_SEM_CONFIANCA = "o texto não deixou claro o assunto"
MOTIVO_SEM_TEXTO = "a avaliação é só nota, sem texto"

# Acima disto, a classificação usa o modelo local mesmo com a IA configurada.
#
# A conta: a IA vai em lotes de 8 e a conta gratuita aceita 12 chamadas por
# minuto, então 450 avaliações (um histórico normal de 15 meses, que é o primeiro
# arquivo de todo cliente novo) são 57 chamadas e cerca de cinco minutos. Cinco
# minutos **dentro de um pedido web**: o operador acha que travou, o navegador ou
# o proxy desiste no meio, e a transação morre com a importação pela metade.
# Aconteceu no primeiro teste em produção.
#
# A escolha, então: o histórico antigo entra pelo modelo local, e a IA fica para
# a coleta do dia a dia, que é pequena. Quem quiser a IA no histórico tem o
# caminho certo, que é a coleta agendada rodando fora do pedido web — está em
# docs/producao.md como o próximo passo.
LIMITE_PARA_IA = 120


@dataclass(frozen=True)
class Resultado:
    lidas: int
    novas: int
    repetidas: int
    com_assunto: int
    sem_assunto: int
    meses_refeitos: int
    previsoes: int
    avisos: int
    modelo: str

    def em_uma_frase(self) -> str:
        if self.novas == 0:
            return f"{self.lidas} avaliações lidas, nenhuma nova."
        quem = "a inteligência artificial" if self.modelo.startswith("ia:") else "o modelo próprio"
        return (
            f"{self.novas} avaliações novas de {self.lidas} lidas, separadas por {quem}. "
            f"{self.com_assunto} com assunto, {self.sem_assunto} sem. "
            f"{self.previsoes} estimativas e {self.avisos} avisos."
        )


def _mes_de(dia: date) -> date:
    return date(dia.year, dia.month, 1)


def _proximo_mes(mes: date) -> date:
    return date(mes.year + mes.month // 12, mes.month % 12 + 1, 1)


def _versao_do_modelo(sessao: Session, empresa_id: str, nome: str, tipo: str) -> modelo.VersaoModelo:
    """A linha do modelo que está no ar. Uma por (empresa, tipo, nome)."""
    achada = sessao.scalar(
        select(modelo.VersaoModelo).where(
            modelo.VersaoModelo.empresa_id == empresa_id,
            modelo.VersaoModelo.tipo == tipo,
            modelo.VersaoModelo.nome == nome,
        )
    )
    if achada is not None:
        if not achada.ativa:
            achada.ativa = True
        return achada
    # Só uma ativa por tipo: a anterior sai do ar quando o modelo muda.
    for antiga in sessao.scalars(select(modelo.VersaoModelo).where(
        modelo.VersaoModelo.empresa_id == empresa_id,
        modelo.VersaoModelo.tipo == tipo,
        modelo.VersaoModelo.ativa.is_(True),
    )).all():
        antiga.ativa = False
    nova = modelo.VersaoModelo(
        id=f"{tipo}-{uuid.uuid4().hex[:12]}", empresa_id=empresa_id, tipo=tipo,
        nome=nome, treinada_em=datetime.now(), ativa=True,
    )
    sessao.add(nova)
    sessao.flush()      # sem relationship(), quem aponta para ela precisa do id já existir
    return nova


# ------------------------------------------------------------ 1. guardar

def _guardar_avaliacoes(sessao: Session, empresa_id: str, comercio_id: str,
                        brutas: list[AvaliacaoBruta],
                        execucao_id: str) -> list[modelo.Avaliacao]:
    conhecidas = set(sessao.scalars(
        select(modelo.Avaliacao.id_origem).where(modelo.Avaliacao.comercio_id == comercio_id)
    ).all())
    novas: list[modelo.Avaliacao] = []
    for bruta in brutas:
        if bruta.id_origem in conhecidas:
            continue
        conhecidas.add(bruta.id_origem)
        linha = modelo.Avaliacao(
            id=f"{comercio_id}-{uuid.uuid4().hex[:16]}",
            empresa_id=empresa_id,
            comercio_id=comercio_id,
            id_origem=bruta.id_origem,
            data=bruta.data,
            estrelas=bruta.estrelas,
            texto=mascarar(bruta.texto),
            execucao_coleta_id=execucao_id,
        )
        sessao.add(linha)
        novas.append(linha)
    sessao.flush()
    return novas


# ------------------------------------------------------------ 2. separar por assunto

def _escolher_classificador(quantas: int) -> tuple[object, str]:
    """O classificador e o nome dele, pelo tamanho do lote. Ver LIMITE_PARA_IA."""
    if ativo.usando_ia() and quantas > LIMITE_PARA_IA:
        return (ativo.local(), "local:tfidf+regressao (lote grande)")
    em_uso = ativo.classificador_em_uso()
    return (em_uso, ativo.nome_do_modelo())


def _classificar(sessao: Session, empresa_id: str,
                 novas: list[modelo.Avaliacao]) -> tuple[int, int, str]:
    """Classifica as avaliações novas. Devolve (com assunto, sem assunto, modelo).

    Só avaliação com texto é classificada: avaliação sem texto não tem assunto a
    descobrir, e mandá-la ao modelo gastaria chamada de IA para nada.
    """
    if not novas:
        return (0, 0, ativo.nome_do_modelo())
    com_texto = [a for a in novas if a.texto]
    em_uso, nome = _escolher_classificador(len(com_texto))
    versao = _versao_do_modelo(sessao, empresa_id, nome, "classificacao")

    respostas = em_uso.prever_muitos([a.texto for a in com_texto]) if com_texto else []
    por_avaliacao: dict[str, tuple[str | None, float, str | None]] = {}
    for avaliacao, (assunto, confianca) in zip(com_texto, respostas, strict=True):
        motivo = None if assunto else MOTIVO_SEM_CONFIANCA
        por_avaliacao[avaliacao.id] = (assunto, confianca, motivo)
    for avaliacao in novas:
        if not avaliacao.texto:
            por_avaliacao[avaliacao.id] = (None, 0.0, MOTIVO_SEM_TEXTO)

    com, sem = 0, 0
    for avaliacao in novas:
        assunto, confianca, motivo = por_avaliacao[avaliacao.id]
        if assunto is not None and assunto not in CATEGORIAS:
            # Assunto fora dos cinco combinados nunca entra: seria uma categoria
            # nova aparecendo na tela sem ninguém ter combinado.
            assunto, motivo = None, MOTIVO_SEM_CONFIANCA
        sessao.add(modelo.Classificacao(
            id=f"c-{uuid.uuid4().hex[:18]}",
            empresa_id=empresa_id,
            avaliacao_id=avaliacao.id,
            categoria_id=assunto,
            confianca=round(float(confianca), 4),
            motivo_sem_assunto=motivo,
            versao_modelo_id=versao.id,
        ))
        if assunto is None:
            sem += 1
        else:
            com += 1
    sessao.flush()
    return (com, sem, nome)


# ------------------------------------------------------------ 3. refazer a contagem por mês

def _refazer_series(sessao: Session, empresa_id: str, comercio_id: str, hoje: date) -> int:
    """Conta as reclamações de cada assunto por mês, a partir das classificações.

    Refeito do zero, não incrementado: uma avaliação reclassificada muda a
    contagem de um mês antigo, e um contador que só soma nunca desce.
    """
    linhas = sessao.execute(
        select(modelo.Avaliacao.data, modelo.Classificacao.categoria_id)
        .join(modelo.Classificacao, modelo.Classificacao.avaliacao_id == modelo.Avaliacao.id)
        .join(modelo.VersaoModelo, modelo.VersaoModelo.id == modelo.Classificacao.versao_modelo_id)
        .where(modelo.Avaliacao.empresa_id == empresa_id,
               modelo.Avaliacao.comercio_id == comercio_id,
               modelo.Classificacao.categoria_id.is_not(None),
               modelo.VersaoModelo.ativa.is_(True))
    ).all()

    contagem: Counter[tuple[date, str]] = Counter(
        (_mes_de(quando), categoria) for quando, categoria in linhas
    )
    sessao.execute(delete(modelo.SerieMensal).where(
        modelo.SerieMensal.comercio_id == comercio_id
    ))
    sessao.flush()

    mes_corrente = _mes_de(hoje)
    if contagem:
        # Todo mês entre o primeiro e o corrente entra, inclusive com zero: um mês
        # faltando no meio faria a previsão tratar dois meses distantes como vizinhos.
        primeiro = min(mes for mes, _ in contagem)
        mes = primeiro
        while mes <= mes_corrente:
            for categoria in CATEGORIAS:
                sessao.add(modelo.SerieMensal(
                    empresa_id=empresa_id, comercio_id=comercio_id, categoria_id=categoria,
                    mes=mes, quantidade=contagem.get((mes, categoria), 0),
                    fechado=mes < mes_corrente,
                ))
            mes = _proximo_mes(mes)
    sessao.flush()
    return len({mes for mes, _ in contagem})


# ------------------------------------------------------------ 4. estimar e avisar

def _estado(ultimo: int, faixa) -> str:
    """A mesma régua de `app/banco/consultas._estado`, para os dois nunca divergirem."""
    from app.banco.consultas import _estado as regua

    return regua(ultimo, faixa)


def _estimar(sessao: Session, empresa_id: str, comercio_id: str,
             hoje: date) -> tuple[int, int]:
    """Gera a estimativa do mês corrente e do seguinte, e o aviso quando cabe."""
    versao = _versao_do_modelo(sessao, empresa_id, "tendencia+faixa-p10p90", "previsao")
    mes_corrente = _mes_de(hoje)

    sessao.execute(delete(modelo.Alerta).where(modelo.Alerta.comercio_id == comercio_id))
    sessao.execute(delete(modelo.Previsao).where(modelo.Previsao.comercio_id == comercio_id))
    sessao.flush()

    quantas, avisos = 0, 0
    for categoria in CATEGORIAS:
        fechados = sessao.execute(
            select(modelo.SerieMensal.mes, modelo.SerieMensal.quantidade)
            .where(modelo.SerieMensal.comercio_id == comercio_id,
                   modelo.SerieMensal.categoria_id == categoria,
                   modelo.SerieMensal.fechado.is_(True))
            .order_by(modelo.SerieMensal.mes)
        ).all()
        historico = [(mes, quantidade) for mes, quantidade in fechados]
        if len(historico) < previsao.MINIMO_TREINO:
            continue        # histórico curto: a estimativa não sai, e a tela diz isso

        faixas = []
        for passos in (1, 2):
            faixa = previsao.prever(historico, passos)
            linha = modelo.Previsao(
                id=f"p-{uuid.uuid4().hex[:18]}", empresa_id=empresa_id,
                comercio_id=comercio_id, categoria_id=categoria, mes=faixa.mes,
                p10=faixa.p10, p50=faixa.p50, p90=faixa.p90, versao_modelo_id=versao.id,
            )
            sessao.add(linha)
            faixas.append((faixa, linha))
            quantas += 1
        sessao.flush()

        faixa_corrente, linha_corrente = faixas[0]
        if faixa_corrente.mes != mes_corrente:
            continue
        ultimo = historico[-1][1]
        estado = _estado(ultimo, faixa_corrente)
        if estado == "normal":
            continue
        sessao.add(modelo.Alerta(
            id=f"a-{uuid.uuid4().hex[:18]}", empresa_id=empresa_id, comercio_id=comercio_id,
            categoria_id=categoria, estado=estado, atual=ultimo,
            previsao_id=linha_corrente.id, gerado_em=hoje, situacao="aberto",
        ))
        avisos += 1
    sessao.flush()
    return (quantas, avisos)


# ------------------------------------------------------------ o que a rota chama

def coletar(sessao: Session, empresa_id: str, comercio_id: str,
            brutas: list[AvaliacaoBruta], *, fonte_id: str | None = None,
            usuario_id: str | None = None, hoje: date | None = None) -> Resultado:
    """Roda o caminho inteiro e devolve o que mudou. Quem chamou dá o commit."""
    hoje = hoje or date.today()
    negocio = sessao.get(modelo.Comercio, comercio_id)
    if negocio is None or negocio.empresa_id != empresa_id:
        raise ValueError(f"o negócio {comercio_id!r} não é da empresa {empresa_id!r}")

    execucao = modelo.ExecucaoColeta(
        id=f"e-{uuid.uuid4().hex[:18]}", empresa_id=empresa_id, comercio_id=comercio_id,
        iniciada_em=datetime.now(), lidas=len(brutas), estado="em_andamento",
    )
    sessao.add(execucao)
    sessao.flush()

    novas = _guardar_avaliacoes(sessao, empresa_id, comercio_id, brutas, execucao.id)
    com, sem, nome_do_modelo = _classificar(sessao, empresa_id, novas)
    meses = _refazer_series(sessao, empresa_id, comercio_id, hoje)
    quantas, avisos = _estimar(sessao, empresa_id, comercio_id, hoje)

    execucao.novas = len(novas)
    execucao.terminada_em = datetime.now()
    execucao.estado = "concluida"
    if fonte_id:
        fonte = sessao.get(modelo.Fonte, fonte_id)
        if fonte is not None:
            fonte.ultima_coleta = datetime.now()
            fonte.estado = "ligada"
            fonte.erro = None

    resultado = Resultado(
        lidas=len(brutas), novas=len(novas), repetidas=len(brutas) - len(novas),
        com_assunto=com, sem_assunto=sem, meses_refeitos=meses,
        previsoes=quantas, avisos=avisos, modelo=nome_do_modelo,
    )
    auditoria.registrar(
        sessao, empresa_id=empresa_id, usuario_id=usuario_id, acao="coleta_rodada",
        objeto=comercio_id, detalhe=resultado.em_uma_frase(),
    )
    return resultado


def marcar_erro(sessao: Session, fonte_id: str, mensagem: str) -> None:
    """Fonte que falhou fica com o motivo na tela, em vez de parecer que nunca rodou."""
    fonte = sessao.get(modelo.Fonte, fonte_id)
    if fonte is None:
        return
    fonte.estado = "erro"
    fonte.erro = mensagem[:500]


__all__ = ["LIMITE_CONFIANCA", "Resultado", "coletar", "marcar_erro"]
