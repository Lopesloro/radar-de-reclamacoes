"""O cookie assinado, sem passar pelo site."""

from app.seguranca import sessao
from app.seguranca.sessao import VALIDADE_SEGUNDOS, Assinador, Sessao


def _sessao(**campos) -> Sessao:
    return Sessao(csrf="token", inicio=sessao._agora(), **campos)


def test_ida_e_volta_do_cookie():
    assinador = Assinador("chave")
    original = _sessao(usuario="bella", empresa_id="bella-massa")
    volta = assinador.abrir(assinador.assinar(original))
    assert (volta.csrf, volta.usuario, volta.empresa_id) == ("token", "bella", "bella-massa")


def test_sessao_anonima_tambem_faz_a_ida_e_volta():
    assinador = Assinador("chave")
    volta = assinador.abrir(assinador.assinar(_sessao()))
    assert volta.usuario is None and volta.empresa_id is None


def test_outra_chave_nao_abre():
    assert Assinador("outra").abrir(Assinador("chave").assinar(_sessao())) is None


def test_lixo_nao_abre_e_nao_quebra():
    assinador = Assinador("chave")
    for lixo in ("", "x", "a.b.c", "....", "e30.AAAA"):
        assert assinador.abrir(lixo) is None


def test_cookie_vencido_nao_abre(monkeypatch):
    assinador = Assinador("chave")
    cookie = assinador.assinar(_sessao(usuario="bella", empresa_id="bella-massa"))
    agora = sessao._agora()
    monkeypatch.setattr(sessao, "_agora", lambda: agora + VALIDADE_SEGUNDOS - 1)
    assert assinador.abrir(cookie) is not None
    monkeypatch.setattr(sessao, "_agora", lambda: agora + VALIDADE_SEGUNDOS + 1)
    assert assinador.abrir(cookie) is None


def test_conteudo_assinado_mas_torto_nao_abre():
    """Só nosso próprio defeito produziria isto, mas o site não pode confiar nem nisso."""
    assinador = Assinador("chave")
    agora = sessao._agora()
    tortos = [
        {}, [], "texto", {"c": "t", "i": agora, "u": "bella"},                   # usuário sem empresa
        {"c": "t", "i": agora, "e": "bella-massa"},                               # empresa sem usuário
        {"c": "", "i": agora}, {"c": 5, "i": agora}, {"c": "t", "i": "ontem"}, {"c": "t", "i": True},
        {"c": "t", "i": agora, "u": 1, "e": 2},
    ]
    for conteudo in tortos:
        assert assinador.abrir(assinador._serializador.dumps(conteudo)) is None, conteudo
