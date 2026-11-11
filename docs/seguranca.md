# Segurança: o que foi pedido, onde está e o que prova

Frente do **Matheus Rocafa Moraes**. Cada linha da lista pedida aparece aqui com
três colunas: onde está no código, qual teste prova, e o que a decisão custou.
O recorte do projeto é **defesa**: nada aqui ataca nada.

| Item pedido | Onde está | O que prova |
|---|---|---|
| Isolamento por empresa, com teste que tenta ler dado de outra e exige 403 | `app/seguranca/isolamento.py` | `tests/seguranca/test_isolamento.py`, `test_vazamento_na_pagina.py` |
| Autenticação por sessão, senha com Argon2, cookie HttpOnly + Secure + SameSite | `app/seguranca/senha.py`, `sessao.py` | `test_senha_e_contas.py`, `test_sessao.py` |
| Token de acesso da plataforma cifrado em repouso, nunca em log nem no repo | `app/seguranca/cofre.py` | `test_cofre.py`, gitleaks |
| Rate limit nas rotas de ingestão, de LLM e de exportação | `app/seguranca/limite.py`, `app/investigacao/ia.py` | `test_limite_e_destino.py`, `test_ia_segura.py` |
| Cabeçalhos: CSP sem `unsafe-inline`, HSTS, nosniff, Referrer-Policy | `app/seguranca/cabecalhos.py` | `test_cabecalhos.py` |
| CSRF em todo formulário, entrada validada com Pydantic estrito | `app/seguranca/middleware.py`, `app/rotas/formularios.py` | `test_entrada.py`, `test_admin.py` |
| Trilha de auditoria: quem viu dado de qual empresa e quando | `app/auditoria.py` | `test_admin.py`, `test_coleta.py` |
| Defesa contra injeção de prompt | `app/investigacao/protecao.py` | `test_ia_segura.py` (32 testes) + evidência real |
| CI: bandit, pip-audit, gitleaks, testes de autorização | `.github/workflows/seguranca.yml` | `docs/evidencias/seguranca/` |

---

## 1. Isolamento por empresa

Três travas, da mais ampla para a mais estreita. A razão de serem três e não uma
é que cada uma falha de um jeito diferente.

**Trava 1, no roteador.** `vigiar_empresa` é dependência de **toda** rota, ligada
uma única vez em `instalar(app)`. Se o endereço, a consulta ou o formulário citam
um negócio que não é da empresa da sessão, a resposta é 403 antes de a rota
rodar. É o que faz uma tela nova nascer protegida sem ninguém lembrar.

**Trava 2, na rota.** `exigir_comercio` para a rota que descobre o negócio por
outro caminho.

**Trava 3, dentro da função.** A rota de conferência recebe `avaliacao_id`, um
nome que a trava 1 não conhece, e confere a empresa da avaliação por dentro. O
teste `test_avaliacao_de_outra_empresa_nao_pode_ser_conferida` existe para essa
terceira trava não ser removida por alguém que ache que a primeira já resolve.

**Negócio que não existe leva o mesmo 403 que negócio dos outros.** Com 404 de um
lado e 403 do outro, a diferença das respostas contaria quais negócios existem no
sistema.

**A prova vai além do código de status.** `test_vazamento_na_pagina.py` abre as
telas de índice e procura o nome da outra empresa no corpo do HTML. Houve um
vazamento real exatamente aí: a tela respondia 200 para a empresa certa e listava
o negócio das outras dentro da página.

**O administrador atravessa a trava 1 de propósito**, porque sem isso não há como
cadastrar cliente. Em troca, toda ação dele passa pela trilha de auditoria.

## 2. Senha e sessão

**Argon2id, com os parâmetros mínimos da OWASP** (m=19456 KiB, t=2, p=1). O custo
de memória **não** foi aumentado, e o motivo é medido: o serviço roda num plano de
512 MB, cada conferência reserva o `m` inteiro, e com os 64 MiB que a biblioteca
usa por padrão duas conferências simultâneas custariam 128 MiB. Uma rajada de
entradas derrubava o serviço — foi medido em 699 MiB de pico antes do portão de
duas conferências simultâneas de `app/seguranca/rotas.py`.

