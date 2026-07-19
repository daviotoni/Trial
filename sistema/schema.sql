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

-- Avaliação de desempenho semestral dos efetivos (Lei 3.226/2022).
-- O conceito determina o Adicional de Produtividade do art. 14.
CREATE TABLE avaliacao_desempenho (
    id          INTEGER PRIMARY KEY,
    servidor_id INTEGER NOT NULL REFERENCES servidor (id),
    periodo     TEXT NOT NULL,             -- "2025-S2" (semestre)
    pontuacao   INTEGER NOT NULL CHECK (pontuacao BETWEEN 0 AND 100),
    conceito    TEXT NOT NULL CHECK (conceito IN
                  ('EXCELENTE', 'MUITO_BOM', 'BOM', 'REGULAR',
                   'INSATISFATORIO')),
    avaliador   TEXT NOT NULL,             -- chefia imediata (art. 4º)
    data        TEXT NOT NULL,
    UNIQUE (servidor_id, periodo)
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
    -- Rito configurável opcional (Módulo 9). NULL = tramitação livre.
    tipo_processo_id  INTEGER REFERENCES tipo_processo (id),
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
    -- Prazo (SLA) para a unidade destino se manifestar/receber. NULL = sem prazo.
    prazo              TEXT,
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
                          ('PL', 'PLC', 'PDL', 'PR', 'EMENDA', 'INDICACAO',
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
-- Módulo 5b: Comissões, relatoria e pareceres
-- ============================================================
-- Instrução da matéria nas comissões permanentes temáticas antes da
-- deliberação em Plenário (art. 33 e segs. do Regimento Interno,
-- Resolução nº 1.835/2000). Distinta das comissões administrativas do
-- art. 45 da Lei 3.525/2025 (que estão em `designacao_comissao`).

CREATE TABLE comissao_permanente (
    id   INTEGER PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE
);

-- Distribuição de relatoria: a comissão designa um relator (parlamentar)
-- para a proposição, com prazo regimental para o parecer.
CREATE TABLE relatoria (
    id                     INTEGER PRIMARY KEY,
    proposicao_id          INTEGER NOT NULL REFERENCES proposicao (id),
    comissao_id            INTEGER NOT NULL REFERENCES comissao_permanente (id),
    relator_parlamentar_id INTEGER NOT NULL REFERENCES parlamentar (id),
    distribuida_em         TEXT NOT NULL,
    prazo                  TEXT,   -- prazo regimental para o parecer
    situacao               TEXT NOT NULL DEFAULT 'ATIVA' CHECK (situacao IN
                             ('ATIVA', 'SUBSTITUIDA', 'CONCLUIDA', 'CANCELADA'))
);

-- Uma única relatoria ATIVA por proposição em cada comissão.
CREATE UNIQUE INDEX idx_relatoria_ativa
    ON relatoria (proposicao_id, comissao_id) WHERE situacao = 'ATIVA';

-- Parecer da comissão sobre a proposição. Não vincula o Plenário
-- (parecer contrário não impede a deliberação), mas a matéria de mérito
-- só entra em Ordem do Dia com parecer aprovado, salvo regime de urgência.
CREATE TABLE parecer (
    id            INTEGER PRIMARY KEY,
    relatoria_id  INTEGER NOT NULL REFERENCES relatoria (id),
    proposicao_id INTEGER NOT NULL REFERENCES proposicao (id),
    comissao_id   INTEGER NOT NULL REFERENCES comissao_permanente (id),
    tipo          TEXT NOT NULL CHECK (tipo IN
                    ('FAVORAVEL', 'FAVORAVEL_COM_EMENDAS',
                     'CONTRARIO', 'PELA_REJEICAO')),
    ementa        TEXT NOT NULL,
    situacao      TEXT NOT NULL DEFAULT 'EMITIDO' CHECK (situacao IN
                    ('RASCUNHO', 'EMITIDO', 'APROVADO', 'REJEITADO')),
    emitido_em    TEXT NOT NULL
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

-- ============================================================
-- Módulo 8: Usuários e perfis de acesso
-- ============================================================

-- Perfis espelham os setores da Lei 3.525/2025:
--   ADMIN (Diretoria-Geral/TI), RH (Coord. de Recursos Humanos),
--   PROTOCOLO (Secretaria-Geral), LEGISLATIVO (Plenário/Apoio
--   Legislativo), COMPRAS (Compras/Licitações), CONTROLE
--   (Controladoria-Geral/Publicações e Transparência).
CREATE TABLE usuario (
    id          INTEGER PRIMARY KEY,
    login       TEXT NOT NULL UNIQUE,
    senha_hash  TEXT NOT NULL,             -- PBKDF2-SHA256
    sal         TEXT NOT NULL,
    perfil      TEXT NOT NULL CHECK (perfil IN
                  ('ADMIN', 'RH', 'PROTOCOLO', 'LEGISLATIVO',
                   'COMPRAS', 'CONTROLE')),
    servidor_id INTEGER REFERENCES servidor (id),
    -- Lotação do usuário: o setor (unidade) em que ele trabalha. Quando
    -- preenchida, o acesso vem das áreas mapeadas para essa unidade
    -- (unidade_area), tornando o controle por setor real. NULL = usa o
    -- perfil como alçada (compatibilidade). ADMIN é sempre superusuário.
    unidade_id  INTEGER REFERENCES unidade (id),
    ativo       INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

-- Áreas funcionais que cada unidade (setor) opera. É o que dá sentido a
-- "cada setor só acessa o que lhe cabe": o usuário lotado na unidade
-- herda essas áreas. Ex.: Secretaria-Geral → PROTOCOLO; CPL → COMPRAS;
-- gabinetes → LEGISLATIVO; RH → PESSOAL/FOLHA.
CREATE TABLE unidade_area (
    unidade_id INTEGER NOT NULL REFERENCES unidade (id),
    area       TEXT NOT NULL CHECK (area IN
                 ('PESSOAL', 'FOLHA', 'PROTOCOLO', 'LEGISLATIVO',
                  'COMPRAS', 'TRANSPARENCIA', 'CONTROLE', 'USUARIOS')),
    PRIMARY KEY (unidade_id, area)
);

-- Ações específicas que cada unidade pode praticar dentro de uma área
-- (trava fina por competência). Ex.: um gabinete opera a área LEGISLATIVO,
-- mas dentro dela só APRESENTAR_PROPOSICAO; CONVOCAR_SESSAO é da
-- Presidência/Mesa. Sem regra de ação, a área basta.
CREATE TABLE unidade_acao (
    unidade_id INTEGER NOT NULL REFERENCES unidade (id),
    acao       TEXT NOT NULL,
    PRIMARY KEY (unidade_id, acao)
);

-- ============================================================
-- Módulo 9: Competências legais e fluxo processual
-- ============================================================
-- Traduz a Lei 3.525/2025 em regra operacional: cada unidade tem
-- competências (o que a lei lhe atribui) e cada tipo de processo tem um
-- rito — a sequência de setores por onde ele deve passar. É a base para
-- "cada setor faz só o que lhe cabe e remete ao setor seguinte".

-- Competências de cada unidade (fonte: orgao/cmdc.py → Lei 3.525/2025).
CREATE TABLE competencia (
    id         INTEGER PRIMARY KEY,
    unidade_id INTEGER NOT NULL REFERENCES unidade (id),
    descricao  TEXT NOT NULL,
    base_legal TEXT
);

-- Tipo de processo (rito). Configurável — o caminho não é fixo no código.
CREATE TABLE tipo_processo (
    id      INTEGER PRIMARY KEY,
    codigo  TEXT NOT NULL UNIQUE,      -- 'PL', 'COMPRA', 'OFICIO'...
    nome    TEXT NOT NULL,
    dominio TEXT NOT NULL CHECK (dominio IN ('LEGISLATIVO', 'ADMINISTRATIVO'))
);

-- Etapas ordenadas do rito: cada etapa é a passagem por uma unidade, com
-- a ação que aquele setor executa e um prazo (SLA) sugerido.
CREATE TABLE fluxo_etapa (
    id               INTEGER PRIMARY KEY,
    tipo_processo_id INTEGER NOT NULL REFERENCES tipo_processo (id),
    ordem            INTEGER NOT NULL,
    unidade_id       INTEGER NOT NULL REFERENCES unidade (id),
    acao             TEXT NOT NULL,       -- o que a unidade faz nesta etapa
    prazo_dias       INTEGER,             -- SLA sugerido para a etapa
    obrigatoria      INTEGER NOT NULL DEFAULT 1 CHECK (obrigatoria IN (0, 1)),
    UNIQUE (tipo_processo_id, ordem)
);

CREATE INDEX idx_competencia_unidade ON competencia (unidade_id);
CREATE INDEX idx_fluxo_etapa_tipo ON fluxo_etapa (tipo_processo_id, ordem);

-- Índices para as consultas mais frequentes
CREATE INDEX idx_unidade_pai ON unidade (unidade_pai_id);
CREATE INDEX idx_provimento_ativo ON provimento (cargo_id, data_fim);
CREATE INDEX idx_tramitacao_processo ON tramitacao (processo_id);
CREATE INDEX idx_folha_item_servidor ON folha_item (folha_id, servidor_id);
CREATE INDEX idx_voto_votacao ON voto (votacao_id);
CREATE INDEX idx_relatoria_proposicao ON relatoria (proposicao_id);
CREATE INDEX idx_parecer_proposicao ON parecer (proposicao_id);
