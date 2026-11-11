"""A área da equipe: fechada ao cliente, estrita no formulário e auditada.

Três perguntas, nesta ordem de importância:

1. **O cliente entra em `/admin`?** Não, e a recusa acontece no caminho, antes
   de a rota rodar. Vale para tela nova sem ninguém lembrar de protegê-la.
2. **O formulário aceita campo a mais?** Não. Um cadastro que aceitasse
   `papel=admin` criaria administrador pela tela de cliente.
3. **Toda mudança deixa rastro?** Sim, na mesma transação da mudança.
"""

import re

import pytest
from sqlalchemy import select

from app.banco import modelo
from app.banco import sessao as banco


def _token(sessao, caminho="/admin/clientes") -> str:
    achado = re.search(r'name="csrf" value="([^"]+)"', sessao.get(caminho).text)
    assert achado, f"a tela {caminho} precisa trazer o token contra CSRF"
    return achado.group(1)


# ------------------------------------------------------------ 1. a porta

@pytest.mark.parametrize("rota", [
    "/admin", "/admin/clientes", "/admin/clientes/patinhas", "/admin/fontes",
    "/admin/coletas", "/admin/auditoria", "/admin/sistema",
])
def test_o_cliente_nao_entra_na_area_da_equipe(cliente, rota):
    assert cliente.get(rota).status_code == 403


@pytest.mark.parametrize("rota", [
    "/admin", "/admin/clientes", "/admin/fontes", "/admin/coletas",
    "/admin/auditoria", "/admin/sistema",
])
def test_a_equipe_entra(equipe, rota):
    assert equipe.get(rota).status_code == 200


def test_quem_nao_entrou_vai_para_a_entrada(anonimo):
    resposta = anonimo.get("/admin")
    assert resposta.status_code == 303
    assert "/entrar" in resposta.headers["location"]


def test_o_cliente_nao_consegue_mudar_nada_na_area_da_equipe(cliente):
    """POST também é barrado, e antes de a rota rodar."""
    token = re.search(r'name="csrf" value="([^"]+)"',
                      cliente.get("/configuracao").text).group(1)
    resposta = cliente.post("/admin/clientes", data={
        "csrf": token, "identificador": "invadido", "nome": "Invadido",
        "negocio_nome": "x", "ramo": "y", "cidade": "z", "entrada": "invasor",
    }, follow_redirects=False)
    assert resposta.status_code == 403
    with banco.Sessao() as sessao:
        assert sessao.get(modelo.Empresa, "invadido") is None


# ------------------------------------------------------------ 2. o formulário

def test_cadastro_cria_empresa_negocio_e_conta_de_uma_vez(equipe):
    resposta = equipe.post("/admin/clientes", data={
        "csrf": _token(equipe), "identificador": "cantina-teste",
        "nome": "Cantina de Teste", "plano": "piloto",
        "negocio_nome": "Cantina do Centro", "ramo": "Restaurante",
        "cidade": "Campinas, SP", "entrada": "cantina-teste", "email_aviso": "",
    }, follow_redirects=False)
    assert resposta.status_code == 303
    with banco.Sessao() as sessao:
        empresa = sessao.get(modelo.Empresa, "cantina-teste")
        assert empresa is not None and empresa.plano == "piloto"
        assert sessao.get(modelo.Comercio, "cantina-teste-1") is not None
        conta = sessao.scalar(select(modelo.Usuario).where(
            modelo.Usuario.email == "cantina-teste"))
        assert conta is not None and conta.papel == "dono"
        # A senha existe só como hash, e é Argon2id.
        assert conta.senha_hash.startswith("$argon2id$")


def test_a_senha_sorteada_aparece_uma_vez_e_nao_e_guardada_em_texto(equipe):
    resposta = equipe.post("/admin/clientes", data={
        "csrf": _token(equipe), "identificador": "padaria-teste",
        "nome": "Padaria de Teste", "negocio_nome": "Padaria", "ramo": "Padaria",
        "cidade": "Campinas, SP", "entrada": "padaria-teste",
    }, follow_redirects=False)
    recado = resposta.headers["location"]
    achado = re.search(r"senha\+([A-Za-z0-9_%-]+)", recado)
    assert achado, f"a senha precisa voltar no recado: {recado}"
    sorteada = achado.group(1)
    with banco.Sessao() as sessao:
        conta = sessao.scalar(select(modelo.Usuario).where(
            modelo.Usuario.email == "padaria-teste"))
        assert sorteada not in (conta.senha_hash or "")


