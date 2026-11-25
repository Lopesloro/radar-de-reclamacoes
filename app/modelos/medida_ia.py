"""O acerto da IA no conjunto de teste da equipe, medido uma vez e guardado.

Por que guardado e não medido na hora: são 500 frases, que viram 63 chamadas à
IA e mais de cinco minutos. Dentro de um pedido web a tela não carregaria. Então
a medida roda fora do site, por linha de comando, e o resultado vai para
`medida_ia.json`, com a data, o modelo e o tamanho da amostra. A tela "Dá para
confiar?" mostra esse arquivo quando a IA é quem está separando, e diz a data.

Rodar de novo (troca de modelo ou de instrução da IA):

    RADAR_IA_CHAVE=... python -m app.modelos.medida_ia

O número sai da comparação com o rótulo escrito pela equipe, pela mesma função
`classificador.medir` que mede o modelo local. A IA não calcula o número: ela só
responde o assunto de cada frase.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from app.contratos import AcuraciaClassificacao, LinhaAcerto

ARQUIVO = Path(__file__).with_name("medida_ia.json")


def ler() -> tuple[AcuraciaClassificacao, str, str] | None:
    """(medida, modelo, data) da última medição guardada, ou None se não houver."""
    if not ARQUIVO.exists():
        return None
    dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    medida = dict(dados["medida"])
    medida["linhas"] = tuple(LinhaAcerto(**linha) for linha in medida["linhas"])
    return AcuraciaClassificacao(**medida), dados["modelo"], dados["medida_em"]


def medir_e_gravar() -> AcuraciaClassificacao:
    from app.investigacao import ia
    from app.modelos import amostras, classificador
    from app.modelos.classificador_ia import ClassificadorIA

    cliente = ia.do_ambiente()
    if cliente is None:
        raise SystemExit("Sem RADAR_IA_CHAVE no ambiente: não há IA para medir.")
    _, teste = amostras.separar()
    # Sem reserva: onde a IA não responder, conta como erro, e não como acerto
    # do modelo local disfarçado de acerto da IA.
    medida = classificador.medir(ClassificadorIA(cliente), teste)
    ARQUIVO.write_text(json.dumps({
        "modelo": cliente.nome,
        "medida_em": date.today().isoformat(),
        "medida": asdict(medida),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return medida


if __name__ == "__main__":
    resultado = medir_e_gravar()
    print(f"acerto {resultado.acerto_geral}  F1 macro {resultado.f1_macro}  "
          f"(régua {resultado.f1_macro_regua})  em {resultado.amostra} frases")
