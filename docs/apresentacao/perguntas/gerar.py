"""Gera os PDFs de preparação para a banca do Radar de Reclamações.

Um PDF por integrante (perguntas por nível de importância, com resposta e onde
mostrar, mais os erros que podem acontecer na parte dele e como mostrar a
solução) e um PDF geral com o que falta, o roteiro e a contingência.

Rodar: python3 gerar.py  (usa o Chrome instalado para imprimir em PDF)
"""

from __future__ import annotations

import html
import subprocess
from pathlib import Path

PASTA = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SITE = "radar-de-reclamacoes-pi6.onrender.com"

CSS = """
:root{--tinta:#15212B;--tinta-2:#43535F;--filete:#D8DDE0;--acao:#0F6E7B;--alt:#F1F4F5;
--critica:#9B2C2C;--alta:#B4531F;--media:#0F6E7B;
--serif:Georgia,"Times New Roman",serif;--ui:"Helvetica Neue",Helvetica,Arial,sans-serif}
*{box-sizing:border-box}
html,body{margin:0;color:var(--tinta);font:400 10.5pt/1.5 var(--ui);-webkit-print-color-adjust:exact;print-color-adjust:exact}
.capa{border-bottom:2px solid var(--tinta);padding-bottom:14px;margin-bottom:20px}
.capa__projeto{margin:0 0 6px;font:600 8.5pt/1 var(--ui);letter-spacing:.14em;text-transform:uppercase;color:var(--tinta-2)}
.capa__nome{margin:0;font:400 25pt/1.1 var(--serif)}
.capa__papel{margin:8px 0 0;font:600 11.5pt/1.4 var(--ui);color:var(--acao)}
.capa__linha{margin:10px 0 0;color:var(--tinta-2)}
h2{margin:22px 0 8px;font:400 16pt/1.2 var(--serif);break-after:avoid}
h3{margin:14px 0 4px;font:600 10.5pt/1.4 var(--ui);break-after:avoid}
p{margin:0 0 8px}
.nivel{display:inline-block;padding:2px 9px;border-radius:3px;color:#fff;font:600 8pt/1.6 var(--ui);letter-spacing:.1em;text-transform:uppercase;margin-right:8px;vertical-align:2px}
.nivel--critica{background:var(--critica)}.nivel--alta{background:var(--alta)}.nivel--media{background:var(--media)}
.explica{color:var(--tinta-2);font-size:9.5pt;margin:-2px 0 10px}
.pergunta{border-left:3px solid var(--filete);padding:6px 0 6px 12px;margin:0 0 10px;break-inside:avoid}
.pergunta__q{margin:0 0 4px;font-weight:600}
.pergunta__r{margin:0 0 4px}
.pergunta__onde{margin:0;font-size:9.5pt;color:var(--acao)}
table{width:100%;border-collapse:collapse;margin:6px 0 12px;font-size:9.8pt}
th,td{text-align:left;padding:6px 8px 6px 0;border-bottom:1px solid var(--filete);vertical-align:top}
thead th{font:600 8pt/1.3 var(--ui);letter-spacing:.1em;text-transform:uppercase;color:var(--tinta-2);border-bottom:1px solid var(--tinta)}
tr{break-inside:avoid}
.caixa{background:var(--alt);border-left:3px solid var(--acao);padding:10px 14px;margin:10px 0}
.caixa p{margin:0}
ol,ul{margin:0 0 10px;padding-left:20px}li{margin-bottom:4px}
code{font:9.5pt/1 Menlo,monospace;background:var(--alt);padding:1px 4px;border-radius:3px}
.junto{break-inside:avoid}
.rodape{margin-top:20px;padding-top:8px;border-top:1px solid var(--filete);font-size:8.5pt;color:var(--tinta-2)}
@page{size:A4;margin:14mm 14mm}
"""

NIVEIS = {
    "critica": ("Crítica", "A banca quase certamente pergunta. Saiba responder sem olhar."),
    "alta": ("Alta", "Pergunta provável. Responda com o número e mostre na tela."),
    "media": ("Média", "Pode aparecer. Uma frase e o lugar onde está basta."),
}

