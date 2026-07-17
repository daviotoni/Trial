"""Funções para exibir a estrutura de um órgão de forma legível."""

from __future__ import annotations

from orgao.modelos import Orgao, UnidadeAdministrativa


def arvore_unidade(unidade: UnidadeAdministrativa) -> str:
    """Devolve uma representação em árvore (estilo `tree`) da unidade."""
    linhas: list[str] = [str(unidade)]

    filhos = unidade.subunidades
    for i, filho in enumerate(filhos):
        ultimo = i == len(filhos) - 1
        conector = "└── " if ultimo else "├── "
        extensao = "    " if ultimo else "│   "
        sub_linhas = arvore_unidade(filho).split("\n")
        linhas.append(conector + sub_linhas[0])
        linhas.extend(extensao + linha for linha in sub_linhas[1:])
    return "\n".join(linhas)


def ficha_orgao(orgao: Orgao) -> str:
    """Monta uma ficha textual completa do órgão para leitura no terminal."""
    linhas: list[str] = []
    linhas.append("=" * 68)
    linhas.append(f"ÓRGÃO: {orgao.nome} ({orgao.sigla})")
    linhas.append("=" * 68)
    linhas.append(f"Esfera............: {orgao.esfera.value}")
    linhas.append(f"Poder.............: {orgao.poder.value}")
    linhas.append(f"Natureza jurídica.: {orgao.natureza_juridica.value}")
    if orgao.base_legal_criacao:
        linhas.append(f"Base legal........: {orgao.base_legal_criacao}")
    if orgao.finalidade:
        linhas.append(f"Finalidade........: {orgao.finalidade}")
    linhas.append("")
    linhas.append(f"Unidades..........: {orgao.total_unidades()}")
    linhas.append(f"Cargos............: {orgao.total_cargos()} "
                  f"({len(orgao.cargos_vagos())} vago(s))")
    linhas.append("")
    linhas.append("ESTRUTURA ORGANIZACIONAL")
    linhas.append("-" * 68)
    if orgao.unidade_topo:
        linhas.append(arvore_unidade(orgao.unidade_topo))
    else:
        linhas.append("(sem unidade de topo definida)")
    return "\n".join(linhas)


def detalhar_competencias(orgao: Orgao) -> str:
    """Lista, por unidade, as competências e cargos cadastrados."""
    linhas: list[str] = []
    for nivel, unidade in orgao.percorrer():
        recuo = "  " * nivel
        linhas.append(f"{recuo}▸ {unidade}")
        for comp in unidade.competencias:
            linhas.append(f"{recuo}    • {comp}")
        for cargo in unidade.cargos:
            linhas.append(f"{recuo}    ⋅ {cargo}")
    return "\n".join(linhas)
