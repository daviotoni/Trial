"""Estrutura administrativa real: Câmara Municipal de Duque de Caxias (CMDC).

Montada conforme a Lei nº 3.525, de 29/08/2025 ("Dispõe sobre a organização
administrativa da Câmara Municipal de Duque de Caxias"), que estrutura a Casa
em quatro graus funcionais:

- 1º grau: Órgãos Superiores de Direção e Assessoramento Técnico;
- 2º grau: Órgãos de Coordenação Técnico-Administrativa;
- 3º grau: Órgãos de Assessoramento Parlamentar (gabinetes);
- 4º grau: Serviços Auxiliares.

Presidência e Mesa Diretora exercem comando político-institucional e não
integram a hierarquia técnico-administrativa (art. 2º, parágrafo único); a
Diretoria-Geral é o órgão central de apoio administrativo, diretamente
subordinada à Presidência (art. 15).

Fontes: texto da lei no site oficial (https://www.cmdc.rj.gov.br/?p=30397) e
relatório em docs/pesquisa-estrutura-cmdc.md. Os quantitativos de cargos
comissionados constam do Anexo I da lei, não reproduzido na publicação
online — por isso este módulo modela unidades e competências, não o quadro
de cargos completo.
"""

from __future__ import annotations

from orgao.modelos import (
    BaseLegal,
    Competencia,
    Esfera,
    NaturezaJuridica,
    Orgao,
    Poder,
    UnidadeAdministrativa,
)

LEI_3525 = BaseLegal(
    especie="Lei",
    numero="3.525/2025",
    ementa=(
        "Dispõe sobre a organização administrativa da Câmara Municipal de "
        "Duque de Caxias, e dá outras providências"
    ),
)

ESTATUTO_SERVIDORES = BaseLegal(
    especie="Lei Municipal",
    numero="1.506/2000",
    ementa="Estatuto dos Servidores Públicos do Município de Duque de Caxias",
)

# 1º grau — Órgãos Superiores de Direção e Assessoramento Técnico.
# A Diretoria-Geral é tratada à parte por ser o órgão central (art. 15).
ORGAOS_SUPERIORES = [
    ("Consultoria-Geral Legislativa", "CGL"),
    ("Controladoria-Geral", "CG"),
    ("Diretoria da Escola do Legislativo", "DEL"),
    ("Diretoria de Plenário", "DP"),
    ("Ouvidoria-Geral", "OG"),
    ("Procuradoria-Geral", "PG"),
    ("Superintendência-Geral", "SG"),
    ("Superintendência de Assuntos Estratégicos", "SAE"),
]

# 2º grau — Órgãos de Coordenação Técnico-Administrativa, subordinados à
# Diretoria-Geral.
COORDENADORIAS = [
    "Coordenadoria de Apoio Legislativo",
    "Coordenadoria de Assuntos de Plenário",
    "Coordenadoria de Atas e Projetos",
    "Coordenadoria de Avaliação e Acompanhamento de Compras",
    "Coordenadoria de Cerimonial e Comunicação Social",
    "Coordenadoria de Contabilidade",
    "Coordenadoria de Documentação Histórica",
    "Coordenadoria de Finanças",
    "Coordenadoria de Licitações e Contratos",
    "Coordenadoria de Manutenção",
    "Coordenadoria de Material",
    "Coordenadoria de Patrimônio",
    "Coordenadoria de Polícia Legislativa",
    "Coordenadoria de Prevenção a Incêndio",
    "Coordenadoria de Publicações e Transparência",
    "Coordenadoria de Redação Oficial e Legislativa",
    "Coordenadoria de Recursos Humanos",
    "Coordenadoria de Tecnologia da Informação e Comunicação",
    "Coordenadoria da Secretaria-Geral",
    "Diretoria Administrativa",
]

# 3º grau — Órgãos de Assessoramento Parlamentar, lotados nos gabinetes
# (art. 3º, §2º).
ASSESSORAMENTO_PARLAMENTAR = [
    "Assessoria de Gabinete Parlamentar",
    "Assessoria Especial da Presidência",
    "Assessores Parlamentares",
    "Assistência às Comissões Permanentes",
]

# 4º grau — Serviços Auxiliares.
SERVICOS_AUXILIARES = [
    "Departamento do e-Social",
    "Serviços de Copa",
    "Manutenção Predial",
    "Telefonia",
    "Reprografia",
    "Limpeza",
    "Transporte",
    "Vigilância Patrimonial",
]


def construir_cmdc() -> Orgao:
    """Monta a CMDC conforme a Lei 3.525/2025."""
    cmdc = Orgao(
        nome="Câmara Municipal de Duque de Caxias",
        sigla="CMDC",
        esfera=Esfera.MUNICIPAL,
        poder=Poder.LEGISLATIVO,
        natureza_juridica=NaturezaJuridica.ADMINISTRACAO_DIRETA,
        base_legal_criacao=LEI_3525,
        finalidade=(
            "Exercer a função legislativa municipal e fiscalizar a "
            "administração do Município de Duque de Caxias."
        ),
    )

    mesa = cmdc.definir_topo(
        UnidadeAdministrativa(nome="Mesa Diretora", sigla="MESA")
    )
    mesa.adicionar_competencia(
        Competencia(
            "Comando político-institucional da Casa; não integra a "
            "hierarquia técnico-administrativa (art. 2º, parágrafo único)",
            LEI_3525,
        )
    )

    presidencia = mesa.adicionar_subunidade(
        UnidadeAdministrativa(nome="Presidência", sigla="PRES")
    )
    presidencia.adicionar_competencia(
        Competencia("Dirigir os trabalhos legislativos e administrativos", LEI_3525)
    )

    gabinetes = mesa.adicionar_subunidade(
        UnidadeAdministrativa(nome="Gabinetes de Vereadores", sigla="GAB")
    )
    for nome in ASSESSORAMENTO_PARLAMENTAR:
        unidade = gabinetes.adicionar_subunidade(UnidadeAdministrativa(nome=nome))
        unidade.adicionar_competencia(
            Competencia(
                "Assessoramento parlamentar (3º grau); provimento por "
                "indicação dos titulares (art. 3º, §2º)",
                LEI_3525,
            )
        )

    # Órgãos superiores (1º grau) — vinculados à Presidência.
    for nome, sigla in ORGAOS_SUPERIORES:
        unidade = presidencia.adicionar_subunidade(
            UnidadeAdministrativa(nome=nome, sigla=sigla)
        )
        unidade.adicionar_competencia(
            Competencia("Órgão superior de direção e assessoramento técnico", LEI_3525)
        )

    # Diretoria-Geral: órgão central de apoio administrativo (art. 15).
    diretoria_geral = presidencia.adicionar_subunidade(
        UnidadeAdministrativa(nome="Diretoria-Geral", sigla="DG")
    )
    diretoria_geral.adicionar_competencia(
        Competencia(
            "Órgão central de apoio administrativo, diretamente subordinado "
            "à Presidência (art. 15)",
            LEI_3525,
        )
    )
    for nome in COORDENADORIAS:
        diretoria_geral.adicionar_subunidade(UnidadeAdministrativa(nome=nome))

    # Serviços auxiliares (4º grau) — sob a Diretoria Administrativa.
    diretoria_admin = next(
        u for u in diretoria_geral.subunidades if u.nome == "Diretoria Administrativa"
    )
    for nome in SERVICOS_AUXILIARES:
        diretoria_admin.adicionar_subunidade(UnidadeAdministrativa(nome=nome))

    return cmdc


if __name__ == "__main__":
    from orgao.visualizar import ficha_orgao

    print(ficha_orgao(construir_cmdc()))
