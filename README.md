# Radar de Reclamações · PI6

Lê as avaliações públicas de um pequeno negócio, separa cada uma por assunto,
estima quantas reclamações de cada assunto devem chegar no mês e avisa quando um
assunto deve crescer. Cada número aparece na tela ao lado do chute mais simples
que existe, e onde o sistema não ganha do chute, está escrito que não ganha.

Projeto Integrador VI · Engenharia de Software · PUC-Campinas · 2026.2.
Gabriel Lopes Londe Rodrigues, Matheus Rocafa Moraes e Nicolas Marques Linares.
Orientação da Profa. Sílvia C. de Matos Soares.

Repositório: <https://github.com/NicolasML28/PI-VI>.

As regras do repositório estão em [`CLAUDE.md`](CLAUDE.md). A documentação está
em [`docs/`](docs/):

| Documento | Responde a |
|---|---|
| [`docs/fontes-de-avaliacao.md`](docs/fontes-de-avaliacao.md) | de onde as avaliações entram hoje, e o que Google e iFood exigiriam |
| [`docs/previsao-e-ia.md`](docs/previsao-e-ia.md) | o que o sistema acerta, o que não acerta, e como foi medido |
| [`docs/seguranca.md`](docs/seguranca.md) | cada item de segurança, onde está e qual teste prova |
| [`docs/producao.md`](docs/producao.md) | como pôr no ar e atender vinte clientes |

## O que já funciona

| Parte | Estado |
|---|---|
| Entrada das avaliações por arquivo CSV/JSON exportado da plataforma | Pronta. Google e iFood ficaram fora: dependem de autorização da plataforma |
| Separação por assunto, com IA (Gemini) e modelo próprio de reserva | Pronta. IA: F1 macro 0,895 em 500 frases de teste; modelo próprio 0,419; régua 0,067 |
| Contagem por mês, estimativa e faixa de mínimo e máximo | Pronta. Faixa cobre 0,82 do que promete 0,80 |
| Aviso de assunto que vai crescer | Pronto. Acerta 0,59 contra 0,22 da régua de alarme |
| Área do cliente: resumo, avisos, estimativa, configuração e conferência | Pronta |
| Área da equipe: cadastro de cliente, importação de arquivo, coletas, auditoria | Pronta |
| Entrada com senha Argon2id, isolamento por empresa e auditoria | Prontos |
| Banco PostgreSQL com as tabelas num script SQL único (`app/banco/esquema.sql`) | Pronto. Testes rodam no mesmo PostgreSQL |
| Por quê?: cada mudança do diário do negócio e o fim de semana testados como causa | Pronta. Razão de taxas de Poisson e Fisher, com correção de Benjamini-Hochberg |
| E se?: a fila de cada turno cadastrado e o efeito na demora | Pronta. Simulação com SimPy, conferida contra a fórmula de Erlang C |
| Testes na prática: sorteio dos dias, plano selado e comparação no fim | Pronta. Sorteio equilibrado por dia da semana, selo SHA-256, intenção de tratar |
| Conta de demonstração com dados simulados | Pronta. Só em cliente com o plano demonstração, com aviso em toda tela |
| Coleta rodando sozinha, aviso por e-mail, sessão revogável | Faltam. Ver `docs/producao.md` |

Só a conta de demonstração tem dado simulado, e toda tela dela avisa. Nas
outras, o que aparece veio de avaliação pública ou do que o dono cadastrou;
quando não há dado, a tela diz isso em uma frase.

### Duas contas para mostrar

- **Poco Loco Bar**: avaliações reais do Google, montadas com a SerpApi (ver abaixo)
  e importadas na tela Fontes.
- **Demonstração**: área da equipe → Clientes → cadastrar com o plano
  "demonstração" → na tela do cliente, "Preencher com dados simulados". Entram 15
  meses de avaliações simuladas (semente fixa), um diário com três mudanças, os
  turnos da semana e um teste já terminado, tudo pelo mesmo motor das reais.

## Rodar na sua máquina

Windows (PowerShell):

```powershell
py -3.12 -m venv .venv
```

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

```powershell
.venv\Scripts\python.exe -m uvicorn app.web:app --reload --port 8000
```

Mac ou Linux:

