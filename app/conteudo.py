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
        "Descobre por que os clientes do seu negócio reclamam, mostra o efeito de uma "
        "mudança antes de você gastar e prova se ela funcionou."
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
        "faz": "As contas: separar as avaliações por assunto, prever o mês seguinte, "
               "investigar a causa, simular a mudança e analisar o teste na prática.",
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

MENU = (
    {"id": "resumo", "rotulo": "Resumo", "href": "/resumo"},
    {"id": "avisos", "rotulo": "Avisos", "href": "/avisos"},
    {"id": "investigacao", "rotulo": "Por quê?", "href": "/investigacao"},
    {"id": "simulador", "rotulo": "E se?", "href": "/simulador"},
    {"id": "experimentos", "rotulo": "Testes", "href": "/experimentos"},
    {"id": "ajuda", "rotulo": "Ajuda", "href": "/ajuda"},
)

MENU_MAIS = (
    {"id": "confianca", "rotulo": "Dá para confiar?", "href": "/confianca"},
    {"id": "o-que-falta", "rotulo": "O que falta", "href": "/o-que-falta"},
    {"id": "sobre", "rotulo": "Sobre o sistema", "href": "/sobre"},
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

VEREDITOS = {
    "sustentada": {"rotulo": "Provável causa", "classe": "provavel"},
    "inconclusiva": {"rotulo": "Ainda não dá para dizer", "classe": "incerta"},
    "descartada": {"rotulo": "Não parece ser isso", "classe": "descartada"},
}

FORCAS = {"forte": 3, "moderada": 2, "fraca": 1}

RESULTADOS_TESTE = {
    "funcionou": {"rotulo": "Funcionou", "classe": "provavel"},
    "nao_funcionou": {"rotulo": "Não funcionou", "classe": "descartada"},
    "ainda_nao_da_para_saber": {"rotulo": "Ainda não dá para saber", "classe": "incerta"},
}

# Cada termo: o rótulo, duas frases simples e um exemplo. Usado pelo botão "?".
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
    "possivel_causa": {
        "rotulo": "Possível causa",
        "texto": "Uma explicação que o sistema testou com as contas. Vem do seu diário, do "
                 "calendário, do clima, dos dias da semana ou das palavras que os clientes usam.",
        "exemplo": "“A demora aumentou depois que entrou o entregador novo.”",
    },
    "provavel_causa": {
        "rotulo": "Provável causa",
        "texto": "As contas mostram que essa explicação bate com o que aconteceu, e com folga. "
                 "É por ela que vale começar.",
        "exemplo": "Antes eram 4 reclamações por semana; depois, 8.",
    },
    "ainda_nao_da": {
        "rotulo": "Ainda não dá para dizer",
        "texto": "Pode ser, pode não ser. Faltam dados para ter certeza para um lado ou para o "
                 "outro.",
        "exemplo": "Com mais algumas semanas de chuva, dá para saber se a chuva pesa.",
    },
    "nao_parece": {
        "rotulo": "Não parece ser isso",
        "texto": "As contas mostram que essa explicação não muda nada, ou muda muito pouco. "
                 "Pode deixar de lado.",
        "exemplo": "O cardápio novo não mexeu na demora.",
    },
    "forca": {
        "rotulo": "Força da evidência",
        "texto": "O quanto as contas apoiam a explicação. Três barras é forte, uma barra é "
                 "fraca.",
        "exemplo": "Forte: a diferença é grande e aparece em quase todas as semanas.",
    },
    "ia_sugere": {
        "rotulo": "Ideia da inteligência artificial",
        "texto": "A inteligência artificial lê as avaliações, sem nomes nem telefones, e sugere "
                 "ideias. Quem decide se a ideia vale são as contas, nunca ela.",
        "exemplo": "Ela sugeriu “pizza saindo mais devagar”; as contas não confirmaram.",
    },
    "diario": {
        "rotulo": "Diário do negócio",
        "texto": "Onde você anota as mudanças do negócio, com a data. É dele que saem muitas "
                 "das possíveis causas.",
        "exemplo": "“2 de junho: entrou um entregador novo para sexta e sábado.”",
    },
    "simulador": {
        "rotulo": "E se?",
        "texto": "Mostra o que deve acontecer com as reclamações se você mudar quantas pessoas "
                 "trabalham em cada turno, e quanto isso custa. Nada muda de verdade.",
        "exemplo": "Um entregador a mais na sexta e no sábado à noite: de 50 para cerca de 36 reclamações.",
    },
    "espera": {
        "rotulo": "Espera média",
        "texto": "Quanto tempo, em média, o cliente espera para ser atendido ou receber o "
                 "pedido. É calculada pelo movimento e pela equipe de cada turno.",
        "exemplo": "Com 2 entregadores para 22 pedidos numa noite, a espera passa de meia hora.",
    },
    "custo_por_reclamacao": {
        "rotulo": "Custo por reclamação evitada",
        "texto": "Quanto a mudança custa por mês dividido por quantas reclamações ela deve "
                 "evitar. Ajuda a comparar mudanças diferentes.",
        "exemplo": "R$ 780 por mês para evitar 14 reclamações: cerca de R$ 56 cada.",
    },
    "teste_na_pratica": {
        "rotulo": "Teste na prática",
        "texto": "Você faz a mudança só em alguns dias, escolhidos por sorteio, e compara com os "
                 "outros dias. É o jeito de saber se funcionou de verdade ou foi coincidência.",
        "exemplo": "Entregador extra em 6 das 12 noites de sexta e sábado.",
    },
    "sorteio": {
        "rotulo": "Por que sortear os dias",
        "texto": "Se você escolhe os dias, sem querer escolhe os mais fáceis. O sorteio deixa a "
                 "comparação justa.",
        "exemplo": "Metade das sextas com a mudança, metade sem, por sorteio.",
    },
    "codigo_plano": {
        "rotulo": "Código do plano",
        "texto": "Um código que nasce junto com o plano do teste. Se alguém mudar o plano "
                 "depois de começar, o código deixa de bater e o sistema avisa.",
        "exemplo": "Anote o código: 3F9A-71C2.",
    },
    "seguiu_sorteio": {
        "rotulo": "Seguiu o sorteio",
        "texto": "Quantos dias a mudança foi feita exatamente como o sorteio mandou. Quanto mais "
                 "perto de todos, mais confiável o resultado.",
        "exemplo": "Seguiu em 11 de 12 dias.",
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
    "laboratorio": {
        "rotulo": "Laboratório",
        "texto": "Negócios de mentira em que nós sabemos a causa verdadeira. Servem para medir "
                 "se o sistema acerta antes de usar com negócio de verdade.",
        "exemplo": "Em 200 negócios de mentira, ele achou a causa certa em 148.",
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
     "Não. Ela só sugere ideias de possíveis causas, lendo avaliações sem nomes nem telefones. "
     "Quem decide se a ideia vale são as contas, e você vê o resultado de cada uma."),
    ("Por que os dias do teste são sorteados?",
     "Para a comparação ser justa. Se você escolhesse, sem querer pegaria os dias mais calmos, "
     "e a mudança pareceria melhor do que é."),
    ("O simulador muda alguma coisa no meu negócio?",
     "Não. Ele só mostra o que deve acontecer. Para mudar de verdade, você faz o teste na "
     "prática."),
    ("E se eu não souber quantas pessoas trabalham em cada turno?",
     "Responda “não sei”. O simulador avisa que falta esse dado em vez de inventar um "
     "número."),
    ("Por que algumas avaliações ficam sem assunto?",
     "Elogios, avaliações só com estrelas e frases vagas não dizem do que o cliente reclamou. O "
     "sistema prefere dizer que não sabe a chutar."),
)

# Página pública. Linguagem de quem tem o negócio, nada de sigla.
ENTREGAS = (
    {
        "titulo": "Por quê?",
        "texto": "Quando uma reclamação começa a crescer, o sistema investiga a causa: confere o "
                 "que mudou no seu negócio, o calendário, o clima e o que os clientes escrevem. "
                 "Mostra o que é provável e o que não é.",
    },
    {
        "titulo": "E se?",
        "texto": "Antes de contratar ou mudar a escala, você vê quantas reclamações a mudança "
                 "deve evitar e quanto ela custa por mês.",
    },
    {
        "titulo": "Testar na prática",
        "texto": "Você faz a mudança em dias sorteados e o sistema compara com os outros dias. "
                 "No fim, diz se funcionou de verdade ou se foi coincidência.",
    },
)

PASSOS = (
    ("01", "Lê o que já está escrito",
     "As avaliações do seu negócio são públicas. Com a sua autorização, o sistema lê todas e "
     "separa por assunto."),
    ("02", "Avisa antes de virar problema",
     "Com os meses anteriores, estima o próximo e avisa quando um assunto deve crescer."),
    ("03", "Ajuda a decidir e confere",
     "Mostra a causa provável, simula a solução e prova, com um teste, se ela funcionou."),
)

DISPENSADO = (
    "Instalar programa, aplicativo ou aparelho no seu negócio.",
    "Dar acesso ao seu caixa, à sua agenda ou ao seu financeiro.",
    "Pedir para o seu cliente responder pesquisa.",
    "Ler avaliação uma por uma.",
)

TECNOLOGIAS = (
    ("O site", ("Python 3.12, FastAPI e Uvicorn", "Jinja2, com as telas montadas no servidor",
                "Gráficos em SVG desenhados em Python", "CSS próprio, sem framework")),
    ("Dados e inteligência artificial", ("PostgreSQL, SQLAlchemy e Alembic",
                                         "pandas, NumPy, SciPy e statsmodels",
                                         "scikit-learn com TF-IDF na separação por assunto",
                                         "SimPy e teoria de filas no simulador")),
    ("Qualidade e segurança", ("pytest e Playwright, em celular e computador",
                               "axe para acessibilidade", "Ruff, bandit, pip-audit e gitleaks",
                               "Senha guardada com scrypt e proteção contra formulário falso")),
)
