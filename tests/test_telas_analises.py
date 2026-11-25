"""As telas "Por quê?", "E se?" e "Testes" no banco de verdade, com as duas contas.

A conta de demonstração é preenchida pelo gerador simulado, que passa pelo
mesmo motor das avaliações reais. A data é fixa: o gerador e as contas usam o
mesmo dia, e o teste dá o mesmo resultado em qualquer dia em que rodar.
"""

import re
from datetime import date

import pytest
from starlette.testclient import TestClient

from app import servicos
from app.banco import modelo
from app.banco import sessao as banco
from app.coleta import simulado
from app.web import app
from tests.conftest import SENHA, token_de
from tests.test_telas import JARGAO, _texto_visivel

HOJE = date(2026, 11, 26)
DEMO = "cantina-demo"


@pytest.fixture(scope="module")
def demonstracao(banco_de_teste):
    from app.seguranca import senha as _senha

    with pytest.MonkeyPatch.context() as remendo:
        remendo.setattr(servicos, "hoje", lambda: HOJE)
        with banco.Sessao() as sessao:
            sessao.add(modelo.Empresa(id=DEMO, nome="Cantina Demonstração", plano="demonstracao"))
            sessao.flush()
            sessao.add(modelo.Comercio(id=DEMO, empresa_id=DEMO, nome="Cantina Demonstração",
                                       ramo="Restaurante", cidade="Campinas, SP"))
            sessao.add(modelo.Usuario(id=f"u-{DEMO}", empresa_id=DEMO, email="demo", nome="Demo",
                                      papel="dono", senha_hash=_senha.gerar_hash(SENHA)))
            sessao.flush()
            simulado.preencher(sessao, DEMO, DEMO, hoje=HOJE)
            sessao.commit()
        with TestClient(app) as cliente:
            pagina = cliente.get("/entrar")
            token = re.search(r'name="csrf" value="([^"]+)"', pagina.text).group(1)
            cliente.post("/entrar", data={"usuario": "demo", "senha": SENHA, "csrf": token,
                                          "proximo": "/resumo"})
            yield cliente
    with banco.Sessao() as sessao:
        sessao.delete(sessao.get(modelo.Empresa, DEMO))
        sessao.commit()


def _plano_da_demo(cliente):
    return re.search(r'href="/experimentos/(tp-[0-9a-f]+)"', cliente.get("/experimentos").text).group(1)


TELAS_DA_DEMO = ["/investigacao", f"/investigacao/{DEMO}/demora", f"/investigacao/{DEMO}/preco",
                 "/simulador", f"/simulador/{DEMO}", f"/simulador/{DEMO}?t-4-noite=3&t-5-noite=3",
                 "/experimentos"]


@pytest.mark.parametrize("rota", TELAS_DA_DEMO)
def test_as_telas_da_demonstracao_abrem_avisam_e_falam_a_lingua_do_dono(demonstracao, rota):
    pagina = demonstracao.get(rota)
    assert pagina.status_code == 200
    assert "faixa-demonstracao" in pagina.text, "a conta simulada avisa em toda tela"
    texto = _texto_visivel(pagina.text)
    for termo in JARGAO:
        assert not re.search(rf"(?<!\w){re.escape(termo)}(?!\w)", texto, re.IGNORECASE), (termo, rota)
    assert not re.search(r"\sstyle\s*=", pagina.text) and not re.search(r"\son[a-z]+\s*=", pagina.text)


def test_o_teste_da_demonstracao_abre_e_diz_que_funcionou(demonstracao):
    pagina = demonstracao.get(f"/experimentos/{_plano_da_demo(demonstracao)}")
    assert pagina.status_code == 200
    assert 'veredito__rotulo">Funcionou<' in pagina.text
    assert "O plano foi alterado" not in pagina.text


def test_o_por_que_da_demonstracao_aponta_a_saida_do_garcom(demonstracao):
    pagina = demonstracao.get(f"/investigacao/{DEMO}/demora").text
    primeira = re.search(r'class="hipotese__frase">([^<]+)<', pagina).group(1)
    assert "Provável causa" in pagina
    assert "garçom" in primeira or "sexta a domingo" in primeira
    cardapio = re.search(r'etiqueta--(\w+)">[^<]+</span>(?:(?!etiqueta--).)*?cardápio de inverno',
                         pagina, re.S)
    assert cardapio and cardapio.group(1) != "provavel"


def test_mais_gente_a_noite_corta_a_demora_no_simulador(demonstracao):
    pagina = demonstracao.get(f"/simulador/{DEMO}?t-4-noite=3&t-5-noite=3&t-6-noite=3").text
    assert "devem cair de" in pagina


def test_conta_de_cliente_real_nao_mostra_a_faixa_de_demonstracao(cliente):
    assert "faixa-demonstracao" not in cliente.get("/investigacao").text


def test_dono_anota_no_diario_salva_turno_e_comeca_um_teste(cliente):
    token = token_de(cliente, "/investigacao/bella-massa/demora")
    r = cliente.post("/investigacao/bella-massa/diario", data={
        "data": "2026-06-02", "tipo": "equipe", "descricao": "Entrou um entregador novo",
        "categoria": "demora", "csrf": token})
    assert r.status_code == 200 and "Entrou um entregador novo" in r.text
    r = cliente.post("/simulador/bella-massa/turno", data={
        "dia_semana": "5", "periodo": "noite", "equipe": "2", "clientes": "90",
        "minutos_atendimento": "6", "custo_hora": "18", "csrf": token})
    assert r.status_code == 200 and "Turno salvo" in r.text and "Ver o que acontece" in r.text
    amanha = date.fromordinal(date.today().toordinal() + 1).isoformat()
    r = cliente.post("/experimentos", data={
        "comercio_id": "bella-massa", "categoria": "demora", "acao": "Entregador extra no sábado",
        "inicio": amanha, "dias": "28", "csrf": token})
    assert r.status_code == 200 and "Código do plano" in r.text and "Entregador extra no sábado" in r.text


def test_teste_que_comeca_no_passado_e_recusado(cliente):
    token = token_de(cliente, "/experimentos")
    r = cliente.post("/experimentos", data={
        "comercio_id": "bella-massa", "categoria": "demora", "acao": "Teste no passado",
        "inicio": "2020-01-01", "dias": "28", "csrf": token})
    assert "o sorteio vem antes dos dias" in r.text


def test_dono_nao_mexe_no_diario_nem_no_teste_de_outra_empresa(cliente, demonstracao):
    token = token_de(cliente, "/investigacao/bella-massa/demora")
    r = cliente.post(f"/investigacao/{DEMO}/diario", data={
        "data": "2026-06-02", "tipo": "equipe", "descricao": "invasão", "categoria": "demora",
        "csrf": token}, follow_redirects=False)
    assert r.status_code == 403
    assert cliente.get(f"/simulador/{DEMO}").status_code == 403
    assert cliente.get(f"/experimentos/{_plano_da_demo(demonstracao)}").status_code == 403


def test_formulario_sem_token_e_recusado(cliente):
    r = cliente.post("/investigacao/bella-massa/diario", data={
        "data": "2026-06-02", "tipo": "equipe", "descricao": "sem token"}, follow_redirects=False)
    assert r.status_code == 403


def test_dado_simulado_nao_entra_em_cliente_de_verdade(banco_de_teste):
    with banco.Sessao() as sessao, pytest.raises(ValueError, match="demonstração"):
        simulado.preencher(sessao, "patinhas", "patinhas", hoje=HOJE)
