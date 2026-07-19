"""Módulo de comissões: relatoria e pareceres.

Cobre a instrução da matéria nas comissões permanentes temáticas antes da
deliberação em Plenário (art. 33 e seguintes do Regimento Interno,
Resolução nº 1.835/2000):

- distribuição da proposição a uma comissão, com designação de relator
  (parlamentar) e prazo regimental para o parecer;
- emissão do parecer (favorável, favorável com emendas, contrário ou pela
  rejeição) e sua aprovação pelo colegiado;
- controle de relatorias em atraso (prazo vencido sem parecer).

Regra de mérito adotada pelo módulo legislativo: proposições de mérito
(PL, PLC, PDL, PR) só entram em Ordem do Dia com **parecer aprovado**,
salvo regime de urgência — o parecer, porém, **não vincula** o Plenário
(parecer contrário não impede a deliberação).

Uso demonstrativo:
    python -m sistema.comissoes
"""

from __future__ import annotations

import sqlite3

from sistema.servicos import RegraViolada

# Tipos de proposição de mérito que dependem de parecer de comissão antes
# da Ordem do Dia (as demais — requerimentos, indicações, moções — seguem
# rito de expediente e dispensam parecer prévio).
TIPOS_QUE_EXIGEM_PARECER = {"PL", "PLC", "PDL", "PR"}

TIPOS_PARECER = {
    "FAVORAVEL", "FAVORAVEL_COM_EMENDAS", "CONTRARIO", "PELA_REJEICAO",
}


def _comissao_id(banco: sqlite3.Connection, comissao: str | int) -> int:
    """Resolve a comissão por id ou por nome exato."""
    if isinstance(comissao, int):
        linha = banco.execute(
            "SELECT id FROM comissao_permanente WHERE id = ?", (comissao,)
        ).fetchone()
    else:
        linha = banco.execute(
            "SELECT id FROM comissao_permanente WHERE nome = ?", (comissao,)
        ).fetchone()
    if linha is None:
        raise RegraViolada("comissão permanente inexistente")
    return linha[0]


def distribuir_relatoria(
    banco: sqlite3.Connection,
    proposicao_id: int,
    comissao: str | int,
    relator_parlamentar_id: int,
    data: str,
    prazo: str | None = None,
) -> int:
    """Distribui a proposição a uma comissão e designa o relator.

    Bloqueia relatoria duplicada ativa na mesma comissão. Devolve o id.
    """
    linha = banco.execute(
        "SELECT tipo FROM proposicao WHERE id = ?", (proposicao_id,)
    ).fetchone()
    if linha is None:
        raise RegraViolada("proposição inexistente")
    comissao_id = _comissao_id(banco, comissao)
    if banco.execute(
        "SELECT id FROM parlamentar WHERE id = ?", (relator_parlamentar_id,)
    ).fetchone() is None:
        raise RegraViolada("relator (parlamentar) inexistente")

    ja_ativa = banco.execute(
        "SELECT COUNT(*) FROM relatoria WHERE proposicao_id = ? AND "
        "comissao_id = ? AND situacao = 'ATIVA'",
        (proposicao_id, comissao_id),
    ).fetchone()[0]
    if ja_ativa:
        raise RegraViolada(
            "já há relatoria ativa desta proposição nesta comissão")

    return banco.execute(
        "INSERT INTO relatoria (proposicao_id, comissao_id, "
        "relator_parlamentar_id, distribuida_em, prazo) VALUES (?, ?, ?, ?, ?)",
        (proposicao_id, comissao_id, relator_parlamentar_id, data, prazo),
    ).lastrowid


def emitir_parecer(
    banco: sqlite3.Connection,
    relatoria_id: int,
    tipo: str,
    ementa: str,
    data: str,
) -> int:
    """Registra o parecer do relator e conclui a relatoria. Devolve o id.

    O parecer nasce EMITIDO; a aprovação pelo colegiado é passo separado
    (`aprovar_parecer`).
    """
    if tipo not in TIPOS_PARECER:
        raise RegraViolada(
            "tipo de parecer inválido: use FAVORAVEL, FAVORAVEL_COM_EMENDAS, "
            "CONTRARIO ou PELA_REJEICAO")
    linha = banco.execute(
        "SELECT proposicao_id, comissao_id, situacao FROM relatoria "
        "WHERE id = ?", (relatoria_id,)
    ).fetchone()
    if linha is None:
        raise RegraViolada("relatoria inexistente")
    proposicao_id, comissao_id, situacao = linha
    if situacao != "ATIVA":
        raise RegraViolada(f"relatoria {situacao.lower()} não comporta parecer")

    parecer_id = banco.execute(
        "INSERT INTO parecer (relatoria_id, proposicao_id, comissao_id, "
        "tipo, ementa, situacao, emitido_em) "
        "VALUES (?, ?, ?, ?, ?, 'EMITIDO', ?)",
        (relatoria_id, proposicao_id, comissao_id, tipo, ementa, data),
    ).lastrowid
    banco.execute(
        "UPDATE relatoria SET situacao = 'CONCLUIDA' WHERE id = ?",
        (relatoria_id,),
    )
    return parecer_id


