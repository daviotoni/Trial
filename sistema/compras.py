"""Módulo de compras e contratos (Lei nº 14.133/2021).

Atende a Superintendência-Geral e as Coordenadorias de Avaliação e
Acompanhamento de Compras, de Licitações e Contratos, de Contabilidade e
de Finanças (estrutura da Lei 3.525/2025).

Fluxo implementado:
    abrir_contratacao (autua processo)  →  homologar  →  celebrar_contrato
                                        →  fracassar/revogar
    empenhar (livre ou vinculado a contrato, sem exceder o valor)

Regras aplicadas:
- dispensa por valor (art. 75, I e II) validada contra os limites
  vigentes — atualizados periodicamente por decreto federal, por isso
  parametrizáveis em LIMITES_DISPENSA;
- contrato só após homologação;
- soma dos empenhos de um contrato não excede seu valor;
- toda operação registra trilha na tabela `auditoria` (controle interno
  da Controladoria-Geral).
"""

from __future__ import annotations

import sqlite3

from sistema.servicos import RegraViolada, autuar_processo

# Limites de dispensa do art. 75 da Lei 14.133/2021 (valores atualizados
# por decreto federal — Decreto nº 11.871/2023; ajustar quando houver
# novo decreto).
LIMITES_DISPENSA = {
    "OBRAS_SERVICOS_ENGENHARIA": 119_812.02,   # art. 75, I
    "COMPRAS_OUTROS_SERVICOS": 59_906.02,      # art. 75, II
}


def auditar(banco: sqlite3.Connection, tabela: str, registro_id: int,
            operacao: str, usuario: str, datahora: str, detalhes: str = "") -> None:
    banco.execute(
        "INSERT INTO auditoria (tabela, registro_id, operacao, usuario, "
        "datahora, detalhes) VALUES (?, ?, ?, ?, ?, ?)",
        (tabela, registro_id, operacao, usuario, datahora, detalhes),
    )


def cadastrar_fornecedor(banco: sqlite3.Connection, razao_social: str,
                         cnpj: str | None = None) -> int:
    return banco.execute(
        "INSERT INTO fornecedor (razao_social, cnpj) VALUES (?, ?)",
        (razao_social, cnpj),
    ).lastrowid


def abrir_contratacao(
    banco: sqlite3.Connection,
    modalidade: str,
    objeto: str,
    valor_estimado: float,
    unidade_demandante_id: int,
    data: str,
    categoria: str = "COMPRAS_OUTROS_SERVICOS",
    usuario: str = "sistema",
) -> tuple[int, str]:
    """Abre a contratação, autuando o processo. Devolve (id, 'modalidade n/ano')."""
    if modalidade == "DISPENSA":
        limite = LIMITES_DISPENSA.get(categoria)
        if limite is None:
            raise RegraViolada("categoria de dispensa desconhecida")
        if valor_estimado > limite:
            raise RegraViolada(
                f"valor estimado excede o limite de dispensa de "
                f"R$ {limite:,.2f} (Lei 14.133/2021, art. 75)"
            )

    ano = int(data[:4])
    (ultimo,) = banco.execute(
        "SELECT COALESCE(MAX(numero), 0) FROM contratacao "
        "WHERE modalidade = ? AND ano = ?", (modalidade, ano),
    ).fetchone()
    numero = ultimo + 1

    processo_id, _ = autuar_processo(
        banco, "ADMINISTRATIVO",
        f"{modalidade} {numero}/{ano} — {objeto}",
        unidade_demandante_id, data,
    )
    contratacao_id = banco.execute(
        "INSERT INTO contratacao (modalidade, numero, ano, objeto, "
        "valor_estimado, processo_id) VALUES (?, ?, ?, ?, ?, ?)",
        (modalidade, numero, ano, objeto, valor_estimado, processo_id),
    ).lastrowid
    auditar(banco, "contratacao", contratacao_id, "INSERT", usuario, data,
            f"abertura {modalidade} {numero}/{ano}")
    return contratacao_id, f"{modalidade} {numero}/{ano}"


