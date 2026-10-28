"""O site no navegador de verdade, no celular (390px) e no computador (1280px)."""

from __future__ import annotations

import os
import re

import pytest
from axe_playwright_python.sync_playwright import Axe

from tests.e2e.conftest import LARGURAS

pytestmark = pytest.mark.e2e

TELAS = [
    "/", "/entrar", "/resumo", "/comercio/bella-massa", "/previsao/bella-massa", "/avisos",
    # A sessão do teste é da Bella Massa. Tela de outra empresa devolve 403 de
    # propósito, e isso é verificado em tests/seguranca/test_isolamento.py.
    "/investigacao", "/investigacao/bella-massa/demora", "/investigacao/bella-massa/ambiente",
    "/simulador", "/simulador/bella-massa", "/experimentos", "/experimentos/exp-bella-entregador",
     "/confianca", "/o-que-falta", "/ajuda", "/sobre",
]

# Mede, em cada gráfico visível, o tamanho em que a letra aparece de fato na tela.
MENOR_LETRA_DOS_GRAFICOS = """() => {
  let menor = 99;
  for (const svg of document.querySelectorAll('svg')) {
    const caixa = svg.getBoundingClientRect();
    if (!caixa.width) continue;
    const vb = svg.viewBox && svg.viewBox.baseVal;
    const escala = vb && vb.width ? caixa.width / vb.width : 1;
    for (const texto of svg.querySelectorAll('text')) {
      menor = Math.min(menor, parseFloat(texto.getAttribute('font-size')) * escala);
    }
  }
  return menor;
}"""


def _nome_do_print(rota: str, largura: int) -> str:
    return (re.sub(r"[^a-z0-9-]+", "_", rota.strip("/")) or "inicio") + f"-{largura}.png"


@pytest.mark.parametrize("largura", LARGURAS)
@pytest.mark.parametrize("rota", TELAS)
def test_tela_abre_sem_erro_e_sem_rolagem_lateral(abrir, pasta_evidencias, rota, largura):
    pagina = abrir(largura)
    resposta = pagina.ir(rota)
    assert resposta.status == 200
    assert pagina.erros == []
    largura_da_pagina = pagina.evaluate("document.documentElement.scrollWidth")
    assert largura_da_pagina <= largura, f"{rota} rola para o lado em {largura}px"
    assert pagina.evaluate(MENOR_LETRA_DOS_GRAFICOS) >= 12, f"letra de gráfico menor que 12px em {rota}"
    pagina.screenshot(path=pasta_evidencias / _nome_do_print(rota, largura), full_page=True)


@pytest.mark.parametrize("largura", LARGURAS)
@pytest.mark.parametrize("rota", ["/resumo", "/comercio/bella-massa", "/investigacao/bella-massa/demora",
                                  "/simulador/bella-massa", "/confianca"])
def test_todo_botao_de_ajuda_abre_dentro_da_tela_e_fecha(abrir, rota, largura):
    pagina = abrir(largura)
    pagina.ir(rota)
    ajudas = pagina.locator("details.ajuda")
    assert ajudas.count() > 0
    for i in range(ajudas.count()):
        ajuda = ajudas.nth(i)
        botao = ajuda.locator("summary")
        if not botao.is_visible():
            continue
        botao.scroll_into_view_if_needed()
        botao.click()
        balao = ajuda.locator(".ajuda__balao")
        assert balao.is_visible()
        caixa = balao.bounding_box()
        assert caixa["x"] >= 0 and caixa["x"] + caixa["width"] <= largura, "balão vazou da tela"
        pagina.keyboard.press("Escape")
        assert not ajuda.evaluate("d => d.open")


@pytest.mark.parametrize("rota", TELAS)
def test_acessibilidade_sem_problema_grave(abrir, rota):
    pagina = abrir(390)
    pagina.ir(rota)
    resultado = Axe().run(pagina)
    graves = [v for v in resultado.response["violations"] if v["impact"] in ("serious", "critical")]
    assert not graves, resultado.generate_snapshot()


@pytest.mark.parametrize("rota", ["/", "/resumo", "/investigacao/bella-massa/demora",
                                  "/simulador/bella-massa", "/experimentos", "/ajuda"])
def test_botao_principal_se_alcanca_so_com_o_teclado(abrir, rota):
    pagina = abrir(1280)
    pagina.ir(rota)
    for _ in range(80):
        pagina.keyboard.press("Tab")
        if pagina.evaluate("document.activeElement && document.activeElement.hasAttribute('data-principal')"):
            return
    pytest.fail(f"o botão principal de {rota} não foi alcançado com Tab")


