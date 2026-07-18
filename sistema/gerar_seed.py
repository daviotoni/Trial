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
    pilha = [(cmdc.unidade_topo, None)]
    proximo = 1
    while pilha:
        unidade, pai_db = pilha.pop(0)
        ids[id(unidade)] = proximo
        tipo, grau = _tipo_unidade(unidade.nome)
        valores.append(
            f"  ({proximo}, {_sql(unidade.nome)}, {_sql(unidade.sigla or None)}, "
            f"{_sql(grau)}, {_sql(tipo)}, {_sql(pai_db)}, 1, {_sql(VIGENCIA)})"
        )
        for sub in unidade.subunidades:
            pilha.append((sub, proximo))
        proximo += 1
    out("INSERT INTO unidade (id, nome, sigla, grau, tipo, unidade_pai_id, "
        "norma_id, vigente_desde) VALUES")
    out(",\n".join(valores) + ";")
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
    return "\n".join(linhas)


if __name__ == "__main__":
    print(gerar())
