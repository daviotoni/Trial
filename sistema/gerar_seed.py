"""Gera a carga inicial (seed.sql) a partir do modelo de domínio da CMDC.

Fonte única de verdade: `orgao/cmdc.py` (estrutura e Anexo I da Lei
3.525/2025). Produz INSERTs portáveis para as tabelas norma, unidade,
simbolo, cargo e rubrica.

Uso:
    python -m sistema.gerar_seed > sistema/seed.sql
"""

from __future__ import annotations

from orgao.cmdc import (
    ANEXO_I,
    ASSESSORAMENTO_PARLAMENTAR,
    COMISSOES_PERMANENTES_ADMINISTRATIVAS,
    COORDENADORIAS,
    DIRIGENTES_POR_UNIDADE,
    LEI_3525,
    SERVICOS_AUXILIARES,
    construir_cmdc,
    eh_funcao_confianca,
)

VIGENCIA = "2025-09-01"  # efeitos financeiros da Lei 3.525/2025 (art. 102)

# Vereadores da 20ª Legislatura (nome parlamentar) — fonte: portal da CMDC.
# Cada um tem um gabinete próprio, que é um setor com acesso legislativo.
VEREADORES_20A_LEGISLATURA = [
    "Chiquinho Caipira", "Alex Freitas", "Andréia Zito", "Junior Uios",
    "Carlinhos da Barreira", "Claudio Thomaz", "Clovinho Sempre Junto",
    "Delza de Oliveira", "Junior Reis", "Anderson Lopes", "Eduardo Moreira",
    "Fernanda Costa", "Giorgio Monteiro", "Juliana do Taxi",
    "Leandro Enfermeiro", "Catiti", "Marquinho Oi", "Marquinho Dentista",
    "Marquinho da Pipa", "Dr. Maurício", "Michel Reis", "Michele Tavares",
    "Moises Neguinho", "Beto Gabriel", "Saulo Henrique", "Serginho Corrêa",
    "Valdecy Nunes", "Vitinho Grandão", "Wendell Oliveira",
]

