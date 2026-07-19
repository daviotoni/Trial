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

O Anexo I da lei ("Cargos Isolados de Provimento em Comissão e Funções de
Confiança Gratificadas") está reproduzido em ANEXO_I: denominação,
retribuição-base (R$), símbolo e quantitativo. Símbolos FC-(N) indicam que
só existe a função de confiança, sem cargo em comissão correspondente
(nota do próprio anexo) — servidor efetivo designado, TipoCargo
FUNCAO_CONFIANCA; os demais são cargos em comissão.

Fontes: texto integral da lei (site oficial, https://www.cmdc.rj.gov.br/?p=30397)
e relatório em docs/pesquisa-estrutura-cmdc.md.
"""

from __future__ import annotations

from orgao.modelos import (
    BaseLegal,
    Cargo,
    Competencia,
    Esfera,
    NaturezaJuridica,
    Orgao,
    Poder,
    TipoCargo,
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

# Competência funcional de cada coordenadoria (2º grau). Descrições fiéis
# ao papel de cada setor; base normativa: Lei 3.525/2025. Coordenadorias
# não listadas recebem uma competência genérica de apoio administrativo.
COMPETENCIAS_COORDENADORIA = {
    "Coordenadoria de Apoio Legislativo":
        "Apoio ao processo legislativo e às sessões plenárias (art. 20)",
    "Coordenadoria de Assuntos de Plenário":
        "Suporte à ordem do dia e aos trabalhos de Plenário (art. 21)",
    "Coordenadoria de Atas e Projetos":
        "Elaboração de atas das sessões e autuação de projetos e "
        "proposições (art. 22)",
    "Coordenadoria de Avaliação e Acompanhamento de Compras":
        "Fiscalização e acompanhamento das aquisições e contratações "
        "(art. 23)",
    "Coordenadoria de Cerimonial e Comunicação Social":
        "Cerimonial, comunicação institucional e imprensa (art. 24)",
    "Coordenadoria de Contabilidade":
        "Escrituração contábil, empenho e execução orçamentária (art. 25)",
    "Coordenadoria de Documentação Histórica":
        "Guarda e preservação do acervo documental e histórico (art. 26)",
    "Coordenadoria de Finanças":
        "Gestão financeira, pagamentos e conciliação (art. 27)",
    "Coordenadoria de Licitações e Contratos":
        "Formalização e gestão de licitações e contratos, Lei 14.133/2021 "
        "(art. 28)",
    "Coordenadoria de Manutenção":
        "Manutenção predial e das instalações; serviços de copa, limpeza e "
        "reprografia (art. 29)",
    "Coordenadoria de Material":
        "Gestão de material e almoxarifado; termo de referência e pesquisa "
        "de preços (art. 30)",
    "Coordenadoria de Patrimônio":
        "Registro, controle e baixa dos bens patrimoniais (art. 31)",
    "Coordenadoria de Polícia Legislativa":
        "Segurança institucional, poder de polícia e fiscalização da "
        "vigilância (art. 32)",
    "Coordenadoria de Prevenção a Incêndio":
        "Prevenção e combate a incêndio e segurança predial (art. 33)",
    "Coordenadoria de Publicações e Transparência":
        "Publicação oficial dos atos e transparência ativa, LAI (art. 34)",
    "Coordenadoria de Redação Oficial e Legislativa":
        "Redação final de autógrafos, leis e atos normativos (art. 35)",
    "Coordenadoria de Recursos Humanos":
        "Gestão de pessoal: cadastro, provimento, lotação e vida funcional "
        "dos servidores (art. 36)",
    "Coordenadoria da Secretaria-Geral":
        "Protocolo-geral, autuação, numeração e tramitação de processos "
        "administrativos e legislativos (art. 37)",
    "Coordenadoria de Tecnologia da Informação e Comunicação":
        "Gestão dos sistemas e da infraestrutura de tecnologia da "
        "informação (art. 38)",
    "Diretoria Administrativa":
        "Coordenação dos serviços administrativos e auxiliares (art. 39)",
}

# Órgãos superiores (1º grau) e seus artigos de competência (arts. 11-19).
COMPETENCIAS_ORGAO_SUPERIOR = {
    "Consultoria-Geral Legislativa":
        "Consultoria e assessoramento técnico-legislativo (art. 11)",
    "Controladoria-Geral":
        "Controle interno, auditoria e fiscalização (art. 12)",
    "Diretoria da Escola do Legislativo":
        "Formação e capacitação legislativa (art. 13)",
    "Diretoria de Plenário":
        "Organização dos trabalhos e da ordem do dia do Plenário (art. 14)",
    "Superintendência-Geral":
        "Superintendência dos serviços administrativos (art. 16)",
    "Superintendência de Assuntos Estratégicos":
        "Planejamento e assuntos estratégicos (art. 17)",
    "Ouvidoria-Geral":
        "Ouvidoria: recebimento e encaminhamento de demandas (art. 18)",
    "Procuradoria-Geral":
        "Representação e consultoria jurídica da Câmara (art. 19)",
}

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

# Competência de cada serviço auxiliar (4º grau). Só o e-Social tem artigo
# próprio (art. 48); os demais aparecem nas competências de outros órgãos.
COMPETENCIAS_SERVICO_AUXILIAR = {
    "Departamento do e-Social":
        "Gestão, consolidação e envio das informações trabalhistas, "
        "previdenciárias e fiscais ao e-Social (art. 48)",
    "Serviços de Copa":
        "Serviços de copa e apoio, geridos pela Coordenadoria de Manutenção "
        "(art. 29, V)",
    "Manutenção Predial":
        "Manutenção predial e das instalações (art. 29)",
    "Telefonia":
        "Serviços de telefonia, sob supervisão da Diretoria-Geral "
        "(art. 15, VIII)",
    "Reprografia":
        "Reprografia; manutenção dos equipamentos pela Coordenadoria de "
        "Manutenção (art. 29, VIII)",
    "Limpeza":
        "Serviços de limpeza, coordenados pela Coordenadoria de Manutenção "
        "(art. 29, I, X e XI)",
    "Transporte":
        "Serviços de transporte, sob supervisão do Diretor Administrativo "
        "(art. 78, III)",
    "Vigilância Patrimonial":
        "Vigilância e segurança patrimonial, fiscalizada pela Polícia "
        "Legislativa (art. 32, II)",
}

# Comissões permanentes de apoio à administração (art. 45, §1º). Membros
# fazem jus a gratificação de 40% (art. 46, §2º).
COMISSOES_PERMANENTES_ADMINISTRATIVAS = [
    "Comissão Permanente de Licitação",
    "Comissão Permanente de Recebimento Definitivo de Obras, Serviços e Bens",
    "Comissão Permanente de Aplicação de Sanções",
    "Comissão Permanente de Proteção de Dados Pessoais",
    "Comissão Permanente de Atualização e Consolidação de Leis e Normas Municipais",
]

# Anexo I da Lei 3.525/2025: (denominação, retribuição-base R$, símbolo,
# quantidade). Símbolo FC-* = apenas função de confiança gratificada.
ANEXO_I = [
    ("Assessor de Assuntos Especiais", 15925, "DAS-8", 1),
    ("Controlador-Geral", 15925, "FC-1", 1),
    ("Diretor da Escola do Legislativo", 15925, "DAS-8", 1),
    ("Diretor-Geral", 15925, "DAS-8", 1),
    ("Diretor de Plenário", 15925, "DAS-8", 1),
    ("Consultor-Geral Legislativo", 15925, "DAS-8", 1),
    ("Consultor Especial das Comissões Técnicas", 15925, "DAS-8", 1),
    ("Procurador-Geral", 15925, "DAS-8", 1),
    ("Superintendente-Geral", 15925, "DAS-8", 1),
    ("Superintendente de Assuntos Estratégicos", 12250, "SAS-6", 1),
    ("Ouvidor-Geral", 6870, "CAE-1", 1),
    ("Secretário Legislativo", 10125, "SL-1", 29),
    ("Assessor de Mediação de Conflitos", 6870, "ASS-1", 1),
    ("Assessor Parlamentar I", 6870, "PAR-3", 96),
    ("Assessor Parlamentar II", 6870, "PAR-2", 96),
    ("Assistente do Cerimonial e Comunicação", 6870, "ASS-3", 1),
    ("Assistente do Presidente", 6870, "GAB-3", 4),
    ("Chefe de Gabinete", 6870, "GAB-1", 29),
    ("Assessor de Comissão Legislativa e Parlamentar", 6870, "ASS-1", 31),
    ("Assessor Parlamentar III", 6870, "PAR-1", 70),
    ("Coord. de Apoio Legislativo", 6870, "FC-2", 1),
    ("Coord. de Assuntos de Plenário", 6870, "FC-2", 1),
    ("Coord. de Atas e Projetos", 6870, "FC-2", 1),
    ("Coord. de Avaliação e Acompanhamento de Compras", 6870, "CAE-1", 1),
    ("Coord. de Contabilidade", 6870, "FC-2", 1),
    ("Coord. de Documentação Histórica", 6870, "CAE-1", 1),
    ("Coord. de Finanças", 6870, "CAE-1", 1),
    ("Coord. de Cerimonial e Comunicação Social", 6870, "CAE-1", 1),
    ("Coord. de Licitações e Contratos", 6870, "CAE-1", 1),
    ("Coord. de Manutenção", 6870, "FC-2", 1),
    ("Coord. de Material", 6870, "FC-2", 1),
    ("Coord. de Patrimônio", 6870, "FC-2", 1),
    ("Coord. de Polícia Legislativa", 6870, "FC-2", 1),
    ("Coord. de Prevenção a Incêndio", 6870, "FC-2", 1),
    ("Coord. de Publicações e Transparência", 6870, "CAE-1", 1),
    ("Coord. de Redação Oficial e Legislativa", 6870, "FC-2", 1),
    ("Coord. de Recursos Humanos", 6870, "CAE-1", 1),
    ("Coord. de Tecnologia da Informação e Comunicação", 6870, "FC-2", 1),
    ("Coord. da Secretaria-Geral", 6870, "FC-2", 1),
    ("Diretor Administrativo", 6870, "CAE-1", 1),
    ("Assistente das Comissões Permanentes", 4125, "ASS-5", 33),
    ("Assessor de Plenário", 4125, "ASS-6", 29),
    ("Assistente do 1º Secretário", 4125, "ASS-7", 1),
    ("Assistente do Diretor I", 6870, "ASS-8", 1),
    ("Assistente do Diretor II", 4125, "ASS-9", 1),
    ("Assistente de Gabinete I", 3000, "ASS-10", 90),
    ("Assistente de Gabinete II", 1560, "ASS-11", 70),
    ("Assessor de Coordenadoria", 6870, "ASS-12", 1),
    ("Assistente da Coordenadoria", 4125, "ASS-13", 1),
]

# Dirigente titular de cada unidade, conforme o Anexo I.
DIRIGENTES_POR_UNIDADE = {
    "Consultoria-Geral Legislativa": "Consultor-Geral Legislativo",
    "Controladoria-Geral": "Controlador-Geral",
    "Diretoria da Escola do Legislativo": "Diretor da Escola do Legislativo",
    "Diretoria de Plenário": "Diretor de Plenário",
    "Diretoria-Geral": "Diretor-Geral",
    "Ouvidoria-Geral": "Ouvidor-Geral",
    "Procuradoria-Geral": "Procurador-Geral",
    "Superintendência-Geral": "Superintendente-Geral",
    "Superintendência de Assuntos Estratégicos": "Superintendente de Assuntos Estratégicos",
    "Coordenadoria de Apoio Legislativo": "Coord. de Apoio Legislativo",
    "Coordenadoria de Assuntos de Plenário": "Coord. de Assuntos de Plenário",
    "Coordenadoria de Atas e Projetos": "Coord. de Atas e Projetos",
    "Coordenadoria de Avaliação e Acompanhamento de Compras":
        "Coord. de Avaliação e Acompanhamento de Compras",
    "Coordenadoria de Cerimonial e Comunicação Social":
        "Coord. de Cerimonial e Comunicação Social",
    "Coordenadoria de Contabilidade": "Coord. de Contabilidade",
    "Coordenadoria de Documentação Histórica": "Coord. de Documentação Histórica",
    "Coordenadoria de Finanças": "Coord. de Finanças",
    "Coordenadoria de Licitações e Contratos": "Coord. de Licitações e Contratos",
    "Coordenadoria de Manutenção": "Coord. de Manutenção",
    "Coordenadoria de Material": "Coord. de Material",
    "Coordenadoria de Patrimônio": "Coord. de Patrimônio",
    "Coordenadoria de Polícia Legislativa": "Coord. de Polícia Legislativa",
    "Coordenadoria de Prevenção a Incêndio": "Coord. de Prevenção a Incêndio",
    "Coordenadoria de Publicações e Transparência":
        "Coord. de Publicações e Transparência",
    "Coordenadoria de Redação Oficial e Legislativa":
        "Coord. de Redação Oficial e Legislativa",
    "Coordenadoria de Recursos Humanos": "Coord. de Recursos Humanos",
    "Coordenadoria de Tecnologia da Informação e Comunicação":
        "Coord. de Tecnologia da Informação e Comunicação",
    "Coordenadoria da Secretaria-Geral": "Coord. da Secretaria-Geral",
    "Diretoria Administrativa": "Diretor Administrativo",
}

_ANEXO_I_POR_NOME = {denominacao: (valor, simbolo, qtd)
                     for denominacao, valor, simbolo, qtd in ANEXO_I}


def eh_funcao_confianca(simbolo: str) -> bool:
    """FC-(N) indica que só há a função de confiança (nota do Anexo I)."""
    return simbolo.startswith("FC-")


def total_vagas_anexo_i() -> int:
    return sum(qtd for _, _, _, qtd in ANEXO_I)


def total_funcoes_gratificadas() -> int:
    return sum(qtd for _, _, simbolo, qtd in ANEXO_I if eh_funcao_confianca(simbolo))


def total_cargos_comissionados() -> int:
    return total_vagas_anexo_i() - total_funcoes_gratificadas()


def _cargo_dirigente(unidade: UnidadeAdministrativa) -> None:
    """Anexa à unidade o cargo de seu dirigente titular, conforme o Anexo I."""
    denominacao = DIRIGENTES_POR_UNIDADE.get(unidade.nome)
    if denominacao is None:
        return
    _, simbolo, _ = _ANEXO_I_POR_NOME[denominacao]
    tipo = (TipoCargo.FUNCAO_CONFIANCA if eh_funcao_confianca(simbolo)
            else TipoCargo.COMISSAO)
    unidade.adicionar_cargo(
        Cargo(f"{denominacao} ({simbolo})", tipo, nivel_hierarquico=3)
    )


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
        descricao = COMPETENCIAS_ORGAO_SUPERIOR.get(
            nome, "Órgão superior de direção e assessoramento técnico")
        unidade.adicionar_competencia(Competencia(descricao, LEI_3525))
        _cargo_dirigente(unidade)

    # Comissões permanentes de apoio à administração (art. 45, §1º).
    for nome in COMISSOES_PERMANENTES_ADMINISTRATIVAS:
        comissao = mesa.adicionar_subunidade(UnidadeAdministrativa(nome=nome))
        comissao.adicionar_competencia(
            Competencia(
                "Órgão colegiado de apoio à administração; membros com "
                "gratificação de 40% (art. 46, §2º)",
                LEI_3525,
            )
        )

    # Diretoria-Geral: órgão central de apoio administrativo (art. 15).
    diretoria_geral = presidencia.adicionar_subunidade(
        UnidadeAdministrativa(nome="Diretoria-Geral", sigla="DG")
    )
    diretoria_geral.adicionar_competencia(
        Competencia(
            "Órgão central de apoio administrativo, diretamente subordinado "
            "à Presidência; supervisiona telefonia e transporte (art. 15)",
            LEI_3525,
        )
    )
    for nome in COORDENADORIAS:
        unidade = diretoria_geral.adicionar_subunidade(
            UnidadeAdministrativa(nome=nome)
        )
        descricao = COMPETENCIAS_COORDENADORIA.get(
            nome, "Coordenadoria de apoio administrativo (2º grau)")
        unidade.adicionar_competencia(Competencia(descricao, LEI_3525))
        _cargo_dirigente(unidade)
    _cargo_dirigente(diretoria_geral)

    # Serviços auxiliares (4º grau) — sob a Diretoria Administrativa.
    diretoria_admin = next(
        u for u in diretoria_geral.subunidades if u.nome == "Diretoria Administrativa"
    )
    for nome in SERVICOS_AUXILIARES:
        servico = diretoria_admin.adicionar_subunidade(
            UnidadeAdministrativa(nome=nome))
        descricao = COMPETENCIAS_SERVICO_AUXILIAR.get(
            nome, "Serviço auxiliar de apoio logístico (Diretoria Administrativa)")
        servico.adicionar_competencia(Competencia(descricao, LEI_3525))

    return cmdc


if __name__ == "__main__":
    from orgao.visualizar import ficha_orgao

    print(ficha_orgao(construir_cmdc()))
