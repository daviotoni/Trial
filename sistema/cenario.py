"""Estudo de caso executável: um mês de funcionamento da CMDC no sistema.

Cadastra servidores, faz nomeações (validando as regras da Lei 3.525/2025),
designa comissão de licitação, autua e tramita um processo de contratação e
calcula a folha da competência 2025-09 (primeira sob a lei nova).

Uso:
    python -m sistema.cenario
"""

from __future__ import annotations

from sistema.demo import criar_banco
from sistema import servicos


def montar_cenario(banco):
    """Popula o banco com um cenário mínimo e devolve dados úteis."""
    consulta = banco.execute

    def unidade(nome):
        return consulta("SELECT id FROM unidade WHERE nome = ?", (nome,)).fetchone()[0]

    def cargo(denominacao):
        return consulta(
            "SELECT id FROM cargo WHERE denominacao = ?", (denominacao,)
        ).fetchone()[0]

    # Cargos efetivos (fora do Anexo I — quadro de carreira, concurso 2012).
    consulta(
        "INSERT INTO cargo (denominacao, tipo, quantidade_vagas, norma_id) "
        "VALUES ('Técnico Legislativo', 'EFETIVO', 20, NULL)"
    )

    servidores = [
        # (nome, matrícula, vínculo, admissão, vencimento efetivo)
        ("Marcos Vidal", "2025001", "COMISSIONADO", "2025-09-01", None),
        ("Helena Duarte", "2012034", "EFETIVO", "2012-08-01", 5200.00),
        ("Paulo Sales", "2012051", "EFETIVO", "2012-08-01", 5200.00),
    ]
    for nome, matricula, vinculo, admissao, venc in servidores:
        consulta(
            "INSERT INTO servidor (nome, matricula, vinculo, data_admissao, "
            "vencimento_base) VALUES (?, ?, ?, ?, ?)",
            (nome, matricula, vinculo, admissao, venc),
        )

    def servidor(nome):
        return consulta("SELECT id FROM servidor WHERE nome = ?", (nome,)).fetchone()[0]

    # Nomeações (Portaria do Presidente, art. 3º).
    servicos.nomear(
        banco, servidor("Marcos Vidal"), cargo("Diretor-Geral"),
        unidade("Diretoria-Geral"), "Portaria nº 001/2025", "2025-09-01",
    )
    servicos.nomear(
        banco, servidor("Helena Duarte"), cargo("Coord. de Licitações e Contratos"),
        unidade("Coordenadoria de Licitações e Contratos"),
        "Portaria nº 002/2025", "2025-09-01",
    )
    servicos.nomear(
        banco, servidor("Paulo Sales"), cargo("Técnico Legislativo"),
        unidade("Coordenadoria de Apoio Legislativo"),
        "Concurso 001/2012", "2025-09-01",
    )

    # Comissão Permanente de Licitação (art. 45) — gratificação de 40% (art. 46).
    consulta(
        "INSERT INTO designacao_comissao (servidor_id, comissao_unidade_id, "
        "funcao, base_incidencia, data_inicio) VALUES (?, ?, ?, ?, ?)",
        (servidor("Helena Duarte"),
         unidade("Comissão Permanente de Licitação"),
         "Presidente", "CARGO_OU_FUNCAO_EXERCIDA", "2025-09-01"),
    )

    # Processo de contratação: protocolo → tramitação.
    processo_id, numero = servicos.autuar_processo(
        banco, "ADMINISTRATIVO",
        "Contratação de manutenção predial (Lei 14.133/2021)",
        unidade("Coordenadoria de Manutenção"), "2025-09-02",
    )
    servicos.tramitar(
        banco, processo_id, unidade("Coordenadoria de Avaliação e Acompanhamento de Compras"),
        "Para pesquisa de preços", "2025-09-03",
    )
    servicos.tramitar(
        banco, processo_id, unidade("Coordenadoria de Licitações e Contratos"),
        "Instaurar procedimento licitatório", "2025-09-10",
    )
    servicos.tramitar(
        banco, processo_id, unidade("Diretoria-Geral"),
        "Para autorização da despesa", "2025-09-15",
    )

    return {"processo": (processo_id, numero)}


def main() -> None:
    banco = criar_banco()
    dados = montar_cenario(banco)

    print("=" * 66)
    print("CENÁRIO: primeiro mês sob a Lei 3.525/2025 (competência 2025-09)")
    print("=" * 66)

    processo_id, numero = dados["processo"]
    print(f"\nProcesso {numero} — trilha de tramitação:")
    for origem, destino, despacho in banco.execute(
        """SELECT o.nome, d.nome, t.despacho FROM tramitacao t
           JOIN unidade o ON o.id = t.unidade_origem_id
           JOIN unidade d ON d.id = t.unidade_destino_id
           WHERE t.processo_id = ? ORDER BY t.id""",
        (processo_id,),
    ):
        print(f"  {origem}\n    → {destino}  ({despacho})")

    folha_id = servicos.calcular_folha(banco, "2025-09", percentual_gal=100)
    print("\nFolha 2025-09 (GAL parametrizada em 100%):")
    for nome, rubrica, base, perc, valor in banco.execute(
        """SELECT s.nome, fi.rubrica_codigo, fi.base_calculo, fi.percentual,
                  fi.valor
           FROM folha_item fi JOIN servidor s ON s.id = fi.servidor_id
           WHERE fi.folha_id = ? ORDER BY s.nome, fi.id""",
        (folha_id,),
    ):
        perc_txt = f"{perc:.0f}%" if perc else "  —"
        print(f"  {nome:<16} {rubrica:<9} base {base:>9,.2f}  {perc_txt:>5}"
              f"  = R$ {valor:>10,.2f}")
    print(f"  {'TOTAL':<16} {'':<9} {'':>21}"
          f"  = R$ {servicos.total_folha(banco, folha_id):>10,.2f}")

    print("\nValidações de regra (esperado: bloqueio):")
    try:
        servicos.nomear(banco, 1, 4, 1, "Portaria X", "2025-10-01")
    except servicos.RegraViolada as erro:
        print(f"  ✗ 2ª nomeação p/ Diretor-Geral: {erro}")

    banco.commit()
    banco.close()


if __name__ == "__main__":
    main()