# Áreas funcionais operadas por cada setor (unidade → áreas). Base do
# controle de acesso por unidade: quem trabalha ali herda estas áreas.
UNIDADE_AREAS = {
    "Presidência": ["LEGISLATIVO"],
    "Mesa Diretora": ["LEGISLATIVO"],
    "Procuradoria-Geral": ["JURIDICO"],
    "Consultoria-Geral Legislativa": ["JURIDICO"],
    "Coordenadoria da Secretaria-Geral": ["PROTOCOLO"],
    "Coordenadoria de Recursos Humanos": ["PESSOAL", "FOLHA"],
    "Departamento do e-Social": ["FOLHA"],
    "Coordenadoria de Contabilidade": ["FOLHA"],
    "Coordenadoria de Finanças": ["FOLHA"],
    "Comissão Permanente de Licitação": ["COMPRAS"],
    "Coordenadoria de Licitações e Contratos": ["COMPRAS"],
    "Coordenadoria de Material": ["COMPRAS"],
    "Coordenadoria de Avaliação e Acompanhamento de Compras": ["COMPRAS"],
    "Controladoria-Geral": ["CONTROLE", "FOLHA"],
    "Coordenadoria de Publicações e Transparência": ["TRANSPARENCIA", "CONTROLE"],
    "Diretoria de Plenário": ["LEGISLATIVO"],
    "Coordenadoria de Apoio Legislativo": ["LEGISLATIVO"],
    "Coordenadoria de Assuntos de Plenário": ["LEGISLATIVO"],
    "Coordenadoria de Atas e Projetos": ["LEGISLATIVO"],
    "Assistência às Comissões Permanentes": ["LEGISLATIVO"],
    "Coordenadoria de Tecnologia da Informação e Comunicação": ["USUARIOS"],
    # Órgãos de 1º grau
    "Diretoria-Geral": ["ADMINISTRACAO"],
    "Superintendência-Geral": ["ADMINISTRACAO"],
    "Superintendência de Assuntos Estratégicos": ["PLANEJAMENTO"],
    "Diretoria da Escola do Legislativo": ["CAPACITACAO"],
    "Ouvidoria-Geral": ["OUVIDORIA"],
    # Coordenadorias (2º grau) restantes
    "Coordenadoria de Cerimonial e Comunicação Social": ["COMUNICACAO"],
    "Coordenadoria de Documentação Histórica": ["DOCUMENTACAO"],
    "Coordenadoria de Manutenção": ["SERVICOS"],
    "Coordenadoria de Patrimônio": ["PATRIMONIO"],
    "Coordenadoria de Polícia Legislativa": ["SEGURANCA"],
    "Coordenadoria de Prevenção a Incêndio": ["SEGURANCA"],
    "Coordenadoria de Redação Oficial e Legislativa": ["LEGISLATIVO"],
    "Diretoria Administrativa": ["ADMINISTRACAO"],
    # Assessoramento parlamentar (3º grau)
    "Assessores Parlamentares": ["LEGISLATIVO"],
    "Assessoria Especial da Presidência": ["ADMINISTRACAO"],
    "Assessoria de Gabinete Parlamentar": ["LEGISLATIVO"],
    # Os serviços auxiliares operacionais de 4º grau (copa, limpeza,
    # reprografia, telefonia, transporte, manutenção predial, vigilância)
    # NÃO são setores com login próprio: são operados sob a coordenadoria
    # responsável (art. 29, 32, etc.). Só o Departamento do e-Social, que
    # tem artigo próprio (art. 48), é setor com atividade (FOLHA).
    # Comissões permanentes administrativas (art. 45)
    "Comissão Permanente de Aplicação de Sanções": ["COMPRAS"],
    "Comissão Permanente de Atualização e Consolidação de Leis e Normas "
    "Municipais": ["JURIDICO"],
    "Comissão Permanente de Proteção de Dados Pessoais": ["JURIDICO"],
    "Comissão Permanente de Recebimento Definitivo de Obras, Serviços e Bens":
        ["COMPRAS"],
}

# Ações legislativas específicas e quem pode praticá-las (trava fina por
# competência). Os gabinetes recebem APRESENTAR_PROPOSICAO à parte (loop).
UNIDADE_ACOES = {
    # DESPACHAR: requerimentos sujeitos a despacho do Presidente
    # (arts. 108-110 do Regimento Interno).
    "Presidência": ["CONVOCAR_SESSAO", "PAUTAR", "DESPACHAR"],
    "Mesa Diretora": ["CONVOCAR_SESSAO", "APRESENTAR_PROPOSICAO"],
    "Diretoria de Plenário": ["PAUTAR"],
    # Setor único de comissões: recebe as matérias e emite os pareceres,
    # marcando a comissão temática (art. 33 do Regimento Interno).
    "Assistência às Comissões Permanentes": ["EMITIR_PARECER"],
}

