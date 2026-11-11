# De onde as avaliações vêm, e o que cada plataforma exige

Pergunta que sustenta este documento: **como o comerciante liga a conta dele para
o sistema puxar as avaliações sozinho?** A resposta curta é que depende da
plataforma, e que em duas das três o caminho automático existe mas está atrás de
uma aprovação que não está na mão da equipe. Por isso existe um terceiro caminho
que funciona no primeiro dia e não depende de ninguém.

A tabela abaixo é a que a área da equipe mostra em `/admin/fontes`, e o código
que ela descreve está em `app/coleta/`.

| Plataforma | Caminho automático | O que trava hoje | Código |
|---|---|---|---|
| Perfil da Empresa no Google | Sim, API v4 de avaliações | Aprovação manual do Google; a cota começa em zero | `app/coleta/google.py` |
| iFood | Sim, API de parceiro | Liberação do módulo de avaliações para o aplicativo | `app/coleta/ifood.py` |
| 99Food | Não há API pública | — | exportar do portal e enviar arquivo |
| Rappi | Não há documentação pública | — | mesmo caminho |
| Uber Eats | Saiu da operação de refeições no Brasil | — | não há integração a fazer |
| Reclame Aqui | Não há API aberta | — | mesmo caminho |
| Arquivo (CSV ou JSON) | Sim, imediato | Nada | `app/coleta/arquivo.py` |

---

## 1. Perfil da Empresa no Google

É a fonte que mais importa: é onde está a avaliação pública da maioria dos
negócios de rua.

### Como o dono liga a conta dele

1. Na tela de configuração, o dono clica em ligar o Google. Ele vai para a tela
   de consentimento do próprio Google, pedindo o escopo
   `https://www.googleapis.com/auth/business.manage`.
2. Quem autoriza é o dono, na conta Google dele. A autorização vale **só** para
   os perfis que essa conta administra; o sistema não consegue ler o perfil de
   um negócio que o dono não administra, nem com a autorização dele.
3. O Google volta com um código, que o sistema troca uma única vez por um
   *refresh token*. Esse token é cifrado (`app/seguranca/cofre.py`) e guardado.
   A cada coleta ele é trocado por um token de acesso de uma hora.

### O que trava, e é importante dizer antes de prometer prazo a um cliente

A API de avaliações do Google **não vem liberada**. Todo projeto no Google Cloud
começa com cota zero nessas chamadas, e a liberação é um pedido analisado à mão
pelo Google, com resposta por e-mail em cerca de duas semanas. Enquanto o pedido
não é aprovado, a chamada volta com 403 e a fonte fica em `pendente` na tela.

Três detalhes que mudam o planejamento:

- **Não existe ambiente de teste.** O Google não oferece sandbox para essa API,
  então todo teste de integração acontece contra perfil de verdade. É um motivo a
  mais para o módulo ter sido escrito com o cliente HTTP injetável: o teste roda
  contra um cliente de mentira.
- **O escopo pode exigir verificação do aplicativo** se ele for usado por conta
  de fora da organização, que é exatamente o caso de um cliente.
- **Pedir aumento de cota não resolve.** O formulário certo é o de solicitação de
  acesso básico; pedir aumento de cota quando a cota é zero cai numa fila que não
  libera nada.

### Detalhe técnico

`GET https://mybusiness.googleapis.com/v4/{parent}/reviews`, com `parent` na
forma `accounts/{conta}/locations/{local}` e no máximo 50 avaliações por página.
A nota vem escrita (`ONE` a `FIVE`), não como número. O campo
`reviewer.displayName` existe na resposta e **não** é lido: o nome de quem
escreveu não entra no sistema em campo nenhum.

Referência: `developers.google.com/my-business/reference/rest/v4/accounts.locations.reviews/list`

---

## 2. iFood

### Como o dono liga

No Portal do Parceiro ele autoriza o aplicativo do Radar, e o iFood entrega um
par `clientId`/`clientSecret` mais o `merchantId` da loja. O par vai cifrado no
cofre e é trocado por um token de acesso a cada coleta.

### O que trava

O módulo de avaliações precisa ser liberado para o aplicativo pela distribuição
do iFood. Sem a liberação, a chamada volta com erro de autorização.

### Três detalhes que mudaram o código

- **O período padrão da listagem é só os últimos 7 dias.** Para o histórico de
  seis meses que a estimativa precisa, a coleta pede mês a mês com `dateFrom` e
  `dateTo`, em fatias de 30 dias. Quem não notar isso vai achar que a loja tem
  poucas avaliações.