**O hash carrega os próprios parâmetros**, então subir o custo depois não
invalida senha já guardada. `precisa_regerar` avisa, e quem entra recebe um hash
novo na hora. O formato antigo (scrypt) continua conferindo e é trocado no
primeiro acerto: nenhum cliente precisa trocar de senha por causa da migração.

**Usuário que não existe paga o mesmo custo de hash** que um que existe. Sem
isso, o tempo de resposta entregaria quais contas existem.

**Nenhuma senha mora no código.** A do administrador vem de `RADAR_ADMIN_SENHA`;
sem a variável, **ninguém entra**. A senha de cliente é sorteada no cadastro e
aparece na tela uma única vez. Um teste varre `app/seguranca/*.py` procurando
atribuição de senha literal.

**O cookie** é `HttpOnly`, `SameSite=Lax` e `Secure` quando o acesso é https. A
validade de oito horas vai assinada dentro do cookie, então não dá para
estendê-la por fora. O papel (`dono` ou `admin`) também vai assinado: trocá-lo no
navegador quebra a assinatura e derruba a sessão.

**O que ainda não é verdade:** o cookie não é revogável no servidor. Sair apaga o
cookie do navegador, mas uma cópia guardada por quem a roubou valeria até o
prazo. Revogar de verdade pede sessão guardada no servidor, e isso está em
`docs/producao.md` como o próximo passo desta frente.

## 3. Token da plataforma cifrado em repouso

O token do Google ou do iFood é a chave da casa do cliente. Guardá-lo em texto
significa que qualquer cópia do banco entrega a conta dele.

A regra, com teste: **sem chave de cofre, o sistema recusa gravar.** Não grava em
texto "por enquanto". É o único jeito de a falta de configuração não virar
vazamento silencioso. A tela da equipe diz, em vermelho, que a chave não está
configurada e que Google e iFood não funcionam sem ela.

A cifra é Fernet, que é autenticada: um segredo adulterado no banco falha ao
abrir em vez de devolver lixo. Isso importa porque um segredo trocado por outro
texto válido faria a coleta tentar entrar na conta errada.

A chave do Fernet é derivada por SHA-256 do valor da variável de ambiente. O
motivo é prático: o `generateValue` do Render gera um texto aleatório que não
está no formato do Fernet, e exigir o formato exato faria a configuração parecer
certa no painel e o primeiro token não gravar.

## 4. Rate limit

| Onde | Limite | Por quê |
|---|---|---|
| Entrada (`/entrar`) | 8 tentativas por 300 s, por origem | força bruta de senha |
| Conferências de senha simultâneas | 2 | memória do plano de 512 MB |
| Chamadas de IA | 12 por minuto | limite da conta gratuita e custo |
| Formulário | 64 KiB | corpo gigante enchendo a memória |
| Importação de arquivo | 20 000 linhas, 900 KiB | mesma razão |
| Leitura do Google | 50 por página, 40 páginas por coleta | não varrer o dia inteiro numa chamada |

**A origem do pedido é o último item do `X-Forwarded-For`, não o primeiro.** Foi
um defeito real e reproduzível: o uvicorn roda com `--forwarded-allow-ips='*'` e
confia no primeiro item, que é exatamente o que o cliente manda. Quem errava a
senha trocava o cabeçalho e ganhava um balde de tentativas novo. O último item é
o que o proxy mais próximo escreveu, e esse o cliente não escolhe.

**IPv6 conta pelo bloco /64**, porque quem recebe um IPv6 recebe milhões de
endereços e trocaria de origem a cada tentativa.

## 5. Cabeçalhos

CSP sem `unsafe-inline` e sem `unsafe-eval`, HSTS de um ano com subdomínios,
`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` e
`Referrer-Policy: strict-origin-when-cross-origin`.

A CSP sem `unsafe-inline` custou trabalho e mudou o código das telas: nenhum
`<script>` embutido, nenhum atributo `style`, nenhum `onclick`. Há teste que
varre o HTML de toda tela procurando os três. E ela cobrou o preço num lugar
inesperado: um teste de navegador usava `wait_for_function`, que avalia texto
como script, e a própria política bloqueou. O teste foi reescrito para respeitar
a política, e não a política afrouxada para passar o teste.

