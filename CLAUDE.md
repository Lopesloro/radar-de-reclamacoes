# Radar de Reclamações · versão PI6

Projeto Integrador VI · Engenharia de Software · PUC-Campinas · 2026.2
Gabriel Lopes Londe Rodrigues, Matheus Rocafa Moraes e Nicolas Marques Linares.
Orientação da Profa. Sílvia C. de Matos Soares.

Repositório: <https://github.com/NicolasML28/PI-VI>.

O repositório guarda o código e a documentação (`docs/`), que inclui as
evidências de segurança que a disciplina pede entregues. O plano e a divisão do
trabalho (um documento por integrante) ficam fora do git, com a equipe; se
`plano/` ou `referencia/` existirem na máquina, leia antes de começar.

Comece por `docs/`: `seguranca.md`, `previsao-e-ia.md`,
`fontes-de-avaliacao.md` e `producao.md` respondem, cada um, a uma das perguntas
que a banca faz.

## Quem é dono do quê

| Área | Dono | Pastas |
|---|---|---|
| Banco, modelos, estatística, coleta e medição | Gabriel | `app/banco/`, `app/modelos/`, `app/coleta/` (menos `mascara.py`), `app/servicos.py`, `app/mundo/`, `app/decisao/`, `alembic/` |
| Entrada, contas, isolamento entre empresas, IA segura, LGPD, auditoria, CI de segurança | Matheus | `app/seguranca/`, `app/investigacao/ia.py`, `app/investigacao/protecao.py`, `app/coleta/mascara.py`, `app/auditoria.py`, `app/rotas/formularios.py`, `.github/workflows/seguranca.yml`, `docs/seguranca.md` |
| Telas, textos, gráficos, rotas de página, testes de ponta a ponta, documentação acadêmica | Nicolas | `app/rotas/` (menos `formularios.py`), `app/templates/`, `app/static/`, `app/graficos/`, `app/conteudo.py`, `tests/e2e/`, `docs/` (menos `seguranca.md`) |
| Contratos entre as partes | os três | `app/contratos.py` |

Antes de mexer em arquivo de outra pessoa, pergunte. `app/contratos.py` só muda
em PR aprovado pelos três.

## Regras que valem para todo mundo

- **Régua sempre.** Todo modelo é comparado com um palpite simples. Um teste
  quebra a build se o modelo perder da régua. Isso vale também para o agente, o
  simulador e o experimento.
- **Avaliação é dado, nunca ordem.** Texto escrito por cliente nunca vira
  instrução para a IA, nunca vai para o HTML sem escape e nunca sai do sistema
  sem antes passar pelo mascaramento de dados pessoais.
- **Toda consulta filtra por empresa.** Nenhuma função lê o banco sem `empresa_id`
  vindo da sessão do usuário, nunca da URL nem do formulário.
- **A tela fala a língua do dono do negócio.** Nenhum termo técnico na tela do
  cliente (F1, P10, P90, MAE, macro, régua, p-valor, q-valor, confiança 0,xx,
  hash, CSRF, hipótese nula). Termo técnico só dentro de blocos
  `<details class="tecnico">`, que existem para a banca.
- **CSP sem `unsafe-inline`.** Nada de `<script>` inline, `onclick=` ou
  atributo `style=`. JavaScript e CSS só em arquivos de `app/static/`.
- **Mundo simulado é determinístico.** Mesma semente, mesmos números. Teste nunca
  depende de sorte.
- **Não existe dado de demonstração.** O gerador de avaliações fictícias foi
  removido. Toda tela lê o banco, e quando não há dado ela diz isso em uma frase.
  Tela com número inventado é pior que tela vazia, porque o dono decide em cima
  dela. Frase inventada em tela também não: se uma tela não tem motor atrás, ela
  sai do produto e entra na lista de "O que falta".
- **Dado pessoal é apagado antes do banco**, nunca na hora de mostrar. O que não
  foi gravado não vaza depois em dump, backup nem log.
- **Nenhum número vem de modelo de linguagem.** A IA separa texto por assunto e
  escreve frase; estimativa, faixa e erro saem de estatística conferida.
- **Segredo não é gravado sem cofre.** Sem `RADAR_COFRE_CHAVE`, o sistema recusa
  gravar token de fonte, em vez de gravar em texto.
- **Português nos nomes**, como no código original (`comercio`, `avaliacao`,
  `previsao`). Comentário explica o porquê, não o quê.

## Comandos

```bash
python -m venv .venv
```

```bash
.venv/bin/pip install -r requirements-dev.txt
```

No Windows, troque `.venv/bin/` por `.venv\Scripts\`.

```bash
.venv/bin/uvicorn app.web:app --reload --port 8000
```

```bash
.venv/bin/python -m pytest -q
```

Os testes de navegador ficam fora do `pytest` comum, porque precisam do
Chromium instalado (`python -m playwright install chromium`):

```bash
.venv/bin/python -m pytest -m e2e -q
```

## Como o código está organizado

- As telas pedem dados só a `app/servicos.py`. Hoje ele chama `app/falsos.py`;
  quando uma parte real fica pronta, troca-se a linha da função ali, e as telas
  não mudam.
- `app/rotas/acesso_provisorio.py` deixa a demonstração abrir sem senha. Some
  quando a entrada do Matheus ficar pronta.
- Todo botão "?" usa o `GLOSSARIO` de `app/conteudo.py`. Todo gráfico tem
  "Como ler este gráfico" e "Ver os números em tabela" (macro `grafico` em
  `app/templates/_macros.html`).
- Gráfico largo tem versão estreita para o celular, e um teste de navegador
  falha se alguma letra de gráfico aparecer com menos de 12px.

## Fluxo de trabalho

- Uma branch por tarefa: `gabriel/classificador`, `matheus/isolamento`,
  `nicolas/painel-cards`.
- PR para `main` com a CI verde e revisão de pelo menos um dos outros dois.
- Cada PR diz qual item do plano ele fecha (ex.: "Gabriel, Fase 2, item 2.3").
- Mudou o comportamento de uma tela? Anexe print em 390px e 1280px no PR.
