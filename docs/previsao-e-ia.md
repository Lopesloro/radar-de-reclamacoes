# A previsão e a IA: o que o sistema sabe, o que não sabe, e como foi medido

Frente do **Gabriel Lopes Londe Rodrigues**. Este documento existe para a
resposta a "dá para confiar?" não depender de ninguém lembrar.

A regra que organiza tudo: **todo número do sistema aparece ao lado do chute mais
simples que existe.** Se o sistema não ganha do chute, isso está escrito, na tela
e aqui.

---

## 1. Separar a avaliação por assunto

Cinco assuntos: atendimento, demora, preço, qualidade e ambiente.

### Dois modelos, e por que os dois existem

**A IA (Gemini).** É o que roda quando há chave configurada. Ela lê gíria, erro
de digitação e frase com dois assuntos como gente lê. Numa prova de oito
avaliações reais, acertou as seis que tinham assunto e se absteve nas duas que
não tinham.

**O modelo próprio (TF-IDF com regressão logística).** Treina num corpus de 90
frases rotuladas à mão pela equipe, variadas de forma determinística. Ele existe
por dois motivos: é a reserva quando a IA não responde (rede, limite da conta,
formato errado), e é a régua que mostra o que a IA acrescenta.

Medido no corpus da equipe, o modelo próprio dá **F1 macro de 0,419** contra
**0,067** da régua de responder sempre o assunto mais comum.

### A abstenção é resposta

Abaixo de 0,55 de confiança, o modelo próprio devolve "não sei" e a tela mostra
"sem assunto" com o motivo. Isso é melhor que chutar: o dono decide em cima
desse número.

**A abstenção conta como erro na medida.** Senão bastaria o modelo abster-se das
difíceis para o F1 subir, e o número ficaria bonito sem o modelo ter melhorado.

### Uma ressalva que vale dizer na banca

**A confiança que a IA declara não é probabilidade calibrada.** Nos testes ela
responde 1,0 em quase tudo, inclusive quando erra. Então a abstenção da IA não
vem de um limiar de confiança e sim da própria resposta "nenhum". O número que
diz se dá para confiar é o acerto medido no conjunto de conferência.

### O conjunto de conferência, e por que a tela diz qual foi usado

Em ordem de preferência:

1. **As avaliações que o dono conferiu à mão** na tela `/conferir`. É o rótulo
   que vale, porque é sobre o negócio dele. A partir de 30 conferências, a tela
   "Dá para confiar?" passa a medir aqui.
2. **O corpus da equipe**, enquanto não houver as 30.

A diferença é grande e a tela mostra qual foi usada: medir no corpus da equipe
mede um problema mais fácil que o real, porque as frases foram escritas por quem
conhece os cinco assuntos.

### Um erro que foi cometido e corrigido, e que vale contar

Numa versão anterior o F1 do classificador deu **1,0**. Era vazamento: a
separação entre treino e teste era por *variação* da frase, então quase a mesma
frase ficava dos dois lados. Com a separação por **frase base**, uma frase
inteira com todas as suas variações fica só de um lado, e o número caiu para o
que ele é de verdade. É a mesma armadilha de sortear o mês de teste na previsão.

---

## 2. Estimar o mês seguinte

### O resultado honesto, que muda o que a tela promete

Seis métodos foram medidos em seis formas de série (plana, subindo, descendo,
degrau, sazonal, com um pico), em 144 séries, por origem móvel: treina até o mês
k, prevê k+1, anda um mês e repete. Nunca com divisão aleatória dos meses —
sortear mês de teste deixa o modelo ver o futuro.

| Método | Erro médio (reclamações por mês) |
|---|---|
| Repetir o mês passado (a régua) | 2,65 |
| Média dos 2 últimos + tendência amortecida | 2,66 |
| Média dos 3 últimos | 2,83 |
| Seletor automático entre métodos | 2,62 |

**Nenhum método ganhou da régua de forma que importe.** Isso não é defeito do
código: numa contagem mensal pequena, o sobe-e-desce aleatório é maior que a
tendência, e nenhum método extrai sinal que não existe.

A conclusão certa não foi inventar um método mais complicado até o número ficar
bonito. Foi parar de prometer o que o número central não entrega e entregar o
que de fato ajuda o dono a decidir.

