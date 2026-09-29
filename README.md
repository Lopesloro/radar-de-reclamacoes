# Radar de Reclamações

Projeto Integrador VI · Engenharia de Software · PUC-Campinas · 2º semestre de 2026

Site que lê a avaliação pública de um comércio parceiro, diz **por que** os
clientes reclamam hoje e **qual reclamação tende a crescer** no próximo mês.

Integrantes: Gabriel Lopes Londe Rodrigues, Nicolas Marques Linares e
Matheus Rocafa Moraes. Orientação da Profa. Sílvia C. de Matos Soares.

## Os dois modelos

| | Pergunta | Métrica | Régua |
|---|---|---|---|
| **Classificação** | Por que este cliente reclamou? | F1 por categoria e F1 macro | responder sempre a categoria mais comum |
| **Previsão** | Quantas reclamações desta categoria no mês que vem? | erro médio absoluto e cobertura da faixa | repetir o mês anterior |

Nenhum dos dois vai para a tela sem superar a régua. O resultado medido fica
aberto na tela **Acurácia**, e há teste que falha quando o modelo perde.

O previsor parte da régua — o último mês fechado — e só se afasta dela quando a
inclinação dos últimos seis meses supera o próprio erro padrão. Onde não há
tendência distinguível de ruído, ele devolve a régua, de propósito.

## Telas

| Rota | O que mostra |
|---|---|
| `/` | A ideia, os dois modelos, a equipe, as tecnologias e o tratamento de situações não previstas |
| `/painel` | Os comércios parceiros, a categoria mais reclamada e a que está em alta prevista |
| `/comercio/{id}` | Distribuição por categoria, variação sobre o mês anterior e as avaliações lidas |
| `/previsao/{id}` | Histórico, mês em andamento e a faixa P10–P90 prevista, categoria a categoria |
| `/alertas` | Fila de alta prevista, com confirmar e descartar |
| `/acuracia` | F1 por categoria e previsto contra realizado, sempre ao lado da régua |
| `/saude` | Estado do serviço em JSON |

## Como abrir

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
```

```bash
./.venv/bin/uvicorn app.web:app --reload --port 8000
```

Depois abra <http://localhost:8000>.

Testes:

```bash
./.venv/bin/python -m pytest -q -ra
```

## Dados

Os números das telas são **de demonstração** (`app/demo.py`): comércios,
avaliações e contagens fictícias, geradas no servidor de forma determinística.
Nenhuma avaliação exibida foi escrita por um cliente real. A coleta real começa
quando os termos de autorização dos parceiros estiverem assinados — é a primeira
tarefa da sprint de dados, e sem ela nada é coletado.

Quando a coleta começar: a avaliação é pública, o autor dela não entra no
projeto. Nome, foto e qualquer tentativa de identificar quem escreveu ficam fora,
e a citação no relatório é anonimizada.

## Estrutura

```
app/
  web.py            rotas FastAPI
  conteudo.py       texto institucional: projeto, equipe, tecnologias, robustez
  demo.py           dados de demonstração, previsão e avaliação dos modelos
  formatos.py       números e datas no padrão brasileiro
  graficos/svg.py   gráficos gerados no servidor
  templates/        Jinja2, um arquivo por tela
  static/           CSS e JS próprios, sem framework
tests/              pytest sobre o cliente de teste do Starlette
```

O visual segue o Dialeto A (Autoridade) do padrão de sites, adaptado para
painel: serifa no título, régua de 140×6px, filete no lugar de sombra, uma só
cor de ação, e número sempre em sans com algarismos tabulares.
