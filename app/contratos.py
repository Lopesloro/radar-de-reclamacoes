"""Os tipos que passam entre as partes do sistema.

Combinado entre os três: o motor (Gabriel) devolve estes tipos, a segurança
(Matheus) protege o caminho deles e as telas (Nicolas) só leem o que está aqui.
Mudou um campo? Só com PR aprovado pelos três.

As categorias usam identificador sem acento (`preco`); o nome com acento, para
a tela, fica em `app/conteudo.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

CATEGORIAS: tuple[str, ...] = ("atendimento", "demora", "preco", "qualidade", "ambiente")

Veredito = Literal["sustentada", "descartada", "inconclusiva"]
Forca = Literal["forte", "moderada", "fraca"]
OrigemHipotese = Literal["diario", "calendario", "clima", "dia_turno", "termo_novo", "ia"]
TipoEvento = Literal["equipe", "produto", "canal_venda", "horario", "preco", "estrutura", "outro"]
Periodo = Literal["manha", "tarde", "noite"]
Estado = Literal["vai_piorar", "fique_de_olho", "normal"]
Certeza = Literal["alta", "media", "baixa"]


# ------------------------------------------------------------ telas de sempre

@dataclass(frozen=True)
class PrevisaoMes:
    """Estimativa de um mês: o mais provável (p50) e o mínimo e máximo esperados."""

    mes: date
    p10: int
    p50: int
    p90: int


@dataclass(frozen=True)
class SerieMensal:
    """Um assunto de um negócio ao longo dos meses, com o mês aberto e a estimativa."""

    empresa_id: str
    categoria: str
    meses: tuple[tuple[date, int], ...]     # meses fechados, do mais antigo ao mais novo
    parcial: tuple[date, int]               # mês corrente: quanto chegou até hoje
    parcial_fracao: float                   # quanto do mês corrente já passou, de 0 a 1
    previsoes: tuple[PrevisaoMes, ...]      # [0] = total do mês corrente, [1] = mês seguinte

    @property
    def ultimo(self) -> int:
        return self.meses[-1][1]

    @property
    def anterior(self) -> int:
        return self.meses[-2][1]

    @property
    def variacao(self) -> int:
        return self.ultimo - self.anterior


@dataclass(frozen=True)
class ResumoComercio:
    """O cartão de um negócio no Resumo."""

    empresa_id: str
    nome: str
    ramo: str
    cidade: str
    estado: Estado
    mes_referencia: date                    # último mês fechado
    avaliacoes_lidas: int
    reclamacoes: int
    sem_assunto: int
    nota_media: float
    mais_reclamado: str
    mais_reclamado_qtd: int
    vai_crescer: str
    vai_crescer_de: int                     # último mês fechado
    vai_crescer_para: PrevisaoMes           # estimativa do mês corrente
    etapas_concluidas: int
    etapas_total: int


@dataclass(frozen=True)
class AvaliacaoTela:
    """Uma avaliação como aparece na tela. O texto já chega mascarado."""

    id: str
    data: date
    estrelas: int
    texto: str | None
    categoria: str | None
    certeza: Certeza | None
    motivo_sem_assunto: str | None


@dataclass(frozen=True)
class Alerta:
    """Aviso de que um assunto deve crescer."""

    id: str
    empresa_id: str
    empresa_nome: str
    categoria: str
    estado: Estado
    atual: int
    previsto: PrevisaoMes
    gerado_em: date
    situacao: Literal["aberto", "confirmado", "descartado"]


@dataclass(frozen=True)
class LinhaAcerto:
    """O quanto o classificador acerta num assunto."""

    categoria: str
    precisao: float
    recall: float
    f1: float
    amostra: int


@dataclass(frozen=True)
class AcuraciaClassificacao:
    """O quanto o classificador acerta, ao lado do chute simples."""

    linhas: tuple[LinhaAcerto, ...]
    acerto_geral: float                     # fração das avaliações com assunto certo
    acerto_regua: float                     # chute: responder sempre o assunto mais comum
    f1_macro: float
    f1_macro_regua: float
    amostra: int
    categoria_regua: str


@dataclass(frozen=True)
class AcuraciaPrevisao:
    """O quanto a previsão acerta, ao lado de repetir o mês anterior."""

    erro_medio: float
    erro_medio_regua: float
    cobertura: float                        # vezes em que o real caiu entre o mínimo e o máximo
    janelas: int
    exemplo: str                            # de qual negócio e assunto são os pontos
    pontos: tuple[tuple[date, int, int], ...]   # (mês, previsto, realizado)


@dataclass(frozen=True)
class EtapaParceiro:
    """Um dos passos entre o combinado com o parceiro e o aviso chegando a ele."""

    numero: int
    titulo: str
    estado: Literal["feito", "andamento", "pendente"]
    detalhe: str
    falta: str | None


# ------------------------------------------------------------ investigação

@dataclass(frozen=True)
class EventoDiario:
    """Mudança que o dono registrou no diário do negócio."""

    id: str
    empresa_id: str
    data: date
    tipo: TipoEvento
    descricao: str


@dataclass(frozen=True)
class PropostaIA:
    """Sugestão da IA. Só vira hipótese depois de passar pela estatística."""

    tipo: OrigemHipotese
    termo: str | None
    dias_semana: tuple[int, ...]
    periodo: Periodo | None
    justificativa_curta: str


@dataclass(frozen=True)
class Hipotese:
    """Uma possível causa, já testada."""

    id: str
    origem: OrigemHipotese
    frase: str                              # português simples, pronto para a tela
    categoria: str
    teste: str                              # nome da ferramenta estatística usada
    antes_semana: float                     # reclamações por semana no período de base
    depois_semana: float                    # reclamações por semana no período da alta
    efeito_semana: float                    # reclamações a mais por semana
    efeito_min: float
    efeito_max: float
    q_valor: float                          # nunca aparece na tela do dono
    veredito: Veredito
    forca: Forca
    avaliacoes_exemplo: tuple[str, ...]     # textos já mascarados


@dataclass(frozen=True)
class PassoInvestigacao:
    """Um passo do agente, para a trilha de auditoria."""

    ordem: int
    quando: datetime
    acao: str
    entrada_resumo: str
    saida_resumo: str


@dataclass(frozen=True)
class Investigacao:
    """O resultado de uma investigação: as causas testadas, da mais provável à menos."""

    id: str
    empresa_id: str
    alerta_id: str | None
    categoria: str
    periodo_alta: tuple[date, date]
    periodo_base: tuple[date, date]
    hipoteses: tuple[Hipotese, ...]
    passos: tuple[PassoInvestigacao, ...]
    usou_ia: bool
    estado: Literal["concluida", "dados_insuficientes"]
    motivo: str | None


# ------------------------------------------------------------ simulador "E se?"

@dataclass(frozen=True)
class Turno:
    """Um turno da operação do negócio."""

    dia_semana: int                         # 0 = segunda
    periodo: Periodo
    equipe: int
    clientes: float                         # média de clientes ou pedidos no turno
    minutos_atendimento: float
    custo_hora: float


@dataclass(frozen=True)
class Cenario:
    """Uma mudança que o dono quer testar no simulador."""

    nome: str
    categoria: str
    mudancas: tuple[Turno, ...]             # só os turnos que mudam


@dataclass(frozen=True)
class ResultadoSimulacao:
    """O que deve acontecer com a mudança, e quanto custa."""

    cenario: Cenario
    reclamacoes_atual: float                # por mês, no assunto
    reclamacoes_cenario: float
    minimo: float
    maximo: float
    espera_atual_min: float
    espera_cenario_min: float
    custo_extra_mes: float
    custo_por_reclamacao_evitada: float | None
    confiavel: bool
    motivo: str | None


# ------------------------------------------------------------ teste na prática

@dataclass(frozen=True)
class PlanoExperimento:
    """O plano do teste na prática, selado antes de começar."""

    id: str
    empresa_id: str
    categoria: str
    acao: str
    inicio: date
    fim: date
    dias_com_acao: tuple[date, ...]
    dias_sem_acao: tuple[date, ...]
    menor_efeito_detectavel: float          # reclamações por mês
    selo: str                               # SHA-256 do plano (Matheus)
    selado_em: datetime
    estado: Literal["rascunho", "em_andamento", "encerrado", "cancelado"]


@dataclass(frozen=True)
class MarcacaoDia:
    """O que o dono marcou num dia do teste."""

    data: date
    com_acao: bool                          # o sorteio mandou fazer a mudança neste dia?
    seguiu: bool | None                     # None = ainda não marcou


@dataclass(frozen=True)
class ResultadoExperimento:
    """O veredito do teste na prática."""

    plano_id: str
    dias_observados: int
    adesao: float                           # fração dos dias em que o sorteio foi seguido
    media_com: float                        # reclamações por dia nos dias com a mudança
    media_sem: float                        # reclamações por dia nos dias sem
    efeito_mes: float                       # negativo = menos reclamação
    efeito_min: float
    efeito_max: float
    veredito: Literal["funcionou", "nao_funcionou", "ainda_nao_da_para_saber"]
    frase: str


# ------------------------------------------------------------ laboratório

@dataclass(frozen=True)
class ResultadoLaboratorio:
    """O quanto o agente, o simulador e o teste acertam no mundo simulado."""

    cenarios: int
    acerto_agente: float                    # a causa principal é a do gabarito
    acerto_agente_top3: float
    acerto_agente_sem_ia: float
    acerto_regua: float                     # culpar o último evento do diário
    falso_alarme_agente: float              # cenários sem causa com alguma "provável causa"
    cobertura_simulador: float              # efeito verdadeiro dentro da faixa
    falso_positivo_aa: float                # testes em que a mudança não fazia nada
    poder_experimento: float