- **`pageSize` vai até 50** e a data tem de ser ISO 8601.
- **Token expirado volta 401**, e o certo é renovar e repetir o mesmo pedido, não
  desistir da coleta.

Referência: `developer.ifood.com.br/pt-BR/docs/guides/modules/review`

---

## 3. As plataformas sem API

**99Food.** O Portal do Estabelecimento Parceiro mostra as avaliações na tela e
cita uma "API" na lista de funções, sem documentação técnica pública. O caminho
que funciona é exportar do portal e enviar como arquivo. Vale registrar que a
99Food encerrou a operação própria de entrega e passou a operar como
marketplace, o que torna a integração menos interessante do que parecia.

**Rappi.** Sem documentação pública de avaliações de loja.

**Uber Eats.** Saiu da operação de refeições no Brasil, mantendo só entrega de
compras de mercado. Não há integração a fazer.

**Reclame Aqui.** Sem API aberta.

Para as quatro, o caminho é o mesmo: o dono exporta do painel dele e a equipe
envia o arquivo. É menos bonito e funciona hoje.

---

## 4. Arquivo enviado: o caminho que não depende de ninguém

É o que faz um cliente novo ver número na tela no mesmo dia, e é por isso que ele
não é um "quebra-galho": é a fonte padrão de um piloto.

O arquivo é CSV ou JSON, e os nomes das colunas aceitam variação, porque nenhum
painel exporta com o mesmo nome:

| Campo | Nomes aceitos | Obrigatório |
|---|---|---|
| identificador | `id_origem`, `id`, `review_id`, `identificador`, `codigo` | sim |
| data | `data`, `date`, `createTime`, `criada_em`, `created_at` | sim |
| nota | `estrelas`, `nota`, `rating`, `starRating`, `score`, `stars` | sim |
| texto | `texto`, `comment`, `comentario`, `review`, `descricao` | não |

A data é aceita em ISO, em `dd/mm/aaaa` e em mais quatro formatos. A nota é
aceita como número e como palavra (`FIVE`), que é o formato do Google. O
separador do CSV é descoberto sozinho, porque painel brasileiro usa `;` e
exportação em inglês usa `,`.

**Linha inválida não derruba o arquivo inteiro.** Ela é contada, o motivo é
descrito na tela, e as válidas entram. Um arquivo de 300 linhas com 2 erros de
data é um arquivo útil, e recusar tudo faria o operador editar CSV à mão sem
saber onde está o erro.

---

## 5. E a leitura por e-mail?

O Google manda um e-mail ao dono a cada avaliação nova. A ideia de ler essa caixa
foi considerada e **não** entrou, por três motivos:

1. **O formato do e-mail não é contrato.** Ele muda sem aviso, e quando mudar a
   coleta para de funcionar calada, que é o pior tipo de falha.
2. **O e-mail não traz o identificador da avaliação.** Sem ele, a mesma avaliação
   entra duas vezes quando o dono encaminha a mensagem de novo.
3. **Pedir acesso à caixa de e-mail do dono é pedir muito mais do que o
   necessário.** Na mesma caixa estão as notas fiscais, os contratos e a conversa
   com o contador dele. O sistema pede autorização para ler avaliação pública, e
   só.

O que o e-mail faz no sistema é o contrário: ele é **saída**, não entrada. O
canal de aviso da tela de configuração manda o aviso de "este assunto deve
crescer" para o e-mail que o dono escolher.

---

## 6. O que o sistema nunca guarda

Vale deixar escrito, porque é o que o termo que o parceiro assina promete:

- **O nome de quem escreveu a avaliação.** A avaliação entra com o identificador
  que a plataforma deu, nunca com o autor.
- **Telefone, e-mail, CPF, CNPJ, CEP, endereço de site e `@usuario`** que
  apareçam dentro do texto. Eles são apagados por `app/coleta/mascara.py`
  **antes** de o texto ir para o banco, e não na hora de mostrar na tela. O que
  não foi gravado não vaza depois em dump, backup nem log.
- **Nome de pessoa que venha depois de uma palavra de papel** ("o entregador
  João", "a atendente Maria", "a Dra. Ana"). Esse é o limite honesto da máscara:
  nome solto no meio da frase passa, porque não existe regra que ache todo nome
  próprio em português sem um dicionário de nomes, e um dicionário erraria no
  outro sentido, apagando palavra comum.
