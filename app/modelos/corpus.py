"""Frases rotuladas à mão pela equipe, para treinar e medir o classificador.

Isto **não** é dado de cliente e nunca aparece em tela nenhuma: é o material de
treino do modelo que roda quando não há IA externa configurada. Cada frase foi
escrita olhando a linguagem de avaliação pública brasileira (frase curta, erro
de digitação, gíria) e rotulada por uma pessoa.

Por que um corpus escrito à mão e não as avaliações do cliente? Porque no
primeiro dia de um cliente novo não existe avaliação rotulada nenhuma, e um
modelo precisa de rótulo para nascer. Conforme chega avaliação real conferida
pelo dono, ela entra no treino e o corpus perde peso — é o caminho previsto em
`docs/previsao-e-ia.md`.

A medida honesta vive em `app/modelos/classificador.py`: F1 macro sempre ao
lado da régua (responder sempre o assunto mais comum).
"""

from __future__ import annotations

# ------------------------------------------------------------ os cinco assuntos

FRASES: dict[str, tuple[str, ...]] = {
    "atendimento": (
        "Ninguém explicou direito o que ia ser feito.",
        "Fiquei sem resposta no WhatsApp.",
        "Me atenderam com pouca paciência.",
        "Pedi uma informação e me trataram mal.",
        "A moça do balcão foi grossa comigo.",
        "Atendente mal educado, não voltarei.",
        "Mandei mensagem e ninguém respondeu até agora.",
        "O rapaz nem olhou na minha cara.",
        "Falta de educação da equipe.",
        "Ninguém me deu atenção, fiquei perdido.",
        "Pedi para falar com o responsável e me ignoraram.",
        "Tratamento péssimo, parecia que eu estava incomodando.",
        "Liguei três vezes e não me atenderam.",
        "Prometeram retornar o contato e nunca retornaram.",
        "A recepção não sabia informar nada.",
        "Fui destratado na hora de pagar.",
    ),
    "demora": (
        "Esperei muito tempo para ser atendido.",
        "Demorou bem mais do que o prometido.",
        "Fila longa e pouca gente atendendo.",
        "Fiquei quase uma hora esperando.",
        "O pedido atrasou mais de 40 minutos.",
        "Marquei horário e me atenderam só depois de muito tempo.",
        "Demora absurda para uma coisa simples.",
        "Entrega atrasou e ninguém avisou nada.",
        "Fiquei esperando em pé por quase 50 minutos.",
        "Lento demais, perdi minha hora de almoço.",
        "Disseram vinte minutos e levou uma hora e meia.",
        "A espera na fila dobrou desde a última vez.",
        "Pedi e esqueceram do meu pedido.",
        "Horário marcado não vale nada aqui, sempre atrasa.",
        "Muito tempo parado esperando alguém aparecer.",
        "Só o aguardo da senha levou meia hora.",
    ),
    "preco": (
        "Achei o valor alto para o que entregam.",
        "Cobraram uma taxa que ninguém avisou.",
        "O preço subiu e nada melhorou.",
        "Mais caro do que outros da região.",
        "Carésimo pelo que é.",
        "Aumentaram o valor sem nenhum aviso.",
        "Não vale o que cobram.",
        "Vieram cobranças a mais na conta.",
        "O orçamento veio bem acima do combinado.",
        "Taxa de serviço escondida no final.",
        "Por esse preço eu faço em casa.",
        "Subiu 30% de um mês para o outro.",
        "Custo benefício ruim, achei salgado.",
        "Cobraram o dobro do que tinham falado no telefone.",
        "Preço fora da realidade do bairro.",
        "Pagar isso de novo não dá.",
    ),
    "qualidade": (
        "O serviço precisou ser refeito.",
        "Veio diferente do combinado.",
        "Faltou capricho no resultado.",
        "Veio faltando item no pedido.",
        "Chegou frio e sem gosto.",
        "O produto quebrou no primeiro dia.",
        "Serviço malfeito, tive que procurar outro lugar.",
        "Veio errado e ainda estava estragado.",
        "Qualidade caiu muito em relação ao ano passado.",
        "Entregaram incompleto, faltou metade.",
        "Mal acabado, dá para ver os defeitos.",
        "O acabamento ficou torto.",
        "O item veio vencido.",
        "Não resolveu o problema, voltei com o mesmo defeito.",
        "Material de péssima qualidade.",
        "Vieram manchas no serviço que fizeram.",
    ),
    "ambiente": (
        "O lugar estava sujo.",
        "Muito barulho, difícil conversar.",
        "Não tinha onde sentar enquanto esperava.",
        "O banheiro estava sem papel.",
        "Cheiro forte no salão.",
        "Mesa suja quando sentamos.",
        "O calor dentro do salão é insuportável, sem ventilação.",
        "Banheiro imundo.",
        "Sala de espera apertada e quente.",
        "Ambiente escuro e mal cuidado.",
        "O chão estava molhado e escorregadio.",
        "Música alta demais, não dava para ouvir ninguém.",
        "Faltou limpeza no atendimento ao público.",
        "Lugar sem acessibilidade nenhuma, só escada.",
        "Estacionamento esburacado e sem vaga.",
        "O local está caindo aos pedaços.",
    ),
}

# Frases com a marca do mascaramento: nome de pessoa nunca chega ao modelo nem
# à tela, chega `[nome]`. Treinar com a marca presente evita o modelo estranhar
# o token quando ele aparece no dado real.
FRASES_MASCARADAS: dict[str, tuple[str, ...]] = {
    "atendimento": (
        "A moça da recepção, [nome], foi seca comigo.",
        "O [nome] do balcão não quis me ajudar.",
    ),
    "demora": (
        "O entregador [nome] não achava o endereço.",
        "Esperei o [nome] voltar do intervalo por 40 minutos.",
    ),
    "preco": (
        "O [nome] cobrou um valor diferente do da tabela.",
        "Falei com [nome] e o preço mudou na hora de pagar.",
    ),
    "qualidade": (
        "O serviço que o [nome] fez teve que ser refeito.",
        "O [nome] entregou o pedido trocado.",
    ),
    "ambiente": (
        "Falei com [nome] sobre o cheiro no salão e nada mudou.",
        "O [nome] disse que o banheiro já estava assim.",
    ),
}

# Elogio e frase vaga: não é reclamação de assunto nenhum. O certo é o modelo
# dizer "não sei" em vez de forçar um dos cinco.
ELOGIOS: tuple[str, ...] = (
    "Gostei muito, voltarei.",
    "Atendimento rápido e educado.",
    "Tudo certo, recomendo.",
    "Excelente, nota dez.",
    "Melhor da cidade, sempre venho.",
    "Equipe atenciosa, ambiente agradável.",
    "Preço justo e serviço bom.",
    "Recomendo de olhos fechados.",
)

VAGAS: tuple[str, ...] = (
    "Passei aqui hoje.",
    "Fui atendido.",
    "Já vim outras vezes.",
    "Fica no centro.",
    "Conheci por indicação.",
    "Estive lá ontem à tarde.",
    "Segunda vez que venho.",
    "Vim com a família.",
)


def frases_por_assunto() -> dict[str, tuple[str, ...]]:
    """As frases de cada assunto, as comuns e as com nome mascarado juntas."""
    return {
        assunto: frases + FRASES_MASCARADAS.get(assunto, ())
        for assunto, frases in FRASES.items()
    }
