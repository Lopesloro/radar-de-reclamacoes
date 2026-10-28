"""A camada de dados real.

Entra em cena só quando `DATABASE_URL` existe. Sem ela, nada é aberto e o site
segue lendo `app/falsos.py`, como hoje — ver `app/banco/sessao.py`.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
