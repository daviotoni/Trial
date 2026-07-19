"""Módulo de controle interno e transparência.

Atende a Controladoria-Geral (trilha de auditoria, pendências) e a
Coordenadoria de Publicações e Transparência (registro do que foi
publicado no portal, LAI/Lei 14.133 art. 94 — divulgação de contratos).
"""

from __future__ import annotations

import sqlite3


def publicar(banco: sqlite3.Connection, tipo: str, referencia: str,
             data: str, url: str | None = None) -> int:
    """Registra uma publicação no portal da transparência."""
    return banco.execute(
        "INSERT INTO publicacao (tipo, referencia, url, data) "
        "VALUES (?, ?, ?, ?)", (tipo, referencia, url, data),
    ).lastrowid


def pendencias_publicacao(banco: sqlite3.Connection) -> dict:
    """O que já deveria estar no portal e ainda não tem registro de
    publicação: contratos (Lei 14.133/2021, art. 94) e folhas fechadas."""
    contratos = [
        {"contrato_id": cid, "objeto": objeto, "valor": valor}
        for cid, objeto, valor in banco.execute(
            """SELECT ct.id, c.objeto, ct.valor
               FROM contrato ct JOIN contratacao c ON c.id = ct.contratacao_id
               WHERE NOT EXISTS (SELECT 1 FROM publicacao p
                                  WHERE p.tipo = 'contrato'
                                    AND p.referencia = 'contrato:' || ct.id)"""
        )
    ]
    folhas = [
        {"folha_id": fid, "competencia": competencia}
        for fid, competencia in banco.execute(
            """SELECT id, competencia FROM folha
               WHERE status IN ('CALCULADA', 'FECHADA', 'PAGA')
                 AND NOT EXISTS (SELECT 1 FROM publicacao p
                                  WHERE p.tipo = 'folha'
                                    AND p.referencia = 'folha:' || folha.id)"""
        )
    ]
    return {"contratos": contratos, "folhas": folhas}


def trilha_auditoria(banco: sqlite3.Connection, limite: int = 50) -> list[dict]:
    """Últimos eventos da trilha de auditoria (controle interno)."""
    return [
        {"tabela": tabela, "registro_id": registro, "operacao": operacao,
         "usuario": usuario, "datahora": datahora, "detalhes": detalhes}
        for tabela, registro, operacao, usuario, datahora, detalhes in
        banco.execute(
            "SELECT tabela, registro_id, operacao, usuario, datahora, "
            "detalhes FROM auditoria ORDER BY id DESC LIMIT ?", (limite,),
        )
    ]


def painel(banco: sqlite3.Connection) -> dict:
    """Números gerais da Casa para o painel de gestão."""
    def um(sql):
        return banco.execute(sql).fetchone()[0]

    return {
        "unidades": um("SELECT COUNT(*) FROM unidade"),
        "vagas_anexo_i": um("SELECT COALESCE(SUM(quantidade_vagas),0) FROM cargo "
                            "WHERE tipo != 'EFETIVO'"),
        "provimentos_ativos": um("SELECT COUNT(*) FROM provimento "
                                 "WHERE data_fim IS NULL"),
        "servidores": um("SELECT COUNT(*) FROM servidor"),
        "processos": um("SELECT COUNT(*) FROM processo"),
        "processos_em_tramitacao": um("SELECT COUNT(*) FROM processo "
                                      "WHERE situacao = 'EM_TRAMITACAO'"),
        # Rascunhos de gabinete não são públicos (só contam protocoladas).
        "proposicoes": um("SELECT COUNT(*) FROM proposicao "
                          "WHERE situacao <> 'RASCUNHO'"),
        "sessoes": um("SELECT COUNT(*) FROM sessao"),
        "votacoes": um("SELECT COUNT(*) FROM votacao"),
        "contratacoes": um("SELECT COUNT(*) FROM contratacao"),
        "contratos": um("SELECT COUNT(*) FROM contrato"),
        "valor_contratado": um("SELECT COALESCE(SUM(valor),0) FROM contrato"),
        "valor_empenhado": um("SELECT COALESCE(SUM(valor),0) FROM empenho"),
        "publicacoes": um("SELECT COUNT(*) FROM publicacao"),
        "eventos_auditoria": um("SELECT COUNT(*) FROM auditoria"),
    }
