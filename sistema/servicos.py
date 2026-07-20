"""Regras de negócio do sistema de gestão da CMDC.

Operações sobre o banco (sqlite3.Connection) aplicando as regras da
Lei nº 3.525/2025 e da Lei nº 1.506/2000:

- Pessoal: nomeação/exoneração respeitando vagas do Anexo I, natureza do
  símbolo e requisitos de função de confiança (art. 5º, §3º: servidor
  efetivo com no mínimo 2 anos de exercício).
- Protocolo: autuação com numeração sequencial por ano e tramitação
  entre unidades.
- Folha: cálculo mensal aplicando as rubricas da lei (GAL, REP-TL, GAP,
  REP-JUD, GRAT-COM, GRAT-CC), sempre validando os tetos cadastrados.

Todas as funções deixam a transação aberta — quem chama decide commit.
"""

from __future__ import annotations

import sqlite3
from datetime import date


class RegraViolada(Exception):
    """Operação contraria uma regra legal/administrativa."""


# ------------------------------------------------------------------
# Pessoal
# ------------------------------------------------------------------

def vagas_disponiveis(banco: sqlite3.Connection, cargo_id: int) -> int:
    total, ocupadas = banco.execute(
        """SELECT c.quantidade_vagas,
                  (SELECT COUNT(*) FROM provimento p
                    WHERE p.cargo_id = c.id AND p.data_fim IS NULL)
           FROM cargo c WHERE c.id = ?""",
        (cargo_id,),
    ).fetchone()
    return total - ocupadas


def _anos_de_exercicio(data_admissao: str, referencia: str) -> float:
    inicio, fim = date.fromisoformat(data_admissao), date.fromisoformat(referencia)
    return (fim - inicio).days / 365.25


def nomear(
    banco: sqlite3.Connection,
    servidor_id: int,
    cargo_id: int,
    unidade_id: int,
    ato: str,
    data_inicio: str,
) -> int:
    """Provê um cargo, validando vagas e requisitos legais. Devolve o id."""
    if vagas_disponiveis(banco, cargo_id) <= 0:
        raise RegraViolada("sem vaga disponível para o cargo (Anexo I)")

    tipo_cargo = banco.execute(
        "SELECT tipo FROM cargo WHERE id = ?", (cargo_id,)
    ).fetchone()[0]
    vinculo, admissao = banco.execute(
        "SELECT vinculo, data_admissao FROM servidor WHERE id = ?",
        (servidor_id,),
    ).fetchone()

    if tipo_cargo == "FUNCAO_CONFIANCA":
        if vinculo != "EFETIVO":
            raise RegraViolada(
                "função de confiança é privativa de servidor efetivo "
                "(Lei 3.525/2025, art. 5º)"
            )
        if _anos_de_exercicio(admissao, data_inicio) < 2:
            raise RegraViolada(
                "função de confiança exige 2 anos de efetivo exercício "
                "(Lei 3.525/2025, art. 5º, §3º)"
            )
    if tipo_cargo == "EFETIVO" and vinculo != "EFETIVO":
        raise RegraViolada("cargo efetivo exige aprovação em concurso público")

    ativo = banco.execute(
        "SELECT COUNT(*) FROM provimento WHERE servidor_id = ? AND data_fim IS NULL",
        (servidor_id,),
    ).fetchone()[0]
    if ativo and tipo_cargo != "FUNCAO_CONFIANCA":
        # Efetivo pode acumular função gratificada (art. 5º, §2º); demais, não.
        raise RegraViolada("servidor já possui provimento ativo")

    cursor = banco.execute(
        "INSERT INTO provimento (servidor_id, cargo_id, unidade_id, ato, "
        "data_inicio) VALUES (?, ?, ?, ?, ?)",
        (servidor_id, cargo_id, unidade_id, ato, data_inicio),
    )
    return cursor.lastrowid


def exonerar(banco: sqlite3.Connection, provimento_id: int, data_fim: str) -> None:
    alterados = banco.execute(
        "UPDATE provimento SET data_fim = ? WHERE id = ? AND data_fim IS NULL",
        (data_fim, provimento_id),
    ).rowcount
    if not alterados:
        raise RegraViolada("provimento inexistente ou já encerrado")


# ------------------------------------------------------------------
# Avaliação de desempenho (Lei 3.226/2022)
# ------------------------------------------------------------------

