"""Ferramenta que monta o arquivo do Google pela SerpApi. Sem rede: as respostas são montadas aqui.

O teste mais importante é o último do arquivo gerado: ele precisa ser aceito pela
importação oficial (`app/coleta/arquivo.py`), senão a ferramenta não serve para nada.
"""

import pytest

from app.coleta import arquivo
from ferramentas import serpapi_para_arquivo as ferramenta


def _avaliacao(i, texto="Demorou muito", estrelas=2):
    return {"review_id": f"r{i}", "rating": estrelas, "iso_date": f"2026-10-{i:02d}T20:00:00Z",
            "snippet": texto, "user": {"name": "Fulano de Tal", "thumbnail": "https://foto"}}


@pytest.fixture
def pedidos(monkeypatch):
    """Simula a SerpApi: busca do lugar e duas páginas de avaliações (com uma repetida)."""
    feitos = []

    def falso(parametros):
        feitos.append(parametros)
        if parametros["engine"] == "google_maps":
            return {"place_results": {"data_id": "0xabc:0x123", "title": "Poco Loco Bar"}}
        if "next_page_token" not in parametros:
            return {"reviews": [_avaliacao(1), _avaliacao(2, texto=None, estrelas=5)],
                    "serpapi_pagination": {"next_page_token": "pagina2"}}
        return {"reviews": [_avaliacao(2), _avaliacao(3, texto="Me liga 19 99876-5432"),
                            {"review_id": "sem-data", "rating": 3}]}

    monkeypatch.setattr(ferramenta, "_pedir", falso)
    return feitos


def test_acha_o_lugar(pedidos):
    assert ferramenta.achar_lugar("Poco Loco Bar Campinas", "chave") == ("0xabc:0x123", "Poco Loco Bar")


def test_baixa_todas_as_paginas_sem_repetir_e_pula_avaliacao_quebrada(pedidos):
    avaliacoes = ferramenta.baixar_avaliacoes("0xabc:0x123", "chave")
    assert [a.id_origem for a in avaliacoes] == ["r1", "r2", "r3"]
    assert "num" not in pedidos[0] and pedidos[1]["num"] == 20


def test_arquivo_sai_sem_autor_e_com_a_mascara_do_sistema(pedidos, tmp_path):
    destino = tmp_path / "avaliacoes.csv"
    ferramenta.salvar_csv(ferramenta.baixar_avaliacoes("x", "chave"), destino)
    conteudo = destino.read_text(encoding="utf-8")
    assert "Fulano" not in conteudo and "foto" not in conteudo
    assert "99876-5432" not in conteudo and "[telefone]" in conteudo


def test_arquivo_gerado_e_aceito_pela_importacao_oficial(pedidos, tmp_path):
    destino = tmp_path / "avaliacoes.csv"
    ferramenta.salvar_csv(ferramenta.baixar_avaliacoes("x", "chave"), destino)
    lido = arquivo.ler(destino.read_text(encoding="utf-8"))
    assert lido.recusadas == 0
    assert [a.id_origem for a in lido.avaliacoes] == ["r1", "r2", "r3"]
    assert lido.avaliacoes[1].texto is None and lido.avaliacoes[1].estrelas == 5


def test_erro_vira_mensagem_clara(monkeypatch):
    monkeypatch.setattr(ferramenta, "_pedir", lambda p: {"place_results": {}})
    with pytest.raises(ferramenta.ErroSerpApi, match="Nenhum lugar"):
        ferramenta.achar_lugar("lugar que não existe", "chave")


def test_chave_vem_do_env_e_avisa_quando_falta(monkeypatch, tmp_path):
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    monkeypatch.setattr(ferramenta, "RAIZ", tmp_path)
    with pytest.raises(ferramenta.ErroSerpApi, match="SERPAPI_KEY"):
        ferramenta.ler_chave()
    (tmp_path / ".env").write_text('﻿SERPAPI_KEY="abc123"\n', encoding="utf-8")
    assert ferramenta.ler_chave() == "abc123"
