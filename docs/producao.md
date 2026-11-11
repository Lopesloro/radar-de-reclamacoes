# Pôr no ar e atender vinte clientes

## 1. O que precisa estar configurado

| Variável | Para quê | Sem ela |
|---|---|---|
| `DATABASE_URL` | o Postgres do serviço | nada é guardado e as telas dizem isso |
| `RADAR_CHAVE` | assina o cookie da sessão | sorteada a cada partida; as sessões caem a cada reinício |
| `RADAR_ADMIN_SENHA` | a conta do primeiro arranque | **ninguém entra** |
| `RADAR_COFRE_CHAVE` | cifra o token das fontes | o sistema recusa gravar token; a fonte de arquivo funciona |
| `RADAR_IA_CHAVE` | a IA que separa por assunto | o modelo próprio assume e nada quebra |
| `RADAR_GOOGLE_CLIENTE_ID` e `..._SEGREDO` | ligar o Perfil da Empresa | a fonte do Google não liga |
| `RADAR_ADMIN_USUARIO` | trocar o nome `admin` | fica `admin` |

As três primeiras são obrigatórias. O `render.yaml` gera `RADAR_CHAVE` e
`RADAR_COFRE_CHAVE` sozinho.

## 2. Ordem de subida

```bash
# 1. o banco, antes do serviço
alembic upgrade head

# 2. o serviço sobe e cria a conta de administrador se nenhuma existir
#    (idempotente: não sobrescreve conta que já exista)
uvicorn app.web:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'
```

O `--forwarded-allow-ips` existe porque o serviço só recebe tráfego pelo proxy do
Render. Ele faz o uvicorn confiar no `X-Forwarded-For`, e é por isso que o limite
de tentativas lê o **último** item desse cabeçalho, não o primeiro.

## 3. Pôr um cliente novo

Pela tela, sem tocar em código:

1. `/admin/clientes`, cadastrar. Cria a empresa, o primeiro negócio e a conta de
   entrada do dono de uma vez. **A senha aparece uma única vez** — copie ali.
2. `/admin/fontes`, ligar a fonte. Se Google e iFood ainda não estiverem
   liberados (ver `docs/fontes-de-avaliacao.md`), cole o CSV exportado do painel
   da plataforma no campo de importação.
3. A importação já classifica, conta por mês, estima e gera aviso. O número
   aparece na tela do cliente na mesma hora.
4. Marque no cadastro do cliente as duas marcas do combinado (autorização
   assinada, assuntos conferidos). Elas alimentam a tela "O que falta" do dono.

## 4. Vinte clientes no plano gratuito: onde aperta

| Recurso | Limite | O que acontece ao estourar | O que fazer |
|---|---|---|---|
| Memória (512 MB) | ~2 conferências de senha simultâneas | o serviço morre | o portão de `app/seguranca/rotas.py` já limita; não aumente o custo do Argon2 sem subir o plano |
| Postgres gratuito do Render | 1 GB | escrita falha | 20 clientes com 2 anos de avaliações dão algo na casa de 300 mil linhas; cabe, mas acompanhe |
| Conta gratuita da IA | poucas chamadas por minuto | a coleta fica lenta | o balde de 12/min já segura; coleta grande roda fora do horário |
| Instância gratuita | dorme sem acesso | primeira visita demora | o `healthCheckPath` reduz, não resolve; plano pago resolve |

**A coleta não roda sozinha ainda.** Hoje ela é disparada pela tela da equipe.
Para vinte clientes isso vira trabalho manual, e o próximo passo é um
`cron job` do Render chamando a coleta de cada fonte ligada uma vez por dia.
Está escrito aqui porque é a diferença entre "funciona" e "funciona sozinho".

## 5. O que ainda falta para ser produção de verdade

Em ordem de importância, com o motivo:

1. **Coleta agendada.** Sem ela, alguém tem de clicar todo dia.
2. **Sessão revogável no servidor.** Hoje sair apaga o cookie do navegador, mas
   uma cópia roubada valeria até o prazo de oito horas.
3. **Envio do aviso por e-mail.** O canal já é configurável na tela do cliente e
   o aviso aparece na tela; o envio em si não está ligado.
4. **Postgres no CI.** Os testes rodam em SQLite. Dois defeitos deste projeto só
   apareceriam no Postgres: o tamanho da coluna de senha e a ordem de inserção
   sem `relationship()`.
5. **Backup do banco.** O plano gratuito do Render não faz.