## 6. CSRF e validação de entrada

O token vive dentro da sessão assinada e sai em todo formulário. O middleware
confere em todo método que altera algo, com comparação em tempo constante. Sem o
token, 403; na tela de entrada, uma volta com recado em português, porque ali a
causa mais comum é a página ter ficado aberta tempo demais.

A validação usa Pydantic no modo **estrito**: campo a mais é erro. O motivo é
concreto: um formulário que aceita campo desconhecido é a porta para alguém
mandar `papel=admin` num cadastro de cliente.

## 7. Trilha de auditoria

A linha é gravada **dentro da mesma transação** da ação. Um interceptador global,
que registrasse depois da resposta sair, teria dois defeitos: ação que falha no
meio deixaria registro de algo que não aconteceu, e ação que acontece com a
resposta quebrada não deixaria registro nenhum.

Essa decisão tem um custo que apareceu em produção simulada: um identificador de
usuário errado na linha de auditoria **desfaz a ação inteira**, por chave
estrangeira. Aconteceu, o teste de navegador pegou, e a correção foi gravar nulo
em vez de quebrar: perder o "quem" de uma linha de trilha é ruim, perder a ação
do cliente por causa disso é pior.

A trilha **nunca repete o conteúdo**: diz que alguém leu ou mudou algo de uma
empresa, não o que estava escrito. Senha, token de fonte e texto de avaliação não
aparecem nela, e há teste que confere isso no HTML da tela.

## 8. Injeção de prompt

A defesa está descrita em `app/investigacao/protecao.py` e tem três camadas:
envelope com etiqueta desarmada, resposta presa a um esquema fechado, e nenhuma
ação disparada pela saída do modelo.

A prova contra o modelo de verdade está em
`docs/evidencias/seguranca/injecao-de-prompt.md`: oito avaliações num lote, duas
com ordem plantada. As seis de verdade saíram certas, as duas plantadas foram
classificadas como "nenhum", e **não contaminaram as vizinhas do mesmo pedido**.

Os 32 testes de `tests/seguranca/test_ia_segura.py` cobrem as três camadas com um
cliente de mentira, sem sair da máquina.

## 9. CI e evidências

`.github/workflows/seguranca.yml` roda a cada push:

- **bandit** procura falha no código. A regra que reprova a build é gravidade
  alta. O relatório completo fica guardado como artefato.
- **pip-audit** procura vulnerabilidade conhecida nas bibliotecas.
- **gitleaks** procura segredo no código **e em todo o histórico do git**, porque
  segredo apagado num commit antigo continua vazado para quem clona.

As saídas da última execução local estão em `docs/evidencias/seguranca/`.

Duas coisas que essas ferramentas pegaram de verdade neste projeto, e não como
exercício:

1. **O pip-audit achou 13 falhas conhecidas na `cryptography` 46.0.3**, que havia
   acabado de ser adicionada para o cofre. Uma delas (PYSEC-2026-3552) só é
   corrigida a partir da 50.0.0. A versão subiu para 50.0.2.
2. **O bandit achou Trojan Source de gravidade alta** em
   `app/investigacao/protecao.py`: o código que apaga caractere invisível do
   texto do cliente estava escrito **com** caracteres invisíveis no fonte, porque
   os escapes viraram bytes reais na hora de escrever o arquivo. A regra de
   gravidade alta reprovaria a build. Os caracteres voltaram a ser escapes
   escritos no fonte.

## 10. LGPD

- **Minimização na origem.** Dado pessoal é apagado do texto **antes** do banco
  (`app/coleta/mascara.py`). O que não foi gravado não vaza depois.
- **O autor da avaliação nunca entra.** Nem nome, nem foto, nem identificador de
  perfil.
- **Base legal.** O parceiro assina autorização para a leitura das avaliações
  públicas do negócio dele, e essa marca é uma das sete etapas da tela "O que
  falta" — ela sai de um fato do banco, não de uma marcação à mão.
- **Rastreabilidade.** A trilha de auditoria responde quem acessou dado de qual
  empresa e quando.
- **O limite honesto da máscara** está escrito no próprio código e neste
  documento: nome solto no meio da frase passa.
