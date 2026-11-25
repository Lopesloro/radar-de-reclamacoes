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


@pytest.mark.parametrize("rota", TELAS_DO_DONO)
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
                                  "/configuracao", "/conferir",
                                  "/confianca"])
def test_tela_tem_botao_de_ajuda(cliente, rota):
    html = cliente.get(rota).text
    assert 'class="ajuda"' in html
    assert 'aria-label="O que é' in html


@pytest.mark.parametrize("rota", ["/comercio/bella-massa", "/previsao/bella-massa",
                                  "/confianca"])
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


def test_a_ficha_tecnica_nao_aparece_para_o_cliente(cliente):
    """Quem contrata não precisa saber quem escreveu o sistema, e o site é B2B.

    A ficha com os nomes da equipe mudou para `/admin/sistema`, que o
    middleware fecha para quem não é da equipe.
    """
    assert cliente.get("/admin/sistema").status_code == 403
    for rota in ("/resumo", "/confianca", "/ajuda", "/configuracao"):
        html = cliente.get(rota).text
        for pessoa in ("Gabriel", "Matheus", "Nicolas", "PUC"):
            assert pessoa not in html, f"{pessoa} aparece em {rota}"


def test_a_ficha_tecnica_aparece_para_a_equipe(equipe):
    html = equipe.get("/admin/sistema").text
    for pessoa in ("Gabriel Lopes Londe Rodrigues", "Matheus Rocafa Moraes",
                   "Nicolas Marques Linares"):
        assert pessoa in html


@pytest.mark.parametrize("rota", ["/comercio/nao-existe", "/previsao/nao-existe",
                                  "/admin/clientes", "/pagina-que-nao-existe"])
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


def test_a_estimativa_mostra_a_faixa_e_nao_so_o_numero(cliente):
    """O número do meio empata com a régua; o que o sistema acrescenta é a faixa.

    Se a tela deixar de mostrar o mínimo e o máximo, ela passa a prometer
    precisão que a medição não sustenta.
    """
    html = cliente.get("/previsao/bella-massa?categoria=demora").text
    assert "entre" in html
    assert "O que isso quer dizer" in html


def test_saude_nao_fala_de_credencial(cliente):
    dados = cliente.get("/saude").json()
    assert dados == {"estado": "ok", "versao": dados["versao"]}


def test_endereco_do_css_muda_quando_o_arquivo_muda(cliente):
    from app.rotas._telas import paginas

    html = cliente.get("/").text
    impressao = paginas.env.globals["impressao"]
    assert f"app.css?v={impressao}" in html
    assert re.fullmatch(r"[0-9a-f]{12}", impressao)


def test_entrada_do_dono_leva_a_tela_que_ele_pediu(cliente):
    from tests.conftest import SENHA

    token = _token_csrf(cliente)
    resposta = cliente.post(
        "/entrar",
        data={"usuario": "bella", "senha": SENHA, "csrf": token, "proximo": "/resumo"},
        follow_redirects=False,
    )
    assert resposta.headers["location"] == "/resumo"


def test_entrada_da_equipe_leva_para_a_area_da_equipe(anonimo):
    """Administrador não cai na tela de cliente: a área dele é outra."""
    import re

    from tests.conftest import SENHA

    token = re.search(r'name="csrf" value="([^"]+)"', anonimo.get("/entrar").text).group(1)
    resposta = anonimo.post("/entrar", data={"usuario": "admin", "senha": SENHA, "csrf": token})
    assert resposta.headers["location"] == "/admin"


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


def test_o_mes_corrente_estourado_aparece_na_tela(cliente, monkeypatch):
    """Defeito visto em produção: a tela dizia "variação normal" com o mês corrente
    já acima do máximo esperado para o mês inteiro.

    A estimativa fala do mês fechado, mas o dono abre a tela no dia 10. O que já
    chegou é informação, e o sistema a ignorava.
    """
    from datetime import date

    from app.contratos import PrevisaoMes, SerieMensal
    from app.graficos import frases

    def _serie(parcial, p10, p50, p90, fracao=0.5, ultimo=19):
        return SerieMensal(
            empresa_id="c", categoria="demora",
            meses=((date(2026, 9, 1), 16), (date(2026, 10, 1), ultimo)),
            parcial=(date(2026, 11, 1), parcial), parcial_fracao=fracao,
            previsoes=(PrevisaoMes(date(2026, 11, 1), p10, p50, p90),
                       PrevisaoMes(date(2026, 12, 1), p10, p50, p90)),
        )

    estourado = frases.leitura_da_faixa(_serie(parcial=22, p10=16, p50=19, p90=21))
    assert "já passou do esperado" in estourado
    assert "variação normal" not in estourado

    no_meio = frases.leitura_da_faixa(_serie(parcial=20, p10=16, p50=19, p90=21, fracao=0.4))
    # "40% do mês passado" lia como "o mês anterior". A frase diz dias.
    assert "40% dos dias deste mês" in no_meio
    assert "do mês passado" not in no_meio
    # Nada de extrapolar: o total projetado seria 50, um número que o sistema não
    # consegue defender, porque avaliação não chega em ritmo constante.
    assert "50" not in no_meio

    # No começo do mês a regra não vale: poucos dias não dizem nada sobre o mês.
    cedo = frases.leitura_da_faixa(_serie(parcial=19, p10=16, p50=19, p90=21, fracao=0.1))
    assert "dos dias deste mês" not in cedo

    tranquilo = frases.leitura_da_faixa(_serie(parcial=8, p10=16, p50=19, p90=21))
    assert "já passou do esperado" not in tranquilo
    assert "sobe-e-desce normal" in tranquilo


