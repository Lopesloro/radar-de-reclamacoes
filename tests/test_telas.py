"""As telas abrem, falam a língua do dono e respeitam a política de segurança."""

import re
from html.parser import HTMLParser

import pytest

from tests.conftest import TELAS_DO_DONO, TODAS_AS_TELAS

JARGAO = ("F1", "P10", "P90", "MAE", "macro", "régua", "p-valor", "q-valor", "hash", "CSRF",
          "recall", "hipótese nula", "intervalo de confiança")


class _TextoForaDoTecnico(HTMLParser):
    """Junta o texto visível, pulando <details class="tecnico">, <script> e <style>."""

    def __init__(self):
        super().__init__()
        self.pilha_tecnico = 0
        self.dentro_codigo = 0
        self.partes: list[str] = []

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class") or ""
        if tag == "details" and ("tecnico" in classes.split() or self.pilha_tecnico):
            self.pilha_tecnico += 1
        if tag in ("script", "style"):
            self.dentro_codigo += 1

    def handle_endtag(self, tag):
        if tag == "details" and self.pilha_tecnico:
            self.pilha_tecnico -= 1
        if tag in ("script", "style"):
            self.dentro_codigo -= 1

    def handle_data(self, data):
        if not self.pilha_tecnico and not self.dentro_codigo:
            self.partes.append(data)


def _texto_visivel(html: str) -> str:
    leitor = _TextoForaDoTecnico()
    leitor.feed(html)
    return " ".join(leitor.partes)


def _token_csrf(cliente):
    """Lê o token do formulário de entrada, como um navegador faria."""
    achado = re.search(r'name="csrf" value="([^"]+)"', cliente.get("/entrar").text)
    assert achado, "a tela de entrada precisa trazer o token contra CSRF"
    return achado.group(1)


@pytest.mark.parametrize("rota", TODAS_AS_TELAS)
def test_tela_abre(cliente, rota):
    assert cliente.get(rota).status_code == 200


@pytest.mark.parametrize("rota", TELAS_DO_DONO + ["/sobre"])
def test_tela_nao_tem_jargao_fora_dos_detalhes_tecnicos(cliente, rota):
    texto = _texto_visivel(cliente.get(rota).text)
    for termo in JARGAO:
        assert not re.search(rf"(?<!\w){re.escape(termo)}(?!\w)", texto, re.IGNORECASE), \
            f"'{termo}' aparece em {rota} fora de <details class=\"tecnico\">"


@pytest.mark.parametrize("rota", TODAS_AS_TELAS)
def test_tela_respeita_a_politica_de_seguranca(cliente, rota):
    """Sem script inline, sem style= e sem onclick=: a CSP do Matheus vai bloquear tudo isso."""
    html = cliente.get(rota).text
    assert not re.search(r"<script(?![^>]*\ssrc=)[^>]*>", html), "script inline"
    assert not re.search(r"\sstyle\s*=", html), "atributo style"
    assert not re.search(r"\son[a-z]+\s*=", html), "atributo de evento"


@pytest.mark.parametrize("rota", ["/resumo", "/comercio/bella-massa", "/previsao/bella-massa",
                                  "/investigacao/bella-massa/demora", "/simulador/bella-massa",
                                  "/confianca"])
def test_tela_tem_botao_de_ajuda(cliente, rota):
    html = cliente.get(rota).text
    assert 'class="ajuda"' in html
    assert 'aria-label="O que é' in html


@pytest.mark.parametrize("rota", ["/comercio/bella-massa", "/previsao/bella-massa",
                                  "/simulador/bella-massa", "/confianca"])
def test_todo_grafico_tem_como_ler_e_tabela(cliente, rota):
    html = cliente.get(rota).text
    graficos = html.count('<figure class="grafico"')
    assert graficos >= 1
    assert html.count("Como ler este gráfico") >= graficos
    assert html.count("Ver os números em tabela") >= graficos


@pytest.mark.parametrize("rota", ["/comercio/bella-massa", "/previsao/bella-massa", "/confianca"])
def test_grafico_largo_tem_versao_de_celular(cliente, rota):
    html = cliente.get(rota).text
    assert html.count("grafico__svg--largo") == html.count("grafico__svg--estreito")


@pytest.mark.parametrize("rota", [r for r in TELAS_DO_DONO if r not in ("/", "/entrar")])
def test_tela_interna_termina_com_proximo_passo(cliente, rota):
    assert 'aria-label="Próximo passo"' in cliente.get(rota).text


