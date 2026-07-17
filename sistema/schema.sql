-- Schema do Sistema de Gestão da CMDC
-- Base normativa: Lei nº 3.525/2025 (estrutura e cargos) e Lei nº 1.506/2000
-- (regime de pessoal). SQL portável: SQLite (estudo/testes) e PostgreSQL.
-- Datas em ISO-8601 (TEXT); valores monetários em NUMERIC.

-- ============================================================
-- Módulo 1: Estrutura organizacional
-- ============================================================

CREATE TABLE norma (
    id          INTEGER PRIMARY KEY,
    especie     TEXT NOT NULL,             -- Lei, Resolução, Portaria...
    numero      TEXT NOT NULL,             -- "3.525/2025"
    ementa      TEXT,
    UNIQUE (especie, numero)
);

CREATE TABLE unidade (
    id             INTEGER PRIMARY KEY,
    nome           TEXT NOT NULL,
    sigla          TEXT,
    -- Grau funcional da Lei 3.525/2025 (art. 2º); NULL para órgãos políticos
    grau           INTEGER CHECK (grau BETWEEN 1 AND 4),
    tipo           TEXT NOT NULL CHECK (tipo IN
                     ('POLITICO', 'SUPERIOR', 'COORDENADORIA',
                      'ASSESSORAMENTO', 'AUXILIAR', 'COMISSAO')),
    unidade_pai_id INTEGER REFERENCES unidade (id),
    norma_id       INTEGER REFERENCES norma (id),
    vigente_desde  TEXT NOT NULL,          -- Lei 3.525/2025: efeitos desde 2025-09-01
    vigente_ate    TEXT                    -- NULL = vigente
);

-- ============================================================
-- Módulo 2: Cargos, servidores e lotação
-- ============================================================

-- Símbolos remuneratórios do Anexo I. FC-* = função de confiança
-- gratificada (apenas servidor efetivo), demais = cargo em comissão.
CREATE TABLE simbolo (
    codigo           TEXT PRIMARY KEY,     -- DAS-8, FC-2, CAE-1...
    retribuicao_base NUMERIC NOT NULL,
    natureza         TEXT NOT NULL CHECK (natureza IN
                       ('COMISSAO', 'FUNCAO_CONFIANCA'))
);

CREATE TABLE cargo (
    id                 INTEGER PRIMARY KEY,
    denominacao        TEXT NOT NULL,
    tipo               TEXT NOT NULL CHECK (tipo IN
                         ('EFETIVO', 'COMISSAO', 'FUNCAO_CONFIANCA')),
    simbolo_codigo     TEXT REFERENCES simbolo (codigo),  -- NULL p/ efetivos
    quantidade_vagas   INTEGER NOT NULL CHECK (quantidade_vagas > 0),
    unidade_lotacao_id INTEGER REFERENCES unidade (id),   -- lotação padrão (dirigentes)
    norma_id           INTEGER REFERENCES norma (id),
    -- Efetivos exigem concurso (CF art. 37, II; Lei 1.506/2000)
    CHECK (tipo = 'EFETIVO' OR simbolo_codigo IS NOT NULL)
);

CREATE TABLE servidor (
    id             INTEGER PRIMARY KEY,
    nome           TEXT NOT NULL,
    matricula      TEXT UNIQUE,
    vinculo        TEXT NOT NULL CHECK (vinculo IN
                     ('EFETIVO', 'COMISSIONADO', 'CEDIDO', 'TEMPORARIO')),
    data_admissao  TEXT NOT NULL,
    -- Vencimento básico do cargo efetivo (plano de carreira próprio;
    -- o Anexo I da Lei 3.525/2025 só remunera comissionados/funções)
    vencimento_base NUMERIC,
    -- Estágio probatório de 36 meses (Lei 1.506/2000, art. 23)
    data_estabilidade TEXT
);

-- Histórico de provimento/lotação (quem ocupa o quê, onde, quando).
CREATE TABLE provimento (
    id           INTEGER PRIMARY KEY,
    servidor_id  INTEGER NOT NULL REFERENCES servidor (id),
    cargo_id     INTEGER NOT NULL REFERENCES cargo (id),
    unidade_id   INTEGER NOT NULL REFERENCES unidade (id),
    ato          TEXT,                     -- Portaria do Presidente (art. 3º)
    data_inicio  TEXT NOT NULL,
    data_fim     TEXT                      -- NULL = ativo
);

-- ============================================================
-- Módulo 3: Folha de pagamento
-- ============================================================

CREATE TABLE rubrica (
    codigo          TEXT PRIMARY KEY,      -- GAL, GAP, REP-TL...
    descricao       TEXT NOT NULL,
    natureza        TEXT NOT NULL CHECK (natureza IN
                      ('VENCIMENTO', 'GRATIFICACAO', 'ADICIONAL', 'DESCONTO')),
    base_legal      TEXT NOT NULL,
    percentual_max  NUMERIC,               -- teto legal (GAL: 150)
    incorporavel    INTEGER NOT NULL DEFAULT 0 CHECK (incorporavel IN (0, 1))
);

