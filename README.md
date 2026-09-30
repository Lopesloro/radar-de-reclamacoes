# Radar de Reclamações

Lê o que os clientes de um comércio escreveram na internet, separa por assunto
— atendimento, demora, preço, qualidade, ambiente — e estima quantas
reclamações de cada assunto devem aparecer no mês seguinte.

Projeto Integrador VI · Engenharia de Software · PUC-Campinas · 2026.2
Gabriel Lopes Londe Rodrigues, Nicolas Marques Linares e Matheus Rocafa Moraes.
Orientação da Profa. Sílvia C. de Matos Soares.

## No ar

<https://radar-de-reclamacoes.onrender.com> — entra com **admin / admin**.

A senha é de demonstração e a tela de entrada avisa isso. Para usar com dado
real, defina no painel do Render:

| Variável | Para quê |
|---|---|
| `RADAR_USUARIO` e `RADAR_SENHA` | Substituem a credencial de demonstração |
| `RADAR_CHAVE` | Assina o cookie de sessão. Sem ela a chave muda a cada reinício, e quem estava logado cai quando o serviço acorda |

O plano é gratuito: depois de quinze minutos parado o serviço dorme, e o
primeiro acesso seguinte demora alguns segundos.

## Rodar na sua máquina

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
```

```bash
./.venv/bin/uvicorn app.web:app --reload --port 8000
```

Abre em <http://localhost:8000>. Para rodar os testes:

```bash
./.venv/bin/python -m pytest -q
```

## Telas

| Endereço | O que mostra |
|---|---|
| `/` | Página pública: o que o sistema faz, para quem e o que ele não pede |
| `/entrar` | Usuário e senha |
| `/painel` | Um resumo por negócio: o assunto mais reclamado e o que deve crescer |
| `/comercio/{id}` | Os assuntos do mês, a variação e as últimas avaliações lidas |
| `/previsao/{id}` | Histórico e estimativa do mês seguinte, com mínimo e máximo |
| `/alertas` | Avisos de alta, com confirmar e descartar |
| `/acuracia` | O quanto o sistema acerta, sempre ao lado do palpite simples |
| `/etapas` | O que já funciona, o que falta e onde a IA entra |
| `/saude` | Estado do serviço, em JSON |

## Como ele decide

São duas perguntas, e cada uma é comparada com um palpite bobo de propósito:

| Pergunta | O palpite bobo | Só entra na tela se |
|---|---|---|
| De que assunto fala esta avaliação? | responder sempre o assunto mais comum | acertar mais que ele |
| Quantas reclamações no mês que vem? | repetir o número do mês passado | errar menos que ele |

A estimativa começa no número do mês passado e só se afasta dele quando os seis
últimos meses mostram uma tendência forte o bastante para não ser oscilação
normal. Há teste que quebra a build se o sistema perder do palpite bobo.

## Segurança

Só defesa. Nada aqui ataca nada.

- Sessão assinada em cookie `HttpOnly`, `SameSite=Lax`, oito horas
- Senha guardada como hash `scrypt` e comparada em tempo constante
- Token contra CSRF em todo formulário
- Oito tentativas de entrada por origem a cada cinco minutos
- `Content-Security-Policy` sem `unsafe-inline`, HSTS, `X-Frame-Options`,
  `X-Content-Type-Options` e `Referrer-Policy` em toda resposta
- Depois do login, só redireciona para endereço interno

Onze testes cobrem isso, incluindo um que falha se a política de segurança
voltar a aceitar `unsafe-inline`.

## Dados

Os números das telas são **de demonstração**: negócios, avaliações e contagens
inventadas, geradas pelo próprio servidor e sempre iguais. Nenhuma avaliação
exibida foi escrita por um cliente real.

Quando a coleta real começar, a avaliação é pública mas o autor dela não entra
no projeto: nome, foto e qualquer tentativa de identificar quem escreveu ficam
de fora, e citação em relatório vai anonimizada.

## Pastas

```
app/
  web.py            os endereços do site
  conteudo.py       os textos fixos
  demo.py           os dados de demonstração e as contas dos dois modelos
  seguranca.py      senha, sessão, CSRF e cabeçalhos
  formatos.py       número e data no jeito brasileiro
  graficos/svg.py   os gráficos, desenhados no servidor
  templates/        uma tela por arquivo
  static/           CSS e JavaScript próprios
tests/              48 testes
```