RUBRICAS = [
    ("VENC", "Vencimento/retribuição básica", "VENCIMENTO",
     "Lei 3.525/2025, art. 6º", None, 1),
    ("GAL", "Gratificação de Atividade Legislativa", "GRATIFICACAO",
     "Lei 3.525/2025, art. 7º", 150, 0),
    ("REP-TL", "Representação — carreira de Técnico Legislativo", "ADICIONAL",
     "Lei 3.525/2025, art. 8º", 60, 0),
    ("GAP", "Gratificação de Atividade Perigosa", "GRATIFICACAO",
     "Lei 3.525/2025, art. 9º", 40, 0),
    ("REP-JUD", "Adicional de Representação Judiciária", "ADICIONAL",
     "Lei 3.525/2025, art. 10", 40, 0),
    ("GRAT-COM", "Gratificação de comissão (indenizatória, não incorporável)",
     "GRATIFICACAO", "Lei 3.525/2025, arts. 46-47", 40, 0),
    ("GRAT-CC", "Gratificação de efetivo nomeado em cargo em comissão",
     "GRATIFICACAO", "Lei 3.525/2025, art. 3º, §4º", 100, 0),
    ("ATS", "Adicional por tempo de serviço (triênio)", "ADICIONAL",
     "Lei 3.525/2025, art. 6º, §2º, III", None, 1),
    ("AD-PROD", "Adicional de Produtividade (por conceito da avaliação)",
     "ADICIONAL", "Lei 3.226/2022, art. 14", 70, 0),
    ("IND-GAB", "Indenização de Representação de Gabinete Avançado",
     "ADICIONAL", "Lei 3.226/2022, art. 13", 70, 0),
    ("AUX-ALIM", "Auxílio-alimentação (valor fixado por ato do Presidente)",
     "ADICIONAL", "Lei 3.226/2022, art. 17; Lei 3.525/2025, art. 4º", None, 0),
    ("AUX-REF", "Auxílio-refeição (valor fixado por ato do Presidente)",
     "ADICIONAL", "Lei 3.226/2022, art. 17; Lei 3.525/2025, art. 4º", None, 0),
    ("AUX-LOC", "Auxílio-locomoção (valor fixado por ato do Presidente)",
     "ADICIONAL", "Lei 3.226/2022, art. 17; Lei 3.525/2025, art. 4º", None, 0),
]


def _sql(valor) -> str:
    if valor is None:
        return "NULL"
    if isinstance(valor, (int, float)):
        return str(valor)
    return "'" + str(valor).replace("'", "''") + "'"


def _tipo_unidade(nome: str) -> tuple[str, int | None]:
    """Classifica a unidade e devolve (tipo, grau) conforme a Lei 3.525/2025."""
    if nome in {"Mesa Diretora", "Presidência", "Gabinetes de Vereadores"}:
        return "POLITICO", None
    if nome in COMISSOES_PERMANENTES_ADMINISTRATIVAS:
        return "COMISSAO", None
    if nome in COORDENADORIAS:
        return "COORDENADORIA", 2
    if nome in ASSESSORAMENTO_PARLAMENTAR:
        return "ASSESSORAMENTO", 3
    if nome in SERVICOS_AUXILIARES:
        return "AUXILIAR", 4
    return "SUPERIOR", 1  # órgãos superiores de direção, incl. Diretoria-Geral


