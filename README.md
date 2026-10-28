# Radar de Reclamações · PI6

Descobre por que os clientes de um pequeno negócio reclamam, mostra o efeito de
uma mudança antes de o dono gastar e prova, com um teste, se ela funcionou.

Projeto Integrador VI · Engenharia de Software · PUC-Campinas · 2026.2.
Gabriel Lopes Londe Rodrigues, Matheus Rocafa Moraes e Nicolas Marques Linares.
Orientação da Profa. Sílvia C. de Matos Soares.

Repositório: <https://github.com/NicolasML28/PI-VI>.

As regras do repositório estão em [`CLAUDE.md`](CLAUDE.md). O plano e a divisão do
trabalho ficam fora do git, com a equipe.

## O que já funciona

| Parte | Estado |
|---|---|
| Telas, gráficos, botões de ajuda e tour | Prontos, com dados de mentira (`app/falsos.py`) |
| Testes das telas e de ponta a ponta (390px e 1280px) | Prontos |
| Entrada com senha e uma conta por empresa | **Provisório:** a demonstração abre sem senha. É a Fase 0 do Matheus |
| Banco de dados | Falta. É a Fase 0 do Gabriel |
| Classificador, previsão, agente, simulador e teste de verdade | Faltam. Fases 1 a 3 do Gabriel |

Quando uma parte real fica pronta, só muda a função correspondente em
`app/servicos.py`; as telas continuam iguais.

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