# Conceito por faixa de pontuação (Lei 3.226/2022) e percentual do
# Adicional de Produtividade correspondente (art. 14).
_CONCEITOS = [  # (pontuação mínima, conceito, % produtividade)
    (91, "EXCELENTE", 70),
    (81, "MUITO_BOM", 50),
    (71, "BOM", 40),
    (50, "REGULAR", 20),
    (0, "INSATISFATORIO", 0),
]


def conceito_por_pontuacao(pontuacao: int) -> tuple[str, int]:
    """Devolve (conceito, % do Adicional de Produtividade)."""
    for minimo, conceito, percentual in _CONCEITOS:
        if pontuacao >= minimo:
            return conceito, percentual
    raise RegraViolada("pontuação inválida")


def avaliar_desempenho(
    banco: sqlite3.Connection,
    servidor_id: int,
    periodo: str,
    pontuacao: int,
    avaliador: str,
    data: str,
) -> str:
    """Registra a avaliação semestral de um efetivo. Devolve o conceito."""
    if not 0 <= pontuacao <= 100:
        raise RegraViolada("pontuação deve estar entre 0 e 100")
    (vinculo,) = banco.execute(
        "SELECT vinculo FROM servidor WHERE id = ?", (servidor_id,)
    ).fetchone()
    if vinculo != "EFETIVO":
        raise RegraViolada(
            "avaliação de desempenho aplica-se a servidores efetivos "
            "(Lei 3.226/2022)"
        )
    conceito, _ = conceito_por_pontuacao(pontuacao)
    banco.execute(
        "INSERT INTO avaliacao_desempenho (servidor_id, periodo, pontuacao, "
        "conceito, avaliador, data) VALUES (?, ?, ?, ?, ?, ?)",
        (servidor_id, periodo, pontuacao, conceito, avaliador, data),
    )
    return conceito


# ------------------------------------------------------------------
# Protocolo e tramitação
# ------------------------------------------------------------------

def autuar_processo(
    banco: sqlite3.Connection,
    tipo: str,
    assunto: str,
    unidade_origem_id: int,
    data_autuacao: str,
    interessado: str | None = None,
) -> tuple[int, str]:
    """Autua processo com número sequencial no ano. Devolve (id, 'n/ano')."""
    ano = int(data_autuacao[:4])
    (ultimo,) = banco.execute(
        "SELECT COALESCE(MAX(numero), 0) FROM processo WHERE ano = ?", (ano,)
    ).fetchone()
    numero = ultimo + 1
    cursor = banco.execute(
        "INSERT INTO processo (numero, ano, tipo, assunto, interessado, "
        "unidade_origem_id, data_autuacao) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (numero, ano, tipo, assunto, interessado, unidade_origem_id, data_autuacao),
    )
    return cursor.lastrowid, f"{numero}/{ano}"


def receber_tramitacao(banco: sqlite3.Connection, tramitacao_id: int,
                       data_recebimento: str) -> None:
    """Registra o recebimento pela unidade de destino."""
    alterados = banco.execute(
        "UPDATE tramitacao SET data_recebimento = ? "
        "WHERE id = ? AND data_recebimento IS NULL",
        (data_recebimento, tramitacao_id),
    ).rowcount
    if not alterados:
        raise RegraViolada("tramitação inexistente ou já recebida")


def _mudar_situacao_processo(banco, processo_id, de, para):
    linha = banco.execute(
        "SELECT situacao FROM processo WHERE id = ?", (processo_id,)
    ).fetchone()
    if linha is None:
        raise RegraViolada("processo inexistente")
    if linha[0] not in de:
        raise RegraViolada(f"processo está '{linha[0]}'; transição inválida")
    banco.execute("UPDATE processo SET situacao = ? WHERE id = ?",
                  (para, processo_id))


def arquivar_processo(banco: sqlite3.Connection, processo_id: int) -> None:
    _mudar_situacao_processo(
        banco, processo_id, {"EM_TRAMITACAO", "SOBRESTADO", "CONCLUIDO"},
        "ARQUIVADO")


def concluir_processo(banco: sqlite3.Connection, processo_id: int) -> None:
    _mudar_situacao_processo(
        banco, processo_id, {"EM_TRAMITACAO", "SOBRESTADO"}, "CONCLUIDO")


def desarquivar_processo(banco: sqlite3.Connection, processo_id: int) -> None:
    _mudar_situacao_processo(banco, processo_id, {"ARQUIVADO"},
                             "EM_TRAMITACAO")


