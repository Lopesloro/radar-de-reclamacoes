"""A jornada da equipe no navegador: cadastrar cliente, importar e ver o número aparecer.

É o teste que prova que o sistema atende cliente novo sem ninguém mexer em
código. Cada clique é o que uma pessoa faria: cadastra, copia a senha que apareceu
uma única vez, cola o arquivo de avaliações, importa, e confere na tela da
equipe que a contagem subiu.
"""

from __future__ import annotations

import re
import uuid

import pytest

from tests.e2e.conftest import EQUIPE, LARGURAS

pytestmark = pytest.mark.e2e


def _avaliacoes_em_csv(quantas: int = 14) -> str:
    """Um arquivo como o que sai do painel de uma plataforma."""
    linhas = ["id;data;nota;comentario"]
    for n in range(1, quantas + 1):
        dia = 1 + n % 27
        linhas.append(f"n{n};{dia:02d}/10/2026;1;Esperei muito tempo para ser atendido")
    return "\n".join(linhas)


@pytest.mark.parametrize("largura", LARGURAS)
def test_a_equipe_cadastra_cliente_e_importa_avaliacoes(abrir, largura):
    pagina = abrir(largura, EQUIPE)
    identificador = f"e2e-{uuid.uuid4().hex[:6]}"

    pagina.ir("/admin")
    pagina.get_by_role("link", name="Cadastrar cliente").first.click()
    pagina.wait_for_url("**/admin/clientes")

    pagina.fill("input[name=identificador]", identificador)
    pagina.fill("input[name=nome]", "Cliente de Navegador")
    pagina.fill("input[name=negocio_nome]", "Loja do Centro")
    pagina.fill("input[name=ramo]", "Restaurante")
    pagina.fill("input[name=cidade]", "Campinas, SP")
    pagina.fill("input[name=entrada]", identificador)
    pagina.get_by_role("button", name="Cadastrar").click()
    pagina.wait_for_url(f"**/admin/clientes/{identificador}**")

    recado = pagina.locator(".aviso").first.inner_text()
    assert "Cliente criado" in recado
    # A senha aparece uma vez só: é o único momento em que ela existe em texto.
    assert re.search(r"senha \S{8,}", recado), recado
    assert "A senha aparece uma vez só" in pagina.locator(".aviso").first.inner_text()

    pagina.get_by_role("link", name="Fontes e coleta").click()
    pagina.wait_for_url("**/admin/fontes")
    pagina.select_option("form[action='/admin/importar'] select[name=comercio_id]",
                         f"{identificador}-1")
    pagina.fill("textarea[name=conteudo_do_arquivo]", _avaliacoes_em_csv())
    pagina.get_by_role("button", name="Importar e classificar").click()
    pagina.wait_for_url("**/admin/fontes**")
    recado = pagina.locator(".aviso").first.inner_text()
    assert "14 avaliações novas" in recado, recado

    # O número chegou na tela da equipe.
    pagina.ir(f"/admin/clientes/{identificador}")
    assert "14" in pagina.locator("table.tabela").first.inner_text()
    assert pagina.erros == []


def test_a_equipe_ve_a_trilha_da_propria_acao(abrir):
    pagina = abrir(1280, EQUIPE)
    pagina.ir("/admin/auditoria")
    texto = pagina.locator("table.tabela").inner_text()
    assert "empresa_criada" in texto or "coleta_rodada" in texto
    # A trilha nunca repete segredo.
    for proibido in ("$argon2id$", "segredo_cifrado"):
        assert proibido not in pagina.content()


def test_o_cliente_nao_ve_o_menu_da_equipe(abrir):
    """O menu muda com o papel: o dono não vê sequer o caminho da área da equipe."""
    pagina = abrir(1280)
    pagina.ir("/resumo")
    menu = pagina.locator("nav.menu").inner_text()
    assert "Clientes" not in menu and "Auditoria" not in menu
    assert "Configuração" in menu


def test_o_menu_da_equipe_abre_no_celular(abrir):
    """Defeito real já corrigido: somar tupla com lista estourava 500 aqui."""
    pagina = abrir(390, EQUIPE)
    pagina.ir("/admin")
    pagina.get_by_text("Menu", exact=True).click()
    painel = pagina.locator(".menu-movel__painel")
    assert painel.is_visible()
    painel.get_by_role("link", name="Auditoria").click()
    pagina.wait_for_url("**/admin/auditoria")
    assert pagina.erros == []
