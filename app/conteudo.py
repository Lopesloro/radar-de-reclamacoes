"""Texto fixo do site: identidade do projeto, menu, equipe e tecnologias.

Tudo o que é institucional mora aqui, fora dos templates, para que a mesma frase
não seja reescrita em duas telas.
"""

from __future__ import annotations

VERSAO = "0.1.0"

PROJETO = {
    "nome": "Radar de Reclamações",
    "resumo": (
        "Lê a avaliação pública do seu negócio, mostra do que os clientes mais "
        "reclamam e avisa qual queixa está crescendo antes de ela virar problema."
    ),
    "disciplina": "Projeto Integrador VI",
    "codigo": "12563",
    "curso": "Engenharia de Software",
    "instituicao": "PUC-Campinas",
    "semestre": "2º semestre de 2026",
    "orientadora": "Profa. Sílvia C. de Matos Soares",
    "repositorio": "https://github.com/Lopesloro/radar-de-reclamacoes",
}

INTEGRANTES = (
    "Gabriel Lopes Londe Rodrigues",
    "Nicolas Marques Linares",
    "Matheus Rocafa Moraes",
)

# Menu de quem está dentro do sistema.
MENU = (
    {"id": "painel", "rotulo": "Painel", "href": "/painel"},
    {"id": "previsao", "rotulo": "Previsão", "href": "/previsao"},
    {"id": "alertas", "rotulo": "Alertas", "href": "/alertas"},
    {"id": "acuracia", "rotulo": "Acurácia", "href": "/acuracia"},
    {"id": "etapas", "rotulo": "Etapas", "href": "/etapas"},
)

# Quem ainda não entrou não tem menu: a página pública é uma só, e a única ação
# dela é entrar.
MENU_PUBLICO = ()

# O que o dono do negócio recebe. Linguagem dele, não a nossa.
ENTREGAS = (
    {
        "titulo": "A lista do que mais incomoda",
        "texto": (
            "Toda avaliação que seus clientes escrevem entra numa lista separada por "
            "assunto: atendimento, demora, preço, qualidade e ambiente. Você abre a "
            "tela e vê, em ordem, o que mais apareceu neste mês."
        ),
    },
    {
        "titulo": "O aviso antes de virar problema",
        "texto": (
            "Quando um assunto começa a crescer mês a mês, o sistema avisa antes de "
            "ele virar o motivo de as pessoas pararem de voltar. Você age enquanto "
            "ainda dá para consertar barato."
        ),
    },
    {
        "titulo": "A conta aberta do que foi acertado",
        "texto": (
            "Cada aviso que o sistema deu fica guardado ao lado do que aconteceu de "
            "verdade no mês seguinte. Você confere se vale confiar, em vez de "
            "acreditar na nossa palavra."
        ),
    },
)

# Os três passos, sem jargão. É o que a pessoa lê antes de decidir.
MOVIMENTOS = (
    {
        "numero": "01",
        "titulo": "A gente lê o que já está escrito",
        "texto": (
            "As avaliações do seu negócio são públicas: qualquer pessoa lê na "
            "internet. O sistema lê todas, todo dia, e guarda cada uma uma única vez."
        ),
    },
    {
        "numero": "02",
        "titulo": "Separa por assunto",
        "texto": (
            "Cada texto é encaixado num assunto. Quando a frase é vaga demais para "
            "ter certeza, o sistema diz que não sabe, e conta isso à parte, em vez "
            "de inventar um assunto para fechar a conta."
        ),
    },
    {
        "numero": "03",
        "titulo": "Olha para a frente",
        "texto": (
            "Com os meses anteriores na mão, ele estima quantas reclamações de cada "
            "assunto devem aparecer no mês que vem, e mostra uma faixa de mínimo e "
            "máximo em vez de fingir que sabe o número exato."
        ),
    },
)

# O que o parceiro NÃO precisa fazer. Diferencial real, não promessa.
DISPENSADO = (
    "Instalar programa, aplicativo ou aparelho no seu negócio.",
    "Dar acesso ao seu sistema de caixa, agenda ou financeiro.",
    "Pedir para o seu cliente responder pesquisa ou preencher formulário.",
    "Contratar alguém para ler avaliação uma por uma.",
)

MODELOS = (
    {
        "rotulo": "A primeira pergunta",
        "titulo": "Do que estão reclamando",
        "pergunta": "Por que este cliente reclamou?",
        "simples": (
            "O sistema lê a frase e diz de que assunto ela trata. Para saber se ele "
            "acerta, separamos avaliações à mão e conferimos uma a uma."
        ),
        "metrica": "acerto por assunto e acerto médio",
        "regua": "chutar sempre o assunto mais comum",
    },
    {
        "rotulo": "A segunda pergunta",
        "titulo": "O que vem no mês que vem",
        "pergunta": "Quantas reclamações desse assunto vão aparecer?",
        "simples": (
            "Com o histórico dos meses anteriores, ele estima o próximo. Para saber "
            "se vale, comparamos com o palpite mais simples que existe: repetir o "
            "número do mês passado."
        ),
        "metrica": "erro médio e acerto da faixa",
        "regua": "repetir o mês anterior",
    },
)