def excluir_processo(banco: sqlite3.Connection, processo_id: int,
                     usuario: str, datahora: str) -> dict:
    """Exclui um processo e tudo o que pende dele (ato privativo do admin).

    Remove tramitações, documentos e as proposições vinculadas (com
    pauta, votações, votos e pareceres); requerimentos derivados que
    apontavam para uma proposição excluída perdem só o vínculo. Processo
    ligado a uma contratação não é excluído (trate a contratação antes).
    A exclusão fica registrada na trilha de auditoria.
    """
    linha = banco.execute(
        "SELECT numero, ano, assunto FROM processo WHERE id = ?",
        (processo_id,),
    ).fetchone()
    if linha is None:
        raise RegraViolada("processo inexistente")
    numero, ano, assunto = linha

    if banco.execute(
        "SELECT 1 FROM contratacao WHERE processo_id = ?", (processo_id,)
    ).fetchone():
        raise RegraViolada(
            "o processo está vinculado a uma contratação — não pode ser "
            "excluído")

    proposicoes = [pid for (pid,) in banco.execute(
        "SELECT id FROM proposicao WHERE processo_id = ?", (processo_id,))]
    if proposicoes:
        marcadores = ", ".join("?" * len(proposicoes))
        banco.execute(
            f"UPDATE proposicao SET proposicao_alvo_id = NULL "
            f"WHERE proposicao_alvo_id IN ({marcadores})", proposicoes)
        banco.execute(
            f"DELETE FROM voto WHERE votacao_id IN "
            f"(SELECT id FROM votacao WHERE proposicao_id IN ({marcadores}))",
            proposicoes)
        for tabela in ("votacao", "pauta_item", "parecer"):
            banco.execute(
                f"DELETE FROM {tabela} WHERE proposicao_id IN ({marcadores})",
                proposicoes)
        banco.execute(
            f"DELETE FROM proposicao WHERE id IN ({marcadores})", proposicoes)

    banco.execute("DELETE FROM tramitacao WHERE processo_id = ?",
                  (processo_id,))
    banco.execute("DELETE FROM documento WHERE processo_id = ?",
                  (processo_id,))
    banco.execute("DELETE FROM processo WHERE id = ?", (processo_id,))
    banco.execute(
        "INSERT INTO auditoria (tabela, registro_id, operacao, usuario, "
        "datahora, detalhes) VALUES ('processo', ?, 'DELETE', ?, ?, ?)",
        (processo_id, usuario, datahora,
         f"Processo {numero}/{ano} — {assunto} "
         f"({len(proposicoes)} proposição(ões) vinculada(s) excluída(s))"))
    return {"numero": f"{numero}/{ano}",
            "proposicoes_excluidas": len(proposicoes)}


def tramitar(
    banco: sqlite3.Connection,
    processo_id: int,
    unidade_destino_id: int,
    despacho: str,
    data_envio: str,
    prazo: str | None = None,
) -> int:
    """Tramita a partir da unidade onde o processo está (origem ou último destino).

    `prazo` (opcional, ISO-8601) fixa o SLA para a unidade destino receber
    ou se manifestar; alimenta a consulta `processos_em_atraso`.
    """
    situacao = banco.execute(
        "SELECT situacao FROM processo WHERE id = ?", (processo_id,)
    ).fetchone()
    if situacao is None:
        raise RegraViolada("processo inexistente")
    if situacao[0] in ("ARQUIVADO", "CONCLUIDO"):
        raise RegraViolada(f"processo {situacao[0].lower()} não tramita")
    if prazo is not None and prazo < data_envio:
        raise RegraViolada("prazo não pode ser anterior à data de envio")

    atual = banco.execute(
        """SELECT COALESCE(
             (SELECT unidade_destino_id FROM tramitacao
               WHERE processo_id = ? ORDER BY id DESC LIMIT 1),
             (SELECT unidade_origem_id FROM processo WHERE id = ?))""",
        (processo_id, processo_id),
    ).fetchone()[0]
    cursor = banco.execute(
        "INSERT INTO tramitacao (processo_id, unidade_origem_id, "
        "unidade_destino_id, despacho, data_envio, prazo) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (processo_id, atual, unidade_destino_id, despacho, data_envio, prazo),
    )
    return cursor.lastrowid


