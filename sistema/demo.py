"""Demonstração do banco do sistema: cria o schema em SQLite, aplica o seed
gerado do modelo de domínio e roda consultas de verificação.

Uso:
    python -m sistema.demo
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from sistema.gerar_seed import gerar

RAIZ = Path(__file__).parent


def criar_banco(caminho: str = ":memory:",
                multithread: bool = False):
    """Cria o banco com schema + seed e devolve a conexão.

    `caminho` pode ser um arquivo SQLite (local/testes) ou uma URL
    postgres:// (produção — ex.: Supabase), atendida pelo adaptador em
    sistema/bancodados. Com multithread=True a conexão pode ser usada por
    várias threads — o chamador deve serializar os acessos (a API usa um
    lock). Em ambos os casos o bootstrap é idempotente: schema + seed só
    entram se o banco ainda estiver vazio.
    """
    from sistema import bancodados

    if bancodados.eh_url_postgres(caminho):
        try:
            conexao = bancodados.ConexaoPostgres(caminho)
            tem_schema = conexao.execute(
                "SELECT to_regclass('public.unidade')").fetchone()[0]
            if not tem_schema:
                conexao.executescript(bancodados.schema_para_postgres(
                    (RAIZ / "schema.sql").read_text()))
            # Seed em etapa própria: cobre banco cujo schema foi aplicado por
            # fora (ex.: migração no Supabase) mas ainda sem dados.
            vazio = conexao.execute(
                "SELECT COUNT(*) FROM unidade").fetchone()[0] == 0
            if vazio:
                conexao.executescript(gerar())
                conexao.executescript(bancodados.SETVAL_POS_SEED)
            conexao.commit()
            return conexao
        except Exception as erro:
            # DATABASE_URL definida mas o Postgres não respondeu (senha
            # errada, host da conexão direta — só IPv6 — em vez do pooler,
            # porta incorreta, banco hibernado...). Em vez de derrubar o
            # serviço inteiro (deploy falho, site fora do ar), o app segue
            # de pé num SQLite efêmero e a rota /saude denuncia o problema
            # (backend=sqlite, persistente=false). O log abaixo aparece no
            # painel do Render para orientar a correção da URL.
            print("=" * 70, flush=True)
            print("ATENCAO: falha ao conectar no PostgreSQL da DATABASE_URL.",
                  flush=True)
            print(f"  Erro: {type(erro).__name__}: {erro}", flush=True)
            print("  O app vai rodar em SQLite EFEMERO (dados NAO persistem).",
                  flush=True)
            print("  Verifique a DATABASE_URL: use o Session pooler do "
                  "Supabase", flush=True)
            print("  (porta 5432, host *.pooler.supabase.com) e a senha "
                  "correta.", flush=True)
            print("  Confira o backend em /saude apos o proximo deploy.",
                  flush=True)
            print("=" * 70, flush=True)
            caminho = os.environ.get("CMDC_DB", "cmdc.db")

    conexao = sqlite3.connect(caminho, check_same_thread=not multithread)
    conexao.execute("PRAGMA foreign_keys = ON")
    ja_iniciado = conexao.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'unidade'"
    ).fetchone()
    if not ja_iniciado:
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
