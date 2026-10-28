# Radar de Reclamações · versão PI6

Projeto Integrador VI · Engenharia de Software · PUC-Campinas · 2026.2
Gabriel Lopes Londe Rodrigues, Matheus Rocafa Moraes e Nicolas Marques Linares.
Orientação da Profa. Sílvia C. de Matos Soares.

Repositório: <https://github.com/NicolasML28/PI-VI>.

O repositório guarda só código. O plano, a divisão do trabalho (um documento por
integrante) e os prints ficam fora do git, com a equipe. Se uma dessas pastas
existir na máquina (`plano/`, `referencia/`, `docs/`), leia antes de começar.

## Quem é dono do quê

| Área | Dono | Pastas |
|---|---|---|
| Banco, modelos, estatística, mundo simulado, simulador e experimento | Gabriel | `app/banco/`, `app/modelos/`, `app/mundo/`, `app/investigacao/` (menos `ia.py` e `protecao.py`), `app/decisao/`, `app/experimento/` (menos `selo.py`), `alembic/` |
| Entrada, contas, isolamento entre empresas, IA segura, LGPD, auditoria, CI de segurança | Matheus | `app/seguranca/`, `app/investigacao/ia.py`, `app/investigacao/protecao.py`, `app/experimento/selo.py`, `app/auditoria.py`, `.github/workflows/seguranca.yml` |
| Telas, textos, gráficos, rotas de página, testes de ponta a ponta, documentação acadêmica | Nicolas | `app/rotas/`, `app/templates/`, `app/static/`, `app/graficos/`, `app/conteudo.py`, `tests/e2e/`, `docs/` |
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
- **Dados de demonstração são avisados na tela.** Nenhuma avaliação fictícia se
  passa por real.
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