# ------------------------------------------------------------------ conteúdo

PESSOAS = [
    {
        "arquivo": "1-gabriel-banco-modelos-e-ia",
        "nome": "Gabriel Lopes Londe Rodrigues",
        "papel": "Banco de dados, modelos, previsão, medida da IA e publicação no Render",
        "linha": "Responde de onde vem o dado, como ele é guardado e quanto cada número do sistema acerta.",
        "parte": "Banco PostgreSQL e script das tabelas, classificador próprio, previsão do mês, medida do acerto, importação de avaliações e o serviço no Render.",
        "perguntas": {
            "critica": [
                ("De onde vêm as avaliações?",
                 "São avaliações públicas do negócio. Hoje entram por arquivo CSV ou JSON exportado do painel da plataforma, enviado pela equipe em Fontes. Google e iFood têm API, mas exigem autorização da plataforma; por isso ficaram fora, e cada cliente já tem a fonte registrada como \"aguardando autorização\".",
                 "Área da equipe, Fontes; e a ficha do cliente em Clientes."),
                ("A previsão funciona? Ganha do chute?",
                 "No número do meio, empata: erro médio 2,66 contra 2,65 de repetir o mês passado, em 2.592 meses de teste. Está escrito na tela. O que o sistema acrescenta é a faixa (o real caiu dentro dela em 82 de 100 meses, prometendo 80) e o aviso (\"vai piorar\" acerta 59 em 100, o chute acerta 22).",
                 "Tela \"Dá para confiar?\", seções 1 e 3."),
                ("Como vocês mediram a separação por assunto?",
                 "Em 500 frases de teste que o modelo nunca viu no treino. Métrica F1 macro, e \"não sei\" conta como erro. IA (Gemini): 0,895, acerta o assunto em 88 de 100. Modelo próprio: 0,419. Chute (sempre o assunto mais comum): 0,067.",
                 "Área da equipe, Sistema; arquivo app/modelos/medida_ia.json."),
                ("Como é o banco de dados?",
                 "PostgreSQL 16 no Render, 13 tabelas. A definição inteira está num script SQL só, app/banco/esquema.sql, que o serviço roda ao ligar. Toda tabela de dado carrega empresa_id, e nenhuma consulta lê sem filtrar por ele.",
                 "Arquivo app/banco/esquema.sql."),
            ],
            "alta": [
                ("Como o banco muda de versão sem ferramenta de migração?",
                 "O script usa CREATE TABLE IF NOT EXISTS e, para coluna nova, ALTER TABLE ... ADD COLUMN IF NOT EXISTS. Rodar de novo não apaga nada. Um teste quebra se o script e o modelo do código divergirem.",
                 "tests/test_banco.py."),
                ("O que é \"origem móvel\"?",
                 "Treina até o mês k, prevê o mês k+1, anda um mês e repete. Nunca sorteia meses: sortear deixa o modelo ver o futuro e dá um número bonito e falso.",
                 "app/modelos/previsao.py, comentário do topo."),
                ("Por que a IA não calcula os números?",
                 "Modelo de linguagem devolve número plausível, não número medido. A IA só diz o assunto de cada avaliação e escreve uma frase; estimativa, faixa e erro saem de estatística conferida.",
                 "docs/previsao-e-ia.md, seção 3."),
                ("Se a mesma avaliação for enviada duas vezes?",
                 "Não conta duas vezes: há chave única (negócio, identificador da avaliação na plataforma).",
                 "Importar o mesmo arquivo duas vezes: o recado diz 0 avaliações novas."),
            ],
            "media": [
                ("Por que ter um modelo próprio se a IA acerta mais?",
                 "Ele é a reserva quando a IA não responde (rede, limite da conta) e a régua que mostra quanto a IA acrescenta. Treina em menos de um segundo.",
                 "Área da equipe, Sistema: diz qual modelo está separando."),
                ("Como vocês testam?",
                 "411 testes de unidade e 66 no navegador (celular e computador), todos rodando em PostgreSQL de verdade, na máquina e no GitHub a cada envio.",
                 "Aba Actions do repositório."),
                ("Isso aguenta mais clientes?",
                 "No plano grátis cabem cerca de 20 negócios com 2 anos de avaliações (1 GB). Para produção paga: plano pago, backup do banco e coleta diária automática.",
                 "docs/producao.md, seção 4."),
                ("O banco de vocês vence?",
                 "O Postgres grátis do Render vence em 30 dias; o atual vai até 25/12/2026. Em produção de verdade é plano pago, com backup.",
                 "Painel do Render."),
            ],
        },
        "erros": [
            ("O site demora quase 1 minuto para abrir.",
             "O plano grátis do Render dorme após 15 min sem visita.",
             "Abrir o site 5 min antes. Se acontecer, dizer isso e mostrar /saude respondendo \"ok\"."),
            ("A tela do cliente diz que ainda não há avaliações.",
             "O negócio foi cadastrado sem avaliações.",
             "É o comportamento certo: sem dado, o sistema não inventa número. Importar o arquivo do negócio em Fontes e voltar à tela."),
            ("A importação recusa algumas linhas.",
             "Linha com data ou nota fora do formato.",
             "O recado diz quantas foram recusadas e as outras entram. Mostrar que um arquivo com 2 erros não perde as 300 linhas boas."),
            ("A IA não responde (limite da conta ou rede).",
             "Conta gratuita aceita poucas chamadas por minuto.",
             "O modelo próprio assume sozinho e nada quebra. Mostrar em Sistema qual modelo está separando."),
        ],
    },
    {
        "arquivo": "2-matheus-seguranca-e-lgpd",
        "nome": "Matheus Rocafa Moraes",
        "papel": "Segurança, LGPD, isolamento entre clientes e IA segura",
        "linha": "Responde por que um cliente nunca vê o dado do outro e por que nada sensível fica exposto.",
        "parte": "Entrada e sessão, senha, isolamento por empresa, defesa contra injeção na IA, mascaramento de dado pessoal, ficha cifrada, auditoria e CI de segurança.",
        "perguntas": {
            "critica": [
                ("Como um cliente não vê o dado do outro?",
                 "A empresa de quem pede vem só da sessão assinada, nunca do endereço nem do formulário. Três travas: uma em toda rota, uma por negócio e uma para a área da equipe. Negócio que não existe e negócio de outro recebem a mesma recusa, para não revelar quais existem.",
                 "Entrar como pocoloco e abrir /comercio/bar-do-alemao-1: o sistema recusa."),
                ("Como as senhas são guardadas?",
                 "Só como hash Argon2id (o recomendado pela OWASP), nunca em texto. A senha de cliente novo é sorteada e aparece uma única vez, no corpo da resposta, nunca no endereço da página e sem ficar em cache.",
                 "Cadastrar um cliente ao vivo em Clientes."),
                ("E a LGPD?",
                 "O autor da avaliação nunca é gravado. Telefone, e-mail, CPF, CNPJ, CEP, site, @usuário e nome depois de \"o atendente\", \"a Dra.\" são apagados antes de gravar. Dados de quem contrata ficam na ficha cifrada. Existe botão para apagar o cliente inteiro.",
                 "Tela do negócio: nomes aparecem como [nome]; botão \"Apagar este cliente\"."),
                ("E se alguém escrever na avaliação \"ignore as instruções\"?",
                 "O texto vai dentro de um envelope marcado como dado, a resposta só aceita um dos cinco assuntos em formato fechado, e o que a IA devolve nunca vira ação no sistema. Testamos ao vivo com essa frase: a IA respondeu \"sem assunto\", como devia.",
                 "tests/seguranca/test_ia_segura.py."),
            ],
            "alta": [
                ("Como funciona a sessão e o CSRF?",
                 "Cookie assinado, HttpOnly, SameSite=Lax e Secure, válido por 8 horas. Todo formulário leva um token contra CSRF, conferido em tempo constante.",
                 "app/seguranca/middleware.py."),
                ("E força bruta na senha?",
                 "8 tentativas a cada 5 minutos por origem; depois disso nem testa a senha. No máximo 2 conferências de senha ao mesmo tempo, para não estourar a memória do servidor.",
                 "Só descrever: testar na banca bloqueia o computador da apresentação por 5 min. Prova: tests/seguranca/test_entrada.py."),
                ("O que é a ficha cifrada?",
                 "CNPJ, responsável, contato e onde o negócio está no Google e no iFood vão cifrados (Fernet) para o banco. Sem a chave do cofre, o sistema recusa gravar. A auditoria registra que a ficha mudou, nunca o conteúdo.",
                 "Ficha do cliente em Clientes; tests/test_ficha.py."),
                ("Quais cabeçalhos de segurança o site manda?",
                 "CSP sem script inline, HSTS, X-Frame-Options DENY e nosniff. A chave da IA vai em cabeçalho, nunca no endereço nem no log.",
                 "Ferramentas do navegador, aba Rede."),
            ],
            "media": [
                ("Como vocês acham falha em dependência?",
                 "A cada envio, o GitHub roda bandit (código), pip-audit (bibliotecas com falha conhecida) e gitleaks (segredo no repositório).",
                 "Aba Actions, workflow Segurança."),
                ("O que ainda falta na segurança?",
                 "Sessão revogável no servidor (hoje um cookie roubado vale até 8 h), segundo fator para a equipe e limite de tentativas também por conta. Está escrito em docs/producao.md.",
                 "docs/producao.md, seção 6."),
                ("Quem fez o quê fica registrado?",
                 "Sim: toda ação da equipe vai para a trilha de auditoria, com empresa, usuário e hora, na mesma transação da mudança.",
                 "Área da equipe, Auditoria."),
                ("A equipe do Radar vê tudo?",
                 "A equipe opera o sistema e atravessa o isolamento de propósito, mas cada ação dela fica na trilha. O cliente nunca entra na área da equipe.",
                 "Entrar como cliente e abrir /admin: recusado."),
            ],
        },
        "erros": [
            ("Ao entrar aparece \"bloqueado\".",
             "Errou a senha 8 vezes em 5 minutos.",
             "É a proteção contra força bruta funcionando. Esperar 5 minutos e mostrar isso como prova."),
            ("Aparece \"Token de segurança inválido\".",
             "A página ficou aberta de uma sessão antiga.",
             "Recarregar a página e enviar de novo. Explicar que é a defesa contra CSRF."),
            ("O cliente abre um negócio e recebe \"Essa página não existe\".",
             "O negócio é de outra empresa.",
             "É o isolamento: a mesma resposta para negócio alheio e inexistente."),
            ("O cliente perdeu a senha.",
             "A senha é mostrada uma vez só e não é guardada em texto.",
             "Na tela do cliente: desligar a conta antiga e criar outra; a senha nova aparece na hora."),
        ],
    },
    {
        "arquivo": "3-nicolas-telas-graficos-e-experiencia",
        "nome": "Nicolas Marques Linares",
        "papel": "Telas, gráficos, textos para leigos e testes no navegador (front)",
        "linha": "Responde se o dono de um bar entende a tela sem ajuda e se ela funciona no celular.",
        "parte": "Todas as telas do cliente e da equipe, os gráficos em SVG, os textos e a ajuda, o tour de primeira vez, o responsivo e os testes de ponta a ponta.",
        "perguntas": {
            "critica": [
                ("Uma pessoa leiga entende essas telas?",
                 "A tela do dono não tem termo técnico. Cada gráfico tem acima a frase que responde à pergunta, embaixo \"Como ler este gráfico\" e \"Ver os números em tabela\", e a legenda fica à vista. Termo técnico só aparece em \"Detalhes técnicos\", para a banca.",
                 "Tela \"O que vem por aí\" de um negócio."),
                ("Mostre o caminho do dono do negócio.",
                 "Resumo (um cartão por negócio, com o sinal) → Ver o que vem por aí (estimativa e faixa) → Avisos → Dá para confiar? → Conferir avaliações.",
                 "Entrar como pocoloco e seguir os botões de \"Próximo passo\"."),
                ("Como a equipe cria um cliente novo?",
                 "Em Clientes: nome, negócio, ramo, cidade, entrada do dono e, se quiser, a ficha cifrada. Um clique cria empresa, negócio e conta, e mostra a senha uma vez. O dono já entra.",
                 "Fazer ao vivo com um terceiro negócio."),
                ("Funciona no celular?",
                 "Sim. Os 66 testes de navegador rodam cada tela em 390 e 1280 pixels, conferem acessibilidade e falham se alguma letra de gráfico ficar menor que 12 px.",
                 "Abrir o site no celular de alguém da banca."),
            ],
            "alta": [
                ("O que significam as cores e o sinal?",
                 "Vai piorar (assunto deve crescer), Fique de olho e Tudo normal. Laranja no gráfico = subiu em relação ao mês anterior; cinza = caiu ou já aconteceu.",
                 "Resumo e tela do negócio; botões \"?\"."),
                ("Por que os gráficos são feitos à mão em SVG?",
                 "Desenhados no servidor, sem biblioteca: a página chega pronta, funciona sem JavaScript e é leve no celular.",
                 "app/graficos/svg.py."),
                ("Por que algumas telas aparecem vazias?",
                 "Sem dado, a tela diz isso numa frase em vez de mostrar número inventado. O dono decide em cima do número; número falso é pior que tela vazia.",
                 "Entrar num negócio sem avaliações."),
                ("O dono pode corrigir a IA?",
                 "Sim, em Conferir: dois cliques por avaliação. Com 30 conferidas, \"Dá para confiar?\" passa a medir o acerto no dado dele.",
                 "Tela Conferir."),
            ],
            "media": [
                ("Tem ajuda para quem entra pela primeira vez?",
                 "Tour de cinco passos no Resumo e a página Ajuda, com perguntas frequentes e o significado de cada palavra.",
                 "Botão \"Primeira vez aqui? Faça o tour\"."),
                ("Com o que as telas foram feitas?",
                 "FastAPI e Jinja2 no servidor, CSS próprio sem framework, JavaScript só para melhorar (o tour), nunca para funcionar.",
                 "Área da equipe, Sistema."),
                ("Por que não há botão de WhatsApp ou chat?",
                 "O produto é um painel de leitura; cada tela tem uma ação principal, para o dono não se perder.",
                 "Qualquer tela: um botão principal."),
                ("Como vocês sabem que não quebrou nada ao mudar uma tela?",
                 "Os testes de navegador clicam como uma pessoa, em celular e computador, e guardam um print de cada tela como evidência.",
                 "Pasta docs/evidencias/telas."),
            ],
        },
        "erros": [
            ("Um gráfico não aparece.",
             "O negócio ainda não tem meses fechados suficientes (a estimativa começa com 6).",
             "A tela diz o motivo numa frase. Mostrar outro negócio com dado ou importar o arquivo."),
            ("Na tela grande a projeção corta a página.",
             "Resolução do projetor.",
             "Usar o zoom do navegador em 80%; o layout se ajusta sem quebrar."),
            ("Sem internet na sala.",
             "O site está no Render, fora da faculdade.",
             "Ter os prints de docs/evidencias/telas e este PDF abertos no computador."),
            ("O tour não abre.",
             "O JavaScript ainda não carregou.",
             "Esperar a página terminar de carregar; sem o tour, tudo continua funcionando."),
        ],
    },
]

