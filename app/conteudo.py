"""Texto fixo do site: identidade do projeto, menu, equipe e tecnologias.

Tudo o que é institucional mora aqui, fora dos templates, para que a mesma frase
não seja reescrita em duas telas.
"""

from __future__ import annotations

VERSAO = "0.1.0"

PROJETO = {
    "nome": "Radar de Reclamações",
    "resumo": (
        "Lê a avaliação pública de um comércio parceiro, diz por que os clientes "
        "reclamam hoje e qual reclamação tende a crescer no próximo mês."
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

# Menu de quem ainda não entrou: só a apresentação do projeto.
MENU_PUBLICO = (
    {"id": "projeto", "rotulo": "O projeto", "href": "/"},
)

# A ideia, em três movimentos. Vira a seção de abertura da home.
MOVIMENTOS = (
    {
        "numero": "01",
        "titulo": "Coletar",
        "texto": (
            "As avaliações públicas da ficha do comércio parceiro entram com data, "
            "texto e identificador próprio, que impede a mesma avaliação de ser "
            "contada duas vezes."
        ),
    },
    {
        "numero": "02",
        "titulo": "Classificar",
        "texto": (
            "Cada texto recebe uma categoria de reclamação. Abaixo do limite de "
            "confiança o sistema responde “sem categoria” em vez de chutar."
        ),
    },
    {
        "numero": "03",
        "titulo": "Prever",
        "texto": (
            "A série de cada categoria projeta o mês seguinte com faixa de "
            "incerteza, e o alerta sai quando a alta prevista passa do limiar."
        ),
    },
)

MODELOS = (
    {
        "rotulo": "Modelo 1",
        "titulo": "Classificação do texto",
        "pergunta": "Por que este cliente reclamou?",
        "metrica": "F1 por categoria e F1 macro",
        "regua": "responder sempre a categoria mais comum",
    },
    {
        "rotulo": "Modelo 2",
        "titulo": "Previsão da contagem",
        "pergunta": "Quantas reclamações desta categoria no mês que vem?",
        "metrica": "erro médio absoluto e cobertura da faixa",
        "regua": "repetir o mês anterior",
    },
)

TECNOLOGIAS = (
    {
        "grupo": "Aplicação",
        "itens": (
            "Python 3.12 com FastAPI e Uvicorn",
            "Jinja2 para a renderização no servidor",
            "HTMX para trocar pedaço de tela sem recarregar",
            "CSS próprio, sem framework de componente",
        ),
    },
    {
        "grupo": "Dados e modelos",
        "itens": (
            "PostgreSQL com SQLAlchemy e Alembic",
            "pandas e NumPy no pré-processamento",
            "scikit-learn na classificação do texto",
            "statsmodels na série temporal de cada categoria",
        ),
    },
    {
        "grupo": "Qualidade e segurança",
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
# para saber o que já existe e o que ainda falta — sem promessa fora do lugar.
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
        "texto": "Classificação com F1 por categoria e previsão com faixa P10–P90, ambas "
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