### O que o sistema acrescenta: a faixa

"Deve fechar entre 20 e 26" é informação que a régua não dá, e é o que separa
"subiu de verdade" de "subiu por acaso".

A largura sai dos erros que o próprio método cometeu um mês à frente no
histórico. **Um defeito real foi corrigido aqui:** a faixa prometia 80% e cobria
**0,73**. A conta supunha erro normal e o desvio era estimado de oito a doze
pontos, e desvio estimado de poucos pontos sai pequeno com mais frequência do
que grande. Com a correção da distribuição t de Student, a cobertura foi para
**0,82** nas 2.592 janelas. Prometer 80 e entregar 73 é promessa quebrada.

### O que o sistema acrescenta: o aviso

É aqui que ele ganha da régua de verdade. Medido nas mesmas 2.592 janelas,
contando como acerto o mês que de fato subiu duas reclamações ou mais:

| Aviso | Acerta | Pega das altas | Quantos avisos deu |
|---|---|---|---|
| "Vai piorar" (o mínimo esperado já passa do mês fechado) | 0,59 | 0,05 | 70 |
| "Fique de olho" (o mais provável sobe o bastante) | 0,43 | 0,25 | 472 |
| Régua de alarme: "o último mês subiu" | 0,22 | 0,30 | 1.133 |

Lido em voz alta: a régua grita 1.133 vezes e acerta uma em cinco. O "fique de
olho" fala 472 vezes e acerta duas em cinco, pegando quase a mesma proporção de
altas. É por isso que o aviso tem dois níveis e não um: **aviso que interrompe o
dono precisa estar certo.**

O limite dos dois níveis é o mesmo número usado na medição
(`CRESCIMENTO_QUE_IMPORTA`), importado e não copiado. Dois números diferentes
para a mesma pergunta fariam a tela avisar numa régua e o relatório medir em
outra.

### Outra correção que vale contar

A tendência passou a usar a **mediana das inclinações entre todos os pares** dos
últimos seis meses (Theil-Sen), amortecida. Antes era a diferença entre o
primeiro e o último mês da janela, e com isso **um único mês fora de série
deixava de ser ruído e virava tendência permanente**. Na série com um pico, o
erro caiu de 3,56 (régua) para 3,41.

### O que este módulo não faz, de propósito

**Não tem termo de mês do ano.** Na forma de série sazonal o método perde da
régua (3,44 contra 2,84), e isso está medido. Um termo sazonal honesto pede 24
meses de histórico para ser estimado e conferido; nenhum cliente tem isso hoje, e
estimá-lo com 12 meses seria ajustar ruído e piorar o resto. Entra quando houver
dado para medi-lo, com a mesma conferência por origem móvel.

**Não sai com menos de seis meses fechados.** Abaixo disso a tela diz quantos
meses faltam, em vez de mostrar uma estimativa que não se sustenta.

---

## 3. O que a IA faz e o que ela nunca faz

**Faz:** separa a avaliação por assunto, e escreve a frase de leitura da
estimativa ("o que isso quer dizer").

**Nunca faz: calcular número.** A estimativa, a faixa e o erro saem de
`app/modelos/previsao.py`, que é estatística conferida por origem móvel. Pedir
número a um modelo de linguagem é pedir um número plausível, não um número
medido, e a banca pergunta de onde veio o número.

A frase de leitura é escrita sobre números que já existem, e fica guardada em
memória por (negócio, assunto, mês): a mesma tela aberta vinte vezes faz uma
chamada, não vinte. Sem a IA, uma frase determinística entra no lugar e a tela
não muda de forma.

---

## 4. Como reproduzir cada número

```bash
# a régua do classificador e a da previsão, mais o estudo do aviso
pytest tests/test_modelos.py -v

# o estudo das 2.592 janelas em seis formas de série
pytest tests/test_modelos.py -k "aviso or oitenta or feio" -v

# o caminho inteiro da coleta, com idempotência e máscara
pytest tests/test_coleta.py -v
```

Os números que a tela mostra como referência estão em
`app/modelos/previsao.MEDIDA_DE_REFERENCIA`, no mesmo arquivo do código que os
produziu.
