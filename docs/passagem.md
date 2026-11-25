# Passagem: o estado do Radar em 25/11/2026

Leia isto primeiro se você (pessoa ou Claude) acabou de pegar o projeto. Diz o
que está no ar, onde cada coisa vive, como fazer as operações do dia a dia e
onde já tropeçamos. Nenhuma senha está aqui: elas ficam no painel do Render e
com a equipe.

## 1. O que está no ar

| Peça | Onde | Observação |
|---|---|---|
| Site | <https://radar-de-reclamacoes-pi6.onrender.com> | Render, plano grátis: dorme após 15 min sem visita, a primeira abertura leva até 1 min |
| Serviço | `radar-de-reclamacoes-pi6` (srv-db7dl55g1s2s73a4ouv0), workspace BlueFree | Deploy automático a cada push na `main` de `Lopesloro/radar-de-reclamacoes` |
| Blueprint | `render.yaml` (exs-dbpuh2jl550s73908dvg) | É a fonte da configuração do serviço |
| Banco | Postgres `radar-reclamacoes-db` (dpg-dc33s0s0916s73fk888g-a), Oregon, v16 | **Vence em 25/12/2026** (plano grátis, 30 dias). Ver seção 4 |
| IA | Gemini `gemini-flash-lite-latest` | Chave em `RADAR_IA_CHAVE` no Render |
| Repositórios | `NicolasML28/PI-VI` (fonte do time) e `Lopesloro/radar-de-reclamacoes` (espelho que o Render publica) | Árvores idênticas; os commits têm hashes diferentes |

Clientes cadastrados em produção (sem avaliações ainda):

| Cliente | Entrada do dono | Situação |
|---|---|---|
| Poco Loco Bar (`poco-loco-bar`) | `pocoloco` | Autorização assinada marcada; fonte do Google aguardando autorização |
| Bar do Alemão Campinas (`bar-do-alemao`) | `bardoalemao` | Sem autorização assinada; fonte do Google aguardando autorização |

As senhas desses donos foram mostradas uma única vez no cadastro e não ficam
guardadas no sistema. Perdeu? Em Clientes, desligue a conta e crie outra.

## 2. Variáveis do serviço (painel do Render → Environment)

| Variável | Para quê |
|---|---|
| `DATABASE_URL` | Ligada pelo Blueprint (`fromDatabase`), nunca colada à mão |
| `RADAR_ADMIN_SENHA` | Senha da conta `admin`, criada na partida se não existir |
| `RADAR_CHAVE` | Assina o cookie da sessão (gerada pelo Render) |
| `RADAR_COFRE_CHAVE` | Cifra a ficha do cliente (gerada pelo Render). Trocar torna ilegível o que já foi cifrado |
| `RADAR_IA_CHAVE` | Chave do Gemini. Sem ela, o modelo próprio separa sozinho |
| `PYTHON_VERSION` | 3.12.7 |

## 3. Como o sistema está montado (o que mudou na reta final)

- **Banco sem ferramenta de migração.** As tabelas estão num script só,
  `app/banco/esquema.sql`, rodado na partida por `app/banco/esquema.py` com uma
  trava do Postgres. Tudo é `CREATE TABLE IF NOT EXISTS`; coluna nova entra por
  `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. Mudou `app/banco/modelo.py`? Mude o
  script; `tests/test_banco.py` quebra se divergirem.
- **Testes só em PostgreSQL.** Nada de SQLite. `tests/postgres.py` cria e apaga
  bancos descartáveis no servidor apontado por `RADAR_TESTE_POSTGRES`. Sem a
  variável, a suíte para com erro (não pula).
- **Avaliações entram por arquivo.** CSV ou JSON colado em Fontes → "Importar e
  classificar". Google e iFood ficaram fora: dependem de autorização da
  plataforma. Cada cliente já tem as fontes registradas no estado `aguardando`.
- **Ficha do cliente cifrada.** CNPJ, responsável, telefone, e-mail, endereço no
  Google Maps e loja no iFood vão em `empresa.ficha_cifrada` (Fernet via
  `app/seguranca/ficha.py`). Sem `RADAR_COFRE_CHAVE`, o cadastro com ficha é recusado.
- **IA medida fora do site.** `python -m app.modelos.medida_ia` mede o Gemini nas
  500 frases de teste (63 chamadas) e grava `app/modelos/medida_ia.json`. A tela
  "Dá para confiar?" e a página Sistema mostram essa medida quando a IA está no ar.
- **Senha nova nunca no endereço.** A tela com a senha sorteada é a resposta do
  próprio POST, com `Cache-Control: no-store`.

## 4. Operações do dia a dia

**Rodar na máquina.** Precisa de Python 3.12 e PostgreSQL 16.

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
```

```bash
export RADAR_TESTE_POSTGRES=postgresql://SEU_USUARIO@127.0.0.1:5432/postgres
```

```bash
.venv/bin/python -m pytest -q
```

