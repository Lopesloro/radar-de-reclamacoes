"""Textos fixos do site: identidade, menu, glossário e perguntas frequentes.

Uma frase escrita uma vez só: se a explicação de "mês fechado" muda, muda aqui e
vale para todas as telas. Regra de escrita: frases curtas, números inteiros,
nenhuma sigla sem tradução.
"""

from __future__ import annotations

VERSAO = "0.1.0"

PROJETO = {
    "nome": "Radar de Reclamações",
    "resumo": (
        "Descobre por que os clientes do seu negócio reclamam e avisa qual "
        "reclamação deve crescer no próximo mês."
    ),
    "disciplina": "Projeto Integrador VI",
    "curso": "Engenharia de Software",
    "instituicao": "PUC-Campinas",
    "semestre": "2º semestre de 2026",
    "orientadora": "Profa. Sílvia C. de Matos Soares",
}

AUTORIA = (
    {
        "nome": "Gabriel Lopes Londe Rodrigues",
        "frente": "Programa, banco de dados e inteligência artificial",
        "faz": "As contas e o banco: separar as avaliações por assunto, prever o mês "
               "seguinte, medir o acerto de cada parte e guardar tudo no PostgreSQL.",
    },
    {
        "nome": "Matheus Rocafa Moraes",
        "frente": "Segurança e proteção dos dados",
        "faz": "A entrada com senha, a separação entre empresas, a proteção da "
               "inteligência artificial contra manipulação e o cuidado com a LGPD.",
    },
    {
        "nome": "Nicolas Marques Linares",
        "frente": "Telas, textos, testes e parceiros",
        "faz": "As telas, os gráficos, os botões de ajuda, os testes de uso, o contato "
               "com as empresas parceiras e o relatório.",
    },
)

# O menu do cliente. Só tela que lê dado do banco dele: as telas "Por quê?",
# "E se?" e "Testes" saíram quando o gerador de dados fictícios foi removido, e
# voltam quando tiverem motor de verdade. A lista do que falta para cada uma
# está em `PROXIMAS_ETAPAS`, e aparece na tela "O que falta".
MENU = (
    {"id": "resumo", "rotulo": "Resumo", "href": "/resumo"},
    {"id": "avisos", "rotulo": "Avisos", "href": "/avisos"},
    {"id": "configuracao", "rotulo": "Configuração", "href": "/configuracao"},
    {"id": "ajuda", "rotulo": "Ajuda", "href": "/ajuda"},
)

MENU_MAIS = (
    {"id": "confianca", "rotulo": "Dá para confiar?", "href": "/confianca"},
    {"id": "o-que-falta", "rotulo": "O que falta", "href": "/o-que-falta"},
)

# O menu da equipe do Radar. Vive atrás de `/admin`, que o middleware fecha para
# quem não é admin antes de a rota rodar.
MENU_ADMIN = (
    {"id": "admin", "rotulo": "Painel", "href": "/admin"},
    {"id": "admin-clientes", "rotulo": "Clientes", "href": "/admin/clientes"},
    {"id": "admin-fontes", "rotulo": "Fontes", "href": "/admin/fontes"},
    {"id": "admin-coletas", "rotulo": "Coletas", "href": "/admin/coletas"},
    {"id": "admin-auditoria", "rotulo": "Auditoria", "href": "/admin/auditoria"},
    {"id": "admin-sistema", "rotulo": "Sistema", "href": "/admin/sistema"},
)

NOMES_CATEGORIA = {
    "atendimento": "atendimento",
    "demora": "demora",
    "preco": "preço",
    "qualidade": "qualidade",
    "ambiente": "ambiente",
}
ARTIGO = {"atendimento": "o", "demora": "a", "preco": "o", "qualidade": "a", "ambiente": "o"}

ESTADOS = {
    "vai_piorar": {"rotulo": "Vai piorar", "icone": "▲", "classe": "piorar"},
    "fique_de_olho": {"rotulo": "Fique de olho", "icone": "●", "classe": "olho"},
    "normal": {"rotulo": "Tudo normal", "icone": "✓", "classe": "normal"},
}