GERAL = {
    "arquivo": "0-roteiro-o-que-falta-e-contingencia",
    "faltam": [
        ("Crítica", "Os dois negócios estão sem avaliações.",
         "Sem elas, as telas do cliente mostram \"ainda sem dados\" e a banca não vê gráfico com dado real. Decidir hoje: importar o arquivo do Poco Loco (autorização assinada) antes da apresentação, ou mostrar a importação ao vivo."),
        ("Crítica", "Slides de resultado.",
         "O deck de 29/09 é a proposta. A banca espera resultado: números medidos, telas e o que ficou de fora."),
        ("Alta", "Testar a entrada dos dois clientes.",
         "Entrar uma vez como pocoloco e bardoalemao antes da banca, com as senhas que o Gabriel guardou."),
        ("Alta", "Abrir o site 5 minutos antes.",
         "O plano grátis dorme; a primeira visita pode levar 1 minuto."),
        ("Média", "Dividir quem fala o quê.",
         "Cada integrante leva o próprio PDF; cada um fala da sua parte e responde as perguntas dela."),
    ],
    "roteiro": [
        "Gabriel (3 min): o problema, de onde vem o dado, como é guardado e os números medidos (IA 0,895; previsão empata e o que a faixa e o aviso acrescentam).",
        "Nicolas (3 min): a experiência do dono. Resumo, O que vem por aí, Avisos, Dá para confiar?. Mostrar no celular.",
        "Matheus (3 min): segurança ao vivo. Cliente tentando abrir negócio de outro (recusado), senha que aparece uma vez, ficha cifrada.",
        "Os três (2 min): cadastro de um cliente novo ao vivo na área da equipe, e o dono entrando com a senha sorteada.",
        "Encerramento (1 min): o que ficou de fora e por quê (Google/iFood dependem de autorização; coleta diária; plano pago).",
    ],
    "contingencia": [
        ("Site não abre ou demora", "Instância grátis dormindo", "Esperar 1 min; mostrar /saude; se cair, prints de docs/evidencias/telas."),
        ("Tela de cliente vazia", "Negócio sem avaliações", "Explicar que não inventa número; importar o arquivo em Fontes."),
        ("IA não responde", "Limite da conta gratuita", "Modelo próprio assume; Sistema mostra qual está ligado."),
        ("\"Bloqueado\" ao entrar", "Senha errada 8 vezes", "Proteção funcionando; esperar 5 min."),
        ("\"Token de segurança inválido\"", "Página antiga aberta", "Recarregar e reenviar."),
        ("Banco não ligado", "Banco do Render fora do ar", "A tela da equipe explica o que fazer; /saude continua respondendo."),
        ("Sem internet", "Rede da sala", "PDFs e prints locais; vídeo de demonstração, se houver."),
    ],
}