@pytest.mark.parametrize("mudanca,esperado", [
    ({"identificador": "Com Maiuscula"}, "minúscula"),
    ({"identificador": "a"}, "at least 3"),
    ({"plano": "gratis-para-sempre"}, "plano"),
    ({"email_aviso": "sem-arroba"}, "@"),
])
def test_formulario_recusa_dado_fora_da_regra(equipe, mudanca, esperado):
    dados = {
        "csrf": _token(equipe), "identificador": "recusado-teste", "nome": "Recusado",
        "negocio_nome": "Negócio", "ramo": "Teste", "cidade": "Campinas, SP",
        "entrada": "recusado-teste",
    }
    dados.update(mudanca)
    resposta = equipe.post("/admin/clientes", data=dados, follow_redirects=False)
    assert resposta.status_code == 303
    assert "erro=" in resposta.headers["location"]
    with banco.Sessao() as sessao:
        assert sessao.get(modelo.Empresa, "recusado-teste") is None


def test_identificador_repetido_e_recusado(equipe):
    dados = {
        "csrf": _token(equipe), "identificador": "bella-massa", "nome": "Outra",
        "negocio_nome": "Outra", "ramo": "Teste", "cidade": "Campinas, SP",
        "entrada": "outra-bella",
    }
    resposta = equipe.post("/admin/clientes", data=dados, follow_redirects=False)
    assert "erro=" in resposta.headers["location"]
    with banco.Sessao() as sessao:
        assert sessao.get(modelo.Empresa, "bella-massa").nome != "Outra"


# ------------------------------------------------------------ 3. o rastro

def test_cadastrar_cliente_deixa_rastro_na_auditoria(equipe):
    equipe.post("/admin/clientes", data={
        "csrf": _token(equipe), "identificador": "rastro-teste", "nome": "Rastro",
        "negocio_nome": "Rastro", "ramo": "Teste", "cidade": "Campinas, SP",
        "entrada": "rastro-teste",
    }, follow_redirects=False)
    with banco.Sessao() as sessao:
        linha = sessao.scalar(select(modelo.Auditoria).where(
            modelo.Auditoria.empresa_id == "rastro-teste",
            modelo.Auditoria.acao == "empresa_criada"))
    assert linha is not None
    assert linha.usuario_id == "admin"
    assert "piloto" in (linha.detalhe or "")


def test_a_trilha_nao_mostra_senha_nem_token(equipe):
    html = equipe.get("/admin/auditoria").text
    for proibido in ("senha_hash", "$argon2id$", "segredo_cifrado"):
        assert proibido not in html


def test_importar_arquivo_classifica_e_conta(equipe):
    """O caminho que funciona sem liberação de API nenhuma."""
    equipe.post("/admin/clientes", data={
        "csrf": _token(equipe), "identificador": "import-teste", "nome": "Import",
        "negocio_nome": "Import", "ramo": "Teste", "cidade": "Campinas, SP",
        "entrada": "import-teste",
    }, follow_redirects=False)
    conteudo = "id;data;nota;comentario\n" + "\n".join(
        f"i{n};0{1 + n % 9}/10/2026;1;Esperei muito tempo para ser atendido"
        for n in range(1, 13)
    )
    resposta = equipe.post("/admin/importar", data={
        "csrf": _token(equipe, "/admin/fontes"),
        "comercio_id": "import-teste-1", "conteudo_do_arquivo": conteudo,
    }, follow_redirects=False)
    assert resposta.status_code == 303
    assert "recado=" in resposta.headers["location"]
    with banco.Sessao() as sessao:
        quantas = sessao.query(modelo.Avaliacao).filter(
            modelo.Avaliacao.empresa_id == "import-teste").count()
    assert quantas == 12


def test_ligar_fonte_sem_chave_de_cofre_recusa_em_vez_de_gravar_em_texto(equipe, monkeypatch):
    from app.seguranca import cofre

    monkeypatch.delenv(cofre.VARIAVEL_CHAVE, raising=False)
    resposta = equipe.post("/admin/fontes", data={
        "csrf": _token(equipe, "/admin/fontes"), "comercio_id": "bella-massa",
        "plataforma": "google", "identificador_externo": "accounts/1/locations/2",
        "segredo": "token-que-nao-pode-ser-gravado",
    }, follow_redirects=False)
    assert "erro=" in resposta.headers["location"]
    with banco.Sessao() as sessao:
        fonte = sessao.scalar(select(modelo.Fonte).where(
            modelo.Fonte.comercio_id == "bella-massa",
            modelo.Fonte.plataforma == "google"))
    assert fonte is None or fonte.segredo_cifrado is None