def _mudar_situacao(banco, contratacao_id, de, para, usuario, data):
    linha = banco.execute(
        "SELECT situacao FROM contratacao WHERE id = ?", (contratacao_id,)
    ).fetchone()
    if linha is None:
        raise RegraViolada("contratação inexistente")
    if linha[0] not in de:
        raise RegraViolada(
            f"transição inválida: contratação está '{linha[0]}'"
        )
    banco.execute("UPDATE contratacao SET situacao = ? WHERE id = ?",
                  (para, contratacao_id))
    auditar(banco, "contratacao", contratacao_id, "UPDATE", usuario, data,
            f"{linha[0]} -> {para}")


def homologar(banco, contratacao_id: int, data: str,
              usuario: str = "sistema") -> None:
    _mudar_situacao(banco, contratacao_id, {"EM_ANDAMENTO"}, "HOMOLOGADA",
                    usuario, data)


def fracassar(banco, contratacao_id: int, data: str,
              usuario: str = "sistema") -> None:
    _mudar_situacao(banco, contratacao_id, {"EM_ANDAMENTO"}, "FRACASSADA",
                    usuario, data)


def revogar(banco, contratacao_id: int, data: str,
            usuario: str = "sistema") -> None:
    _mudar_situacao(banco, contratacao_id, {"EM_ANDAMENTO", "HOMOLOGADA"},
                    "REVOGADA", usuario, data)


def celebrar_contrato(
    banco: sqlite3.Connection,
    contratacao_id: int,
    fornecedor_id: int,
    valor: float,
    inicio: str,
    fim: str | None = None,
    usuario: str = "sistema",
) -> int:
    """Celebra o contrato de uma contratação homologada."""
    _mudar_situacao(banco, contratacao_id, {"HOMOLOGADA"}, "CONTRATADA",
                    usuario, inicio)
    contrato_id = banco.execute(
        "INSERT INTO contrato (contratacao_id, fornecedor_id, valor, "
        "inicio, fim) VALUES (?, ?, ?, ?, ?)",
        (contratacao_id, fornecedor_id, valor, inicio, fim),
    ).lastrowid
    auditar(banco, "contrato", contrato_id, "INSERT", usuario, inicio,
            f"valor {valor}")
    return contrato_id


def empenhar(
    banco: sqlite3.Connection,
    valor: float,
    descricao: str,
    data: str,
    contrato_id: int | None = None,
    usuario: str = "sistema",
) -> tuple[int, str]:
    """Emite empenho, numerado por ano; se vinculado a contrato, a soma dos
    empenhos não pode exceder o valor contratado."""
    if valor <= 0:
        raise RegraViolada("empenho deve ter valor positivo")
    if contrato_id is not None:
        linha = banco.execute(
            "SELECT valor FROM contrato WHERE id = ?", (contrato_id,)
        ).fetchone()
        if linha is None:
            raise RegraViolada("contrato inexistente")
        (empenhado,) = banco.execute(
            "SELECT COALESCE(SUM(valor), 0) FROM empenho WHERE contrato_id = ?",
            (contrato_id,),
        ).fetchone()
        if empenhado + valor > linha[0]:
            raise RegraViolada(
                f"empenhos somariam R$ {empenhado + valor:,.2f}, acima do "
                f"valor contratado de R$ {linha[0]:,.2f}"
            )
    ano = int(data[:4])
    (ultimo,) = banco.execute(
        "SELECT COALESCE(MAX(numero), 0) FROM empenho WHERE ano = ?", (ano,)
    ).fetchone()
    numero = ultimo + 1
    empenho_id = banco.execute(
        "INSERT INTO empenho (numero, ano, valor, descricao, contrato_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (numero, ano, valor, descricao, contrato_id),
    ).lastrowid
    auditar(banco, "empenho", empenho_id, "INSERT", usuario, data,
            f"{numero}/{ano} valor {valor}")
    return empenho_id, f"{numero}/{ano}"