# ------------------------------------------------------------------ montagem

e = html.escape


def cabeca(titulo: str) -> str:
    return f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{e(titulo)}</title><style>{CSS}</style></head><body>'


def capa(nome: str, papel: str, linha: str) -> str:
    return (f'<header class="capa"><p class="capa__projeto">Radar de Reclamações · PI VI · PUC-Campinas · banca de 25/11/2026</p>'
            f'<h1 class="capa__nome">{e(nome)}</h1><p class="capa__papel">{e(papel)}</p>'
            f'<p class="capa__linha">{e(linha)}</p></header>')


def pdf_pessoa(p: dict) -> str:
    partes = [cabeca(p["nome"]), capa(p["nome"], p["papel"], p["linha"])]
    partes.append(f'<div class="caixa"><p><strong>Sua parte:</strong> {e(p["parte"])} '
                  f'São 12 perguntas, quatro por nível, o mesmo número para cada integrante.</p></div>')
    numero = 0
    for chave in ("critica", "alta", "media"):
        rotulo, explica = NIVEIS[chave]
        titulo = (f'<h2><span class="nivel nivel--{chave}">{rotulo}</span>Perguntas de importância {rotulo.lower()}</h2>'
                  f'<p class="explica">{e(explica)}</p>')
        for indice, (pergunta, resposta, onde) in enumerate(p["perguntas"][chave]):
            numero += 1
            bloco = (f'<div class="pergunta"><p class="pergunta__q">{numero}. {e(pergunta)}</p>'
                     f'<p class="pergunta__r">{e(resposta)}</p>'
                     f'<p class="pergunta__onde">Onde mostrar: {e(onde)}</p></div>')
            # O título do nível vai junto da primeira pergunta: nunca sozinho no pé da página.
            partes.append(f'<div class="junto">{titulo}{bloco}</div>' if indice == 0 else bloco)
    partes.append('<h2>Erros que podem acontecer na sua parte</h2>'
                  '<table><thead><tr><th>O que aparece</th><th>Por quê</th><th>Como mostrar a solução</th></tr></thead><tbody>')
    for o_que, porque, solucao in p["erros"]:
        partes.append(f'<tr><td>{e(o_que)}</td><td>{e(porque)}</td><td>{e(solucao)}</td></tr>')
    partes.append('</tbody></table>')
    partes.append(f'<p class="rodape">Site: {SITE} · Repositório: github.com/NicolasML28/PI-VI · '
                  'Números medidos em 24/11/2026.</p></body></html>')
    return "".join(partes)


