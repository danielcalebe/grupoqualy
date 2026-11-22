-- Esquema completo — Sistema de Logística Grupo Qualy (v1)
-- Conforme PLANEJAMENTO_SISTEMA_LOGISTICA.md §5

PRAGMA foreign_keys = ON;

-- ======================= USUÁRIOS E PERFIS =======================

CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    senha_hash    TEXT    NOT NULL,
    perfil        TEXT    NOT NULL CHECK (perfil IN (
        'administradora', 'chefe_logistica', 'motorista', 'balanca', 'financeiro'
    )),
    ativo         INTEGER NOT NULL DEFAULT 1,
    criado_em     TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ======================= CADASTROS =======================

CREATE TABLE IF NOT EXISTS fornecedores (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    razao_social   TEXT    NOT NULL,
    nome_fantasia  TEXT,
    cnpj_cpf       TEXT,
    telefone       TEXT,
    email          TEXT,
    frequente      INTEGER NOT NULL DEFAULT 0,
    ativo          INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS pontos_coleta (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    fornecedor_id             INTEGER NOT NULL REFERENCES fornecedores(id),
    nome                      TEXT    NOT NULL,
    logradouro                TEXT    NOT NULL,
    numero                    TEXT,
    bairro                    TEXT    NOT NULL,
    cidade                    TEXT    NOT NULL,
    uf                        TEXT    NOT NULL,
    cep                       TEXT,
    latitude                  REAL,
    longitude                 REAL,
    nome_responsavel          TEXT    NOT NULL,
    contato_responsavel      TEXT,
    tipo_veiculo_padrao       TEXT    NOT NULL DEFAULT 'garra'
                            CHECK (tipo_veiculo_padrao IN (
                                'roll_on', 'garra', 'carreta_terceirizada'
                            )),
    peso_gatilho_kg           REAL,
    distancia_patio_km        INTEGER,
    tempo_deslocamento_minutos INTEGER,
    observacoes               TEXT,
    ativo                     INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_pontos_bairro ON pontos_coleta(bairro);
CREATE INDEX IF NOT EXISTS idx_pontos_fornecedor ON pontos_coleta(fornecedor_id);

CREATE TABLE IF NOT EXISTS empresas_parceiras (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    razao_social TEXT    NOT NULL,
    cnpj         TEXT,
    telefone     TEXT,
    email        TEXT,
    ativo        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS veiculos (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    placa                       TEXT    NOT NULL UNIQUE,
    descricao                   TEXT,
    tipo                        TEXT    NOT NULL
                                CHECK (tipo IN ('roll_on', 'garra', 'carreta_terceirizada')),
    capacidade_kg               REAL,
    tempo_execucao_padrao_minutos INTEGER NOT NULL DEFAULT 30,
    identificador_rastreador    TEXT,
    terceirizado                INTEGER NOT NULL DEFAULT 0,
    empresa_parceira_id         INTEGER REFERENCES empresas_parceiras(id),
    ativo                       INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS motoristas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nome                TEXT    NOT NULL,
    cpf                 TEXT,
    cnh                 TEXT,
    telefone            TEXT,
    email               TEXT,
    tipo                TEXT    NOT NULL DEFAULT 'interno'
                        CHECK (tipo IN ('interno', 'terceirizado')),
    empresa_parceira_id INTEGER REFERENCES empresas_parceiras(id),
    usuario_id          INTEGER REFERENCES usuarios(id),
    ativo               INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS disponibilidades_motorista (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    motorista_id INTEGER NOT NULL REFERENCES motoristas(id),
    inicio       TEXT    NOT NULL,
    fim          TEXT    NOT NULL,
    disponivel   INTEGER NOT NULL DEFAULT 1,
    motivo       TEXT
);

-- ======================= ROTAS E COLETAS =======================

CREATE TABLE IF NOT EXISTS rotas_diarias (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    data                      TEXT    NOT NULL,
    veiculo_id                INTEGER NOT NULL REFERENCES veiculos(id),
    motorista_id              INTEGER NOT NULL REFERENCES motoristas(id),
    elaborada_por_usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
    distancia_total_prevista_km INTEGER NOT NULL DEFAULT 0,
    tempo_total_previsto_minutos INTEGER NOT NULL DEFAULT 0,
    data_hora_envio_programacao  TEXT
);

CREATE INDEX IF NOT EXISTS idx_rotas_data ON rotas_diarias(data);

CREATE TABLE IF NOT EXISTS coletas (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo                      TEXT    NOT NULL UNIQUE,
    ponto_coleta_id             INTEGER NOT NULL REFERENCES pontos_coleta(id),
    veiculo_id                  INTEGER REFERENCES veiculos(id),
    motorista_id                INTEGER REFERENCES motoristas(id),
    criada_por_usuario_id       INTEGER NOT NULL REFERENCES usuarios(id),
    tipo_veiculo_necessario     TEXT    NOT NULL
                                CHECK (tipo_veiculo_necessario IN (
                                    'roll_on', 'garra', 'carreta_terceirizada'
                                )),
    origem                      TEXT    NOT NULL
                                CHECK (origem IN (
                                    'fornecedor_solicitou', 'logistica_contatou'
                                )),
    status                      TEXT    NOT NULL DEFAULT 'agendada'
                                CHECK (status IN (
                                    'agendada', 'em_andamento', 'concluida', 'cancelada'
                                )),
    urgente                     INTEGER NOT NULL DEFAULT 0,
    data_solicitacao            TEXT    NOT NULL DEFAULT (datetime('now')),
    data_hora_prevista_inicio   TEXT    NOT NULL,
    data_hora_prevista_fim      TEXT    NOT NULL,
    data_hora_real_saida        TEXT,
    data_hora_real_chegada      TEXT,
    tempo_deslocamento_ida_minutos    INTEGER NOT NULL DEFAULT 0,
    tempo_deslocamento_volta_minutos  INTEGER NOT NULL DEFAULT 0,
    tempo_execucao_minutos            INTEGER NOT NULL DEFAULT 0,
    tempo_total_minutos               INTEGER NOT NULL DEFAULT 0,
    peso_estimado_kg          REAL,
    peso_real_kg               REAL,
    ordem_na_rota              INTEGER,
    rota_diaria_id             INTEGER REFERENCES rotas_diarias(id),
    observacoes                TEXT,
    motivo_cancelamento        TEXT,
    id_evento_agenda_externa   TEXT,
    criado_em                  TEXT    NOT NULL DEFAULT (datetime('now')),
    atualizado_em              TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_coletas_inicio ON coletas(data_hora_prevista_inicio);
CREATE INDEX IF NOT EXISTS idx_coletas_status ON coletas(status);
CREATE INDEX IF NOT EXISTS idx_coletas_veiculo ON coletas(veiculo_id, data_hora_prevista_inicio);
CREATE INDEX IF NOT EXISTS idx_coletas_motorista ON coletas(motorista_id, data_hora_prevista_inicio);
CREATE INDEX IF NOT EXISTS idx_coletas_codigo ON coletas(codigo);
CREATE INDEX IF NOT EXISTS idx_coletas_rota ON coletas(rota_diaria_id);

-- ======================= TÍQUETE =======================

CREATE TABLE IF NOT EXISTS tickets_descarregamento (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    coleta_id               INTEGER NOT NULL UNIQUE REFERENCES coletas(id),
    numero                  TEXT    NOT NULL UNIQUE,
    pesagem_id              INTEGER,
    peso_liquido_kg         REAL,
    data_hora_descarregamento TEXT
);

CREATE INDEX IF NOT EXISTS idx_tickets_numero ON tickets_descarregamento(numero);

-- ======================= AUDITORIA E COMUNICAÇÃO =======================

CREATE TABLE IF NOT EXISTS historico_status_coleta (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    coleta_id       INTEGER NOT NULL REFERENCES coletas(id),
    status_anterior TEXT,
    status_novo     TEXT    NOT NULL,
    data_hora       TEXT    NOT NULL DEFAULT (datetime('now')),
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id),
    observacao      TEXT
);

CREATE INDEX IF NOT EXISTS idx_hist_coleta ON historico_status_coleta(coleta_id);

CREATE TABLE IF NOT EXISTS notificacoes_coleta (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    coleta_id    INTEGER REFERENCES coletas(id),
    motorista_id INTEGER REFERENCES motoristas(id),
    usuario_id   INTEGER REFERENCES usuarios(id),
    canal        TEXT    NOT NULL DEFAULT 'sistema'
                 CHECK (canal IN ('sistema', 'email', 'whatsapp', 'telefone')),
    mensagem     TEXT    NOT NULL,
    data_hora_envio TEXT NOT NULL DEFAULT (datetime('now')),
    lida         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS alertas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo        TEXT    NOT NULL,
    severidade  TEXT    NOT NULL DEFAULT 'info'
                CHECK (severidade IN ('info', 'aviso', 'critico')),
    mensagem    TEXT    NOT NULL,
    ref_tabela  TEXT,
    ref_id      INTEGER,
    resolvido   INTEGER NOT NULL DEFAULT 0,
    criado_em   TEXT    NOT NULL DEFAULT (datetime('now')),
    resolvido_em TEXT
);

CREATE INDEX IF NOT EXISTS idx_alertas_resolvido ON alertas(resolvido);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id  INTEGER REFERENCES usuarios(id),
    acao        TEXT    NOT NULL,
    tabela      TEXT,
    registro_id INTEGER,
    detalhe_json TEXT,
    data_hora   TEXT    NOT NULL DEFAULT (datetime('now'))
);