-- Designações para comissões permanentes/temporárias (arts. 45-47) e
-- funções de agente de contratação; alimenta a rubrica GRAT-COM (40%).
CREATE TABLE designacao_comissao (
    id                  INTEGER PRIMARY KEY,
    servidor_id         INTEGER NOT NULL REFERENCES servidor (id),
    comissao_unidade_id INTEGER NOT NULL REFERENCES unidade (id),
    funcao              TEXT NOT NULL,     -- Presidente, Membro, Agente de Contratação, Pregoeiro
    -- Base de incidência escolhida pelo servidor (art. 46, §3º)
    base_incidencia     TEXT NOT NULL CHECK (base_incidencia IN
                          ('VENCIMENTO_EFETIVO', 'SIMBOLO_COMISSAO',
                           'CARGO_OU_FUNCAO_EXERCIDA')),
    data_inicio         TEXT NOT NULL,
    data_fim            TEXT
);

CREATE TABLE folha (
    id           INTEGER PRIMARY KEY,
    competencia  TEXT NOT NULL UNIQUE,     -- "2025-09"
    status       TEXT NOT NULL DEFAULT 'ABERTA' CHECK (status IN
                   ('ABERTA', 'CALCULADA', 'FECHADA', 'PAGA'))
);

CREATE TABLE folha_item (
    id             INTEGER PRIMARY KEY,
    folha_id       INTEGER NOT NULL REFERENCES folha (id),
    servidor_id    INTEGER NOT NULL REFERENCES servidor (id),
    rubrica_codigo TEXT NOT NULL REFERENCES rubrica (codigo),
    base_calculo   NUMERIC NOT NULL,
    percentual     NUMERIC,                -- NULL para valores fixos
    valor          NUMERIC NOT NULL
);

-- ============================================================
-- Módulo 4: Protocolo e tramitação
-- ============================================================

CREATE TABLE processo (
    id                INTEGER PRIMARY KEY,
    numero            INTEGER NOT NULL,
    ano               INTEGER NOT NULL,
    tipo              TEXT NOT NULL CHECK (tipo IN
                        ('ADMINISTRATIVO', 'LEGISLATIVO')),
    assunto           TEXT NOT NULL,
    interessado       TEXT,
    unidade_origem_id INTEGER REFERENCES unidade (id),
    data_autuacao     TEXT NOT NULL,
    situacao          TEXT NOT NULL DEFAULT 'EM_TRAMITACAO' CHECK (situacao IN
                        ('EM_TRAMITACAO', 'SOBRESTADO', 'ARQUIVADO', 'CONCLUIDO')),
    UNIQUE (numero, ano)
);

CREATE TABLE documento (
    id          INTEGER PRIMARY KEY,
    processo_id INTEGER NOT NULL REFERENCES processo (id),
    tipo        TEXT NOT NULL,             -- ofício, parecer, despacho, ata...
    titulo      TEXT NOT NULL,
    autor       TEXT,
    data        TEXT NOT NULL
);

CREATE TABLE tramitacao (
    id                 INTEGER PRIMARY KEY,
    processo_id        INTEGER NOT NULL REFERENCES processo (id),
    unidade_origem_id  INTEGER NOT NULL REFERENCES unidade (id),
    unidade_destino_id INTEGER NOT NULL REFERENCES unidade (id),
    despacho           TEXT,
    data_envio         TEXT NOT NULL,
    data_recebimento   TEXT
);

-- ============================================================
-- Módulo 5: Processo legislativo
-- ============================================================

CREATE TABLE legislatura (
    id     INTEGER PRIMARY KEY,
    numero INTEGER NOT NULL UNIQUE,
    inicio TEXT NOT NULL,
    fim    TEXT NOT NULL
);

CREATE TABLE parlamentar (
    id      INTEGER PRIMARY KEY,
    nome    TEXT NOT NULL,
    partido TEXT
);

CREATE TABLE mandato (
    id                  INTEGER PRIMARY KEY,
    parlamentar_id      INTEGER NOT NULL REFERENCES parlamentar (id),
    legislatura_id      INTEGER NOT NULL REFERENCES legislatura (id),
    gabinete_unidade_id INTEGER REFERENCES unidade (id),
    UNIQUE (parlamentar_id, legislatura_id)
);

CREATE TABLE proposicao (
    id                  INTEGER PRIMARY KEY,
    tipo                TEXT NOT NULL CHECK (tipo IN
                          ('PL', 'PDL', 'PR', 'EMENDA', 'INDICACAO',
                           'REQUERIMENTO', 'MOCAO', 'VETO')),
    numero              INTEGER NOT NULL,
    ano                 INTEGER NOT NULL,
    ementa              TEXT NOT NULL,
    autor_parlamentar_id INTEGER REFERENCES parlamentar (id),  -- NULL: Executivo/Mesa
    processo_id         INTEGER REFERENCES processo (id),
    situacao            TEXT NOT NULL DEFAULT 'EM_TRAMITACAO',
    UNIQUE (tipo, numero, ano)
);