@pytest.mark.parametrize("largura", LARGURAS)
def test_tour_passa_pelos_cinco_passos(abrir, largura):
    pagina = abrir(largura)
    pagina.ir("/resumo")
    pagina.get_by_role("button", name="Primeira vez aqui? Faça o tour").click()
    for passo in range(1, 6):
        assert pagina.locator(".tour__passo").text_content() == f"Passo {passo} de 5"
        assert pagina.locator(".tour-destaque").count() == 1
        pagina.locator(".tour__seguir").click()
    assert pagina.locator(".tour").count() == 0
    assert pagina.get_by_role("button", name="Ver o tour de novo").is_visible()


@pytest.mark.parametrize("largura", LARGURAS)
def test_jornada_do_aviso_ate_o_teste(abrir, largura):
    """Resumo → Por quê? → E se? → Testar na prática → o teste."""
    pagina = abrir(largura)
    pagina.ir("/resumo")
    pagina.locator(".cartao--negocio").first.get_by_role("link", name="Por quê?").click()
    pagina.wait_for_url("**/investigacao/bella-massa/demora")
    assert pagina.get_by_text("Provável causa").first.is_visible()

    pagina.get_by_role("link", name="E se eu mudar algo?").click()
    pagina.wait_for_url("**/simulador/bella-massa?categoria=demora")
    pagina.fill("#t-4-noite", "4")
    pagina.fill("#t-5-noite", "4")
    pagina.get_by_role("button", name="Ver o que acontece").click()
    pagina.wait_for_url("**t-4-noite=4**")
    assert "devem cair de" in pagina.locator(".grafico__frase").first.inner_text()

    pagina.get_by_role("link", name="Testar na prática").click()
    pagina.wait_for_url("**/experimentos")
    pagina.get_by_role("link", name="Ver o teste").first.click()
    assert pagina.get_by_role("heading", name="Os dias sorteados").is_visible()
    assert pagina.erros == []


def test_menu_do_celular_abre_e_leva_a_ajuda(abrir):
    pagina = abrir(390)
    pagina.ir("/resumo")
    assert not pagina.locator("nav.menu").is_visible()
    pagina.get_by_text("Menu", exact=True).click()
    pagina.locator(".menu-movel__painel").get_by_role("link", name="Ajuda").click()
    pagina.wait_for_url("**/ajuda")


def test_sem_javascript_o_site_continua_funcionando(browser, endereco):
    contexto = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 900})
    pagina = contexto.new_page()
    # Entra pelo formulário, que funciona sem JavaScript. Sem isto a tela interna
    # devolve a página de entrada, e o teste mediria a tela errada.
    pagina.goto(endereco + "/entrar")
    pagina.fill('input[name="usuario"]', "bella")
    pagina.fill('input[name="senha"]', os.environ["RADAR_SENHA_DEMO"])
    pagina.click('form.formulario button[type="submit"]')
    pagina.goto(endereco + "/simulador/bella-massa?categoria=demora&t-4-noite=4")
    assert "devem cair de" in pagina.locator(".grafico__frase").first.inner_text()
    pagina.locator("details.ajuda summary").first.click()
    assert pagina.locator("details.ajuda .ajuda__balao").first.is_visible()
    contexto.close()


@pytest.mark.parametrize("largura", LARGURAS)
def test_entrada_da_demonstracao(abrir, largura):
    pagina = abrir(largura)
    pagina.ir("/")
    pagina.get_by_role("link", name="Entrar no painel").click()
    pagina.wait_for_url("**/entrar")
    pagina.fill("input[name=senha]", "errada")
    pagina.get_by_role("button", name="Entrar").click()
    assert pagina.get_by_role("alert").inner_text() == "Usuário ou senha não conferem."
    pagina.fill("input[name=senha]", "admin")
    pagina.get_by_role("button", name="Entrar").click()
    pagina.wait_for_url("**/resumo")


def test_topo_da_pagina_publica_fica_solido_ao_rolar(abrir):
    pagina = abrir(1280)
    pagina.ir("/")
    topo = pagina.locator("header.topo")
    assert "solido" not in (topo.get_attribute("class") or "")
    pagina.mouse.wheel(0, 600)
    # Nada de wait_for_function aqui: ele avalia texto como script, e a nossa CSP
    # não permite 'unsafe-eval'. O teste tem de respeitar a política do site.
    for _ in range(60):
        if "solido" in (topo.get_attribute("class") or ""):
            break
        pagina.wait_for_timeout(100)
    assert "solido" in (topo.get_attribute("class") or ""), "o topo não ficou sólido ao rolar"
