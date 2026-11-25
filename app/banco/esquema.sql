-- Esquema do banco do Radar de Reclamações (PostgreSQL 16).
--
-- Este arquivo é a única definição das tabelas. O serviço roda este script
-- inteiro a cada partida (app/banco/esquema.py). Todo comando usa
-- IF NOT EXISTS ou ON CONFLICT DO NOTHING, então rodar de novo num banco que já
-- existe não muda nada nem apaga dado.
--
-- Regra que vale para todas as tabelas, menos empresa e categoria: cada linha
-- carrega empresa_id. Nenhuma consulta lê sem filtrar por ele, e é isso que
-- impede um cliente de ver o dado de outro.
--
-- Mudou uma tabela em app/banco/modelo.py? Mude aqui também. O teste
-- tests/test_banco.py::test_o_script_sql_cria_o_mesmo_esquema_do_modelo quebra
-- se os dois divergirem.

CREATE TABLE IF NOT EXISTS categoria (
	id VARCHAR(30) NOT NULL,
	nome VARCHAR(60) NOT NULL,
	ordem INTEGER NOT NULL,
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS empresa (
	id VARCHAR(60) NOT NULL,
	nome VARCHAR(160) NOT NULL,
	plano VARCHAR(30) NOT NULL,
	email_aviso VARCHAR(200),
	criada_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	ativa BOOLEAN NOT NULL,
	ficha_cifrada TEXT,
	PRIMARY KEY (id)
);

-- Coluna que chegou depois da primeira versão: num banco que já existia, o
-- CREATE TABLE acima não faz nada, e é este ALTER que a acrescenta.
ALTER TABLE empresa ADD COLUMN IF NOT EXISTS ficha_cifrada TEXT;

CREATE TABLE IF NOT EXISTS comercio (
	id VARCHAR(60) NOT NULL,
	empresa_id VARCHAR(60) NOT NULL,
	nome VARCHAR(160) NOT NULL,
	ramo VARCHAR(80) NOT NULL,
	cidade VARCHAR(120) NOT NULL,
	tem_termo BOOLEAN NOT NULL,
	tem_fonte BOOLEAN NOT NULL,
	categorias_combinadas BOOLEAN NOT NULL,
	tem_canal BOOLEAN NOT NULL,
	criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(empresa_id) REFERENCES empresa (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_comercio_empresa_id ON comercio (empresa_id);

CREATE TABLE IF NOT EXISTS usuario (
	id VARCHAR(60) NOT NULL,
	empresa_id VARCHAR(60) NOT NULL,
	email VARCHAR(200) NOT NULL,
	nome VARCHAR(160) NOT NULL,
	papel VARCHAR(30) NOT NULL,
	senha_hash VARCHAR(400),
	criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	ultimo_acesso TIMESTAMP WITHOUT TIME ZONE,
	ativo BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_usuario_email UNIQUE (email),
	FOREIGN KEY(empresa_id) REFERENCES empresa (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_usuario_empresa_id ON usuario (empresa_id);

CREATE TABLE IF NOT EXISTS versao_modelo (
	id VARCHAR(60) NOT NULL,
	empresa_id VARCHAR(60) NOT NULL,
	tipo VARCHAR(30) NOT NULL,
	nome VARCHAR(80) NOT NULL,
	treinada_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	metricas TEXT,
	ativa BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(empresa_id) REFERENCES empresa (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_versao_modelo_empresa_id ON versao_modelo (empresa_id);

CREATE TABLE IF NOT EXISTS auditoria (
	id SERIAL NOT NULL,
	empresa_id VARCHAR(60) NOT NULL,
	usuario_id VARCHAR(60),
	quando TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	acao VARCHAR(60) NOT NULL,
	objeto VARCHAR(120) NOT NULL,
	detalhe TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY(empresa_id) REFERENCES empresa (id) ON DELETE CASCADE,
	FOREIGN KEY(usuario_id) REFERENCES usuario (id)
);

CREATE INDEX IF NOT EXISTS ix_auditoria_empresa_id ON auditoria (empresa_id);

CREATE TABLE IF NOT EXISTS execucao_coleta (
	id VARCHAR(60) NOT NULL,
	empresa_id VARCHAR(60) NOT NULL,
	comercio_id VARCHAR(60) NOT NULL,
	iniciada_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	terminada_em TIMESTAMP WITHOUT TIME ZONE,
	lidas INTEGER NOT NULL,
	novas INTEGER NOT NULL,
	estado VARCHAR(20) NOT NULL,
	erro TEXT,
	PRIMARY KEY (id),
	FOREIGN KEY(empresa_id) REFERENCES empresa (id) ON DELETE CASCADE,
	FOREIGN KEY(comercio_id) REFERENCES comercio (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_execucao_coleta_comercio_id ON execucao_coleta (comercio_id);
CREATE INDEX IF NOT EXISTS ix_execucao_coleta_empresa_id ON execucao_coleta (empresa_id);

CREATE TABLE IF NOT EXISTS fonte (
	id VARCHAR(60) NOT NULL,
	empresa_id VARCHAR(60) NOT NULL,
	comercio_id VARCHAR(60) NOT NULL,
	plataforma VARCHAR(30) NOT NULL,
	identificador_externo VARCHAR(200) NOT NULL,
	segredo_cifrado TEXT,
	estado VARCHAR(20) NOT NULL,
	erro TEXT,
	ultima_coleta TIMESTAMP WITHOUT TIME ZONE,
	criada_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_fonte_comercio_plataforma UNIQUE (comercio_id, plataforma),
	FOREIGN KEY(empresa_id) REFERENCES empresa (id) ON DELETE CASCADE,
	FOREIGN KEY(comercio_id) REFERENCES comercio (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_fonte_comercio_id ON fonte (comercio_id);
CREATE INDEX IF NOT EXISTS ix_fonte_empresa_id ON fonte (empresa_id);

CREATE TABLE IF NOT EXISTS previsao (
	id VARCHAR(80) NOT NULL,
	empresa_id VARCHAR(60) NOT NULL,
	comercio_id VARCHAR(60) NOT NULL,
	categoria_id VARCHAR(30) NOT NULL,
	mes DATE NOT NULL,
	p10 INTEGER NOT NULL,
	p50 INTEGER NOT NULL,
	p90 INTEGER NOT NULL,
	versao_modelo_id VARCHAR(60) NOT NULL,
	gerada_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_previsao_comercio_cat_mes UNIQUE (comercio_id, categoria_id, mes, versao_modelo_id),
	CONSTRAINT ck_previsao_faixa CHECK (p10 <= p50 AND p50 <= p90),
	FOREIGN KEY(empresa_id) REFERENCES empresa (id) ON DELETE CASCADE,
	FOREIGN KEY(comercio_id) REFERENCES comercio (id) ON DELETE CASCADE,
	FOREIGN KEY(categoria_id) REFERENCES categoria (id),
	FOREIGN KEY(versao_modelo_id) REFERENCES versao_modelo (id)
);

CREATE INDEX IF NOT EXISTS ix_previsao_comercio_id ON previsao (comercio_id);
CREATE INDEX IF NOT EXISTS ix_previsao_empresa_id ON previsao (empresa_id);

CREATE TABLE IF NOT EXISTS serie_mensal (
	id SERIAL NOT NULL,
	empresa_id VARCHAR(60) NOT NULL,
	comercio_id VARCHAR(60) NOT NULL,
	categoria_id VARCHAR(30) NOT NULL,
	mes DATE NOT NULL,
	quantidade INTEGER NOT NULL,
	fechado BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_serie_comercio_cat_mes UNIQUE (comercio_id, categoria_id, mes),
	FOREIGN KEY(empresa_id) REFERENCES empresa (id) ON DELETE CASCADE,
	FOREIGN KEY(comercio_id) REFERENCES comercio (id) ON DELETE CASCADE,
	FOREIGN KEY(categoria_id) REFERENCES categoria (id)
);

CREATE INDEX IF NOT EXISTS ix_serie_mensal_comercio_id ON serie_mensal (comercio_id);
CREATE INDEX IF NOT EXISTS ix_serie_mensal_empresa_id ON serie_mensal (empresa_id);

CREATE TABLE IF NOT EXISTS alerta (
	id VARCHAR(80) NOT NULL,
	empresa_id VARCHAR(60) NOT NULL,
	comercio_id VARCHAR(60) NOT NULL,
	categoria_id VARCHAR(30) NOT NULL,
	estado VARCHAR(20) NOT NULL,
	atual INTEGER NOT NULL,
	previsao_id VARCHAR(80) NOT NULL,
	gerado_em DATE NOT NULL,
	situacao VARCHAR(20) NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(empresa_id) REFERENCES empresa (id) ON DELETE CASCADE,
	FOREIGN KEY(comercio_id) REFERENCES comercio (id) ON DELETE CASCADE,
	FOREIGN KEY(categoria_id) REFERENCES categoria (id),
	FOREIGN KEY(previsao_id) REFERENCES previsao (id)
);

CREATE INDEX IF NOT EXISTS ix_alerta_comercio_id ON alerta (comercio_id);
CREATE INDEX IF NOT EXISTS ix_alerta_empresa_id ON alerta (empresa_id);

CREATE TABLE IF NOT EXISTS avaliacao (
	id VARCHAR(80) NOT NULL,
	empresa_id VARCHAR(60) NOT NULL,
	comercio_id VARCHAR(60) NOT NULL,
	id_origem VARCHAR(200) NOT NULL,
	data DATE NOT NULL,
	estrelas INTEGER NOT NULL,
	texto TEXT,
	coletada_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	execucao_coleta_id VARCHAR(60),
	PRIMARY KEY (id),
	CONSTRAINT uq_avaliacao_comercio_origem UNIQUE (comercio_id, id_origem),
	CONSTRAINT ck_avaliacao_estrelas CHECK (estrelas BETWEEN 1 AND 5),
	FOREIGN KEY(empresa_id) REFERENCES empresa (id) ON DELETE CASCADE,
	FOREIGN KEY(comercio_id) REFERENCES comercio (id) ON DELETE CASCADE,
	FOREIGN KEY(execucao_coleta_id) REFERENCES execucao_coleta (id)
);

CREATE INDEX IF NOT EXISTS ix_avaliacao_comercio_id ON avaliacao (comercio_id);
CREATE INDEX IF NOT EXISTS ix_avaliacao_data ON avaliacao (data);
CREATE INDEX IF NOT EXISTS ix_avaliacao_empresa_id ON avaliacao (empresa_id);

CREATE TABLE IF NOT EXISTS classificacao (
	id VARCHAR(80) NOT NULL,
	empresa_id VARCHAR(60) NOT NULL,
	avaliacao_id VARCHAR(80) NOT NULL,
	categoria_id VARCHAR(30),
	confianca FLOAT NOT NULL,
	motivo_sem_assunto VARCHAR(120),
	versao_modelo_id VARCHAR(60) NOT NULL,
	criada_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_classificacao_avaliacao UNIQUE (avaliacao_id, versao_modelo_id),
	FOREIGN KEY(empresa_id) REFERENCES empresa (id) ON DELETE CASCADE,
	FOREIGN KEY(avaliacao_id) REFERENCES avaliacao (id) ON DELETE CASCADE,
	FOREIGN KEY(categoria_id) REFERENCES categoria (id),
	FOREIGN KEY(versao_modelo_id) REFERENCES versao_modelo (id)
);

CREATE INDEX IF NOT EXISTS ix_classificacao_avaliacao_id ON classificacao (avaliacao_id);
CREATE INDEX IF NOT EXISTS ix_classificacao_empresa_id ON classificacao (empresa_id);

-- As três tabelas de "Por quê?", "E se?" e "Testes". Tudo o que entra nelas é
-- digitado pelo dono (ou gerado pela conta de demonstração, marcada como tal):
-- o diário de mudanças, os turnos da operação e o plano do teste com o sorteio.

CREATE TABLE IF NOT EXISTS evento_diario (
	id VARCHAR(60) NOT NULL,
	empresa_id VARCHAR(60) NOT NULL,
	comercio_id VARCHAR(60) NOT NULL,
	data DATE NOT NULL,
	tipo VARCHAR(20) NOT NULL,
	descricao VARCHAR(200) NOT NULL,
	criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(empresa_id) REFERENCES empresa (id) ON DELETE CASCADE,
	FOREIGN KEY(comercio_id) REFERENCES comercio (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_evento_diario_comercio_id ON evento_diario (comercio_id);
CREATE INDEX IF NOT EXISTS ix_evento_diario_empresa_id ON evento_diario (empresa_id);

CREATE TABLE IF NOT EXISTS turno (
	id VARCHAR(60) NOT NULL,
	empresa_id VARCHAR(60) NOT NULL,
	comercio_id VARCHAR(60) NOT NULL,
	dia_semana INTEGER NOT NULL,
	periodo VARCHAR(10) NOT NULL,
	equipe INTEGER NOT NULL,
	clientes FLOAT NOT NULL,
	minutos_atendimento FLOAT NOT NULL,
	custo_hora FLOAT NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_turno_comercio_dia_periodo UNIQUE (comercio_id, dia_semana, periodo),
	CONSTRAINT ck_turno_valores CHECK (dia_semana BETWEEN 0 AND 6 AND equipe >= 0 AND clientes >= 0 AND minutos_atendimento > 0 AND custo_hora >= 0),
	FOREIGN KEY(empresa_id) REFERENCES empresa (id) ON DELETE CASCADE,
	FOREIGN KEY(comercio_id) REFERENCES comercio (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_turno_comercio_id ON turno (comercio_id);
CREATE INDEX IF NOT EXISTS ix_turno_empresa_id ON turno (empresa_id);

CREATE TABLE IF NOT EXISTS experimento (
	id VARCHAR(60) NOT NULL,
	empresa_id VARCHAR(60) NOT NULL,
	comercio_id VARCHAR(60) NOT NULL,
	categoria_id VARCHAR(30) NOT NULL,
	acao VARCHAR(200) NOT NULL,
	inicio DATE NOT NULL,
	fim DATE NOT NULL,
	dias_com_acao TEXT NOT NULL,
	menor_efeito FLOAT NOT NULL,
	selo VARCHAR(64) NOT NULL,
	selado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	estado VARCHAR(20) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_experimento_periodo CHECK (inicio <= fim),
	FOREIGN KEY(empresa_id) REFERENCES empresa (id) ON DELETE CASCADE,
	FOREIGN KEY(comercio_id) REFERENCES comercio (id) ON DELETE CASCADE,
	FOREIGN KEY(categoria_id) REFERENCES categoria (id)
);

CREATE INDEX IF NOT EXISTS ix_experimento_comercio_id ON experimento (comercio_id);
CREATE INDEX IF NOT EXISTS ix_experimento_empresa_id ON experimento (empresa_id);

CREATE TABLE IF NOT EXISTS marcacao_dia (
	id SERIAL NOT NULL,
	empresa_id VARCHAR(60) NOT NULL,
	experimento_id VARCHAR(60) NOT NULL,
	data DATE NOT NULL,
	seguiu BOOLEAN NOT NULL,
	marcado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_marcacao_experimento_data UNIQUE (experimento_id, data),
	FOREIGN KEY(empresa_id) REFERENCES empresa (id) ON DELETE CASCADE,
	FOREIGN KEY(experimento_id) REFERENCES experimento (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_marcacao_dia_empresa_id ON marcacao_dia (empresa_id);
CREATE INDEX IF NOT EXISTS ix_marcacao_dia_experimento_id ON marcacao_dia (experimento_id);

-- Os cinco assuntos. O id é o que o código usa; o nome é o que a tela mostra.
INSERT INTO categoria (id, nome, ordem) VALUES
	('atendimento', 'atendimento', 0),
	('demora', 'demora', 1),
	('preco', 'preço', 2),
	('qualidade', 'qualidade', 3),
	('ambiente', 'ambiente', 4)
ON CONFLICT (id) DO NOTHING;
