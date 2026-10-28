"""Os dois modelos: separar a avaliação por assunto e estimar o mês seguinte.

`LIMITE_CONFIANCA` fica aqui, e não dentro do classificador, para o banco poder
ler o mesmo número sem carregar o scikit-learn junto.
"""

# Abaixo disto o modelo se abstém: prefere dizer "não sei" a chutar o assunto.
LIMITE_CONFIANCA = 0.55
