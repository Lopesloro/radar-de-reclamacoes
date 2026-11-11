"""O token de acesso da fonte é cifrado em repouso, ou não é gravado.

A regra que estes testes defendem é a mais importante do arquivo: **sem chave de
cofre, o sistema recusa gravar**. Não grava em texto "por enquanto". Um token do
Google ou do iFood guardado em texto entrega a conta do cliente a qualquer cópia
do banco, e "depois a gente cifra" nunca acontece.
"""

import pytest

from app.seguranca import cofre

SEGREDO = "1//0gTokenDeMentiraParaTeste-abcdef"


@pytest.fixture
def com_chave(monkeypatch):
    monkeypatch.setenv(cofre.VARIAVEL_CHAVE, cofre.gerar_chave())


@pytest.fixture
def sem_chave(monkeypatch):
    monkeypatch.delenv(cofre.VARIAVEL_CHAVE, raising=False)


def test_sem_chave_o_sistema_recusa_gravar(sem_chave):
    assert cofre.disponivel() is False
    with pytest.raises(cofre.CofreFechado, match=cofre.VARIAVEL_CHAVE):
        cofre.cifrar(SEGREDO)


def test_valor_curto_demais_recusa(monkeypatch):
    """Qualquer texto longo serve como chave, mas texto curto não tem entropia."""
    monkeypatch.setenv(cofre.VARIAVEL_CHAVE, "curta")
    assert cofre.disponivel() is False
    with pytest.raises(cofre.CofreFechado, match="caracteres"):
        cofre.cifrar(SEGREDO)


def test_o_valor_que_o_render_gera_serve_como_chave(monkeypatch):
    """O `generateValue` do Render não produz chave no formato do Fernet.

    Exigir o formato exato faria a configuração parecer certa no painel e o
    primeiro token não gravar. O valor é derivado por SHA-256, então qualquer
    texto com entropia suficiente funciona.
    """
    monkeypatch.setenv(cofre.VARIAVEL_CHAVE, "A1b2C3d4E5f6G7h8I9j0KlMnOpQrStUvWx")
    assert cofre.disponivel() is True
    assert cofre.decifrar(cofre.cifrar(SEGREDO)) == SEGREDO


def test_ida_e_volta(com_chave):
    guardado = cofre.cifrar(SEGREDO)
    assert SEGREDO not in guardado
    assert SEGREDO.encode().hex() not in guardado
    assert cofre.decifrar(guardado) == SEGREDO


def test_duas_cifras_do_mesmo_segredo_sao_diferentes(com_chave):
    """Se fossem iguais, dava para contar quantas fontes usam o mesmo token."""
    assert cofre.cifrar(SEGREDO) != cofre.cifrar(SEGREDO)


def test_segredo_adulterado_no_banco_nao_abre(com_chave):
    """A cifra é autenticada: mexer no valor dá erro, não devolve lixo.

    Importa porque um segredo trocado por outro texto válido faria a coleta
    tentar entrar na conta errada."""
    guardado = cofre.cifrar(SEGREDO)
    mexido = guardado[:-6] + ("aaaaaa" if not guardado.endswith("aaaaaa") else "bbbbbb")
    assert cofre.decifrar(mexido) is None


def test_chave_trocada_nao_abre_o_que_foi_cifrado_com_a_antiga(monkeypatch):
    monkeypatch.setenv(cofre.VARIAVEL_CHAVE, cofre.gerar_chave())
    guardado = cofre.cifrar(SEGREDO)
    monkeypatch.setenv(cofre.VARIAVEL_CHAVE, cofre.gerar_chave())
    # Devolve None em vez de levantar: fonte que não abre é fonte com erro, e o
    # motor de coleta sabe marcar isso na tela.
    assert cofre.decifrar(guardado) is None


def test_decifrar_vazio_e_none_nao_derruba(com_chave):
    assert cofre.decifrar(None) is None
    assert cofre.decifrar("") is None
    assert cofre.decifrar("lixo") is None


def test_segredo_vazio_nao_vai_para_o_cofre(com_chave):
    with pytest.raises(ValueError):
        cofre.cifrar("")


def test_a_fonte_guarda_o_segredo_cifrado_e_nao_o_texto(com_chave, banco_de_teste):
    """A prova no banco: a coluna não contém o token."""
    import uuid

    from app.banco import modelo
    from app.banco import sessao as banco

    identificador = f"f-{uuid.uuid4().hex[:8]}"
    with banco.Sessao() as sessao:
        sessao.add(modelo.Fonte(
            id=identificador, empresa_id="bella-massa", comercio_id="bella-massa",
            plataforma="google", identificador_externo="accounts/1/locations/2",
            segredo_cifrado=cofre.cifrar(SEGREDO), estado="ligada",
        ))
        sessao.commit()
    with banco.Sessao() as sessao:
        guardado = sessao.scalar(
            modelo.Fonte.__table__.select().where(modelo.Fonte.id == identificador)
        )
        assert SEGREDO not in str(guardado)
        linha = sessao.get(modelo.Fonte, identificador)
        assert cofre.decifrar(linha.segredo_cifrado) == SEGREDO
        sessao.delete(linha)
        sessao.commit()
