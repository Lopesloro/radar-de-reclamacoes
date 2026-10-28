"""O fluxo de segurança do GitHub existe, roda sempre e guarda a saída como evidência."""

from pathlib import Path

import pytest
import yaml

CAMINHO = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "seguranca.yml"


@pytest.fixture(scope="module")
def fluxo():
    return yaml.safe_load(CAMINHO.read_text(encoding="utf-8"))


def _passos(fluxo):
    return [(nome, passo) for nome, tarefa in fluxo["jobs"].items() for passo in tarefa["steps"]]


def _texto(tarefa) -> str:
    return "\n".join(p.get("run", "") for p in tarefa["steps"])


def _comandos(fluxo, ferramenta: str) -> str:
    return "\n".join(p.get("run", "") for _, p in _passos(fluxo) if ferramenta in p.get("run", ""))


def test_roda_a_cada_push_e_a_cada_pull_request(fluxo):
    gatilhos = fluxo.get("on", fluxo.get(True))       # o PyYAML lê a palavra `on` como True
    assert "push" in gatilhos and "pull_request" in gatilhos
    assert not (gatilhos["push"] or {}).get("branches"), "push em qualquer branch, não só na main"


@pytest.mark.parametrize("ferramenta", ["bandit", "pip-audit", "gitleaks"])
def test_roda_cada_uma_das_tres_ferramentas(fluxo, ferramenta):
    assert _comandos(fluxo, ferramenta), f"{ferramenta} não é executado"


def test_cada_ferramenta_tem_a_sua_tarefa_para_uma_nao_esconder_a_outra(fluxo):
    assert len(fluxo["jobs"]) >= 3


def test_a_saida_de_cada_tarefa_vira_artefato_mesmo_quando_a_ferramenta_reprova(fluxo):
    for nome, tarefa in fluxo["jobs"].items():
        envios = [p for p in tarefa["steps"] if str(p.get("uses", "")).startswith("actions/upload-artifact@")]
        assert envios, f"{nome} não guarda evidência"
        assert all(str(p.get("if", "")).strip() == "always()" for p in envios), f"{nome}: sem if: always()"
        assert all(p["with"]["if-no-files-found"] == "error" for p in envios), f"{nome}: evidência vazia"


def test_o_gitleaks_le_o_historico_inteiro(fluxo):
    tarefa = next(t for t in fluxo["jobs"].values() if "gitleaks" in _texto(t))
    saida = next(p for p in tarefa["steps"] if str(p.get("uses", "")).startswith("actions/checkout@"))
    assert saida["with"]["fetch-depth"] == 0, "segredo apagado de um commit antigo continua vazado"


def test_o_gitleaks_baixado_tem_o_hash_conferido(fluxo):
    comandos = _comandos(fluxo, "gitleaks")
    assert "sha256sum" in comandos and "--check" in comandos
    assert "/releases/download/v" in comandos, "versão fixa, nunca `latest`"


def test_so_le_o_repositorio(fluxo):
    assert fluxo["permissions"] == {"contents": "read"}


def test_toda_acao_e_toda_ferramenta_tem_versao_fixa(fluxo):
    for _, passo in _passos(fluxo):
        if "uses" in passo:
            assert "@" in passo["uses"], passo["uses"]
    instalacao = _comandos(fluxo, "pip install")
    for pacote in ("bandit", "pip-audit"):
        assert f"{pacote}==" in instalacao


def test_falha_a_tarefa_quando_o_gitleaks_acha_segredo(fluxo):
    """`| tee` esconderia o código de saída se o shell não tivesse pipefail."""
    assert fluxo["defaults"]["run"]["shell"] == "bash"      # no GitHub, `bash` explícito liga o pipefail
    assert "|| true" not in _comandos(fluxo, "gitleaks")