TECNOLOGIAS = (
    {
        "grupo": "O site que você abre",
        "itens": (
            "Python 3.12 com FastAPI e Uvicorn",
            "Jinja2 para a renderização no servidor",
            "HTMX para trocar pedaço de tela sem recarregar",
            "CSS próprio, sem framework de componente",
        ),
    },
    {
        "grupo": "Onde os dados ficam e como a IA pensa",
        "itens": (
            "PostgreSQL com SQLAlchemy e Alembic",
            "pandas e NumPy no pré-processamento",
            "scikit-learn na classificação do texto",
            "statsmodels na série temporal de cada categoria",
        ),
    },
    {
        "grupo": "O que impede o sistema de quebrar",
        "itens": (
            "pytest com o cliente de teste do Starlette",
            "Playwright nos testes de ponta a ponta",
            "Bandit, pip-audit e gitleaks no integração contínua",
            "Ruff como analisador estático",
        ),
    },
)

# Seção 12 da especificação: o recorte de cibersegurança é defesa.
ROBUSTEZ = (
    ("Serviço de avaliações fora do ar ou cota esgotada",
     "Nova tentativa com espera crescente. O painel mostra a data do último dado válido."),
    ("Parceiro revoga o acesso",
     "O comércio fica marcado como desconectado e o responsável é avisado; os demais seguem."),
    ("Avaliação só com estrela, sem texto",
     "Entra na nota média e não vai para o classificador."),
    ("Texto que não cabe em nenhuma categoria",
     "Fica sem categoria abaixo do limite de confiança, em vez de receber um chute."),
    ("Mesma avaliação importada duas vezes",
     "Chave única pelo identificador externo, que impede a contagem dobrada."),
    ("Avaliação editada ou apagada na origem",
     "Na importação seguinte o registro é atualizado ou marcado como removido."),
    ("Histórico curto demais para prever",
     "A previsão não aparece, e a tela diz que falta histórico."),
    ("Categoria sem nenhuma reclamação no mês",
     "A variação é exibida em contagem, nunca em porcentagem, para não dividir por zero."),
)


# Etapas do produto, na ordem em que precisam acontecer. É o que o empresário vê
# para saber o que já existe e o que ainda falta, sem promessa fora do lugar.
ETAPAS_PROJETO = (
    {
        "fase": "Entregue",
        "titulo": "Telas, navegação e gráficos",
        "estado": "feito",
        "texto": "Painel, ficha do comércio, previsão com faixa, fila de alertas e tela de acurácia, "
                 "todas renderizadas no servidor.",
        "falta": None,
    },
    {
        "fase": "Entregue",
        "titulo": "Entrada com usuário e senha",
        "estado": "feito",
        "texto": "Sessão assinada em cookie HttpOnly, senha guardada como hash, token contra CSRF "
                 "em todo formulário, limite de tentativas e cabeçalhos de segurança na resposta.",
        "falta": "Trocar a senha de demonstração por uma real e criar um usuário por empresa.",
    },
    {
        "fase": "Entregue",
        "titulo": "Dois modelos medidos contra a régua",
        "estado": "feito",
        "texto": "Classificação com F1 por categoria e previsão com faixa P10-P90, ambas "
                 "comparadas com a régua na tela de acurácia.",
        "falta": None,
    },
    {
        "fase": "Próxima",
        "titulo": "Coleta real das avaliações",
        "estado": "andamento",
        "texto": "Leitura diária da ficha pública de cada parceiro, com identificador único por "
                 "avaliação e registro de cada carga.",
        "falta": "Termo assinado de cada parceiro e a via de leitura definida.",
    },
    {
        "fase": "Próxima",
        "titulo": "Banco de dados e histórico que sobrevive ao reinício",
        "estado": "pendente",
        "texto": "Hoje os dados são gerados a cada execução. O histórico real precisa de PostgreSQL "
                 "com migração versionada.",
        "falta": "Modelo de dados com a chave da empresa em toda tabela, e a migração inicial.",
    },
    {
        "fase": "Próxima",
        "titulo": "Alerta que sai da tela",
        "estado": "pendente",
        "texto": "O aviso de alta prevista chegando por e-mail ou WhatsApp, com preferência por empresa.",
        "falta": "Escolher o canal com cada parceiro e definir quem recebe.",
    },
    {
        "fase": "Depois",
        "titulo": "Uma conta por empresa, com isolamento testado",
        "estado": "pendente",
        "texto": "Cada empresa vê só o que é dela, e existe um teste que tenta ler o dado do vizinho "
                 "e espera receber 403.",
        "falta": "Cadastro de usuários e o teste de autorização no integração contínua.",
    },
    {
        "fase": "Depois",
        "titulo": "Evidência de teste e de segurança",
        "estado": "andamento",
        "texto": "Testes de ponta a ponta nas telas e a bateria de verificação de controles, com a "
                 "saída guardada como evidência.",
        "falta": "Playwright nas telas em 390px e 1280px, e a coleta automática das evidências.",
    },
)