def gerar() -> str:
    linhas: list[str] = []
    out = linhas.append

    out("-- Seed gerado por sistema/gerar_seed.py a partir de orgao/cmdc.py")
    out("-- Fonte: Lei nº 3.525/2025 (estrutura e Anexo I)")
    out("")

    out("INSERT INTO norma (id, especie, numero, ementa) VALUES")
    out(f"  (1, {_sql(LEI_3525.especie)}, {_sql(LEI_3525.numero)}, "
        f"{_sql(LEI_3525.ementa)});")
    out("")

    # Unidades: percorre a árvore atribuindo ids e pais.
    cmdc = construir_cmdc()
    ids: dict[int, int] = {}  # id(objeto unidade) -> id no banco
    valores = []
    gab_parent_id = None
    pilha = [(cmdc.unidade_topo, None)]
    proximo = 1
    while pilha:
        unidade, pai_db = pilha.pop(0)
        ids[id(unidade)] = proximo
        if unidade.nome == "Gabinetes de Vereadores":
            gab_parent_id = proximo
        tipo, grau = _tipo_unidade(unidade.nome)
        valores.append(
            f"  ({proximo}, {_sql(unidade.nome)}, {_sql(unidade.sigla or None)}, "
            f"{_sql(grau)}, {_sql(tipo)}, {_sql(pai_db)}, 1, {_sql(VIGENCIA)})"
        )
        for sub in unidade.subunidades:
            pilha.append((sub, proximo))
        proximo += 1

    # Roster operacional: um gabinete (setor com acesso próprio) para cada
    # vereador da 20ª Legislatura. A estrutura da lei (cmdc.py) fica intacta;
    # este é o quadro de ocupação, que muda a cada legislatura.
    gab_ids: list[int] = []
    for apelido in VEREADORES_20A_LEGISLATURA:
        nome = f"Gabinete do(a) Vereador(a) {apelido}"
        valores.append(
            f"  ({proximo}, {_sql(nome)}, {_sql('GAB')}, 3, "
            f"{_sql('ASSESSORAMENTO')}, {_sql(gab_parent_id)}, 1, {_sql(VIGENCIA)})"
        )
        gab_ids.append(proximo)
        proximo += 1

    out("INSERT INTO unidade (id, nome, sigla, grau, tipo, unidade_pai_id, "
        "norma_id, vigente_desde) VALUES")
    out(",\n".join(valores) + ";")
    out("")

    # Competências de cada unidade — a Lei 3.525/2025 traduzida em regra
    # operacional (fonte: as Competencia anexadas às unidades em cmdc.py).
    comp_rows = []
    fila = [cmdc.unidade_topo]
    while fila:
        u = fila.pop(0)
        for c in u.competencias:
            base = str(c.base_legal) if c.base_legal else None
            comp_rows.append(f"  ({ids[id(u)]}, {_sql(c.descricao)}, {_sql(base)})")
        fila.extend(u.subunidades)
    # Competência de cada gabinete (exercício do mandato parlamentar).
    COMP_GABINETE = ("Assessoramento político-legislativo ao titular do "
                     "mandato; autoria e apresentação de proposições "
                     "(art. 1º, p.u., e art. 79)")
    for gid in gab_ids:
        comp_rows.append(
            f"  ({gid}, {_sql(COMP_GABINETE)}, {_sql('Lei 3.525/2025')})")
    if comp_rows:
        out("INSERT INTO competencia (unidade_id, descricao, base_legal) VALUES")
        out(",\n".join(comp_rows) + ";")
        out("")

    # Símbolos únicos do Anexo I (validando consistência de valores).
    simbolos: dict[str, int] = {}
    for _, valor, simbolo, _ in ANEXO_I:
        if simbolo in simbolos and simbolos[simbolo] != valor:
            raise ValueError(f"símbolo {simbolo} com valores divergentes")
        simbolos[simbolo] = valor
    out("INSERT INTO simbolo (codigo, retribuicao_base, natureza) VALUES")
    out(",\n".join(
        f"  ({_sql(cod)}, {valor}, "
        f"{_sql('FUNCAO_CONFIANCA' if eh_funcao_confianca(cod) else 'COMISSAO')})"
        for cod, valor in sorted(simbolos.items())
    ) + ";")
    out("")

    # Cargos do Anexo I, com lotação padrão para os dirigentes de unidade.
    unidade_por_dirigente = {
        cargo: unidade for unidade, cargo in DIRIGENTES_POR_UNIDADE.items()
    }
    unidade_db_por_nome = {}
    fila = [cmdc.unidade_topo]
    while fila:
        u = fila.pop(0)
        unidade_db_por_nome[u.nome] = ids[id(u)]
        fila.extend(u.subunidades)

    out("INSERT INTO cargo (id, denominacao, tipo, simbolo_codigo, "
        "quantidade_vagas, unidade_lotacao_id, norma_id) VALUES")
    valores = []
    for i, (denominacao, _, simbolo, qtd) in enumerate(ANEXO_I, start=1):
        tipo = "FUNCAO_CONFIANCA" if eh_funcao_confianca(simbolo) else "COMISSAO"
        lotacao = unidade_por_dirigente.get(denominacao)
        lotacao_id = unidade_db_por_nome.get(lotacao) if lotacao else None
        valores.append(
            f"  ({i}, {_sql(denominacao)}, {_sql(tipo)}, {_sql(simbolo)}, "
            f"{qtd}, {_sql(lotacao_id)}, 1)"
        )
    out(",\n".join(valores) + ";")
    out("")

    out("INSERT INTO rubrica (codigo, descricao, natureza, base_legal, "
        "percentual_max, incorporavel) VALUES")
    out(",\n".join(
        f"  ({_sql(c)}, {_sql(d)}, {_sql(n)}, {_sql(b)}, {_sql(p)}, {i})"
        for c, d, n, b, p, i in RUBRICAS
    ) + ";")
    out("")

    # Comissões permanentes temáticas do Regimento Interno (art. 33).
    # Fonte única: sistema.legislativo.COMISSOES_PERMANENTES_REGIMENTAIS.
    from sistema.legislativo import COMISSOES_PERMANENTES_REGIMENTAIS

    out("INSERT INTO comissao_permanente (id, nome) VALUES")
    out(",\n".join(
        f"  ({i}, {_sql(nome)})"
        for i, nome in enumerate(COMISSOES_PERMANENTES_REGIMENTAIS, start=1)
    ) + ";")
    out("")

    # 20ª Legislatura (2025-2028) com os 29 vereadores e seus mandatos,
    # cada um vinculado ao respectivo gabinete. Com isso, o login do
    # gabinete identifica o vereador titular — autor automático das
    # proposições que o gabinete protocola.
    out("INSERT INTO legislatura (id, numero, inicio, fim) VALUES")
    out("  (1, 20, '2025-01-01', '2028-12-31');")
    out("")
    out("INSERT INTO parlamentar (id, nome) VALUES")
    out(",\n".join(
        f"  ({i}, {_sql(nome)})"
        for i, nome in enumerate(VEREADORES_20A_LEGISLATURA, start=1)
    ) + ";")
    out("")
    out("INSERT INTO mandato (parlamentar_id, legislatura_id, "
        "gabinete_unidade_id) VALUES")
    out(",\n".join(
        f"  ({i}, 1, {gid})" for i, gid in enumerate(gab_ids, start=1)
    ) + ";")
    out("")

    # Tipos de processo e seus ritos (fluxo por etapas). Configuráveis:
    # o caminho é dado, não fixo no código. Cada etapa é a passagem por uma
    # unidade real da Lei 3.525/2025, com a ação e o prazo (SLA) sugerido.
    def _uid(nome: str) -> int:
        if nome not in unidade_db_por_nome:
            raise ValueError(f"unidade inexistente no fluxo: {nome!r}")
        return unidade_db_por_nome[nome]

    # Rito dos projetos (matéria de mérito: PL, PLC, PELO, PDL, PR).
    ETAPAS_PROJETO = [
        ("Gabinetes de Vereadores", "Autoria e apresentação da proposição", 0),
        ("Coordenadoria da Secretaria-Geral",
         "Protocolo, autuação e numeração", 2),
        ("Consultoria-Geral Legislativa",
         "Análise de constitucionalidade e técnica legislativa", 10),
        ("Assistência às Comissões Permanentes",
         "Distribuição às comissões e coleta de pareceres", 15),
        ("Diretoria de Plenário",
         "Inclusão em Ordem do Dia e deliberação", 5),
        ("Coordenadoria de Redação Oficial e Legislativa",
         "Redação final do autógrafo", 3),
        ("Presidência", "Promulgação ou encaminhamento à sanção", 5),
    ]
    # Rito de expediente sujeito a despacho do Presidente (indicações,
    # arts. 101-104; requerimentos dos arts. 108-110).
    ETAPAS_EXPEDIENTE = [
        ("Gabinetes de Vereadores", "Autoria e apresentação", 0),
        ("Coordenadoria da Secretaria-Geral", "Protocolo e autuação", 2),
        ("Presidência",
         "Despacho: encaminhamento ao Executivo ou à comissão", 5),
    ]
    # Rito das moções (deliberação em Plenário, arts. 105-106).
    ETAPAS_MOCAO = [
        ("Gabinetes de Vereadores", "Autoria e apresentação", 0),
        ("Coordenadoria da Secretaria-Geral", "Protocolo e autuação", 2),
        ("Diretoria de Plenário", "Inclusão em pauta e deliberação", 5),
    ]

    # (codigo, nome, dominio, [(unidade, acao, prazo_dias), ...])
    fluxos = [
        ("PL", "Projeto de Lei", "LEGISLATIVO", ETAPAS_PROJETO),
        ("PLC", "Projeto de Lei Complementar à Lei Orgânica",
         "LEGISLATIVO", ETAPAS_PROJETO),
        ("PELO", "Proposta de Emenda à Lei Orgânica",
         "LEGISLATIVO", ETAPAS_PROJETO),
        ("PDL", "Projeto de Decreto Legislativo",
         "LEGISLATIVO", ETAPAS_PROJETO),
        ("PR", "Projeto de Resolução", "LEGISLATIVO", ETAPAS_PROJETO),
        ("INDICACAO", "Indicação (arts. 101-104)",
         "LEGISLATIVO", ETAPAS_EXPEDIENTE),
        ("REQUERIMENTO", "Requerimento (arts. 107-113)",
         "LEGISLATIVO", ETAPAS_EXPEDIENTE),
        ("MOCAO", "Moção (arts. 105-106)", "LEGISLATIVO", ETAPAS_MOCAO),
        ("COMPRA", "Contratação (Lei 14.133/2021)", "ADMINISTRATIVO", [
            ("Coordenadoria da Secretaria-Geral",
             "Protocolo e autuação do pedido", 2),
            ("Diretoria-Geral", "Autorização da despesa", 3),
            ("Coordenadoria de Material",
             "Termo de referência e pesquisa de preços", 10),
            ("Procuradoria-Geral", "Parecer jurídico prévio", 7),
            ("Comissão Permanente de Licitação",
             "Condução do certame licitatório", 30),
            ("Coordenadoria de Licitações e Contratos",
             "Homologação e formalização do contrato", 5),
            ("Coordenadoria de Contabilidade", "Empenho da despesa", 3),
            ("Coordenadoria de Publicações e Transparência",
             "Publicação do extrato", 2),
        ]),
    ]
    out("INSERT INTO tipo_processo (id, codigo, nome, dominio) VALUES")
    out(",\n".join(
        f"  ({i}, {_sql(cod)}, {_sql(nome)}, {_sql(dom)})"
        for i, (cod, nome, dom, _) in enumerate(fluxos, start=1)
    ) + ";")
    out("")

    etapa_rows = []
    for tp_id, (_, _, _, etapas) in enumerate(fluxos, start=1):
        for ordem, (unidade, acao, prazo) in enumerate(etapas, start=1):
            etapa_rows.append(
                f"  ({tp_id}, {ordem}, {_uid(unidade)}, {_sql(acao)}, "
                f"{_sql(prazo)}, 1)")
    out("INSERT INTO fluxo_etapa (tipo_processo_id, ordem, unidade_id, "
        "acao, prazo_dias, obrigatoria) VALUES")
    out(",\n".join(etapa_rows) + ";")
    out("")

    # Áreas por unidade (controle de acesso por setor). Setores mapeados +
    # os 29 gabinetes, que operam a área LEGISLATIVO.
    area_rows = []
    for nome, areas in UNIDADE_AREAS.items():
        for area in areas:
            area_rows.append(f"  ({_uid(nome)}, {_sql(area)})")
    for gid in gab_ids:
        area_rows.append(f"  ({gid}, {_sql('LEGISLATIVO')})")
    out("INSERT INTO unidade_area (unidade_id, area) VALUES")
    out(",\n".join(area_rows) + ";")
    out("")

    # Ações específicas por unidade (trava fina). Gabinetes só apresentam.
    acao_rows = []
    for nome, acoes in UNIDADE_ACOES.items():
        for acao in acoes:
            acao_rows.append(f"  ({_uid(nome)}, {_sql(acao)})")
    for gid in gab_ids:
        acao_rows.append(f"  ({gid}, {_sql('APRESENTAR_PROPOSICAO')})")
    out("INSERT INTO unidade_acao (unidade_id, acao) VALUES")
    out(",\n".join(acao_rows) + ";")
    out("")
    return "\n".join(linhas)


if __name__ == "__main__":
    print(gerar())