def aprovar_parecer(banco: sqlite3.Connection, parecer_id: int) -> None:
    """Aprova o parecer no colegiado (situação EMITIDO → APROVADO)."""
    _mudar_situacao_parecer(banco, parecer_id, "EMITIDO", "APROVADO")


def rejeitar_parecer(banco: sqlite3.Connection, parecer_id: int) -> None:
    """Rejeita o parecer no colegiado (situação EMITIDO → REJEITADO).

    Rejeitar o parecer do relator não rejeita a matéria: exige novo
    parecer (designar outro relator) antes da Ordem do Dia.
    """
    _mudar_situacao_parecer(banco, parecer_id, "EMITIDO", "REJEITADO")


def _mudar_situacao_parecer(banco, parecer_id, de, para):
    linha = banco.execute(
        "SELECT situacao FROM parecer WHERE id = ?", (parecer_id,)
    ).fetchone()
    if linha is None:
        raise RegraViolada("parecer inexistente")
    if linha[0] != de:
        raise RegraViolada(
            f"parecer em {linha[0].lower()} não pode ir para {para.lower()}")
    banco.execute(
        "UPDATE parecer SET situacao = ? WHERE id = ?", (para, parecer_id))


def tem_parecer_aprovado(banco: sqlite3.Connection, proposicao_id: int) -> bool:
    """Há ao menos um parecer APROVADO para a proposição?"""
    return banco.execute(
        "SELECT COUNT(*) FROM parecer WHERE proposicao_id = ? AND "
        "situacao = 'APROVADO'", (proposicao_id,),
    ).fetchone()[0] > 0


def exige_parecer(tipo_proposicao: str) -> bool:
    """A proposição do tipo dado depende de parecer antes da Ordem do Dia?"""
    return tipo_proposicao in TIPOS_QUE_EXIGEM_PARECER


def pareceres(banco: sqlite3.Connection, proposicao_id: int) -> list[dict]:
    """Lista os pareceres da proposição, com comissão e relator."""
    return [
        {"id": pid, "comissao": comissao, "relator": relator,
         "tipo": tipo, "ementa": ementa, "situacao": situacao,
         "emitido_em": data}
        for pid, comissao, relator, tipo, ementa, situacao, data in banco.execute(
            """SELECT p.id, c.nome, pl.nome, p.tipo, p.ementa,
                      p.situacao, p.emitido_em
                 FROM parecer p
                 JOIN comissao_permanente c ON c.id = p.comissao_id
                 JOIN relatoria r ON r.id = p.relatoria_id
                 JOIN parlamentar pl ON pl.id = r.relator_parlamentar_id
                WHERE p.proposicao_id = ?
                ORDER BY p.id""", (proposicao_id,),
        )
    ]


def relatorias_em_atraso(banco: sqlite3.Connection, referencia: str) -> list[dict]:
    """Relatorias ATIVAS com prazo vencido em relação à data de referência."""
    return [
        {"relatoria_id": rid, "proposicao": f"{tipo} {numero}/{ano}",
         "comissao": comissao, "relator": relator, "prazo": prazo}
        for rid, tipo, numero, ano, comissao, relator, prazo in banco.execute(
            """SELECT r.id, pr.tipo, pr.numero, pr.ano,
                      c.nome, pl.nome, r.prazo
                 FROM relatoria r
                 JOIN proposicao pr ON pr.id = r.proposicao_id
                 JOIN comissao_permanente c ON c.id = r.comissao_id
                 JOIN parlamentar pl ON pl.id = r.relator_parlamentar_id
                WHERE r.situacao = 'ATIVA'
                  AND r.prazo IS NOT NULL AND r.prazo < ?
                ORDER BY r.prazo""", (referencia,),
        )
    ]


# ------------------------------------------------------------------
# Demonstração
# ------------------------------------------------------------------

def main() -> None:
    from sistema import legislativo
    from sistema.demo import criar_banco

    banco = criar_banco()
    legislatura = legislativo.criar_legislatura(
        banco, 1, "2025-01-01", "2028-12-31")
    relator = legislativo.empossar(banco, "Vereadora Ana", "PXX", legislatura)
    proposicao, ref = legislativo.apresentar_proposicao(
        banco, "PL", "Institui a Semana Municipal da Leitura", "2025-09-10",
        autor_parlamentar_id=relator)

    print(f"Proposição apresentada: {ref}")
    rel = distribuir_relatoria(
        banco, proposicao, "Comissão de Legislação, Justiça e Redação Final",
        relator, "2025-09-11", prazo="2025-09-25")
    print(f"Relatoria distribuída (id {rel}), prazo 2025-09-25")

    parecer_id = emitir_parecer(
        banco, rel, "FAVORAVEL",
        "Parecer favorável: matéria constitucional e de interesse público.",
        "2025-09-20")
    aprovar_parecer(banco, parecer_id)
    print("Parecer emitido e aprovado pela comissão.")

    print(f"Tem parecer aprovado? {tem_parecer_aprovado(banco, proposicao)}")
    for p in pareceres(banco, proposicao):
        print(f"  [{p['situacao']}] {p['comissao']} — {p['tipo']} "
              f"(relator: {p['relator']})")
    banco.close()


if __name__ == "__main__":
    main()
