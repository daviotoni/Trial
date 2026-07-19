"""Módulo de fluxo processual: tipos de processo, ritos e competências.

Traduz a Lei 3.525/2025 em regra operacional. Cada **tipo de processo**
tem um **rito** — a sequência de setores (unidades) por onde ele deve
passar, com a ação de cada um e um prazo (SLA) sugerido. O rito é dado
configurável, não fica fixo no código: dá para criar tipos e etapas novas
sem alterar o programa.

A ideia central da visão do sistema — "cada setor faz só o que lhe cabe e
remete ao setor seguinte" — se apoia em três consultas:

- `competencias_da_unidade`: o que a lei atribui àquela unidade;
- `proxima_etapa`: para onde o processo deve seguir a partir de onde está;
- `tramitar_pelo_fluxo`: encaminha automaticamente à próxima etapa,
  já calculando o prazo pela etapa.

Uso demonstrativo:
    python -m sistema.fluxo
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from sistema import servicos
from sistema.servicos import RegraViolada


# ------------------------------------------------------------------
# Competências
# ------------------------------------------------------------------

def competencias_da_unidade(banco: sqlite3.Connection, unidade_id: int) -> list[dict]:
    """Competências legais atribuídas à unidade (Lei 3.525/2025)."""
    return [
        {"id": cid, "descricao": descricao, "base_legal": base}
        for cid, descricao, base in banco.execute(
            "SELECT id, descricao, base_legal FROM competencia "
            "WHERE unidade_id = ? ORDER BY id", (unidade_id,),
        )
    ]


def unidade_tem_competencia(banco: sqlite3.Connection, unidade_id: int) -> bool:
    """A unidade tem ao menos uma competência legal cadastrada?"""
    return banco.execute(
        "SELECT COUNT(*) FROM competencia WHERE unidade_id = ?", (unidade_id,)
    ).fetchone()[0] > 0


# ------------------------------------------------------------------
# Tipos de processo e etapas do rito
# ------------------------------------------------------------------

def _tipo_id(banco: sqlite3.Connection, tipo: str | int) -> int:
    if isinstance(tipo, int):
        linha = banco.execute(
            "SELECT id FROM tipo_processo WHERE id = ?", (tipo,)).fetchone()
    else:
        linha = banco.execute(
            "SELECT id FROM tipo_processo WHERE codigo = ?", (tipo,)).fetchone()
    if linha is None:
        raise RegraViolada("tipo de processo inexistente")
    return linha[0]


def definir_tipo(banco: sqlite3.Connection, codigo: str, nome: str,
                 dominio: str) -> int:
    """Cria um tipo de processo (rito). Devolve o id."""
    if dominio not in ("LEGISLATIVO", "ADMINISTRATIVO"):
        raise RegraViolada("domínio deve ser LEGISLATIVO ou ADMINISTRATIVO")
    return banco.execute(
        "INSERT INTO tipo_processo (codigo, nome, dominio) VALUES (?, ?, ?)",
        (codigo, nome, dominio),
    ).lastrowid


def adicionar_etapa(banco: sqlite3.Connection, tipo: str | int,
                    unidade_id: int, acao: str, prazo_dias: int | None = None,
                    obrigatoria: bool = True) -> int:
    """Anexa uma etapa ao fim do rito do tipo. Devolve o id da etapa."""
    tipo_id = _tipo_id(banco, tipo)
    (ordem,) = banco.execute(
        "SELECT COALESCE(MAX(ordem), 0) + 1 FROM fluxo_etapa "
        "WHERE tipo_processo_id = ?", (tipo_id,),
    ).fetchone()
    return banco.execute(
        "INSERT INTO fluxo_etapa (tipo_processo_id, ordem, unidade_id, "
        "acao, prazo_dias, obrigatoria) VALUES (?, ?, ?, ?, ?, ?)",
        (tipo_id, ordem, unidade_id, acao, prazo_dias, 1 if obrigatoria else 0),
    ).lastrowid


def etapas(banco: sqlite3.Connection, tipo: str | int) -> list[dict]:
    """Rito completo do tipo: etapas ordenadas, com a unidade de cada uma."""
    tipo_id = _tipo_id(banco, tipo)
    return [
        {"ordem": ordem, "unidade_id": uid, "unidade": nome,
         "acao": acao, "prazo_dias": prazo, "obrigatoria": bool(obr)}
        for ordem, uid, nome, acao, prazo, obr in banco.execute(
            """SELECT e.ordem, e.unidade_id, u.nome, e.acao,
                      e.prazo_dias, e.obrigatoria
                 FROM fluxo_etapa e JOIN unidade u ON u.id = e.unidade_id
                WHERE e.tipo_processo_id = ? ORDER BY e.ordem""", (tipo_id,),
        )
    ]


# ------------------------------------------------------------------
# Vínculo processo ↔ rito e navegação
# ------------------------------------------------------------------

def vincular_tipo(banco: sqlite3.Connection, processo_id: int,
                  tipo: str | int) -> None:
    """Associa o processo a um tipo/rito configurado."""
    tipo_id = _tipo_id(banco, tipo)
    if banco.execute(
        "SELECT id FROM processo WHERE id = ?", (processo_id,)
    ).fetchone() is None:
        raise RegraViolada("processo inexistente")
    banco.execute(
        "UPDATE processo SET tipo_processo_id = ? WHERE id = ?",
        (tipo_id, processo_id),
    )


def _unidade_atual(banco: sqlite3.Connection, processo_id: int) -> int | None:
    """Unidade onde o processo está: último destino ou a origem."""
    linha = banco.execute(
        """SELECT COALESCE(
             (SELECT unidade_destino_id FROM tramitacao
               WHERE processo_id = ? ORDER BY id DESC LIMIT 1),
             (SELECT unidade_origem_id FROM processo WHERE id = ?))""",
        (processo_id, processo_id),
    ).fetchone()
    return linha[0] if linha else None


def proxima_etapa(banco: sqlite3.Connection, processo_id: int) -> dict | None:
    """Próxima etapa do rito a partir de onde o processo está.

    Devolve o dicionário da etapa (unidade, ação, prazo) ou None se o
    processo não tem rito, se já terminou o fluxo ou está na última etapa.
    """
    linha = banco.execute(
        "SELECT tipo_processo_id FROM processo WHERE id = ?", (processo_id,)
    ).fetchone()
    if linha is None or linha[0] is None:
        return None
    rito = etapas(banco, linha[0])
    if not rito:
        return None

    atual = _unidade_atual(banco, processo_id)
    indices = [i for i, e in enumerate(rito) if e["unidade_id"] == atual]
    if not indices:
        # Ainda não entrou no rito: a próxima é a primeira etapa.
        return rito[0]
    prox = indices[-1] + 1
    return rito[prox] if prox < len(rito) else None


def tramitar_pelo_fluxo(banco: sqlite3.Connection, processo_id: int,
                        data: str, despacho: str = "") -> dict:
    """Encaminha o processo à próxima etapa do rito automaticamente.

    Calcula o prazo pela etapa (data + prazo_dias) e usa a ação da etapa
    como despacho padrão. Devolve a etapa para a qual encaminhou.
    """
    prox = proxima_etapa(banco, processo_id)
    if prox is None:
        raise RegraViolada("processo sem próxima etapa no rito")
    prazo = None
    if prox["prazo_dias"]:
        prazo = (date.fromisoformat(data)
                 + timedelta(days=prox["prazo_dias"])).isoformat()
    tid = servicos.tramitar(
        banco, processo_id, prox["unidade_id"],
        despacho or prox["acao"], data, prazo)
    return {"tramitacao_id": tid, **prox}


# ------------------------------------------------------------------
# Demonstração
# ------------------------------------------------------------------

def main() -> None:
    from sistema.demo import criar_banco

    banco = criar_banco()

    print("=" * 66)
    print("RITOS CONFIGURADOS (Lei 3.525/2025)")
    print("=" * 66)
    for cod, nome, dom in banco.execute(
        "SELECT codigo, nome, dominio FROM tipo_processo ORDER BY id"
    ):
        print(f"\n{cod} — {nome} [{dom}]")
        for e in etapas(banco, cod):
            prazo = f"{e['prazo_dias']}d" if e["prazo_dias"] else "—"
            print(f"  {e['ordem']}. {e['unidade']:<45} {prazo:>4}  {e['acao']}")

    # Simula um Projeto de Lei percorrendo o rito automaticamente.
    print("\n" + "=" * 66)
    print("SIMULAÇÃO — um PL percorrendo o rito, setor a setor")
    print("=" * 66)
    (origem,) = banco.execute(
        "SELECT id FROM unidade WHERE nome = 'Gabinetes de Vereadores'"
    ).fetchone()
    pid, numero = servicos.autuar_processo(
        banco, "LEGISLATIVO", "Institui a Semana da Leitura", origem,
        "2025-09-10")
    vincular_tipo(banco, pid, "PL")
    print(f"Processo {numero} autuado e vinculado ao rito PL.\n")

    data = "2025-09-11"
    while True:
        prox = proxima_etapa(banco, pid)
        if prox is None:
            break
        etapa = tramitar_pelo_fluxo(banco, pid, data)
        print(f"  → {etapa['unidade']:<45} (prazo {etapa['prazo_dias']}d)")
        # a unidade destino recebe, liberando a etapa seguinte
        (tid,) = (etapa["tramitacao_id"],)
        servicos.receber_tramitacao(banco, tid, data)
    print("\nFim do rito: processo percorreu todos os setores previstos.")
    banco.close()


if __name__ == "__main__":
    main()