def processos_em_atraso(banco: sqlite3.Connection, referencia: str) -> list[dict]:
    """Processos parados: última tramitação sem recebimento e prazo vencido.

    Considera apenas a tramitação mais recente de cada processo; se ela
    ainda não foi recebida e tem `prazo` anterior à data de `referencia`,
    o processo está em atraso na unidade destino.
    """
    return [
        {"processo_id": pid, "processo": f"{numero}/{ano}", "assunto": assunto,
         "unidade_destino": destino, "prazo": prazo, "desde": envio}
        for pid, numero, ano, assunto, destino, prazo, envio in banco.execute(
            """SELECT p.id, p.numero, p.ano, p.assunto,
                      u.nome, t.prazo, t.data_envio
                 FROM tramitacao t
                 JOIN processo p ON p.id = t.processo_id
                 JOIN unidade u ON u.id = t.unidade_destino_id
                WHERE t.id = (SELECT MAX(t2.id) FROM tramitacao t2
                               WHERE t2.processo_id = t.processo_id)
                  AND t.data_recebimento IS NULL
                  AND t.prazo IS NOT NULL AND t.prazo < ?
                ORDER BY t.prazo""", (referencia,),
        )
    ]


# ------------------------------------------------------------------
# Folha de pagamento
# ------------------------------------------------------------------

def _teto(banco: sqlite3.Connection, rubrica: str) -> float:
    (teto,) = banco.execute(
        "SELECT percentual_max FROM rubrica WHERE codigo = ?", (rubrica,)
    ).fetchone()
    return teto


