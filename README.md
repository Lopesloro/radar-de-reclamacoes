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
| [`docs/fontes-de-avaliacao.md`](docs/fontes-de-avaliacao.md) | como o comerciante liga a conta dele, e o que cada plataforma exige |
| [`docs/previsao-e-ia.md`](docs/previsao-e-ia.md) | o que o sistema acerta, o que não acerta, e como foi medido |
| [`docs/seguranca.md`](docs/seguranca.md) | cada item de segurança, onde está e qual teste prova |
| [`docs/producao.md`](docs/producao.md) | como pôr no ar e atender vinte clientes |

## O que já funciona

| Parte | Estado |
|---|---|
| Leitura das avaliações: Google, iFood e arquivo CSV/JSON | Pronta. Google e iFood dependem de liberação da plataforma; o arquivo funciona hoje |
| Separação por assunto, com IA e com modelo próprio de reserva | Pronta. F1 macro 0,42 contra 0,07 da régua |
| Contagem por mês, estimativa e faixa de mínimo e máximo | Pronta. Faixa cobre 0,82 do que promete 0,80 |
| Aviso de assunto que vai crescer | Pronto. Acerta 0,59 contra 0,22 da régua de alarme |
| Área do cliente: resumo, avisos, estimativa, configuração e conferência | Pronta |
| Área da equipe: cadastro de cliente, fontes, coleta, auditoria | Pronta |
| Entrada com senha Argon2id, isolamento por empresa e auditoria | Prontos |
| Coleta rodando sozinha, aviso por e-mail, sessão revogável | Faltam. Ver `docs/producao.md` |
| Por que o assunto cresceu, "E se eu mudar?" e teste na prática | Faltam. Saíram do produto quando o gerador de dados fictícios foi removido |

Nenhuma tela mostra dado de demonstração: o gerador de avaliações fictícias foi
removido. Quando não há dado, a tela diz isso em uma frase.

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

## Telas

| Endereço | O que mostra |
|---|---|
| `/` | Página pública, com uma ação só: entrar |
| `/resumo` | Um cartão por negócio, com o sinal (Vai piorar, Fique de olho, Tudo normal) |
| `/comercio/{negócio}` | Do que reclamaram no mês e as últimas avaliações |
| `/previsao/{negócio}` | O mês corrente e o seguinte, com mínimo e máximo |
| `/avisos` | Assuntos que devem crescer |
| `/investigacao/{negócio}/{assunto}` | **Por quê?** As possíveis causas, testadas |
| `/simulador/{negócio}` | **E se?** O efeito e o custo de mudar a equipe |
| `/experimentos` | **Testes na prática**, com os dias sorteados e o resultado |
| `/confianca` | Dá para confiar? Cada parte comparada com o chute mais simples |
| `/o-que-falta`, `/ajuda`, `/sobre` | O que falta, glossário e a área da banca |
| `/saude` | Estado do serviço, em JSON |

## Pastas

```
app/
  web.py            cria o site e liga as rotas
  contratos.py      os tipos combinados entre os três
  servicos.py       a única porta das telas para os dados
  falsos.py         dados de mentira com o formato dos contratos
  conteudo.py       textos fixos e glossário dos botões "?"
  formatos.py       número, dinheiro e data em português
  graficos/         gráficos em SVG e as frases que os explicam
  rotas/            uma área de telas por arquivo
  templates/        o HTML de cada tela
  static/           CSS e JavaScript
  banco/ modelos/ mundo/ investigacao/ decisao/ experimento/ coleta/   (Gabriel)
  seguranca/                                                           (Matheus)
tests/              testes do código e das telas
tests/e2e/          testes no navegador
```
