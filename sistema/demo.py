"""Demonstração do banco do sistema: cria o schema em SQLite, aplica o seed
gerado do modelo de domínio e roda consultas de verificação.

Uso:
    python -m sistema.demo
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sistema.gerar_seed import gerar

RAIZ = Path(__file__).parent


def criar_banco(caminho: str = ":memory:") -> sqlite3.Connection:
    """Cria o banco com schema + seed e devolve a conexão."""
    conexao = sqlite3.connect(caminho)
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.executescript((RAIZ / "schema.sql").read_text())
    conexao.executescript(gerar())
    return conexao


def main() -> None:
    banco = criar_banco()
    consulta = banco.execute

    print("=" * 66)
    print("SISTEMA CMDC — verificação do banco (SQLite em memória)")
    print("=" * 66)

    (total_unidades,) = consulta("SELECT COUNT(*) FROM unidade").fetchone()
    print(f"Unidades administrativas..........: {total_unidades}")

    for tipo, qtd in consulta(
        "SELECT tipo, COUNT(*) FROM unidade GROUP BY tipo ORDER BY 2 DESC"
    ):
        print(f"  - {tipo:<16} {qtd}")

    (vagas, custo) = consulta(
        """SELECT SUM(c.quantidade_vagas),
                  SUM(c.quantidade_vagas * s.retribuicao_base)
           FROM cargo c JOIN simbolo s ON s.codigo = c.simbolo_codigo"""
    ).fetchone()
    print(f"\nVagas do Anexo I..................: {vagas}")
    print(f"Custo mensal máximo (retribuições): R$ {custo:,.2f}")

    print("\nVagas e custo por símbolo (top 5):")
    for cod, vagas, custo in consulta(
        """SELECT s.codigo, SUM(c.quantidade_vagas),
                  SUM(c.quantidade_vagas * s.retribuicao_base)
           FROM cargo c JOIN simbolo s ON s.codigo = c.simbolo_codigo
           GROUP BY s.codigo ORDER BY 3 DESC LIMIT 5"""
    ):
        print(f"  {cod:<8} {vagas:>4} vagas   R$ {custo:>12,.2f}")

    print("\nSimulação de folha — Diretor-Geral (DAS-8) com GAL a 150%:")
    (base,) = consulta(
        "SELECT retribuicao_base FROM simbolo WHERE codigo = 'DAS-8'"
    ).fetchone()
    (teto_gal,) = consulta(
        "SELECT percentual_max FROM rubrica WHERE codigo = 'GAL'"
    ).fetchone()
    gal = base * teto_gal / 100
    print(f"  VENC (símbolo DAS-8)......: R$ {base:>10,.2f}")
    print(f"  GAL até {teto_gal:.0f}% (art. 7º)...: R$ {gal:>10,.2f}")
    print(f"  Total bruto...............: R$ {base + gal:>10,.2f}")

    print("\nDirigentes com lotação padrão definida:")
    for denominacao, unidade in consulta(
        """SELECT c.denominacao, u.nome
           FROM cargo c JOIN unidade u ON u.id = c.unidade_lotacao_id
           ORDER BY c.id LIMIT 5"""
    ):
        print(f"  {denominacao:<42} → {unidade}")
    (com_lotacao,) = consulta(
        "SELECT COUNT(*) FROM cargo WHERE unidade_lotacao_id IS NOT NULL"
    ).fetchone()
    print(f"  ... ({com_lotacao} no total)")

    banco.close()


if __name__ == "__main__":
    main()