No macOS, se o Postgres local recusar subir por "socket path too long" ou
"postmaster became multithreaded", inicie com `LC_ALL=C` e um diretório de
socket curto: `LC_ALL=C pg_ctl -D <pasta> -o "-p 5432 -k /tmp/rpg" start`.

**Cadastrar cliente.** Área da equipe → Clientes. A senha do dono aparece uma vez.

**Importar avaliações.** Área da equipe → Fontes → escolher o arquivo (ou colar
o conteúdo) → Importar e classificar. Formato: `id;data;nota;comentario`, data
`dd/mm/aaaa`, nota de 1 a 5, sem o nome do autor. Envie em partes de até 90
linhas: a IA classifica até 96 avaliações com texto por envio (12 chamadas de 8,
o que a conta gratuita aceita em um minuto), acima disso entra o modelo próprio.
Reenviar a mesma parte não duplica (chave única por negócio e id). A estimativa
só aparece com 6 meses fechados.

**Montar o CSV do Google sem exportar à mão.** Ferramenta do Nicolas, fora do
site: `python -m ferramentas.serpapi_para_arquivo "Poco Loco Bar Campinas" --saida dados_reais/poco-loco.csv`.
Precisa de `SERPAPI_KEY` num `.env` (modelo em `.env.example`). Sai sem autor e
com a máscara de dados pessoais. Cada página gasta uma busca da cota; limite com
`--max-paginas`. Instruções no `README.md`.

**Conta de demonstração (dados simulados).** Área da equipe → Clientes →
cadastrar com o plano "demonstração" → na tela do cliente, "Preencher com dados
simulados" (só entra em negócio sem avaliações). Toda tela dessa conta mostra a
faixa "Conta de demonstração". Na banca: uma conta com a API (Poco Loco) e outra
simulada, para Por quê?, E se? e Testes terem volume.

**Por quê?, E se? e Testes.** Voltaram com motor de verdade. Por quê? testa as
mudanças anotadas no diário (tela do próprio Por quê?) e o fim de semana; E se?
precisa dos turnos cadastrados na própria tela; Testes sorteia os dias de um
plano novo, que começa hoje ou depois. Num negócio com pouca reclamação (o Poco
Loco tem 36 em nove anos), Por quê? diz que ainda não dá, em vez de inventar.

**Recriar o banco quando vencer.** O Render aceita 1 Postgres grátis por conta.
1. Apagar o banco velho no painel (Settings → Delete Database). A ferramenta MCP
   do Render não apaga banco. Não tem volta: exporte antes o que importar.
2. Criar outro com o **mesmo nome** `radar-reclamacoes-db`, Oregon, versão 16.
3. Blueprint → Manual sync → Approve na troca do `DATABASE_URL`.
4. O serviço reinicia, cria as tabelas e a conta `admin`. Clientes precisam ser
   cadastrados de novo.

**Ver o banco.** Ele não aceita conexão de fora (lista de IP vazia, de
propósito); nem o MCP do Render consulta. Olhe pelas telas da equipe.

## 5. Onde já tropeçamos

| Sintoma | Causa | O que fazer |
|---|---|---|
| `value too long for type character varying(20)` | `fonte.estado` tem 20 caracteres | Estados curtos (`aguardando`, não `aguardando_autorizacao`) |
| Teste verde, produção quebra no banco | Teste antigo rodava em SQLite | Por isso hoje é só Postgres |
| Admin cai em "Ainda não há negócio ligado" | `proximo=/resumo` padrão da tela de entrada | Corrigido: admin sempre vai para `/admin` |
| "cannot have more than one active free tier database" | Limite do Render | Apagar o antigo antes (seção 4) |
| Site leva 1 min para abrir | Plano grátis dormindo | Abrir 5 min antes de qualquer demonstração |
| "Bloqueado" ao entrar | 8 senhas erradas em 5 min por origem | Esperar 5 min; não demonstrar isso na banca |
| "Erro interno do servidor." ao importar (Poco Loco, 357 linhas, 98 com texto) | Provável (o log do Render não foi lido): o teto da IA era 120, acima das 96 que cabem em um minuto, e a 13ª chamada esperava o minuto virar dentro do pedido. O mesmo arquivo importa sem erro num Postgres local | Teto agora sai da conta (96). Envie em partes de até 90 linhas |

## 6. O que falta (em ordem)

1. Importar as avaliações do Poco Loco (autorização assinada) e do Bar do Alemão.
2. Plano pago do Postgres e backup, antes de dado real ficar mais de 30 dias.
3. Pedir acesso à API do Google Perfil da Empresa e a liberação do iFood.
4. Coleta diária automática (cron job do Render), envio do aviso por e-mail,
   sessão revogável no servidor. Detalhes em `docs/producao.md`, seção 6.

## 7. Material da banca

Em `docs/apresentacao/`: os slides (`Radar-de-Reclamacoes-banca.pdf`, fonte em
`deck.html` com as telas em `telas/`) e os PDFs de preparação, um por integrante,
com as perguntas prováveis por nível de importância e os erros que podem
acontecer na demonstração (fonte em `perguntas/gerar.py`).
