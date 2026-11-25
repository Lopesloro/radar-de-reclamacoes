"""A camada de dados real.

Entra em cena só quando `DATABASE_URL` existe. As tabelas são definidas num
script SQL único, `esquema.sql`, rodado na partida por `esquema.py`.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
