"""Exemplo concreto: monta a estrutura de um órgão público fictício.

Modela uma "Secretaria Municipal de Educação" — órgão da Administração
Direta, esfera municipal, Poder Executivo — com uma hierarquia realista de
unidades, competências e cargos. Os números de lei/decreto são ilustrativos.

Use `construir_secretaria_educacao()` para obter um objeto `Orgao` pronto.
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
    Servidor,
    TipoCargo,
    UnidadeAdministrativa,
)


def construir_secretaria_educacao() -> Orgao:
    lei_criacao = BaseLegal(
        especie="Lei Municipal",
        numero="4.210/2013",
        ementa="Cria a Secretaria Municipal de Educação e define sua estrutura",
    )

    orgao = Orgao(
        nome="Secretaria Municipal de Educação",
        sigla="SME",
        esfera=Esfera.MUNICIPAL,
        poder=Poder.EXECUTIVO,
        natureza_juridica=NaturezaJuridica.ADMINISTRACAO_DIRETA,
        base_legal_criacao=lei_criacao,
        finalidade=(
            "Formular e executar a política municipal de educação, "
            "gerindo a rede pública de ensino."
        ),
    )

    # ------------------------------------------------------------------
    # Unidade de topo: Gabinete do Secretário
    # ------------------------------------------------------------------
    gabinete = UnidadeAdministrativa(nome="Gabinete do Secretário", sigla="GAB")
    gabinete.adicionar_competencia(
        Competencia("Dirigir superiormente a Secretaria e representá-la", lei_criacao)
    )
    gabinete.adicionar_cargo(
        Cargo(
            "Secretário Municipal de Educação",
            TipoCargo.COMISSAO,
            nivel_hierarquico=5,
            ocupante=Servidor("Ana Ribeiro", matricula="0001"),
        )
    )
    gabinete.adicionar_cargo(
        Cargo("Chefe de Gabinete", TipoCargo.COMISSAO, nivel_hierarquico=4)
    )
    orgao.definir_topo(gabinete)

    # ------------------------------------------------------------------
    # Diretorias (2º nível)
    # ------------------------------------------------------------------
    dir_ensino = gabinete.adicionar_subunidade(
        UnidadeAdministrativa(nome="Diretoria de Ensino", sigla="DE")
    )
    dir_ensino.adicionar_competencia(
        Competencia("Coordenar a política pedagógica da rede municipal")
    )
    dir_ensino.adicionar_cargo(
        Cargo(
            "Diretor de Ensino",
            TipoCargo.COMISSAO,
            nivel_hierarquico=4,
            ocupante=Servidor("Carlos Menezes", matricula="0007"),
        )
    )

    dir_admin = gabinete.adicionar_subunidade(
        UnidadeAdministrativa(nome="Diretoria Administrativa e Financeira", sigla="DAF")
    )
    dir_admin.adicionar_competencia(
        Competencia("Gerir orçamento, contratos, patrimônio e recursos humanos")
    )
    dir_admin.adicionar_cargo(
        Cargo("Diretor Administrativo e Financeiro", TipoCargo.COMISSAO, nivel_hierarquico=4)
    )

    # ------------------------------------------------------------------
    # Coordenações / Divisões (3º nível)
    # ------------------------------------------------------------------
    coord_ei = dir_ensino.adicionar_subunidade(
        UnidadeAdministrativa(nome="Coordenação de Educação Infantil", sigla="CEI")
    )
    coord_ei.adicionar_competencia(
        Competencia("Acompanhar creches e pré-escolas da rede")
    )
    coord_ei.adicionar_cargo(
        Cargo(
            "Coordenador Pedagógico",
            TipoCargo.EFETIVO,
            nivel_hierarquico=2,
            ocupante=Servidor("Fernanda Lopes", matricula="0142"),
        )
    )

    coord_ef = dir_ensino.adicionar_subunidade(
        UnidadeAdministrativa(nome="Coordenação de Ensino Fundamental", sigla="CEF")
    )
    coord_ef.adicionar_competencia(
        Competencia("Acompanhar as escolas de ensino fundamental")
    )
    coord_ef.adicionar_cargo(
        Cargo("Coordenador Pedagógico", TipoCargo.EFETIVO, nivel_hierarquico=2)
    )

    div_orcamento = dir_admin.adicionar_subunidade(
        UnidadeAdministrativa(nome="Divisão de Orçamento e Finanças", sigla="DOF")
    )
    div_orcamento.adicionar_competencia(
        Competencia("Executar a despesa e acompanhar o orçamento da pasta")
    )
    div_orcamento.adicionar_cargo(
        Cargo(
            "Chefe de Divisão",
            TipoCargo.FUNCAO_CONFIANCA,
            nivel_hierarquico=2,
            ocupante=Servidor("Roberto Alves", matricula="0233"),
        )
    )

    div_rh = dir_admin.adicionar_subunidade(
        UnidadeAdministrativa(nome="Divisão de Recursos Humanos", sigla="DRH")
    )
    div_rh.adicionar_competencia(
        Competencia("Gerir a vida funcional dos servidores da Secretaria")
    )
    div_rh.adicionar_cargo(
        Cargo("Chefe de Divisão", TipoCargo.FUNCAO_CONFIANCA, nivel_hierarquico=2)
    )

    return orgao


if __name__ == "__main__":
    from orgao.visualizar import detalhar_competencias, ficha_orgao

    sme = construir_secretaria_educacao()
    print(ficha_orgao(sme))
    print()
    print("DETALHAMENTO POR UNIDADE")
    print("-" * 68)
    print(detalhar_competencias(sme))