def test_a_trilha_do_cliente_grava_o_identificador_e_nao_o_nome_de_entrada(cliente):
    """Defeito real: a coluna aponta para `usuario.id` por chave estrangeira.

    Gravar o nome de entrada ("bella") no lugar do identificador
    ("u-bella-massa") viola a chave e, porque a trilha é escrita na mesma
    transação da ação, desfaz a ação do cliente inteira. Para o administrador os
    dois valores coincidem, então nenhum teste de administração pegava isso; foi
    o teste de navegador que pegou, conferindo uma avaliação pela tela.
    """
    html = cliente.get("/conferir").text
    token = re.search(r'name="csrf" value="([^"]+)"', html).group(1)
    identificador = re.search(r'name="avaliacao_id" value="([^"]+)"', html).group(1)

    resposta = cliente.post("/conferir", data={
        "csrf": token, "avaliacao_id": identificador, "categoria": "demora",
    }, follow_redirects=False)
    assert resposta.status_code == 303
    assert "erro=" not in resposta.headers["location"], resposta.headers["location"]

    with banco.Sessao() as sessao:
        linha = sessao.scalar(select(modelo.Auditoria).where(
            modelo.Auditoria.empresa_id == "bella-massa",
            modelo.Auditoria.acao == "assunto_conferido",
        ).order_by(modelo.Auditoria.quando.desc()))
        assert linha is not None, "a conferência não deixou rastro"
        assert linha.usuario_id == "u-bella-massa"
        # E a conferência de fato ficou gravada.
        marcada = sessao.scalar(select(modelo.Classificacao).where(
            modelo.Classificacao.avaliacao_id == identificador,
            modelo.Classificacao.motivo_sem_assunto == "conferida pelo dono"))
        assert marcada is not None and marcada.categoria_id == "demora"


# ------------------------------------------------------------ apagar cliente

def test_apagar_cliente_leva_tudo_que_e_dele(equipe):
    """A cascata é do banco, então nada fica órfão quando a empresa sai."""
    equipe.post("/admin/clientes", data={
        "csrf": _token(equipe), "identificador": "apagar-teste", "nome": "Para Apagar",
        "negocio_nome": "Loja", "ramo": "Teste", "cidade": "Campinas, SP",
        "entrada": "apagar-teste",
    }, follow_redirects=False)
    conteudo = "id;data;nota;comentario\n" + "\n".join(
        f"a{n};0{1 + n % 9}/10/2026;1;Esperei muito tempo" for n in range(1, 6))
    equipe.post("/admin/importar", data={
        "csrf": _token(equipe, "/admin/fontes"),
        "comercio_id": "apagar-teste-1", "conteudo_do_arquivo": conteudo,
    }, follow_redirects=False)

    with banco.Sessao() as sessao:
        assert sessao.query(modelo.Avaliacao).filter(
            modelo.Avaliacao.empresa_id == "apagar-teste").count() == 5

    resposta = equipe.post("/admin/clientes/apagar-teste/apagar", data={
        "csrf": _token(equipe, "/admin/clientes/apagar-teste"), "confirmacao": "apagar-teste",
    }, follow_redirects=False)
    assert resposta.status_code == 303
    assert "recado=" in resposta.headers["location"]

    with banco.Sessao() as sessao:
        assert sessao.get(modelo.Empresa, "apagar-teste") is None
        for tabela in (modelo.Comercio, modelo.Usuario, modelo.Avaliacao,
                       modelo.Classificacao, modelo.SerieMensal, modelo.ExecucaoColeta):
            sobrou = sessao.query(tabela).filter(tabela.empresa_id == "apagar-teste").count()
            assert sobrou == 0, f"sobrou linha em {tabela.__tablename__}"
        # A trilha do apagamento fica, na empresa da equipe.
        linha = sessao.scalar(select(modelo.Auditoria).where(
            modelo.Auditoria.acao == "empresa_apagada",
            modelo.Auditoria.objeto == "apagar-teste"))
        assert linha is not None and linha.empresa_id == "radar"
        assert "5 avaliações" in (linha.detalhe or "")


def test_apagar_sem_escrever_o_identificador_nao_apaga(equipe):
    """Botão de apagar sem confirmação escrita é acidente esperando a hora."""
    resposta = equipe.post("/admin/clientes/patinhas/apagar", data={
        "csrf": _token(equipe, "/admin/clientes/patinhas"), "confirmacao": "patinha",
    }, follow_redirects=False)
    assert "erro=" in resposta.headers["location"]
    with banco.Sessao() as sessao:
        assert sessao.get(modelo.Empresa, "patinhas") is not None


def test_a_empresa_da_propria_equipe_nao_se_apaga(equipe):
    """Apagar a empresa da equipe apagaria a conta de administrador junto."""
    resposta = equipe.post("/admin/clientes/radar/apagar", data={
        "csrf": _token(equipe, "/admin/clientes/radar"), "confirmacao": "radar",
    }, follow_redirects=False)
    assert "erro=" in resposta.headers["location"]
    with banco.Sessao() as sessao:
        assert sessao.get(modelo.Empresa, "radar") is not None


def test_o_cliente_nao_apaga_ninguem(cliente):
    token = re.search(r'name="csrf" value="([^"]+)"',
                      cliente.get("/configuracao").text).group(1)
    resposta = cliente.post("/admin/clientes/patinhas/apagar", data={
        "csrf": token, "confirmacao": "patinhas",
    }, follow_redirects=False)
    assert resposta.status_code == 403
    with banco.Sessao() as sessao:
        assert sessao.get(modelo.Empresa, "patinhas") is not None