def test_a_frase_da_ia_nunca_contradiz_a_frase_propria(monkeypatch):
    """A conclusão é calculada uma vez e a IA só a reescreve.

    Na tela de produção as duas discordavam: a frase própria dizia "acima do
    esperado" e a IA dizia "ainda é normal", lado a lado. Duas conclusões opostas
    deixam o dono sem saber o que fazer, e isso é pior que nenhuma frase.
    """
    from datetime import date

    from app.contratos import PrevisaoMes, SerieMensal
    from app.graficos import frases
    from app.modelos import leitura

    serie = SerieMensal(
        empresa_id="c", categoria="demora",
        meses=((date(2026, 9, 1), 16), (date(2026, 10, 1), 19)),
        parcial=(date(2026, 11, 1), 26), parcial_fracao=0.33,
        previsoes=(PrevisaoMes(date(2026, 11, 1), 16, 19, 23),
                   PrevisaoMes(date(2026, 12, 1), 17, 21, 27)),
    )
    propria = frases.leitura_da_faixa(serie)
    assert "já passou do esperado" in propria
    # A pergunta que vai para a IA carrega essa mesma conclusão, palavra por palavra.
    assert propria in leitura._pergunta("Cantina do Centro", "demora", serie)


def test_a_pagina_publica_nunca_chama_cliente_de_demonstracao(cliente, monkeypatch):
    """Defeito real: a página contava todo negócio do banco como "de demonstração,
    com avaliações escritas pela nossa equipe". Com o primeiro cliente de verdade,
    a frase passaria a mentir sobre ele. Não existe mais dado de demonstração.
    """
    from app import servicos

    for quantos in (0, 1, 3):
        monkeypatch.setattr(servicos, "quantos_negocios", lambda q=quantos: q)
        pagina = cliente.get("/").text
        assert "demonstração" not in pagina
        assert "escritas pela nossa equipe" not in pagina
        assert "Peça um acesso" in pagina


def test_o_grafico_do_cartao_mostra_o_assunto_de_que_a_frase_fala(cliente):
    """Defeito real: com tudo normal, a frase dizia "a demora continua sendo o que
    mais aparece" e o gráfico logo abaixo mostrava "Ambiente nos últimos 6 meses".
    Quem lê junta as duas coisas e entende errado.
    """
    from app import servicos
    from app.graficos import frases

    negocio = servicos.comercios("bella-massa")[0]
    assunto = frases.assunto_do_cartao(negocio)
    if negocio.estado == "normal":
        assert assunto == negocio.mais_reclamado
    else:
        assert assunto == negocio.vai_crescer
    pagina = cliente.get("/resumo").text
    assert f"{frases.nome(assunto).capitalize()} nos últimos 6 meses" in pagina


@pytest.mark.parametrize("piorando, total, esperado", [
    (0, 1, "Nenhum assunto deve piorar em novembro."),
    (1, 1, "Um assunto deve piorar em novembro. Veja abaixo."),
    (0, 3, "Nenhum dos seus 3 negócios tem assunto que deve piorar em novembro."),
    (2, 3, "2 dos seus 3 negócios têm assunto que deve piorar em novembro."),
    (1, 3, "1 dos seus 3 negócios tem assunto que deve piorar em novembro."),
])
def test_a_frase_do_resumo_tem_concordancia(piorando, total, esperado):
    """Defeito real: "0 de 1 negócios têm um assunto que vai piorar"."""
    from datetime import date

    from app.graficos import frases

    assert frases.resumo(piorando, total, date(2026, 11, 1)) == esperado


def test_o_mini_grafico_escreve_o_numero_de_cada_mes():
    """Para quem não lê gráfico: a altura da coluna sozinha não diz quantas foram."""
    from datetime import date

    from app.graficos import svg

    pontos = [(date(2026, m, 1), v) for m, v in zip(range(5, 11), (7, 9, 4, 3, 6, 17), strict=True)]
    desenho = str(svg.mini_colunas(pontos, "teste"))
    for valor in (7, 9, 4, 3, 6, 17):
        assert f">{valor}</text>" in desenho


def test_o_grafico_da_estimativa_tem_legenda_a_vista(cliente):
    """Para leigo: cinza, faixa clara e coluna escura precisam de nome sem abrir nada.
    O "Como ler" fica dobrado e quase ninguém abre."""
    pagina = cliente.get("/previsao/bella-massa?categoria=demora").text
    assert 'class="legenda"' in pagina
    for texto in ("Já aconteceu", "Estimativa", "Mínimo e máximo esperados"):
        assert texto in pagina


def test_a_tela_de_confianca_fala_nome_de_gente_e_numero_com_virgula(cliente):
    """Defeitos reais: o gráfico dizia "bella-massa / ambiente" (o código interno)
    e o erro saía "1.2" com ponto, que em português se lê como mil e duzentos."""
    import re

    pagina = cliente.get("/confianca").text
    assert "bella-massa /" not in pagina
    assert "Pizzaria Bella Massa, " in pagina
    assert not re.search(r"<strong>\d+\.\d+</strong>", pagina)
    assert not re.search(r"empata com repetir o mês passado: \d+\.\d", pagina)


def test_a_ajuda_explica_o_que_existe_e_nao_o_que_nao_existe(cliente):
    """"Por quê?", "E se?" e "Testes" voltaram com motor de verdade, e a Ajuda
    explica as três. O que continua fora: o laboratório, e a IA "sugerindo causas"
    (as causas saem da estatística; a IA só separa por assunto)."""
    pagina = cliente.get("/ajuda").text
    for presente in ("E se?", "Teste na prática", "sorteio", "Diário do negócio"):
        assert presente in pagina, presente
    for sumido in ("Laboratório", "sugere ideias de possíveis causas"):
        assert sumido not in pagina, sumido