def calcular_folha(
    banco: sqlite3.Connection,
    competencia: str,
    percentual_gal: float,
) -> int:
    """Calcula a folha da competência ('AAAA-MM'). Devolve o id da folha.

    Aplica, por servidor com provimento ativo:
    - VENC: retribuição do símbolo (comissionado puro) ou vencimento_base
      (efetivo);
    - GRAT-CC: efetivo em cargo em comissão recebe 100% do símbolo
      (art. 3º, §4º) em vez da retribuição do cargo;
    - função gratificada: efetivo recebe o valor do símbolo equivalente
      (art. 5º, §§2º e 4º), lançado na rubrica GRAT-CC por equivalência;
    - GAL sobre o vencimento básico ou símbolo (art. 7º), no percentual
      informado (validado contra o teto de 150%);
    - REP-TL (60%), GAP (40%), REP-JUD (40%) conforme o cargo efetivo;
    - GRAT-COM (40%) por designação de comissão ativa (arts. 46-47).

    O ATS (triênio) não é lançado: o percentual é do Estatuto e ainda não
    foi parametrizado.
    """
    if percentual_gal > _teto(banco, "GAL"):
        raise RegraViolada("GAL acima do teto de 150% (art. 7º)")

    existente = banco.execute(
        "SELECT id, status FROM folha WHERE competencia = ?", (competencia,)
    ).fetchone()
    if existente:
        folha_id, status = existente
        if status in ("FECHADA", "PAGA"):
            raise RegraViolada(
                f"folha {competencia} está {status}; não pode ser recalculada")
        # Recalcula: descarta os itens do cálculo anterior.
        banco.execute("DELETE FROM folha_item WHERE folha_id = ?", (folha_id,))
        banco.execute("UPDATE folha SET status = 'CALCULADA' WHERE id = ?",
                      (folha_id,))
    else:
        folha_id = banco.execute(
            "INSERT INTO folha (competencia, status) VALUES (?, 'CALCULADA')",
            (competencia,),
        ).lastrowid

    def lancar(servidor_id, rubrica, base, percentual):
        valor = round(base * (percentual / 100 if percentual else 1), 2)
        banco.execute(
            "INSERT INTO folha_item (folha_id, servidor_id, rubrica_codigo, "
            "base_calculo, percentual, valor) VALUES (?, ?, ?, ?, ?, ?)",
            (folha_id, servidor_id, rubrica, base, percentual, valor),
        )
        return valor

    provimentos = banco.execute(
        """SELECT p.servidor_id, s.vinculo, s.vencimento_base,
                  c.tipo, c.denominacao, sb.retribuicao_base
           FROM provimento p
           JOIN servidor s ON s.id = p.servidor_id
           JOIN cargo c ON c.id = p.cargo_id
           LEFT JOIN simbolo sb ON sb.codigo = c.simbolo_codigo
           WHERE p.data_fim IS NULL"""
    ).fetchall()

    for (servidor_id, vinculo, venc_efetivo, tipo_cargo, denominacao,
         retribuicao) in provimentos:
        if tipo_cargo == "COMISSAO" and vinculo != "EFETIVO":
            base_gal = lancar(servidor_id, "VENC", retribuicao, None)
        elif tipo_cargo in ("COMISSAO", "FUNCAO_CONFIANCA"):
            # Efetivo em comissão/função: gratificação de 100% do símbolo
            # (arts. 3º, §4º e 5º, §4º), além do vencimento do cargo efetivo.
            lancar(servidor_id, "GRAT-CC", retribuicao,
                   _teto(banco, "GRAT-CC"))
            base_gal = venc_efetivo or 0
            if venc_efetivo:
                lancar(servidor_id, "VENC", venc_efetivo, None)
        else:  # cargo efetivo
            base_gal = lancar(servidor_id, "VENC", venc_efetivo or 0, None)

        if base_gal:
            lancar(servidor_id, "GAL", base_gal, percentual_gal)

        if tipo_cargo == "EFETIVO" and venc_efetivo:
            if "Técnico Legislativo" in denominacao:
                lancar(servidor_id, "REP-TL", venc_efetivo, _teto(banco, "REP-TL"))
            if "Inspetor de Segurança" in denominacao:
                lancar(servidor_id, "GAP", venc_efetivo, _teto(banco, "GAP"))
            if "Consultor Jurídico" in denominacao:
                lancar(servidor_id, "REP-JUD", venc_efetivo, _teto(banco, "REP-JUD"))
            # Adicional de Produtividade pela última avaliação de
            # desempenho (Lei 3.226/2022, art. 14).
            avaliacao = banco.execute(
                "SELECT pontuacao FROM avaliacao_desempenho "
                "WHERE servidor_id = ? ORDER BY periodo DESC LIMIT 1",
                (servidor_id,),
            ).fetchone()
            if avaliacao:
                _, percentual = conceito_por_pontuacao(avaliacao[0])
                if percentual:
                    lancar(servidor_id, "AD-PROD", venc_efetivo, percentual)

    # GRAT-COM por designação ativa (uma por servidor, mesmo em várias comissões).
    designados = banco.execute(
        """SELECT DISTINCT d.servidor_id FROM designacao_comissao d
           WHERE d.data_fim IS NULL OR d.data_fim >= ?""",
        (competencia + "-01",),
    ).fetchall()
    for (servidor_id,) in designados:
        base = banco.execute(
            """SELECT COALESCE(
                 (SELECT COALESCE(sb.retribuicao_base, s.vencimento_base)
                    FROM provimento p
                    JOIN servidor s ON s.id = p.servidor_id
                    LEFT JOIN cargo c ON c.id = p.cargo_id
                    LEFT JOIN simbolo sb ON sb.codigo = c.simbolo_codigo
                   WHERE p.servidor_id = ? AND p.data_fim IS NULL LIMIT 1),
                 (SELECT vencimento_base FROM servidor WHERE id = ?), 0)""",
            (servidor_id, servidor_id),
        ).fetchone()[0]
        if base:
            lancar(servidor_id, "GRAT-COM", base, _teto(banco, "GRAT-COM"))

    return folha_id


def _mudar_status_folha(banco, folha_id, de, para):
    linha = banco.execute(
        "SELECT status FROM folha WHERE id = ?", (folha_id,)
    ).fetchone()
    if linha is None:
        raise RegraViolada("folha inexistente")
    if linha[0] != de:
        raise RegraViolada(f"folha está '{linha[0]}'; esperado '{de}'")
    banco.execute("UPDATE folha SET status = ? WHERE id = ?", (para, folha_id))


def fechar_folha(banco: sqlite3.Connection, folha_id: int) -> None:
    """Fecha a folha calculada — a partir daqui não recalcula mais."""
    _mudar_status_folha(banco, folha_id, "CALCULADA", "FECHADA")


def pagar_folha(banco: sqlite3.Connection, folha_id: int) -> None:
    _mudar_status_folha(banco, folha_id, "FECHADA", "PAGA")


def total_folha(banco: sqlite3.Connection, folha_id: int) -> float:
    (total,) = banco.execute(
        "SELECT COALESCE(SUM(valor), 0) FROM folha_item WHERE folha_id = ?",
        (folha_id,),
    ).fetchone()
    return total
