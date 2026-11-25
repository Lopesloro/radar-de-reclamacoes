"""A área da equipe do Radar: cadastrar cliente, ligar fonte, rodar coleta, ler a trilha.

Ela é fechada em dois lugares, de propósito:

1. No middleware, pelo caminho: tudo sob `/admin` exige papel `admin` antes de a
   rota rodar. Tela nova aqui já nasce fechada mesmo se quem a escreveu esquecer
   a dependência.
2. Na rota, por `exigir_admin`, que é a trava que o teste de autorização lê.

Toda rota que muda algo grava na trilha de auditoria **na mesma transação** da
mudança (`app/auditoria.py`), e passa por conferência estrita do formulário
(`app/rotas/formularios.py`) antes de tocar no banco.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import func, select

from app import auditoria, conteudo
from app.banco import modelo
from app.banco import sessao as banco
from app.coleta import ErroDeFonte, arquivo, fontes, motor
from app.modelos import ativo
from app.rotas import formularios
from app.rotas._telas import tela
from app.seguranca import cofre, contas, exigir_admin, ficha
from app.seguranca import senha as _senha

rotas = APIRouter(prefix="/admin")

TAMANHO_DA_SENHA_NOVA = 12


def _sem_banco(request: Request):
    return tela(
        request, "admin/sem_banco.html", "admin",
        variavel="DATABASE_URL",
    )


def _voltar(destino: str, recado: str = "", erro: str = "") -> RedirectResponse:
    from urllib.parse import urlencode

    partes = {k: v for k, v in (("recado", recado), ("erro", erro)) if v}
    endereco = destino + ("?" + urlencode(partes) if partes else "")
    return RedirectResponse(endereco, status_code=303)


def _senha_nova() -> str:
    """Senha sorteada, mostrada uma vez na tela e nunca guardada em texto.

    Quem cadastra copia e entrega ao cliente. Não há "ver senha depois": se
    perder, gera outra. Guardar para mostrar depois significaria guardar em texto.
    """
    return secrets.token_urlsafe(TAMANHO_DA_SENHA_NOVA)[:TAMANHO_DA_SENHA_NOVA]


# ------------------------------------------------------------ painel

@rotas.get("")
def painel(request: Request, recado: str = "", erro: str = ""):
    exigir_admin(request)
    if not banco.usar_banco():
        return _sem_banco(request)
    with banco.Sessao() as sessao:
        clientes = sessao.scalar(select(func.count(modelo.Empresa.id)).where(
            modelo.Empresa.plano != "interno")) or 0
        negocios = sessao.scalar(select(func.count(modelo.Comercio.id))) or 0
        avaliacoes = sessao.scalar(select(func.count(modelo.Avaliacao.id))) or 0
        sem_assunto = sessao.scalar(select(func.count(modelo.Classificacao.id)).where(
            modelo.Classificacao.categoria_id.is_(None))) or 0
        avisos = sessao.scalar(select(func.count(modelo.Alerta.id)).where(
            modelo.Alerta.situacao == "aberto")) or 0
        com_erro = tuple(sessao.scalars(select(modelo.Fonte).where(
            modelo.Fonte.estado == "erro")).all())
        ultimas = tuple(sessao.scalars(
            select(modelo.ExecucaoColeta)
            .order_by(modelo.ExecucaoColeta.iniciada_em.desc()).limit(8)
        ).all())
        nunca_coletaram = tuple(sessao.scalars(
            select(modelo.Comercio).outerjoin(
                modelo.Avaliacao, modelo.Avaliacao.comercio_id == modelo.Comercio.id
            ).where(modelo.Avaliacao.id.is_(None))
        ).all())
        return tela(
            request, "admin/painel.html", "admin",
            recado=recado, erro=erro,
            clientes=clientes, negocios=negocios, avaliacoes=avaliacoes,
            sem_assunto=sem_assunto, avisos=avisos,
            fontes_com_erro=com_erro, ultimas=ultimas,
            nunca_coletaram=nunca_coletaram,
            modelo_no_ar=ativo.nome_do_modelo(),
            cofre_ligado=cofre.disponivel(),
        )


# ------------------------------------------------------------ clientes

@rotas.get("/clientes")
def clientes(request: Request, recado: str = "", erro: str = ""):
    exigir_admin(request)
    if not banco.usar_banco():
        return _sem_banco(request)
    with banco.Sessao() as sessao:
        linhas = []
        for empresa in sessao.scalars(
            select(modelo.Empresa).order_by(modelo.Empresa.criada_em.desc())
        ).all():
            linhas.append({
                "empresa": empresa,
                "negocios": sessao.scalar(select(func.count(modelo.Comercio.id)).where(
                    modelo.Comercio.empresa_id == empresa.id)) or 0,
                "usuarios": sessao.scalar(select(func.count(modelo.Usuario.id)).where(
                    modelo.Usuario.empresa_id == empresa.id,
                    modelo.Usuario.ativo.is_(True))) or 0,
                "avaliacoes": sessao.scalar(select(func.count(modelo.Avaliacao.id)).where(
                    modelo.Avaliacao.empresa_id == empresa.id)) or 0,
            })
        return tela(request, "admin/clientes.html", "admin-clientes",
                    linhas=linhas, recado=recado, erro=erro)


@rotas.post("/clientes")
def criar_cliente(request: Request, identificador: str = Form(""), nome: str = Form(""),
                  plano: str = Form("piloto"), negocio_nome: str = Form(""),
                  ramo: str = Form(""), cidade: str = Form(""), entrada: str = Form(""),
                  email_aviso: str = Form(""), cnpj: str = Form(""),
                  responsavel: str = Form(""), telefone: str = Form(""),
                  email_contato: str = Form(""), google_local: str = Form(""),
                  ifood_loja: str = Form(""), csrf: str = Form("")):
    usuario = exigir_admin(request)
    try:
        dados = formularios.NovoCliente(
            identificador=identificador, nome=nome, plano=plano, negocio_nome=negocio_nome,
            ramo=ramo, cidade=cidade, entrada=entrada, email_aviso=email_aviso,
        )
        dados_da_ficha = formularios.FichaDoCliente(
            cnpj=cnpj, responsavel=responsavel, telefone=telefone,
            email_contato=email_contato, google_local=google_local, ifood_loja=ifood_loja,
        ).model_dump()
    except ValidationError as erro:
        return _voltar("/admin/clientes", erro=erro.errors()[0]["msg"])
    try:
        # Cifra antes de abrir a transação: sem cofre, nada é criado.
        ficha_cifrada = ficha.cifrar(dados_da_ficha)
    except ficha.FichaSemCofre as erro:
        return _voltar("/admin/clientes", erro=str(erro))

    chave = _senha_nova()
    with banco.Sessao() as sessao:
        if sessao.get(modelo.Empresa, dados.identificador) is not None:
            return _voltar("/admin/clientes", erro="já existe cliente com esse identificador.")
        if sessao.scalar(select(modelo.Usuario).where(
                modelo.Usuario.email == dados.entrada)) is not None:
            return _voltar("/admin/clientes", erro="já existe conta com esse nome de entrada.")

        sessao.add(modelo.Empresa(
            id=dados.identificador, nome=dados.nome, plano=dados.plano,
            email_aviso=dados.email_aviso or None, ficha_cifrada=ficha_cifrada,
        ))
        sessao.flush()      # sem relationship(), quem aponta para a empresa precisa dela gravada
        sessao.add(modelo.Comercio(
            id=f"{dados.identificador}-1", empresa_id=dados.identificador,
            nome=dados.negocio_nome, ramo=dados.ramo, cidade=dados.cidade,
        ))
        sessao.flush()
        _registrar_fontes_futuras(sessao, dados.identificador, f"{dados.identificador}-1",
                                  dados_da_ficha)
        sessao.add(modelo.Usuario(
            id=f"u-{uuid.uuid4().hex[:16]}", empresa_id=dados.identificador,
            email=dados.entrada, nome=dados.nome, papel="dono",
            senha_hash=_senha.gerar_hash(chave),
        ))
        for categoria, rotulo in conteudo.NOMES_CATEGORIA.items():
            if sessao.get(modelo.Categoria, categoria) is None:
                sessao.add(modelo.Categoria(id=categoria, nome=rotulo, ordem=1))
        auditoria.registrar(
            sessao, empresa_id=dados.identificador, usuario_id=usuario.identificador,
            acao="empresa_criada", objeto=dados.identificador,
            # O que está na ficha não entra na trilha. Só o fato de haver uma.
            detalhe=f"plano {dados.plano}, entrada {dados.entrada}"
                    + (", com ficha cifrada" if ficha_cifrada else ""),
        )
        sessao.commit()
    # A senha vai na volta porque é a única vez que ela existe em texto.
    return _com_senha_nova(request, dados.identificador, "Cliente criado.",
                           dados.entrada, chave)


def _registrar_fontes_futuras(sessao, empresa_id: str, comercio_id: str,
                              dados_da_ficha: dict) -> None:
    """Google e iFood ficam registrados para o cliente, aguardando a autorização.

    O identificador na plataforma é dado do cliente e fica na ficha cifrada; a
    fonte guarda só a plataforma e o estado. A leitura automática não roda: ver
    app/coleta/fontes.py.
    """
    for plataforma, campo in (("google", "google_local"), ("ifood", "ifood_loja")):
        if not dados_da_ficha.get(campo):
            continue
        existente = sessao.scalar(select(modelo.Fonte).where(
            modelo.Fonte.comercio_id == comercio_id, modelo.Fonte.plataforma == plataforma))
        if existente is None:
            sessao.add(modelo.Fonte(
                id=f"f-{uuid.uuid4().hex[:16]}", empresa_id=empresa_id,
                comercio_id=comercio_id, plataforma=plataforma, identificador_externo="",
                estado="aguardando",
            ))


@rotas.post("/clientes/{empresa}/ficha")
def editar_ficha(request: Request, empresa: str, cnpj: str = Form(""),
                 responsavel: str = Form(""), telefone: str = Form(""),
                 email_contato: str = Form(""), google_local: str = Form(""),
                 ifood_loja: str = Form(""), csrf: str = Form("")):
    usuario = exigir_admin(request)
    destino = f"/admin/clientes/{empresa}"
    try:
        dados_da_ficha = formularios.FichaDoCliente(
            cnpj=cnpj, responsavel=responsavel, telefone=telefone,
            email_contato=email_contato, google_local=google_local, ifood_loja=ifood_loja,
        ).model_dump()
        ficha_cifrada = ficha.cifrar(dados_da_ficha)
    except ValidationError as erro:
        return _voltar(destino, erro=erro.errors()[0]["msg"])
    except ficha.FichaSemCofre as erro:
        return _voltar(destino, erro=str(erro))
    with banco.Sessao() as sessao:
        linha = sessao.get(modelo.Empresa, empresa)
        if linha is None:
            return _voltar("/admin/clientes", erro="esse cliente não existe.")
        linha.ficha_cifrada = ficha_cifrada
        primeiro = sessao.scalar(select(modelo.Comercio).where(
            modelo.Comercio.empresa_id == empresa).order_by(modelo.Comercio.criado_em))
        if primeiro is not None:
            _registrar_fontes_futuras(sessao, empresa, primeiro.id, dados_da_ficha)
        auditoria.registrar(sessao, empresa_id=empresa, usuario_id=usuario.identificador,
                            acao="ficha_alterada", objeto=empresa)
        sessao.commit()
    return _voltar(destino, recado="Ficha salva, cifrada.")


@rotas.get("/clientes/{empresa}")
def cliente(request: Request, empresa: str, recado: str = "", erro: str = ""):
    exigir_admin(request)
    return _tela_do_cliente(request, empresa, recado=recado, erro=erro)


def _com_senha_nova(request: Request, empresa: str, recado: str, entrada: str, chave: str):
    """A tela do cliente com a senha sorteada, na resposta do próprio POST.

    Nunca num redirecionamento: a senha iria no endereço (`?recado=`), e endereço
    fica no histórico do navegador e no log de acesso do servidor. `no-store`
    impede o navegador de guardar a página com a senha no cache.
    """
    resposta = _tela_do_cliente(request, empresa, recado=recado,
                                senha_nova={"entrada": entrada, "senha": chave})
    resposta.headers["cache-control"] = "no-store"
    return resposta


def _tela_do_cliente(request: Request, empresa: str, *, recado: str = "", erro: str = "",
                     senha_nova: dict | None = None):
    if not banco.usar_banco():
        return _sem_banco(request)
    with banco.Sessao() as sessao:
        linha = sessao.get(modelo.Empresa, empresa)
        if linha is None:
            return _voltar("/admin/clientes", erro="esse cliente não existe.")
        negocios = tuple(sessao.scalars(select(modelo.Comercio).where(
            modelo.Comercio.empresa_id == empresa).order_by(modelo.Comercio.nome)).all())
        usuarios = tuple(sessao.scalars(select(modelo.Usuario).where(
            modelo.Usuario.empresa_id == empresa).order_by(modelo.Usuario.email)).all())
        suas_fontes = tuple(sessao.scalars(select(modelo.Fonte).where(
            modelo.Fonte.empresa_id == empresa)).all())
        contagem = {
            n.id: sessao.scalar(select(func.count(modelo.Avaliacao.id)).where(
                modelo.Avaliacao.comercio_id == n.id)) or 0
            for n in negocios
        }
        return tela(
            request, "admin/cliente.html", "admin-clientes",
            empresa=linha, negocios=negocios, usuarios=usuarios, fontes=suas_fontes,
            contagem=contagem, plataformas=fontes.PLATAFORMAS,
            recado=recado, erro=erro, senha_nova=senha_nova,
            ficha=ficha.abrir(linha.ficha_cifrada), rotulos_da_ficha=ficha.ROTULOS,
            cofre_ligado=cofre.disponivel(),
        )


@rotas.post("/clientes/{empresa}/negocio")
def criar_negocio(request: Request, empresa: str, identificador: str = Form(""),
                  nome: str = Form(""), ramo: str = Form(""), cidade: str = Form(""),
                  csrf: str = Form("")):
    usuario = exigir_admin(request)
    destino = f"/admin/clientes/{empresa}"
    try:
        dados = formularios.NovoNegocio(
            identificador=identificador, nome=nome, ramo=ramo, cidade=cidade)
    except ValidationError as erro:
        return _voltar(destino, erro=erro.errors()[0]["msg"])
    with banco.Sessao() as sessao:
        if sessao.get(modelo.Empresa, empresa) is None:
            return _voltar("/admin/clientes", erro="esse cliente não existe.")
        if sessao.get(modelo.Comercio, dados.identificador) is not None:
            return _voltar(destino, erro="já existe negócio com esse identificador.")
        sessao.add(modelo.Comercio(
            id=dados.identificador, empresa_id=empresa, nome=dados.nome,
            ramo=dados.ramo, cidade=dados.cidade,
        ))
        auditoria.registrar(sessao, empresa_id=empresa, usuario_id=usuario.identificador,
                            acao="comercio_criado", objeto=dados.identificador)
        sessao.commit()
    return _voltar(destino, recado=f"Negócio {dados.nome} criado.")


@rotas.post("/clientes/{empresa}/usuario")
def criar_usuario(request: Request, empresa: str, entrada: str = Form(""),
                  nome: str = Form(""), csrf: str = Form("")):
    usuario = exigir_admin(request)
    destino = f"/admin/clientes/{empresa}"
    try:
        dados = formularios.NovoUsuario(entrada=entrada, nome=nome)
    except ValidationError as erro:
        return _voltar(destino, erro=erro.errors()[0]["msg"])
    chave = _senha_nova()
    with banco.Sessao() as sessao:
        if sessao.get(modelo.Empresa, empresa) is None:
            return _voltar("/admin/clientes", erro="esse cliente não existe.")
        if sessao.scalar(select(modelo.Usuario).where(
                modelo.Usuario.email == dados.entrada)) is not None:
            return _voltar(destino, erro="já existe conta com esse nome de entrada.")
        sessao.add(modelo.Usuario(
            id=f"u-{uuid.uuid4().hex[:16]}", empresa_id=empresa, email=dados.entrada,
            nome=dados.nome, papel="dono", senha_hash=_senha.gerar_hash(chave),
        ))
        auditoria.registrar(sessao, empresa_id=empresa, usuario_id=usuario.identificador,
                            acao="usuario_criado", objeto=dados.entrada)
        sessao.commit()
    return _com_senha_nova(request, empresa, "Conta criada.", dados.entrada, chave)


@rotas.post("/clientes/{empresa}/desligar")
def desligar_usuario(request: Request, empresa: str, usuario_id: str = Form(""),
                     csrf: str = Form("")):
    usuario = exigir_admin(request)
    destino = f"/admin/clientes/{empresa}"
    with banco.Sessao() as sessao:
        linha = sessao.get(modelo.Usuario, usuario_id)
        if linha is None or linha.empresa_id != empresa:
            return _voltar(destino, erro="essa conta não é desse cliente.")
        linha.ativo = False
        auditoria.registrar(sessao, empresa_id=empresa, usuario_id=usuario.identificador,
                            acao="usuario_desligado", objeto=linha.email)
        sessao.commit()
    return _voltar(destino, recado="Conta desligada. Ela não entra mais.")


@rotas.post("/clientes/{empresa}/combinado")
def marcar_combinado(request: Request, empresa: str, comercio_id: str = Form(""),
                     tem_termo: str = Form(""), categorias_combinadas: str = Form(""),
                     csrf: str = Form("")):
    """As marcas do combinado com o parceiro. É fato do contrato, não configuração de código."""
    usuario = exigir_admin(request)
    destino = f"/admin/clientes/{empresa}"
    with banco.Sessao() as sessao:
        negocio = sessao.get(modelo.Comercio, comercio_id)
        if negocio is None or negocio.empresa_id != empresa:
            return _voltar(destino, erro="esse negócio não é desse cliente.")
        negocio.tem_termo = tem_termo == "sim"
        negocio.categorias_combinadas = categorias_combinadas == "sim"
        auditoria.registrar(
            sessao, empresa_id=empresa, usuario_id=usuario.identificador, acao="combinado_atualizado",
            objeto=comercio_id,
            detalhe=f"combinado: termo={negocio.tem_termo} assuntos={negocio.categorias_combinadas}",
        )
        sessao.commit()
    return _voltar(destino, recado="Combinado atualizado.")


@rotas.post("/clientes/{empresa}/apagar")
def apagar_cliente(request: Request, empresa: str, confirmacao: str = Form(""),
                   csrf: str = Form("")):
    """Apaga a empresa e tudo que é dela. Não tem volta.

    Existe por dois motivos, e o segundo é o que obriga:

    1. Cliente que sai do piloto não pode continuar ocupando lugar na lista.
    2. A LGPD dá ao titular o direito de eliminação dos dados. Sem este botão, a
       resposta a um pedido de exclusão seria "abra o banco e apague à mão", o
       que não é resposta.

    Três cuidados:

    - **Confirmação escrita.** Quem apaga digita o identificador do cliente. Um
      botão de apagar ao lado de um botão de salvar, sem confirmação, é um
      acidente esperando a hora.
    - **A trilha fica.** A linha de auditoria é gravada na empresa da equipe, e
      não na que está sendo apagada: as linhas da empresa apagada vão com ela,
      por cascata, e o registro de que alguém apagou um cliente é justamente o
      que não pode desaparecer.
    - **A cascata é do banco.** Toda tabela de dado operacional aponta para
      `empresa` com ON DELETE CASCADE, então nada fica órfão. Apagar com uma
      lista de tabelas escrita à mão esqueceria a tabela que alguém criar amanhã.
    """
    usuario = exigir_admin(request)
    destino = f"/admin/clientes/{empresa}"
    if confirmacao.strip() != empresa:
        return _voltar(destino, erro=(
            "para apagar, escreva o identificador do cliente exatamente como ele é."
        ))
    with banco.Sessao() as sessao:
        linha = sessao.get(modelo.Empresa, empresa)
        if linha is None:
            return _voltar("/admin/clientes", erro="esse cliente não existe.")
        if empresa == contas.EMPRESA_DO_RADAR:
            return _voltar(destino, erro="a empresa da própria equipe não se apaga.")
        quantas = sessao.scalar(select(func.count(modelo.Avaliacao.id)).where(
            modelo.Avaliacao.empresa_id == empresa)) or 0
        nome = linha.nome
        auditoria.registrar(
            sessao, empresa_id=contas.EMPRESA_DO_RADAR, usuario_id=usuario.identificador,
            acao="empresa_apagada", objeto=empresa,
            detalhe=f"{nome}, com {quantas} avaliações",
        )
        sessao.delete(linha)
        sessao.commit()
    return _voltar("/admin/clientes",
                   recado=f"{nome} foi apagado, com as {quantas} avaliações dele.")


# ------------------------------------------------------------ fontes

@rotas.get("/fontes")
def listar_fontes(request: Request, recado: str = "", erro: str = ""):
    exigir_admin(request)
    if not banco.usar_banco():
        return _sem_banco(request)
    with banco.Sessao() as sessao:
        linhas = tuple(sessao.execute(
            select(modelo.Fonte, modelo.Comercio, modelo.Empresa)
            .join(modelo.Comercio, modelo.Comercio.id == modelo.Fonte.comercio_id)
            .join(modelo.Empresa, modelo.Empresa.id == modelo.Fonte.empresa_id)
            .order_by(modelo.Fonte.criada_em.desc())
        ).all())
        negocios = tuple(sessao.scalars(
            select(modelo.Comercio).order_by(modelo.Comercio.nome)).all())
        return tela(
            request, "admin/fontes.html", "admin-fontes",
            linhas=linhas, negocios=negocios, futuras=fontes.FUTURAS,
            sem_api=fontes.SEM_API,
            recado=recado, erro=erro,
        )


@rotas.post("/importar")
def importar(request: Request, comercio_id: str = Form(""), conteudo_do_arquivo: str = Form(""),
             csrf: str = Form("")):
    """Avaliações colados como CSV ou JSON. É o caminho que não depende de API liberada."""
    usuario = exigir_admin(request)
    try:
        dados = formularios.Importacao(comercio_id=comercio_id, conteudo=conteudo_do_arquivo)
    except ValidationError as erro:
        return _voltar("/admin/fontes", erro=erro.errors()[0]["msg"])
    try:
        lido = arquivo.ler(dados.conteudo)
    except ErroDeFonte as erro:
        return _voltar("/admin/fontes", erro=str(erro))

    with banco.Sessao() as sessao:
        negocio = sessao.get(modelo.Comercio, dados.comercio_id)
        if negocio is None:
            return _voltar("/admin/fontes", erro="esse negócio não existe.")
        resultado = motor.coletar(
            sessao, negocio.empresa_id, negocio.id, list(lido.avaliacoes),
            usuario_id=usuario.identificador,
        )
        sessao.commit()
    recado = resultado.em_uma_frase()
    if lido.recusadas:
        recado += f" {lido.recusadas} linhas do arquivo foram recusadas."
    return _voltar("/admin/fontes", recado=recado)


# ------------------------------------------------------------ coletas e trilha

@rotas.get("/coletas")
def coletas(request: Request):
    exigir_admin(request)
    if not banco.usar_banco():
        return _sem_banco(request)
    with banco.Sessao() as sessao:
        linhas = tuple(sessao.execute(
            select(modelo.ExecucaoColeta, modelo.Comercio)
            .join(modelo.Comercio, modelo.Comercio.id == modelo.ExecucaoColeta.comercio_id)
            .order_by(modelo.ExecucaoColeta.iniciada_em.desc()).limit(80)
        ).all())
        return tela(request, "admin/coletas.html", "admin-coletas", linhas=linhas)


@rotas.get("/auditoria")
def trilha(request: Request):
    exigir_admin(request)
    if not banco.usar_banco():
        return _sem_banco(request)
    with banco.Sessao() as sessao:
        return tela(request, "admin/auditoria.html", "admin-auditoria",
                    linhas=auditoria.ultimas(sessao, limite=150), acoes=auditoria.ACOES)


@rotas.get("/sistema")
def sistema(request: Request):
    """A ficha técnica do sistema. Fica aqui, e não na área do cliente: quem
    contrata quer saber se funciona, não com o que foi feito."""
    exigir_admin(request)
    from app.investigacao import ia as _ia
    from app.modelos import conferencia

    acerto = conferencia.acerto_da_separacao()
    return tela(
        request, "admin/sistema.html", "admin-sistema",
        autoria=conteudo.AUTORIA, tecnologias=conteudo.TECNOLOGIAS,
        projeto=conteudo.PROJETO,
        modelo_no_ar=ativo.nome_do_modelo(), ia_ligada=_ia.disponivel(),
        cofre_ligado=cofre.disponivel(), banco_ligado=banco.usar_banco(),
        acerto=acerto, origem_da_medida=conferencia.origem(),
        hoje=date.today(), agora=datetime.now(),
    )
