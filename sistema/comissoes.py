"""Módulo de comissões: setor único de comissões e pareceres.

As comissões permanentes temáticas (art. 33 do Regimento Interno) não se
ramificam em setores distintos: um **único setor de comissões** recebe
todas as matérias e dá prosseguimento. As comissões temáticas
(Legislação/Justiça, Finanças, Educação…) ficam como uma **lista de
classificação** — ao emitir o parecer, o setor **marca** a qual comissão
ele corresponde.

- emissão do parecer (favorável, com emendas, contrário ou pela rejeição),
  marcando a comissão temática e, opcionalmente, o relator;
- aprovação do parecer pelo colegiado.

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


def comissoes(banco: sqlite3.Connection) -> list[dict]:
    """Lista as comissões temáticas (para marcar o parecer)."""
    return [
        {"id": cid, "nome": nome}
        for cid, nome in banco.execute(
            "SELECT id, nome FROM comissao_permanente ORDER BY id")
    ]


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


def emitir_parecer(
    banco: sqlite3.Connection,
    proposicao_id: int,
    comissao: str | int,
    tipo: str,
    ementa: str,
    data: str,
    relator_parlamentar_id: int | None = None,
    prazo: str | None = None,
) -> int:
    """Emite um parecer sobre a proposição, MARCANDO a comissão temática.

    O parecer nasce EMITIDO; a aprovação pelo colegiado é passo separado
    (`aprovar_parecer`). `relator_parlamentar_id` é opcional.
    """
    if tipo not in TIPOS_PARECER:
        raise RegraViolada(
            "tipo de parecer inválido: use FAVORAVEL, FAVORAVEL_COM_EMENDAS, "
            "CONTRARIO ou PELA_REJEICAO")
    if banco.execute(
        "SELECT id FROM proposicao WHERE id = ?", (proposicao_id,)
    ).fetchone() is None:
        raise RegraViolada("proposição inexistente")
    comissao_id = _comissao_id(banco, comissao)
    if relator_parlamentar_id is not None and banco.execute(
        "SELECT id FROM parlamentar WHERE id = ?", (relator_parlamentar_id,)
    ).fetchone() is None:
        raise RegraViolada("relator (parlamentar) inexistente")

    return banco.execute(
        "INSERT INTO parecer (proposicao_id, comissao_id, "
        "relator_parlamentar_id, tipo, ementa, prazo, situacao, emitido_em) "
        "VALUES (?, ?, ?, ?, ?, ?, 'EMITIDO', ?)",
        (proposicao_id, comissao_id, relator_parlamentar_id, tipo, ementa,
         prazo, data),
    ).lastrowid


def aprovar_parecer(banco: sqlite3.Connection, parecer_id: int) -> None:
    """Aprova o parecer no colegiado (situação EMITIDO → APROVADO)."""
    _mudar_situacao_parecer(banco, parecer_id, "EMITIDO", "APROVADO")


def rejeitar_parecer(banco: sqlite3.Connection, parecer_id: int) -> None:
    """Rejeita o parecer no colegiado (situação EMITIDO → REJEITADO).

    Rejeitar o parecer não rejeita a matéria: exige novo parecer antes da
    Ordem do Dia.
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


def materias_para_parecer(banco: sqlite3.Connection) -> list[dict]:
    """Matérias de mérito aguardando parecer de comissão (art. 33).

    Proposições de mérito (PL, PLC, PDL, PR) em tramitação que ainda não
    têm parecer aprovado — a fila de trabalho do setor de comissões.
    Traz os pareceres já emitidos (para aprovar/rejeitar).
    """
    tipos = ", ".join(f"'{t}'" for t in sorted(TIPOS_QUE_EXIGEM_PARECER))
    return [
        {"id": pid, "rotulo": f"{tipo} {numero}/{ano}", "tipo": tipo,
         "ementa": ementa, "autor": autor,
         "pareceres": pareceres(banco, pid)}
        for (pid, tipo, numero, ano, ementa, autor) in banco.execute(
            f"""SELECT p.id, p.tipo, p.numero, p.ano, p.ementa, pl.nome
                  FROM proposicao p
                  LEFT JOIN parlamentar pl ON pl.id = p.autor_parlamentar_id
                 WHERE p.situacao = 'EM_TRAMITACAO' AND p.numero IS NOT NULL
                   AND p.tipo IN ({tipos})
                   AND NOT EXISTS (SELECT 1 FROM parecer pa
                                    WHERE pa.proposicao_id = p.id
                                      AND pa.situacao = 'APROVADO')
                 ORDER BY p.id""",
        )
    ]


def pareceres_por_comissao(banco: sqlite3.Connection,
                           comissao_id: int | None = None) -> list[dict]:
    """Pareceres do setor, individualizados pela comissão temática.

    Sem `comissao_id`, lista todos; com ele, filtra pela comissão — o
    "identificar a qual comissão cada parecer está vinculado" dentro do
    setor único de Comissões Permanentes.
    """
    condicao = "WHERE pa.comissao_id = ?" if comissao_id else ""
    args = (comissao_id,) if comissao_id else ()
    return [
        {"id": pid, "comissao": comissao, "comissao_id": cid,
         "proposicao": f"{tipo} {numero}/{ano}", "proposicao_id": prop_id,
         "tipo": tipo_parecer, "ementa": ementa, "situacao": situacao,
         "relator": relator, "emitido_em": emitido_em}
        for (pid, comissao, cid, tipo, numero, ano, prop_id, tipo_parecer,
             ementa, situacao, relator, emitido_em) in banco.execute(
            f"""SELECT pa.id, c.nome, c.id, p.tipo, p.numero, p.ano, p.id,
                       pa.tipo, pa.ementa, pa.situacao, pl.nome, pa.emitido_em
                  FROM parecer pa
                  JOIN comissao_permanente c ON c.id = pa.comissao_id
                  JOIN proposicao p ON p.id = pa.proposicao_id
                  LEFT JOIN parlamentar pl
                         ON pl.id = pa.relator_parlamentar_id
                  {condicao}
                 ORDER BY c.nome, pa.id DESC""", args,
        )
    ]


def pareceres(banco: sqlite3.Connection, proposicao_id: int) -> list[dict]:
    """Lista os pareceres da proposição, com a comissão marcada e o relator."""
    return [
        {"id": pid, "comissao": comissao, "relator": relator,
         "tipo": tipo, "ementa": ementa, "situacao": situacao,
         "emitido_em": data}
        for pid, comissao, relator, tipo, ementa, situacao, data in banco.execute(
            """SELECT p.id, c.nome, pl.nome, p.tipo, p.ementa,
                      p.situacao, p.emitido_em
                 FROM parecer p
                 JOIN comissao_permanente c ON c.id = p.comissao_id
                 LEFT JOIN parlamentar pl ON pl.id = p.relator_parlamentar_id
                WHERE p.proposicao_id = ?
                ORDER BY p.id""", (proposicao_id,),
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
    print("O setor de comissões recebe a matéria e emite o parecer, "
          "marcando a comissão:")
    parecer_id = emitir_parecer(
        banco, proposicao, "Comissão de Educação e Cultura", "FAVORAVEL",
        "Parecer favorável: matéria de interesse público.", "2025-09-20",
        relator_parlamentar_id=relator)
    aprovar_parecer(banco, parecer_id)

    print(f"Tem parecer aprovado? {tem_parecer_aprovado(banco, proposicao)}")
    for p in pareceres(banco, proposicao):
        print(f"  [{p['situacao']}] {p['comissao']} — {p['tipo']} "
              f"(relator: {p['relator']})")
    banco.close()


if __name__ == "__main__":
    main()