# Onde a inteligência artificial realmente entra, o que ela faz e como a gente
# confere. Escrito para quem nunca programou: nenhuma sigla sem tradução.
IA_NO_SISTEMA = (
    {
        "onde": "Separar cada avaliação por assunto",
        "faz": "Lê a frase escrita pelo cliente e decide se ela fala de atendimento, "
               "demora, preço, qualidade ou ambiente.",
        "confere": "Separamos um monte de avaliações e marcamos o assunto à mão. "
                   "Depois comparamos o que a máquina disse com o que a gente marcou.",
        "melhorar": "Ensinar o sistema a entender quando uma frase fala de dois "
                    "assuntos ao mesmo tempo e contar nos dois.",
    },
    {
        "onde": "Admitir que não sabe",
        "faz": "Quando a frase é vaga, curta ou confusa, o sistema responde "
               "“não sei” em vez de escolher um assunto qualquer.",
        "confere": "Contamos quantas ficaram sem assunto. Se esse número dispara, "
                   "é sinal de que o modelo precisa de mais exemplos.",
        "melhorar": "Mostrar essas frases numa fila para alguém marcar à mão, e o "
                    "sistema aprender com a correção.",
    },
    {
        "onde": "Estimar o mês seguinte",
        "faz": "Olha os meses anteriores de cada assunto e calcula quantas "
               "reclamações devem aparecer no próximo, com mínimo e máximo.",
        "confere": "Comparamos com o palpite mais simples que existe, repetir o mês "
                   "passado. Se a máquina não ganhar dele, ela não vai para a tela.",
        "melhorar": "Levar em conta feriado, férias e promoção, que mexem no "
                    "movimento e hoje o sistema não enxerga.",
    },
    {
        "onde": "Decidir quando avisar",
        "faz": "Dispara o aviso quando a alta estimada é grande o bastante para não "
               "ser apenas variação normal do mês.",
        "confere": "Todo aviso fica guardado. Quando você confirma ou descarta, "
                   "o sistema ajusta o quanto precisa subir para avisar de novo.",
        "melhorar": "Aprender o limite de cada negócio separadamente, em vez de usar "
                    "o mesmo limite para todos.",
    },
    {
        "onde": "Explicar o aviso em português",
        "faz": "Ainda não faz. Hoje a frase do aviso é montada com os números "
               "calculados, sem a IA escrever nada.",
        "confere": "",
        "melhorar": "Deixar a IA escrever a explicação, mas sempre em cima de "
                    "números que vieram do banco. Ela explica, nunca inventa número.",
    },
)

# O que a IA ainda erra. Dito na tela, porque banca e cliente vão perguntar.
LIMITES_DA_IA = (
    ("Ironia", "“Adorei esperar uma hora” é elogio para a máquina e reclamação para gente."),
    ("Duas queixas na mesma frase", "Hoje ela escolhe uma só, e a outra se perde."),
    ("Gíria e erro de digitação", "Quanto mais longe do português comum, menos ela acerta."),
    ("Negócio novo", "Sem alguns meses de histórico, não há o que estimar, e a tela diz isso."),
    ("Mês fora do normal", "Reforma, feriadão ou promoção mudam tudo, e o sistema ainda não sabe disso."),
)


# Quem construiu, e o que cada um fez. Fica na área interna: a página pública é
# comercial, mas a autoria do trabalho precisa estar escrita em algum lugar do
# próprio sistema, não só no relatório.
AUTORIA = (
    {
        "nome": "Gabriel Lopes Londe Rodrigues",
        "frente": "Programa em Python, banco de dados e os dois modelos",
        "feito": "Escreveu a aplicação, a geração dos dados, a conta da previsão, "
                 "a avaliação dos modelos e os gráficos desenhados no servidor.",
    },
    {
        "nome": "Matheus Rocafa Moraes",
        "frente": "Segurança e proteção dos dados",
        "feito": "Montou a entrada com usuário e senha, a guarda da senha, a proteção "
                 "dos formulários, o limite de tentativas e os cabeçalhos de defesa.",
    },
    {
        "nome": "Nicolas Marques Linares",
        "frente": "Telas, textos, testes e parceiros",
        "feito": "Desenhou e escreveu as telas, cuidou da leitura em celular e "
                 "computador, dos testes de uso e do contato com as empresas parceiras.",
    },
)