```bash
python3.12 -m venv .venv
```

```bash
.venv/bin/pip install -r requirements-dev.txt
```

```bash
.venv/bin/uvicorn app.web:app --reload --port 8000
```

Abre em <http://localhost:8000>.

## Testes

Os testes usam um PostgreSQL de verdade, onde criam e apagam bancos de teste:

```bash
export RADAR_TESTE_POSTGRES=postgresql://usuario@127.0.0.1:5432/postgres
```

Testes do código e das telas (rápidos):

```bash
python -m pytest -q
```

Testes no navegador, em celular e computador. Na primeira vez, instale o Chromium:

```bash
python -m playwright install chromium
```

```bash
python -m pytest -m e2e -q
```

No Windows dá para usar o Edge, sem baixar nada: `python -m pytest -m e2e --browser-channel msedge`.
Os prints de cada tela ficam em `docs/evidencias/telas/`, só na máquina (fora do git).

## Montar o arquivo do Google com a SerpApi

Para o negócio que **autorizou** a leitura mas não consegue exportar as avaliações
do painel. A ferramenta não faz parte do site: ela só monta o CSV, e o arquivo
entra pelo caminho de sempre, na tela **Fontes** da área da equipe.

1. Crie o arquivo `.env` na raiz (ele não vai para o git) com a chave da SerpApi,
   como no `.env.example`.
2. Rode, com o nome do lugar como aparece no Google Maps:

```bash
python -m ferramentas.serpapi_para_arquivo "Poco Loco Bar Campinas" --saida dados_reais/poco-loco.csv
```

O CSV sai sem o nome de quem escreveu e com a mesma máscara de dados pessoais do
sistema. Cada página de avaliações gasta uma busca da cota da SerpApi; use
`--max-paginas` para limitar. A pasta `dados_reais/` fica fora do git.

## Telas

| Endereço | O que mostra |
|---|---|
| `/` | Página pública, com uma ação só: entrar |
| `/resumo` | Um cartão por negócio, com o sinal (Vai piorar, Fique de olho, Tudo normal) |
| `/comercio/{negócio}` | Do que reclamaram no mês e as últimas avaliações |
| `/previsao/{negócio}` | O mês corrente e o seguinte, com mínimo e máximo |
| `/avisos` | Assuntos que devem crescer |
| `/investigacao/{negócio}/{assunto}` | Por quê?: as possíveis causas testadas, e o diário do negócio |
| `/simulador/{negócio}` | E se?: os turnos, a mudança de equipe e o efeito na espera e na demora |
| `/experimentos`, `/experimentos/{plano}` | Testes na prática: criar, ver os dias sorteados, marcar e ler o resultado |
| `/configuracao`, `/conferir` | De onde vêm as avaliações, canal de aviso e conferência dos assuntos pelo dono |
| `/confianca` | Dá para confiar? Cada parte comparada com o chute mais simples |
| `/o-que-falta`, `/ajuda` | Os passos que faltam em cada negócio, e o glossário |
| `/admin/...` | Área da equipe: clientes, fontes, coletas, auditoria e ficha do sistema |
| `/saude` | Estado do serviço, em JSON |

## Pastas

```
app/
  web.py            cria o site e liga as rotas
  contratos.py      os tipos combinados entre os três
  servicos.py       a única porta das telas para os dados
  conteudo.py       textos fixos e glossário dos botões "?"
  formatos.py       número, dinheiro e data em português
  graficos/         gráficos em SVG e as frases que os explicam
  rotas/            uma área de telas por arquivo
  templates/        o HTML de cada tela
  static/           CSS e JavaScript
  banco/            esquema.sql (as tabelas), modelo.py e as consultas  (Gabriel)
  modelos/          classificador, previsão, medida do acerto, e as contas de
                    Por quê? (causas.py), E se? (fila.py) e Testes (experimento.py)
  coleta/           leitura do arquivo, o motor que classifica e conta, e o
                    gerador da conta de demonstração (simulado.py)
  investigacao/     cliente da IA e a defesa contra injeção              (Matheus)
  seguranca/        entrada, sessão, isolamento, cofre                   (Matheus)
tests/              testes do código e das telas
tests/e2e/          testes no navegador
```