CREATE TABLE sessao (
    id     INTEGER PRIMARY KEY,
    tipo   TEXT NOT NULL CHECK (tipo IN
             ('ORDINARIA', 'EXTRAORDINARIA', 'SOLENE')),
    numero INTEGER NOT NULL,
    data   TEXT NOT NULL
);

CREATE TABLE pauta_item (
    id            INTEGER PRIMARY KEY,
    sessao_id     INTEGER NOT NULL REFERENCES sessao (id),
    proposicao_id INTEGER NOT NULL REFERENCES proposicao (id),
    ordem         INTEGER NOT NULL
);

CREATE TABLE votacao (
    id            INTEGER PRIMARY KEY,
    sessao_id     INTEGER NOT NULL REFERENCES sessao (id),
    proposicao_id INTEGER NOT NULL REFERENCES proposicao (id),
    modalidade    TEXT NOT NULL CHECK (modalidade IN ('SIMBOLICA', 'NOMINAL')),
    resultado     TEXT CHECK (resultado IN ('APROVADA', 'REJEITADA', 'RETIRADA'))
);

CREATE TABLE voto (
    id             INTEGER PRIMARY KEY,
    votacao_id     INTEGER NOT NULL REFERENCES votacao (id),
    parlamentar_id INTEGER NOT NULL REFERENCES parlamentar (id),
    valor          TEXT NOT NULL CHECK (valor IN ('SIM', 'NAO', 'ABSTENCAO')),
    UNIQUE (votacao_id, parlamentar_id)
);

-- ============================================================
-- Módulo 6: Compras, contratos e execução (Lei 14.133/2021)
-- ============================================================

CREATE TABLE fornecedor (
    id           INTEGER PRIMARY KEY,
    razao_social TEXT NOT NULL,
    cnpj         TEXT UNIQUE
);

CREATE TABLE contratacao (
    id             INTEGER PRIMARY KEY,
    modalidade     TEXT NOT NULL CHECK (modalidade IN
                     ('PREGAO', 'CONCORRENCIA', 'CONCURSO', 'LEILAO',
                      'DIALOGO_COMPETITIVO', 'DISPENSA', 'INEXIGIBILIDADE')),
    numero         INTEGER NOT NULL,
    ano            INTEGER NOT NULL,
    objeto         TEXT NOT NULL,
    valor_estimado NUMERIC,
    processo_id    INTEGER REFERENCES processo (id),
    situacao       TEXT NOT NULL DEFAULT 'EM_ANDAMENTO',
    UNIQUE (modalidade, numero, ano)
);

CREATE TABLE contrato (
    id             INTEGER PRIMARY KEY,
    contratacao_id INTEGER NOT NULL REFERENCES contratacao (id),
    fornecedor_id  INTEGER NOT NULL REFERENCES fornecedor (id),
    valor          NUMERIC NOT NULL,
    inicio         TEXT NOT NULL,
    fim            TEXT
);

CREATE TABLE empenho (
    id          INTEGER PRIMARY KEY,
    numero      INTEGER NOT NULL,
    ano         INTEGER NOT NULL,
    valor       NUMERIC NOT NULL,
    descricao   TEXT NOT NULL,
    contrato_id INTEGER REFERENCES contrato (id),
    UNIQUE (numero, ano)
);

-- ============================================================
-- Módulo 7: Controle interno e transparência
-- ============================================================

CREATE TABLE publicacao (
    id         INTEGER PRIMARY KEY,
    tipo       TEXT NOT NULL,              -- lei, ata, contrato, folha...
    referencia TEXT NOT NULL,              -- identificação do objeto publicado
    url        TEXT,
    data       TEXT NOT NULL
);

CREATE TABLE auditoria (
    id          INTEGER PRIMARY KEY,
    tabela      TEXT NOT NULL,
    registro_id INTEGER NOT NULL,
    operacao    TEXT NOT NULL CHECK (operacao IN ('INSERT', 'UPDATE', 'DELETE')),
    usuario     TEXT NOT NULL,
    datahora    TEXT NOT NULL,
    detalhes    TEXT
);

-- Índices para as consultas mais frequentes
CREATE INDEX idx_unidade_pai ON unidade (unidade_pai_id);
CREATE INDEX idx_provimento_ativo ON provimento (cargo_id, data_fim);
CREATE INDEX idx_tramitacao_processo ON tramitacao (processo_id);
CREATE INDEX idx_folha_item_servidor ON folha_item (folha_id, servidor_id);
CREATE INDEX idx_voto_votacao ON voto (votacao_id);