GLOSSARIO = {
    "avaliacoes_lidas": {
        "rotulo": "Avaliações lidas",
        "texto": "Todas as avaliações que os clientes escreveram sobre o negócio no mês, "
                 "boas e ruins. Inclui quem deu só estrelas, sem escrever nada.",
        "exemplo": "163 avaliações lidas: 142 viraram reclamação e 21 não.",
    },
    "reclamacoes": {
        "rotulo": "Reclamações",
        "texto": "Avaliações em que o cliente reclamou de alguma coisa. Cada uma é "
                 "encaixada num assunto: atendimento, demora, preço, qualidade ou ambiente.",
        "exemplo": "“A pizza chegou fria” é uma reclamação de demora.",
    },
    "assunto": {
        "rotulo": "Assunto",
        "texto": "O tema da reclamação. São cinco: atendimento, demora, preço, qualidade e "
                 "ambiente.",
        "exemplo": "“Cobraram uma taxa que ninguém avisou” fala de preço.",
    },
    "sem_assunto": {
        "rotulo": "Sem assunto",
        "texto": "Avaliações que não viraram reclamação: elogios, quem deu só estrelas e "
                 "frases vagas demais. O sistema prefere dizer que não sabe a inventar um assunto.",
        "exemplo": "“Fui atendido.” não diz se foi bom ou ruim.",
    },
    "nota_media": {
        "rotulo": "Nota média",
        "texto": "A média das estrelas, de 1 a 5, de todas as avaliações do mês. Quem deu só "
                 "estrelas também conta.",
        "exemplo": "Nota 2,1 quer dizer que a maioria deu 1 ou 2 estrelas.",
    },
    "mes_fechado": {
        "rotulo": "Mês fechado",
        "texto": "Um mês que já terminou. Só mês inteiro entra nas comparações, para não "
                 "comparar meio mês com mês inteiro.",
        "exemplo": "Em 13 de outubro, o último mês fechado é setembro.",
    },
    "mes_andamento": {
        "rotulo": "Mês em andamento",
        "texto": "O mês de agora, que ainda vai receber avaliações. A tela mostra quanto já "
                 "chegou e quanto deve chegar até o fim.",
        "exemplo": "Até 13 de outubro chegaram 22; até o fim do mês devem ser perto de 50.",
    },
    "estimativa": {
        "rotulo": "Estimativa",
        "texto": "Quantas reclamações devem chegar, olhando os meses anteriores. Vem sempre "
                 "com o mínimo e o máximo, porque ninguém sabe o número exato.",
        "exemplo": "“Cerca de 50, entre 47 e 52”.",
    },
    "minimo_maximo": {
        "rotulo": "Entre o mínimo e o máximo",
        "texto": "A faixa onde o número real deve cair. Em 8 de cada 10 meses, ele cai dentro "
                 "dela; quanto mais longe o mês, mais larga a faixa.",
        "exemplo": "“Entre 47 e 52”: menos de 47 ou mais de 52 seria surpresa.",
    },
    "avisos": {
        "rotulo": "Avisos",
        "texto": "Assuntos que devem crescer no mês. O sistema avisa antes de a reclamação virar "
                 "o motivo de o cliente não voltar.",
        "exemplo": "“A demora deve passar de 46 para cerca de 50.”",
    },
    "vai_piorar": {
        "rotulo": "Vai piorar",
        "texto": "O assunto deve crescer, e nem o melhor cenário volta ao número de hoje. "
                 "Vale agir já.",
        "exemplo": "A demora teve 46 em setembro; o mínimo esperado para outubro é 47.",
    },
    "fique_de_olho": {
        "rotulo": "Fique de olho",
        "texto": "O assunto deve crescer, mas ainda pode voltar ao normal sozinho. Vale "
                 "acompanhar.",
        "exemplo": "O preço deve subir de 22 para 24, mas pode ficar em 22.",
    },
    "chute_simples": {
        "rotulo": "O chute mais simples",
        "texto": "O palpite mais bobo possível, que serve de comparação. Se o sistema não ganhar "
                 "dele, não vale a pena usar o sistema.",
        "exemplo": "Para a estimativa, o chute é repetir o número do mês passado.",
    },
    "acerto": {
        "rotulo": "Acerto",
        "texto": "De cada 10 avaliações conferidas à mão, em quantas o sistema escolheu o "
                 "assunto certo.",
        "exemplo": "Acerta 8 de cada 10; o chute mais simples acerta 3.",
    },
    "certeza": {
        "rotulo": "Certeza",
        "texto": "O quanto o sistema tem certeza do assunto que escolheu. Com pouca certeza, ele "
                 "prefere deixar sem assunto.",
        "exemplo": "“A pizza chegou fria”: certeza alta de que é demora.",
    },
    "etapas": {
        "rotulo": "Passos combinados",
        "texto": "O que precisa estar pronto entre o combinado com o negócio e o aviso chegando "
                 "até o dono.",
        "exemplo": "Sem a autorização assinada, nenhuma avaliação real é lida.",
    },
}

FAQ = (
    ("Por que a estimativa não é um número exato?",
     "Porque ninguém sabe o futuro. Em vez de fingir, o sistema mostra o número mais provável "
     "e a faixa onde o real deve cair. Em 8 de cada 10 meses, ele cai dentro dela."),
    ("De onde vêm as avaliações?",
     "Das avaliações públicas do seu negócio na internet, lidas só com a sua autorização "
     "assinada. O nome e a foto de quem escreveu nunca são guardados."),
    ("A inteligência artificial decide alguma coisa?",
     "Não. Ela só lê cada avaliação, já sem nomes nem telefones, e diz de qual assunto ela "
     "reclama. Os números da estimativa e do aviso saem de contas conferidas, nunca da IA."),
    ("Por que algumas avaliações ficam sem assunto?",
     "Elogios, avaliações só com estrelas e frases vagas não dizem do que o cliente reclamou. O "
     "sistema prefere dizer que não sabe a chutar."),
)