def pdf_geral() -> str:
    g = GERAL
    partes = [cabeca("Roteiro, o que falta e contingência"),
              capa("Roteiro da banca", "O que falta, a ordem da apresentação e o que fazer se algo der errado",
                   "Para os três. Lido na véspera, aberto no dia.")]
    partes.append('<div class="caixa"><p><strong>Estamos prontos?</strong> O sistema está no ar e testado '
                  '(411 testes de unidade e 66 no navegador, em PostgreSQL). O que falta não é código: '
                  'são os dados dos negócios e os slides de resultado.</p></div>')
    partes.append('<h2>O que falta antes da banca</h2><table><thead><tr><th>Nível</th><th>O quê</th><th>Por quê e como</th></tr></thead><tbody>')
    for nivel, o_que, como in g["faltam"]:
        classe = {"Crítica": "critica", "Alta": "alta", "Média": "media"}[nivel]
        partes.append(f'<tr><td><span class="nivel nivel--{classe}">{nivel}</span></td><td>{e(o_que)}</td><td>{e(como)}</td></tr>')
    partes.append('</tbody></table><h2>Roteiro, dividido em partes iguais</h2><ol>')
    partes += [f'<li>{e(item)}</li>' for item in g["roteiro"]]
    partes.append('</ol><h2>Se algo der errado</h2><table><thead><tr><th>O que aparece</th><th>Por quê</th><th>O que fazer na hora</th></tr></thead><tbody>')
    for o_que, porque, fazer in g["contingencia"]:
        partes.append(f'<tr><td>{e(o_que)}</td><td>{e(porque)}</td><td>{e(fazer)}</td></tr>')
    partes.append('</tbody></table>')
    partes.append('<h2>Números para ter na ponta da língua</h2><table><thead><tr><th>Medida</th><th>Sistema</th><th>Chute simples</th></tr></thead><tbody>'
                  '<tr><td>Separação por assunto (F1 macro, 500 frases)</td><td>IA 0,895 · modelo próprio 0,419</td><td>0,067</td></tr>'
                  '<tr><td>Aviso "vai piorar" (acerto)</td><td>59 em 100</td><td>22 em 100</td></tr>'
                  '<tr><td>Erro médio da estimativa do mês</td><td>2,66</td><td>2,65 (empata)</td></tr>'
                  '<tr><td>Faixa de mínimo e máximo (prometido 80)</td><td>82 em 100</td><td>não tem faixa</td></tr>'
                  '</tbody></table>')
    partes.append(f'<p class="rodape">Site: {SITE} · As senhas dos clientes ficam com o Gabriel, fora deste PDF.</p></body></html>')
    return "".join(partes)


def imprimir(nome: str, conteudo: str) -> None:
    fonte = PASTA / f"{nome}.html"
    fonte.write_text(conteudo, encoding="utf-8")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={PASTA / (nome + '.pdf')}", fonte.as_uri()],
                   check=True, capture_output=True, timeout=120)


if __name__ == "__main__":
    imprimir(GERAL["arquivo"], pdf_geral())
    for pessoa in PESSOAS:
        imprimir(pessoa["arquivo"], pdf_pessoa(pessoa))
    print("ok")