def test_pagina_publica_tem_uma_acao_so(cliente):
    html = cliente.get("/").text
    destinos = set(re.findall(r'<a [^>]*class="botao[^"]*"[^>]*href="([^"]+)"', html))
    destinos |= set(re.findall(r'<a [^>]*href="([^"]+)"[^>]*class="botao', html))
    assert destinos == {"/entrar"}


def test_pagina_publica_nao_mostra_nome_de_negocio(cliente):
    html = cliente.get("/").text
    for nome in ("Bella Massa", "Sorriso Claro", "Patinhas"):
        assert nome not in html


def test_sobre_registra_quem_construiu(cliente):
    html = cliente.get("/sobre").text
    for pessoa in ("Gabriel Lopes Londe Rodrigues", "Matheus Rocafa Moraes", "Nicolas Marques Linares"):
        assert pessoa in html


@pytest.mark.parametrize("rota", ["/comercio/nao-existe", "/previsao/nao-existe",
                                  "/investigacao/bella-massa/fofoca", "/experimentos/nao-existe",
                                  "/pagina-que-nao-existe"])
def test_endereco_errado_responde_404_com_saida(cliente, rota):
    """Empresa inexistente devolve 403, e não 404.

    Responder 404 só para quem não existe entregaria, pela diferença das
    respostas, quais empresas existem no sistema. A recusa é a mesma.
    """
    resposta = cliente.get(rota)
    assert resposta.status_code in (403, 404)
    if resposta.status_code == 404:
        assert 'href="/resumo"' in resposta.text


def test_assunto_invalido_na_previsao_volta_para_o_padrao(cliente):
    resposta = cliente.get("/previsao/bella-massa?categoria=fofoca")
    assert resposta.status_code == 200
    assert "fofoca" not in resposta.text


def test_simulador_aceita_a_mudanca_pelo_endereco(cliente):
    sem = cliente.get("/simulador/bella-massa?categoria=demora&t-4-noite=2&t-5-noite=2").text
    com = cliente.get("/simulador/bella-massa?categoria=demora&t-4-noite=4&t-5-noite=4").text
    assert "Essa mudança quase não mexe" in sem or "Mude a equipe" in sem
    assert "devem cair de" in com


def test_simulador_ignora_numero_invalido(cliente):
    resposta = cliente.get("/simulador/bella-massa?t-4-noite=abc&t-5-noite=999")
    assert resposta.status_code == 200


def test_saude_nao_fala_de_credencial(cliente):
    dados = cliente.get("/saude").json()
    assert dados == {"estado": "ok", "versao": dados["versao"]}


def test_endereco_do_css_muda_quando_o_arquivo_muda(cliente):
    from app.rotas._telas import paginas

    html = cliente.get("/").text
    impressao = paginas.env.globals["impressao"]
    assert f"app.css?v={impressao}" in html
    assert re.fullmatch(r"[0-9a-f]{12}", impressao)


def test_entrada_com_a_credencial_de_demonstracao_leva_ao_resumo(cliente):
    token = _token_csrf(cliente)
    resposta = cliente.post(
        "/entrar",
        data={"usuario": "bella", "senha": "admin", "csrf": token, "proximo": "/resumo"},
        follow_redirects=False,
    )
    assert resposta.headers["location"] == "/resumo"


def test_entrada_com_senha_errada_volta_com_aviso(cliente):
    token = _token_csrf(cliente)
    resposta = cliente.post(
        "/entrar",
        data={"usuario": "bella", "senha": "errada", "csrf": token, "proximo": "/resumo"},
        follow_redirects=False,
    )
    assert resposta.headers["location"] == "/entrar?erro=credencial"
    assert "Usuário ou senha não conferem." in cliente.get("/entrar?erro=credencial").text


def test_entrada_aceita_texto_com_acento_sem_quebrar(cliente):
    token = _token_csrf(cliente)
    resposta = cliente.post(
        "/entrar",
        data={"usuario": "joão", "senha": "ação", "csrf": token, "proximo": "/resumo"},
        follow_redirects=False,
    )
    assert resposta.headers["location"] == "/entrar?erro=credencial"


def test_pagina_publica_tem_o_titulo_do_print(cliente):
    html = cliente.get("/").text
    assert "Você sabe a sua nota. Não sabe o motivo dela." in html
    assert "Entrar no painel" in html