# Página pública. Linguagem de quem tem o negócio, nada de sigla. Cada bloco
# descreve algo que o sistema faz hoje: promessa sem código atrás vira a
# reclamação do primeiro cliente.
ENTREGAS = (
    {
        "titulo": "Separa por assunto",
        "texto": "Cada avaliação entra em um de cinco assuntos: atendimento, demora, preço, "
                 "qualidade e ambiente. Quando o texto não deixa claro, o sistema diz que não "
                 "sabe, em vez de chutar e inflar uma conta.",
    },
    {
        "titulo": "Estima o mês e mostra a faixa",
        "texto": "Com os meses anteriores, estima quanto deve fechar o mês e entre que mínimo e "
                 "máximo. É a faixa que separa subida de verdade de sobe-e-desce normal.",
    },
    {
        "titulo": "Avisa com acerto medido",
        "texto": "Quando um assunto deve crescer, o aviso aparece. O acerto desse aviso é medido "
                 "e fica na tela: nenhuma promessa sem número atrás.",
    },
)

PASSOS = (
    ("01", "Liga a sua conta",
     "As avaliações do seu negócio são públicas. Você autoriza a leitura, ou envia o arquivo "
     "que exportou do painel da plataforma. Nada é instalado no seu negócio."),
    ("02", "Separa e conta por mês",
     "Cada avaliação vai para um assunto, e o sistema monta a contagem mês a mês. Nome de "
     "pessoa, telefone e documento são apagados antes de qualquer coisa ser guardada."),
    ("03", "Estima e avisa",
     "Com os meses fechados, estima o próximo e a faixa dele, e avisa quando um assunto deve "
     "crescer. O acerto do aviso fica na tela, ao lado do chute mais simples."),
)

DISPENSADO = (
    "Instalar programa, aplicativo ou aparelho no seu negócio.",
    "Dar acesso ao seu caixa, à sua agenda ou ao seu financeiro.",
    "Pedir para o seu cliente responder pesquisa.",
    "Ler avaliação uma por uma.",
)

TECNOLOGIAS = (
    ("O site", ("Python 3.12, FastAPI e Uvicorn", "Jinja2, com as telas montadas no servidor",
                "Gráficos em SVG desenhados em Python, sem biblioteca de gráfico",
                "CSS próprio, sem framework", "JavaScript só para melhorar, nunca para funcionar")),
    ("Dados", ("PostgreSQL 16 no Render e SQLAlchemy 2; as tabelas num script SQL único",
               "Toda tabela de dado operacional chega à empresa por chave estrangeira",
               "Chave única (negócio, id da plataforma) contra contagem dobrada")),
    ("Inteligência artificial", ("Gemini separa a avaliação por assunto, em formato fechado",
                                 "scikit-learn com TF-IDF e regressão, de reserva e de régua",
                                 "Estatística própria na estimativa do mês, conferida por "
                                 "origem móvel",
                                 "Nenhum número vem de modelo de linguagem")),
    ("Qualidade e segurança", ("pytest e Playwright, em celular e computador",
                               "axe para acessibilidade", "Ruff, bandit, pip-audit e gitleaks",
                               "Senha com Argon2id, token de fonte cifrado em repouso",
                               "Isolamento entre empresas provado por teste que tenta vazar")),
)

# O que falta para cada tela que saiu, e o que ela precisa para voltar sendo
# verdade. A tela "O que falta" lista isto para o cliente, sem termo técnico.
PROXIMAS_ETAPAS = (
    {
        "titulo": "Por que o assunto cresceu",
        "texto": "Hoje o sistema diz qual assunto cresce. Dizer o motivo exige o diário de "
                 "mudanças do negócio (troca de equipe, de preço, de horário) e teste "
                 "estatístico comparando antes e depois, com correção para quem testa muitas "
                 "hipóteses.",
        "falta": "O diário do negócio e o teste de hipótese.",
    },
    {
        "titulo": "E se eu mudar?",
        "texto": "Simular o efeito de contratar alguém ou mudar a escala exige saber a operação "
                 "do negócio: turnos, equipe por turno e tempo de atendimento.",
        "falta": "O cadastro dos turnos e o modelo de fila.",
    },
    {
        "titulo": "Testar na prática",
        "texto": "Provar que a mudança funcionou exige sortear os dias com e sem a mudança antes "
                 "de começar, e o dono marcar o que de fato fez em cada dia.",
        "falta": "O sorteio selado e a marcação diária.",
    },
)
