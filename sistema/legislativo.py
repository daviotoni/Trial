"""Módulo legislativo: proposições, sessões, pautas e votações.

Cobre o coração da atividade-fim da Câmara (Diretoria de Plenário e
coordenadorias de Apoio Legislativo, Assuntos de Plenário e Atas e
Projetos, na estrutura da Lei 3.525/2025):

- apresentação de proposições com numeração sequencial por tipo/ano e
  autuação automática do processo legislativo correspondente;
- convocação de sessões (ordinárias/extraordinárias/solenes) numeradas
  por tipo e ano;
- montagem de pauta (ordem do dia);
- votação simbólica ou NOMINAL (voto individual por parlamentar), com
  apuração automática por maioria simples e atualização da situação da
  proposição.

Uso demonstrativo:
    python -m sistema.legislativo
"""

from __future__ import annotations

import sqlite3

from sistema import comissoes
from sistema.servicos import (
    RegraViolada, arquivar_processo, autuar_processo, concluir_processo,
    desarquivar_processo,
)

# Comissões permanentes temáticas do art. 33 do Regimento Interno
# (Resolução nº 1.835/2000, com a redação da Resolução nº 2.399/2013).
# Não confundir com as comissões administrativas do art. 45 da Lei 3.525/2025.
COMISSOES_PERMANENTES_REGIMENTAIS = [
    "Comissão de Legislação, Justiça e Redação Final",
    "Comissão de Finanças e Orçamento",
    "Comissão de Educação e Cultura",
    "Comissão de Saúde e Assistência Social",
    "Comissão de Transportes",
    "Comissão de Defesa do Consumidor",
    "Comissão de Obras e Serviços Públicos",
    "Comissão de Meio Ambiente e Qualidade de Vida",
    "Comissão de Fiscalização",
    "Comissão de Desenvolvimento Urbano",
    "Comissão dos Direitos da Mulher e da Criança e Adolescente",
    "Comissão da Defesa dos Direitos Humanos",
    "Comissão de Defesa dos Portadores de Necessidades Especiais",
    "Comissão de Segurança Alimentar e Nutricional",
    "Comissão de Segurança",
    "Comissão de Esporte, Lazer e Turismo",
    "Comissão de Prevenção e Combate às Drogas",
    "Comissão de Prevenção e Combate à Pirataria",
    "Comissão de Defesa dos Direitos dos Idosos",
    "Comissão de Defesa dos Direitos da Juventude",
]

# Tipos de proposição que exigem maioria absoluta dos MEMBROS da Câmara
# (art. 178 do Regimento: Projetos de Lei Complementar à Lei Orgânica).
TIPOS_MAIORIA_ABSOLUTA = {"PLC"}

# Catálogo das proposições que um gabinete pode apresentar (art. 87, §1º,
# e arts. 96-113 do Regimento Interno). `exige_texto` marca os projetos,
# que precisam de texto articulado (art. 92); `subtipos` são as espécies
# regimentais que a proposição deve declarar.
CATALOGO_PROPOSICOES = {
    "PELO": {"nome": "Proposta de Emenda à Lei Orgânica",
             "exige_texto": True, "subtipos": None,
             "base": "art. 87, §1º"},
    "PLC": {"nome": "Projeto de Lei Complementar à Lei Orgânica",
            "exige_texto": True, "subtipos": None,
            "base": "art. 87, §1º; art. 178 (maioria absoluta)"},
    "PL": {"nome": "Projeto de Lei", "exige_texto": True, "subtipos": None,
           "base": "arts. 92 e 96"},
    "PR": {"nome": "Projeto de Resolução", "exige_texto": True,
           "subtipos": None, "base": "art. 100"},
    "PDL": {"nome": "Projeto de Decreto Legislativo", "exige_texto": True,
            "subtipos": None, "base": "art. 99"},
    "INDICACAO": {"nome": "Indicação", "exige_texto": False,
                  "subtipos": {
                      "SIMPLES": "Encaminhada pelo Presidente ao Executivo "
                                 "(art. 102)",
                      "LEGISLATIVA": "Encaminhada à Comissão de Justiça "
                                     "(art. 103)"},
                  "base": "arts. 101-104"},
    "REQUERIMENTO": {"nome": "Requerimento", "exige_texto": False,
                     "subtipos": {
                         "DESPACHO_PRESIDENTE": "Sujeito a despacho do "
                                                "Presidente (arts. 108-110)",
                         "DELIBERACAO_PLENARIO": "Sujeito a deliberação do "
                                                 "Plenário (arts. 111-113)"},
                     "base": "art. 107"},
    "MOCAO": {"nome": "Moção", "exige_texto": False,
              "subtipos": {
                  "APLAUSO": "Aplauso/louvor",
                  "CONGRATULACOES": "Congratulações",
                  "PESAR": "Pesar",
                  "REPUDIO": "Repúdio",
                  "DESAPROVACAO": "Desaprovação (exige 1/3 — colher em "
                                  "papel nesta fase)"},
              "base": "arts. 105-106"},
}

REGIMES_TRAMITACAO = {"ORDINARIA", "PRIORIDADE", "ESPECIAL", "URGENCIA"}


# ------------------------------------------------------------------
# Parlamentares e legislaturas
# ------------------------------------------------------------------

def criar_legislatura(banco: sqlite3.Connection, numero: int,
                      inicio: str, fim: str) -> int:
    return banco.execute(
        "INSERT INTO legislatura (numero, inicio, fim) VALUES (?, ?, ?)",
        (numero, inicio, fim),
    ).lastrowid


def empossar(banco: sqlite3.Connection, nome: str, partido: str,
             legislatura_id: int, gabinete_unidade_id: int | None = None) -> int:
    """Cadastra o parlamentar e o mandato na legislatura. Devolve o id."""
    parlamentar_id = banco.execute(
        "INSERT INTO parlamentar (nome, partido) VALUES (?, ?)",
        (nome, partido),
    ).lastrowid
    banco.execute(
        "INSERT INTO mandato (parlamentar_id, legislatura_id, "
        "gabinete_unidade_id) VALUES (?, ?, ?)",
        (parlamentar_id, legislatura_id, gabinete_unidade_id),
    )
    return parlamentar_id


# ------------------------------------------------------------------
# Proposições
# ------------------------------------------------------------------

def apresentar_proposicao(
    banco: sqlite3.Connection,
    tipo: str,
    ementa: str,
    data: str,
    autor_parlamentar_id: int | None = None,
    unidade_protocolo_id: int | None = None,
) -> tuple[int, str]:
    """Protocola uma proposição. Devolve (id, 'TIPO numero/ano').

    Numera sequencialmente por tipo e ano e autua o processo legislativo
    correspondente no protocolo geral.
    """
    ano = int(data[:4])
    (ultimo,) = banco.execute(
        "SELECT COALESCE(MAX(numero), 0) FROM proposicao "
        "WHERE tipo = ? AND ano = ?", (tipo, ano),
    ).fetchone()
    numero = ultimo + 1

    processo_id = None
    if unidade_protocolo_id is not None:
        processo_id, _ = autuar_processo(
            banco, "LEGISLATIVO", f"{tipo} {numero}/{ano} — {ementa}",
            unidade_protocolo_id, data,
        )

    proposicao_id = banco.execute(
        "INSERT INTO proposicao (tipo, numero, ano, ementa, "
        "autor_parlamentar_id, processo_id) VALUES (?, ?, ?, ?, ?, ?)",
        (tipo, numero, ano, ementa, autor_parlamentar_id, processo_id),
    ).lastrowid
    return proposicao_id, f"{tipo} {numero}/{ano}"


# ------------------------------------------------------------------
# Sessões, pauta e votação
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# Gabinete: rascunhos e protocolo (arts. 87-92 do Regimento)
# ------------------------------------------------------------------

def parlamentar_do_gabinete(banco: sqlite3.Connection,
                            unidade_id: int) -> int | None:
    """Vereador titular do gabinete (mandato mais recente), ou None."""
    linha = banco.execute(
        "SELECT parlamentar_id FROM mandato WHERE gabinete_unidade_id = ? "
        "ORDER BY legislatura_id DESC LIMIT 1", (unidade_id,),
    ).fetchone()
    return linha[0] if linha else None


def _validar_tipo_e_subtipo(tipo: str, subtipo: str | None,
                            regime: str) -> dict:
    meta = CATALOGO_PROPOSICOES.get(tipo)
    if meta is None:
        raise RegraViolada(
            "tipo de proposição inválido para apresentação pelo gabinete")
    if regime not in REGIMES_TRAMITACAO:
        raise RegraViolada("regime deve ser ORDINARIA, PRIORIDADE, "
                           "ESPECIAL ou URGENCIA (art. 91)")
    if subtipo and (not meta["subtipos"] or subtipo not in meta["subtipos"]):
        raise RegraViolada(f"subtipo inválido para {tipo}")
    return meta


def criar_rascunho(
    banco: sqlite3.Connection,
    unidade_id: int,
    tipo: str,
    ementa: str,
    subtipo: str | None = None,
    texto: str | None = None,
    justificativa: str | None = None,
    regime: str = "ORDINARIA",
) -> int:
    """Cria um rascunho do gabinete: sem número, visível só ao setor autor.

    O rascunho exige apenas a ementa; texto e justificativa são cobrados
    no protocolo (arts. 88, §4º, e 92).
    """
    _validar_tipo_e_subtipo(tipo, subtipo, regime)
    if not ementa or not ementa.strip():
        raise RegraViolada("a ementa é obrigatória (art. 87, §3º)")
    return banco.execute(
        "INSERT INTO proposicao (tipo, subtipo, ementa, texto, "
        "justificativa, regime, unidade_autora_id, situacao) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'RASCUNHO')",
        (tipo, subtipo, ementa.strip(), texto, justificativa, regime,
         unidade_id),
    ).lastrowid


def _rascunho_do_setor(banco, rascunho_id, unidade_id):
    linha = banco.execute(
        "SELECT situacao, unidade_autora_id FROM proposicao WHERE id = ?",
        (rascunho_id,),
    ).fetchone()
    if linha is None:
        raise RegraViolada("rascunho inexistente")
    situacao, autora = linha
    if situacao != "RASCUNHO":
        raise RegraViolada("a proposição já foi protocolada")
    if autora != unidade_id:
        raise RegraViolada("o rascunho pertence a outro gabinete")


def atualizar_rascunho(banco: sqlite3.Connection, rascunho_id: int,
                       unidade_id: int, **campos) -> None:
    """Edita um rascunho do próprio gabinete (tipo, subtipo, ementa,
    texto, justificativa, regime)."""
    _rascunho_do_setor(banco, rascunho_id, unidade_id)
    permitidos = {"tipo", "subtipo", "ementa", "texto", "justificativa",
                  "regime"}
    atualizacao = {c: v for c, v in campos.items() if c in permitidos}
    if not atualizacao:
        return
    atual = banco.execute(
        "SELECT tipo, subtipo, regime FROM proposicao WHERE id = ?",
        (rascunho_id,),
    ).fetchone()
    tipo = atualizacao.get("tipo", atual[0])
    subtipo = atualizacao.get("subtipo", atual[1])
    regime = atualizacao.get("regime", atual[2]) or "ORDINARIA"
    _validar_tipo_e_subtipo(tipo, subtipo, regime)
    sets = ", ".join(f"{c} = ?" for c in atualizacao)
    banco.execute(
        f"UPDATE proposicao SET {sets} WHERE id = ?",
        (*atualizacao.values(), rascunho_id),
    )


def excluir_rascunho(banco: sqlite3.Connection, rascunho_id: int,
                     unidade_id: int) -> None:
    """Exclui um rascunho do próprio gabinete (nunca matéria protocolada)."""
    _rascunho_do_setor(banco, rascunho_id, unidade_id)
    banco.execute("DELETE FROM proposicao WHERE id = ?", (rascunho_id,))


def rascunhos_do_setor(banco: sqlite3.Connection,
                       unidade_id: int) -> list[dict]:
    """Rascunhos do gabinete, do mais recente para o mais antigo."""
    return [
        {"id": pid, "tipo": tipo, "subtipo": subtipo, "ementa": ementa,
         "texto": texto, "justificativa": justificativa, "regime": regime}
        for pid, tipo, subtipo, ementa, texto, justificativa, regime in
        banco.execute(
            "SELECT id, tipo, subtipo, ementa, texto, justificativa, regime "
            "FROM proposicao WHERE situacao = 'RASCUNHO' AND "
            "unidade_autora_id = ? ORDER BY id DESC", (unidade_id,),
        )
    ]


def protocolar_rascunho(banco: sqlite3.Connection, rascunho_id: int,
                        unidade_id: int, data: str) -> tuple[int, str]:
    """Protocola o rascunho: valida, numera, autua e define o autor.

    Validações do Regimento: justificativa obrigatória (art. 88, §4º),
    texto articulado para projetos (art. 92) e subtipo para as espécies
    que o exigem. A numeração sequencial por tipo/ano nasce aqui; o
    processo é autuado com origem no gabinete e entra no rito quando o
    tipo tiver fluxo configurado. Autor = vereador titular do gabinete.
    """
    from sistema import fluxo as fluxo_mod

    _rascunho_do_setor(banco, rascunho_id, unidade_id)
    tipo, subtipo, ementa, texto, justificativa = banco.execute(
        "SELECT tipo, subtipo, ementa, texto, justificativa "
        "FROM proposicao WHERE id = ?", (rascunho_id,),
    ).fetchone()
    meta = CATALOGO_PROPOSICOES[tipo]
    if not justificativa or not justificativa.strip():
        raise RegraViolada(
            "a justificativa é obrigatória para protocolar (art. 88, §4º)")
    if meta["exige_texto"] and (not texto or not texto.strip()):
        raise RegraViolada(
            "projetos exigem o texto articulado (art. 92)")
    if meta["subtipos"] and not subtipo:
        raise RegraViolada(
            f"{meta['nome']} exige a espécie (subtipo): "
            + ", ".join(meta["subtipos"]))

    ano = int(data[:4])
    (ultimo,) = banco.execute(
        "SELECT COALESCE(MAX(numero), 0) FROM proposicao "
        "WHERE tipo = ? AND ano = ?", (tipo, ano),
    ).fetchone()
    numero = ultimo + 1
    rotulo = f"{tipo} {numero}/{ano}"

    processo_id, _ = autuar_processo(
        banco, "LEGISLATIVO", f"{rotulo} — {ementa}", unidade_id, data)
    if banco.execute("SELECT 1 FROM tipo_processo WHERE codigo = ?",
                     (tipo,)).fetchone():
        fluxo_mod.vincular_tipo(banco, processo_id, tipo)

    banco.execute(
        "UPDATE proposicao SET numero = ?, ano = ?, processo_id = ?, "
        "autor_parlamentar_id = ?, situacao = 'EM_TRAMITACAO' WHERE id = ?",
        (numero, ano, processo_id,
         parlamentar_do_gabinete(banco, unidade_id), rascunho_id),
    )
    return rascunho_id, rotulo


# ------------------------------------------------------------------
# Bloco 3: emendas a matéria alheia (arts. 114-115 e 88, VIII)
# ------------------------------------------------------------------

# Espécies regimentais de emenda (art. 114). O SUBSTITUTIVO substitui a
# proposição por inteiro; as demais alteram partes dela.
ESPECIES_EMENDA = {
    "SUPRESSIVA": "Suprime parte da proposição",
    "SUBSTITUTIVA": "Substitui parte da proposição",
    "ADITIVA": "Acrescenta disposição à proposição",
    "MODIFICATIVA": "Altera a redação sem mudar a substância",
    "SUBSTITUTIVO": "Substitui integralmente a proposição",
}

# Só projetos recebem emenda (a espécie acessória pressupõe texto
# articulado a alterar — art. 92); indicações, moções e requerimentos não.
TIPOS_EMENDAVEIS = {"PELO", "PLC", "PL", "PR", "PDL"}


def apresentar_emenda(
    banco: sqlite3.Connection,
    unidade_id: int,
    proposicao_alvo_id: int,
    especie: str,
    texto: str,
    justificativa: str,
    data: str,
) -> tuple[int, str]:
    """Apresenta emenda a uma proposição em tramitação (arts. 114-115).

    Qualquer gabinete pode emendar matéria de outro (é o ponto do
    instituto). A emenda é acessória: aponta a matéria alvo e NÃO abre
    processo próprio — junta-se ao da principal. Texto e justificativa
    são obrigatórios; a pertinência com a matéria (art. 115) é juízo da
    comissão/Presidência na instrução. Devolve (id, rótulo).
    """
    if especie not in ESPECIES_EMENDA:
        raise RegraViolada("espécie de emenda inválida: use "
                           + ", ".join(ESPECIES_EMENDA))
    if not texto or not texto.strip():
        raise RegraViolada("a emenda exige o texto da alteração (art. 92)")
    if not justificativa or not justificativa.strip():
        raise RegraViolada("a justificativa é obrigatória (art. 88, §4º)")

    linha = banco.execute(
        """SELECT p.tipo, p.numero, p.ano, p.situacao,
                  (SELECT situacao FROM processo WHERE id = p.processo_id)
             FROM proposicao p WHERE p.id = ?""", (proposicao_alvo_id,),
    ).fetchone()
    if linha is None or linha[3] == "RASCUNHO" or linha[1] is None:
        raise RegraViolada("proposição alvo inexistente ou não protocolada")
    tipo_alvo, numero_alvo, ano_alvo, situacao_alvo, situacao_processo = linha
    if tipo_alvo not in TIPOS_EMENDAVEIS:
        raise RegraViolada(
            f"{tipo_alvo} não recebe emenda — só projetos "
            f"({', '.join(sorted(TIPOS_EMENDAVEIS))})")
    if situacao_alvo != "EM_TRAMITACAO" or \
            situacao_processo in ("ARQUIVADO", "CONCLUIDO"):
        raise RegraViolada(
            f"a proposição {tipo_alvo} {numero_alvo}/{ano_alvo} não está "
            "em tramitação")

    ano = int(data[:4])
    (ultimo,) = banco.execute(
        "SELECT COALESCE(MAX(numero), 0) FROM proposicao "
        "WHERE tipo = 'EMENDA' AND ano = ?", (ano,),
    ).fetchone()
    numero = ultimo + 1
    emenda_id = banco.execute(
        "INSERT INTO proposicao (tipo, subtipo, numero, ano, ementa, "
        "texto, justificativa, autor_parlamentar_id, unidade_autora_id, "
        "situacao, proposicao_alvo_id) "
        "VALUES ('EMENDA', ?, ?, ?, ?, ?, ?, ?, ?, 'EM_TRAMITACAO', ?)",
        (especie, numero, ano,
         f"Emenda {especie.lower()} ao {tipo_alvo} {numero_alvo}/{ano_alvo}",
         texto.strip(), justificativa.strip(),
         parlamentar_do_gabinete(banco, unidade_id), unidade_id,
         proposicao_alvo_id),
    ).lastrowid
    return emenda_id, (f"EMENDA {numero}/{ano} ao "
                       f"{tipo_alvo} {numero_alvo}/{ano_alvo}")


def emendas_da_proposicao(banco: sqlite3.Connection,
                          proposicao_id: int) -> list[dict]:
    """Emendas apresentadas à proposição, com espécie, autor e situação."""
    return [
        {"id": eid, "rotulo": f"EMENDA {numero}/{ano}", "especie": especie,
         "ementa": ementa, "texto": texto, "justificativa": justificativa,
         "autor": autor, "gabinete": gabinete, "situacao": situacao}
        for (eid, numero, ano, especie, ementa, texto, justificativa,
             autor, gabinete, situacao) in banco.execute(
            """SELECT e.id, e.numero, e.ano, e.subtipo, e.ementa, e.texto,
                      e.justificativa, pl.nome, u.nome, e.situacao
                 FROM proposicao e
                 LEFT JOIN parlamentar pl ON pl.id = e.autor_parlamentar_id
                 LEFT JOIN unidade u ON u.id = e.unidade_autora_id
                WHERE e.tipo = 'EMENDA' AND e.proposicao_alvo_id = ?
                ORDER BY e.id""", (proposicao_id,),
        )
    ]


def proposicoes_protocoladas(banco: sqlite3.Connection) -> list[dict]:
    """Proposições protocoladas (transparência ativa; base da tela de
    emendas). Exclui rascunhos e as próprias emendas."""
    return [
        {"id": pid, "rotulo": f"{tipo} {numero}/{ano}", "tipo": tipo,
         "ementa": ementa, "autor": autor, "gabinete": gabinete,
         "situacao": situacao, "regime": regime,
         "emendavel": (tipo in TIPOS_EMENDAVEIS
                       and situacao == "EM_TRAMITACAO"
                       and situacao_processo not in
                       ("ARQUIVADO", "CONCLUIDO"))}
        for (pid, tipo, numero, ano, ementa, autor, gabinete, situacao,
             regime, situacao_processo) in banco.execute(
            """SELECT p.id, p.tipo, p.numero, p.ano, p.ementa, pl.nome,
                      u.nome, p.situacao, p.regime,
                      (SELECT situacao FROM processo WHERE id = p.processo_id)
                 FROM proposicao p
                 LEFT JOIN parlamentar pl ON pl.id = p.autor_parlamentar_id
                 LEFT JOIN unidade u ON u.id = p.unidade_autora_id
                WHERE p.situacao <> 'RASCUNHO' AND p.numero IS NOT NULL
                  AND p.tipo <> 'EMENDA'
                ORDER BY p.id DESC""",
        )
    ]


# ------------------------------------------------------------------
# Recebimento/recusa da Presidência e recurso à CLJRF (art. 88, §1º)
# ------------------------------------------------------------------

def recusar_proposicao(banco: sqlite3.Connection, proposicao_id: int,
                       motivo: str, data: str) -> str:
    """Recusa formal da Presidência (art. 88, §1º). Devolve o rótulo.

    Cabe a matéria em tramitação (não a requerimento, que se resolve por
    despacho). A proposição vai a RECUSADA e o processo é arquivado; da
    recusa cabe recurso do autor à CLJRF. Uma proposição só passa uma vez
    pelo juízo de admissibilidade.
    """
    if not motivo or not motivo.strip():
        raise RegraViolada("a recusa exige fundamentação (art. 88, §1º)")
    linha = banco.execute(
        "SELECT tipo, numero, ano, situacao, processo_id FROM proposicao "
        "WHERE id = ?", (proposicao_id,)).fetchone()
    if linha is None or linha[1] is None:
        raise RegraViolada("proposição inexistente ou não protocolada")
    tipo, numero, ano, situacao, processo_id = linha
    if tipo == "REQUERIMENTO":
        raise RegraViolada(
            "requerimento sujeita-se a despacho do Presidente, não à recusa")
    if situacao != "EM_TRAMITACAO":
        raise RegraViolada("só cabe recusar matéria em tramitação")
    if banco.execute("SELECT 1 FROM recusa WHERE proposicao_id = ?",
                     (proposicao_id,)).fetchone():
        raise RegraViolada(
            "a proposição já passou pelo juízo de admissibilidade da "
            "Presidência")
    banco.execute(
        "INSERT INTO recusa (proposicao_id, motivo, data, situacao) "
        "VALUES (?, ?, ?, 'RECUSADA')", (proposicao_id, motivo.strip(), data))
    banco.execute("UPDATE proposicao SET situacao = 'RECUSADA' WHERE id = ?",
                  (proposicao_id,))
    if processo_id:
        (situacao_processo,) = banco.execute(
            "SELECT situacao FROM processo WHERE id = ?",
            (processo_id,)).fetchone()
        if situacao_processo in ("EM_TRAMITACAO", "SOBRESTADO", "CONCLUIDO"):
            arquivar_processo(banco, processo_id)
    return f"{tipo} {numero}/{ano}"


def _recusa_ativa(banco, proposicao_id):
    return banco.execute(
        "SELECT id, motivo, data, recurso_razoes, decisao, decisao_motivo, "
        "situacao FROM recusa WHERE proposicao_id = ? ORDER BY id DESC "
        "LIMIT 1", (proposicao_id,)).fetchone()


def recorrer_da_recusa(banco: sqlite3.Connection, proposicao_id: int,
                       unidade_id: int, razoes: str, data: str) -> str:
    """Recurso do autor à CLJRF contra a recusa (art. 88, §1º).

    Só o autor da matéria e só enquanto a recusa não foi recorrida. A
    proposição vai a EM_RECURSO e aguarda a decisão da Comissão de
    Legislação, Justiça e Redação Final.
    """
    if not razoes or not razoes.strip():
        raise RegraViolada("o recurso exige as razões (art. 88, §1º)")
    recusa = _recusa_ativa(banco, proposicao_id)
    if recusa is None or recusa[6] != "RECUSADA":
        raise RegraViolada(
            "não há recusa pendente de recurso para esta proposição")
    autora, autor_parlamentar = banco.execute(
        "SELECT unidade_autora_id, autor_parlamentar_id FROM proposicao "
        "WHERE id = ?", (proposicao_id,)).fetchone()
    titular = parlamentar_do_gabinete(banco, unidade_id)
    if autora != unidade_id and (autor_parlamentar is None
                                 or autor_parlamentar != titular):
        raise RegraViolada("só o autor pode recorrer da recusa")
    banco.execute(
        "UPDATE recusa SET recurso_razoes = ?, recurso_data = ?, "
        "situacao = 'EM_RECURSO' WHERE id = ?",
        (razoes.strip(), data, recusa[0]))
    banco.execute("UPDATE proposicao SET situacao = 'EM_RECURSO' WHERE id = ?",
                  (proposicao_id,))
    return "EM_RECURSO"


def decidir_recurso(banco: sqlite3.Connection, proposicao_id: int,
                    provido: bool, data: str, motivo: str | None = None) -> str:
    """Decisão da CLJRF sobre o recurso (art. 88, §1º).

    PROVIDO reverte a recusa: a proposição volta a tramitar e o processo
    é desarquivado. NEGADO mantém a recusa (definitiva). Devolve
    'PROVIDO' ou 'NEGADO'.
    """
    recusa = _recusa_ativa(banco, proposicao_id)
    if recusa is None or recusa[6] != "EM_RECURSO":
        raise RegraViolada("não há recurso pendente de decisão")
    (processo_id,) = banco.execute(
        "SELECT processo_id FROM proposicao WHERE id = ?",
        (proposicao_id,)).fetchone()
    if provido:
        banco.execute(
            "UPDATE recusa SET decisao = 'PROVIDO', decisao_motivo = ?, "
            "decisao_data = ?, situacao = 'REVERTIDA' WHERE id = ?",
            (motivo, data, recusa[0]))
        banco.execute(
            "UPDATE proposicao SET situacao = 'EM_TRAMITACAO' WHERE id = ?",
            (proposicao_id,))
        if processo_id:
            (situacao_processo,) = banco.execute(
                "SELECT situacao FROM processo WHERE id = ?",
                (processo_id,)).fetchone()
            if situacao_processo == "ARQUIVADO":
                desarquivar_processo(banco, processo_id)
        return "PROVIDO"
    banco.execute(
        "UPDATE recusa SET decisao = 'NEGADO', decisao_motivo = ?, "
        "decisao_data = ?, situacao = 'MANTIDA' WHERE id = ?",
        (motivo, data, recusa[0]))
    banco.execute("UPDATE proposicao SET situacao = 'RECUSADA' WHERE id = ?",
                  (proposicao_id,))
    return "NEGADO"


def proposicoes_para_recebimento(banco: sqlite3.Connection) -> list[dict]:
    """Matérias em tramitação que a Presidência ainda pode receber/recusar."""
    return [
        {"id": pid, "rotulo": f"{tipo} {numero}/{ano}", "tipo": tipo,
         "ementa": ementa, "autor": autor, "gabinete": gabinete,
         "regime": regime}
        for (pid, tipo, numero, ano, ementa, autor, gabinete, regime) in
        banco.execute(
            """SELECT p.id, p.tipo, p.numero, p.ano, p.ementa, pl.nome,
                      u.nome, p.regime
                 FROM proposicao p
                 LEFT JOIN parlamentar pl ON pl.id = p.autor_parlamentar_id
                 LEFT JOIN unidade u ON u.id = p.unidade_autora_id
                WHERE p.situacao = 'EM_TRAMITACAO' AND p.tipo <> 'REQUERIMENTO'
                  AND p.numero IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM recusa r
                                   WHERE r.proposicao_id = p.id)
                ORDER BY p.id DESC""",
        )
    ]


def recursos_pendentes(banco: sqlite3.Connection) -> list[dict]:
    """Recursos aguardando decisão da CLJRF (setor de comissões)."""
    return [
        {"id": pid, "rotulo": f"{tipo} {numero}/{ano}", "ementa": ementa,
         "autor": autor, "gabinete": gabinete, "motivo": motivo,
         "recurso_razoes": razoes, "recusa_data": data,
         "recurso_data": recurso_data}
        for (pid, tipo, numero, ano, ementa, autor, gabinete, motivo,
             razoes, data, recurso_data) in banco.execute(
            """SELECT p.id, p.tipo, p.numero, p.ano, p.ementa, pl.nome,
                      u.nome, r.motivo, r.recurso_razoes, r.data,
                      r.recurso_data
                 FROM recusa r
                 JOIN proposicao p ON p.id = r.proposicao_id
                 LEFT JOIN parlamentar pl ON pl.id = p.autor_parlamentar_id
                 LEFT JOIN unidade u ON u.id = p.unidade_autora_id
                WHERE r.situacao = 'EM_RECURSO'
                ORDER BY r.id""",
        )
    ]


# ------------------------------------------------------------------
# Bloco 4: requerimentos derivados, despacho do Presidente e
# acompanhamento (arts. 90, 93-95 e 107-113 do Regimento Interno)
# ------------------------------------------------------------------

# O que o autor pode requerer sobre uma proposição sua já protocolada.
# A espécie (subtipo) segue o Regimento: retirada de matéria SEM parecer
# é despacho do Presidente (art. 110, I); com parecer, deliberação do
# Plenário (art. 111); inclusão em pauta e desarquivamento deliberam-se
# em Plenário (arts. 111-113).
FINALIDADES_REQUERIMENTO = {
    "RETIRADA": {
        "nome": "Retirada da proposição",
        "ementa": "Requer a retirada da proposição {alvo}",
        "base": "arts. 110, I, e 111, III",
    },
    "INCLUSAO_PAUTA": {
        "nome": "Inclusão na Ordem do Dia",
        "ementa": "Requer a inclusão da proposição {alvo} na Ordem do Dia",
        "base": "arts. 111-113",
    },
    "DESARQUIVAMENTO": {
        "nome": "Desarquivamento da proposição",
        "ementa": "Requer o desarquivamento da proposição {alvo}",
        "base": "arts. 111-113",
    },
}


def _alvo_do_gabinete(banco, proposicao_alvo_id, unidade_id):
    """Carrega a proposição alvo validando que pertence ao gabinete."""
    linha = banco.execute(
        """SELECT p.tipo, p.numero, p.ano, p.situacao, p.processo_id,
                  p.unidade_autora_id, p.autor_parlamentar_id,
                  (SELECT situacao FROM processo WHERE id = p.processo_id)
             FROM proposicao p WHERE p.id = ?""", (proposicao_alvo_id,),
    ).fetchone()
    if linha is None or linha[3] == "RASCUNHO" or linha[1] is None:
        raise RegraViolada("proposição alvo inexistente ou não protocolada")
    titular = parlamentar_do_gabinete(banco, unidade_id)
    if linha[5] != unidade_id and (linha[6] is None or linha[6] != titular):
        raise RegraViolada(
            "só o autor pode requerer sobre a própria proposição nesta fase")
    return {"tipo": linha[0], "rotulo": f"{linha[0]} {linha[1]}/{linha[2]}",
            "situacao": linha[3], "processo_id": linha[4],
            "situacao_processo": linha[7]}


def requerimento_derivado(
    banco: sqlite3.Connection,
    unidade_id: int,
    proposicao_alvo_id: int,
    finalidade: str,
    data: str,
    justificativa: str,
) -> tuple[int, str]:
    """Protocola um REQUERIMENTO do autor sobre proposição sua.

    Finalidades: RETIRADA, INCLUSAO_PAUTA e DESARQUIVAMENTO (arts.
    107-113). O requerimento nasce protocolado (numerado e autuado com
    origem no gabinete); a espécie é definida pela regra regimental. O
    efeito sobre a matéria alvo só ocorre no deferimento (despacho) ou
    na aprovação em Plenário.
    """
    meta = FINALIDADES_REQUERIMENTO.get(finalidade)
    if meta is None:
        raise RegraViolada("finalidade deve ser RETIRADA, INCLUSAO_PAUTA "
                           "ou DESARQUIVAMENTO")
    if not justificativa or not justificativa.strip():
        raise RegraViolada(
            "a justificativa é obrigatória (art. 88, §4º)")
    alvo = _alvo_do_gabinete(banco, proposicao_alvo_id, unidade_id)

    if finalidade == "DESARQUIVAMENTO":
        if alvo["situacao_processo"] != "ARQUIVADO":
            raise RegraViolada(
                "desarquivamento só cabe a proposição com processo "
                "arquivado")
    else:
        if alvo["situacao"] != "EM_TRAMITACAO" or \
                alvo["situacao_processo"] in ("ARQUIVADO", "CONCLUIDO"):
            raise RegraViolada(
                f"a proposição {alvo['rotulo']} não está em tramitação")
        if finalidade == "INCLUSAO_PAUTA" and \
                comissoes.exige_parecer(alvo["tipo"]) and \
                not comissoes.tem_parecer_aprovado(banco, proposicao_alvo_id):
            raise RegraViolada(
                "inclusão em pauta exige parecer de comissão aprovado "
                "(ou regime de urgência)")

    pendente = banco.execute(
        "SELECT COUNT(*) FROM proposicao WHERE proposicao_alvo_id = ? AND "
        "finalidade = ? AND situacao = 'EM_TRAMITACAO'",
        (proposicao_alvo_id, finalidade),
    ).fetchone()[0]
    if pendente:
        raise RegraViolada(
            "já há requerimento pendente com a mesma finalidade sobre "
            "essa proposição")

    tem_parecer = banco.execute(
        "SELECT COUNT(*) FROM parecer WHERE proposicao_id = ?",
        (proposicao_alvo_id,),
    ).fetchone()[0] > 0
    if finalidade == "RETIRADA" and not tem_parecer:
        subtipo = "DESPACHO_PRESIDENTE"     # art. 110, I
    else:
        subtipo = "DELIBERACAO_PLENARIO"    # arts. 111-113

    ano = int(data[:4])
    (ultimo,) = banco.execute(
        "SELECT COALESCE(MAX(numero), 0) FROM proposicao "
        "WHERE tipo = 'REQUERIMENTO' AND ano = ?", (ano,),
    ).fetchone()
    numero = ultimo + 1
    rotulo = f"REQUERIMENTO {numero}/{ano}"
    ementa = meta["ementa"].format(alvo=alvo["rotulo"])

    processo_id, _ = autuar_processo(
        banco, "LEGISLATIVO", f"{rotulo} — {ementa}", unidade_id, data)
    if banco.execute("SELECT 1 FROM tipo_processo WHERE codigo = "
                     "'REQUERIMENTO'").fetchone():
        from sistema import fluxo as fluxo_mod
        fluxo_mod.vincular_tipo(banco, processo_id, "REQUERIMENTO")

    requerimento_id = banco.execute(
        "INSERT INTO proposicao (tipo, subtipo, numero, ano, ementa, "
        "justificativa, autor_parlamentar_id, unidade_autora_id, "
        "processo_id, situacao, finalidade, proposicao_alvo_id) "
        "VALUES ('REQUERIMENTO', ?, ?, ?, ?, ?, ?, ?, ?, "
        "'EM_TRAMITACAO', ?, ?)",
        (subtipo, numero, ano, ementa, justificativa.strip(),
         parlamentar_do_gabinete(banco, unidade_id), unidade_id,
         processo_id, finalidade, proposicao_alvo_id),
    ).lastrowid
    return requerimento_id, rotulo


def _aplicar_efeito_requerimento(banco: sqlite3.Connection,
                                 requerimento_id: int) -> None:
    """Aplica sobre a matéria alvo o efeito do requerimento deferido/aprovado.

    RETIRADA: a proposição sai de tramitação (situação RETIRADA) e o
    processo é arquivado. DESARQUIVAMENTO: o processo volta a tramitar.
    INCLUSAO_PAUTA: sem efeito automático — o deferimento instrui a
    Diretoria de Plenário a pautar.
    """
    linha = banco.execute(
        "SELECT finalidade, proposicao_alvo_id FROM proposicao WHERE id = ?",
        (requerimento_id,),
    ).fetchone()
    if not linha or not linha[0] or not linha[1]:
        return
    finalidade, alvo_id = linha
    alvo = banco.execute(
        "SELECT situacao, processo_id, (SELECT situacao FROM processo "
        "WHERE id = processo_id) FROM proposicao WHERE id = ?", (alvo_id,),
    ).fetchone()
    if alvo is None:
        return
    situacao_alvo, processo_alvo, situacao_processo = alvo
    if finalidade == "RETIRADA":
        banco.execute(
            "UPDATE proposicao SET situacao = 'RETIRADA' WHERE id = ?",
            (alvo_id,))
        if processo_alvo and situacao_processo not in (None, "ARQUIVADO"):
            arquivar_processo(banco, processo_alvo)
    elif finalidade == "DESARQUIVAMENTO":
        if processo_alvo and situacao_processo == "ARQUIVADO":
            desarquivar_processo(banco, processo_alvo)
        if situacao_alvo == "RETIRADA":
            banco.execute(
                "UPDATE proposicao SET situacao = 'EM_TRAMITACAO' "
                "WHERE id = ?", (alvo_id,))


def despachar_requerimento(
    banco: sqlite3.Connection,
    requerimento_id: int,
    resultado: str,
    data: str,
    texto: str | None = None,
) -> str:
    """Despacho do Presidente sobre requerimento (arts. 108-110).

    Só a espécie DESPACHO_PRESIDENTE se resolve aqui; as de deliberação
    vão a Plenário (pauta + votação). DEFERIDO aplica o efeito sobre a
    matéria alvo; em ambos os resultados o processo do requerimento é
    concluído.
    """
    if resultado not in ("DEFERIDO", "INDEFERIDO"):
        raise RegraViolada("resultado deve ser DEFERIDO ou INDEFERIDO")
    linha = banco.execute(
        "SELECT tipo, subtipo, situacao, processo_id, (SELECT situacao "
        "FROM processo WHERE id = processo_id) FROM proposicao WHERE id = ?",
        (requerimento_id,),
    ).fetchone()
    if linha is None or linha[0] != "REQUERIMENTO":
        raise RegraViolada("requerimento inexistente")
    tipo, subtipo, situacao, processo_id, situacao_processo = linha
    if subtipo != "DESPACHO_PRESIDENTE":
        raise RegraViolada(
            "requerimento sujeito a deliberação do Plenário, não a "
            "despacho (art. 111)")
    if situacao != "EM_TRAMITACAO":
        raise RegraViolada(f"requerimento já {situacao.lower()}")

    banco.execute(
        "UPDATE proposicao SET situacao = ?, despacho = ?, "
        "despacho_data = ? WHERE id = ?",
        (resultado, texto, data, requerimento_id))
    if resultado == "DEFERIDO":
        _aplicar_efeito_requerimento(banco, requerimento_id)
    if processo_id and situacao_processo in ("EM_TRAMITACAO", "SOBRESTADO"):
        concluir_processo(banco, processo_id)
    return resultado


def despachos_pendentes(banco: sqlite3.Connection) -> list[dict]:
    """Requerimentos aguardando despacho do Presidente (arts. 108-110)."""
    return [
        {"id": rid, "rotulo": f"REQUERIMENTO {numero}/{ano}",
         "ementa": ementa, "justificativa": justificativa,
         "autor": autor, "gabinete": gabinete, "finalidade": finalidade,
         "alvo": alvo}
        for (rid, numero, ano, ementa, justificativa, autor, gabinete,
             finalidade, alvo) in banco.execute(
            """SELECT p.id, p.numero, p.ano, p.ementa, p.justificativa,
                      pl.nome, u.nome, p.finalidade,
                      (SELECT a.tipo || ' ' || a.numero || '/' || a.ano
                         FROM proposicao a WHERE a.id = p.proposicao_alvo_id)
                 FROM proposicao p
                 LEFT JOIN parlamentar pl ON pl.id = p.autor_parlamentar_id
                 LEFT JOIN unidade u ON u.id = p.unidade_autora_id
                WHERE p.tipo = 'REQUERIMENTO'
                  AND p.subtipo = 'DESPACHO_PRESIDENTE'
                  AND p.situacao = 'EM_TRAMITACAO'
                ORDER BY p.id""",
        )
    ]


def acompanhamento_do_gabinete(banco: sqlite3.Connection, unidade_id: int,
                               referencia: str) -> list[dict]:
    """Acompanhamento rico das proposições do gabinete (arts. 90 e 93-95).

    Para cada proposição protocolada do setor: situação, localização
    atual do processo, pareceres, ALERTAS (arquivamento, prazo vencido,
    parecer contrário) e as finalidades de requerimento derivado
    cabíveis no estado atual. `referencia` (ISO) é a data usada para
    apurar prazos vencidos.
    """
    linhas = banco.execute(
        """SELECT p.id, p.tipo, p.subtipo, p.numero, p.ano, p.ementa,
                  p.regime, p.situacao, p.finalidade, p.despacho,
                  p.despacho_data, p.processo_id, pr.situacao,
                  COALESCE(
                    (SELECT ud.nome FROM tramitacao t
                       JOIN unidade ud ON ud.id = t.unidade_destino_id
                      WHERE t.processo_id = pr.id
                      ORDER BY t.id DESC LIMIT 1),
                    (SELECT uo.nome FROM unidade uo
                      WHERE uo.id = pr.unidade_origem_id)),
                  (SELECT t.prazo FROM tramitacao t
                    WHERE t.processo_id = pr.id
                      AND t.data_recebimento IS NULL AND t.prazo IS NOT NULL
                    ORDER BY t.id DESC LIMIT 1),
                  (SELECT a.tipo || ' ' || a.numero || '/' || a.ano
                     FROM proposicao a WHERE a.id = p.proposicao_alvo_id)
             FROM proposicao p
             LEFT JOIN processo pr ON pr.id = p.processo_id
            WHERE p.situacao <> 'RASCUNHO' AND p.numero IS NOT NULL
              AND (p.unidade_autora_id = ? OR pr.unidade_origem_id = ?)
            ORDER BY p.id DESC""", (unidade_id, unidade_id),
    ).fetchall()

    resultado = []
    for (pid, tipo, subtipo, numero, ano, ementa, regime, situacao,
         finalidade, despacho, despacho_data, processo_id,
         situacao_processo, localizacao, prazo_pendente, alvo) in linhas:
        pareceres = comissoes.pareceres(banco, pid)
        alertas, acoes = [], []
        recurso_disponivel = False
        recusa = _recusa_ativa(banco, pid)
        recusa_info = None
        if recusa:
            recusa_info = {"motivo": recusa[1], "situacao": recusa[6],
                           "decisao": recusa[4],
                           "decisao_motivo": recusa[5]}
            if recusa[6] == "RECUSADA":
                alertas.append({
                    "tipo": "RECUSADA",
                    "mensagem": f"Recusada pela Presidência: {recusa[1]} — "
                                "cabe recurso à CLJRF (art. 88, §1º)"})
                recurso_disponivel = True
            elif recusa[6] == "EM_RECURSO":
                alertas.append({
                    "tipo": "EM_RECURSO",
                    "mensagem": "Em recurso à CLJRF (aguarda decisão)"})
            elif recusa[6] == "MANTIDA":
                alertas.append({
                    "tipo": "RECUSA_MANTIDA",
                    "mensagem": "Recusa mantida pela CLJRF — matéria "
                                "definitivamente rejeitada (art. 88, §1º)"})
            elif recusa[6] == "REVERTIDA":
                alertas.append({
                    "tipo": "RECUSA_REVERTIDA",
                    "mensagem": "Recurso provido pela CLJRF — matéria "
                                "readmitida e de volta à tramitação"})

        if situacao_processo == "ARQUIVADO" and situacao not in (
                "RETIRADA", "RECUSADA", "EM_RECURSO"):
            alertas.append({
                "tipo": "ARQUIVADA",
                "mensagem": "Processo arquivado — cabe requerimento de "
                            "desarquivamento (arts. 111-113)"})
        if prazo_pendente and prazo_pendente < referencia:
            alertas.append({
                "tipo": "PRAZO_VENCIDO",
                "mensagem": f"Parada em {localizacao} com prazo vencido "
                            f"desde {prazo_pendente}"})
        for parecer in pareceres:
            if parecer["tipo"] in ("CONTRARIO", "PELA_REJEICAO") and \
                    parecer["situacao"] != "REJEITADO":
                alertas.append({
                    "tipo": "PARECER_CONTRARIO",
                    "mensagem": f"{parecer['comissao']}: parecer "
                                f"{parecer['tipo'].lower()} "
                                f"({parecer['situacao'].lower()})"})

        # Matéria em ciclo de recusa/recurso não aceita requerimento
        # comum — só o recurso à CLJRF a move (art. 88, §1º).
        em_recusa = recusa_info is not None and recusa_info["situacao"] in (
            "RECUSADA", "EM_RECURSO", "MANTIDA")
        if not finalidade and not em_recusa:  # requerimento não deriva outro
            if situacao_processo == "ARQUIVADO":
                acoes.append("DESARQUIVAMENTO")
            elif situacao == "EM_TRAMITACAO" and \
                    situacao_processo != "CONCLUIDO":
                acoes.append("RETIRADA")
                # Emenda não entra em pauta sozinha: é votada com a
                # matéria principal (arts. 114-115).
                if tipo != "EMENDA" and (
                        not comissoes.exige_parecer(tipo) or
                        comissoes.tem_parecer_aprovado(banco, pid)):
                    acoes.append("INCLUSAO_PAUTA")

        pendentes = [
            f"REQUERIMENTO {n}/{a} ({f})"
            for n, a, f in banco.execute(
                "SELECT numero, ano, finalidade FROM proposicao "
                "WHERE proposicao_alvo_id = ? AND finalidade IS NOT NULL "
                "AND situacao = 'EM_TRAMITACAO'", (pid,),
            )
        ]
        emendas = [
            {"rotulo": e["rotulo"], "especie": e["especie"],
             "autor": e["autor"] or e["gabinete"],
             "situacao": e["situacao"]}
            for e in emendas_da_proposicao(banco, pid)
        ] if tipo in TIPOS_EMENDAVEIS else []

        resultado.append({
            "id": pid, "rotulo": f"{tipo} {numero}/{ano}", "tipo": tipo,
            "subtipo": subtipo, "ementa": ementa, "regime": regime,
            "situacao": situacao, "situacao_processo": situacao_processo,
            "localizacao": localizacao, "pareceres": pareceres,
            "alertas": alertas, "acoes_possiveis": acoes,
            "finalidade": finalidade, "alvo": alvo, "despacho": despacho,
            "despacho_data": despacho_data,
            "requerimentos_pendentes": pendentes,
            "emendas": emendas,
            "recusa": recusa_info, "recurso_disponivel": recurso_disponivel,
        })
    return resultado


def convocar_sessao(banco: sqlite3.Connection, tipo: str, data: str) -> tuple[int, int]:
    """Convoca sessão numerada sequencialmente por tipo/ano. Devolve (id, número)."""
    ano = data[:4]
    (ultimo,) = banco.execute(
        "SELECT COALESCE(MAX(numero), 0) FROM sessao "
        "WHERE tipo = ? AND data LIKE ?", (tipo, ano + "%"),
    ).fetchone()
    numero = ultimo + 1
    sessao_id = banco.execute(
        "INSERT INTO sessao (tipo, numero, data) VALUES (?, ?, ?)",
        (tipo, numero, data),
    ).lastrowid
    return sessao_id, numero


def pautar(banco: sqlite3.Connection, sessao_id: int, proposicao_id: int,
           urgencia: bool = False) -> int:
    """Inclui a proposição no fim da ordem do dia da sessão.

    Matéria de mérito (PL, PLC, PDL, PR) só entra em Ordem do Dia com
    **parecer aprovado** de comissão (art. 33 e segs. do Regimento
    Interno). O regime de `urgencia=True` dispensa o parecer prévio
    (pareceres podem ser proferidos oralmente em Plenário).
    """
    linha = banco.execute(
        "SELECT tipo, situacao FROM proposicao WHERE id = ?", (proposicao_id,)
    ).fetchone()
    if linha is None:
        raise RegraViolada("proposição inexistente")
    tipo_proposicao, situacao_proposicao = linha
    if situacao_proposicao == "RASCUNHO":
        raise RegraViolada("rascunho não protocolado não entra em pauta")
    if situacao_proposicao in ("RECUSADA", "EM_RECURSO", "RETIRADA"):
        raise RegraViolada(
            "matéria recusada, em recurso ou retirada não entra em pauta")
    if not urgencia and comissoes.exige_parecer(tipo_proposicao) \
            and not comissoes.tem_parecer_aprovado(banco, proposicao_id):
        raise RegraViolada(
            f"{tipo_proposicao} só entra em pauta com parecer de comissão "
            "aprovado (ou em regime de urgência)")

    (ordem,) = banco.execute(
        "SELECT COALESCE(MAX(ordem), 0) + 1 FROM pauta_item WHERE sessao_id = ?",
        (sessao_id,),
    ).fetchone()
    return banco.execute(
        "INSERT INTO pauta_item (sessao_id, proposicao_id, ordem) "
        "VALUES (?, ?, ?)", (sessao_id, proposicao_id, ordem),
    ).lastrowid


def votar(
    banco: sqlite3.Connection,
    sessao_id: int,
    proposicao_id: int,
    modalidade: str,
    votos: dict[int, str] | None = None,
    resultado_simbolico: str | None = None,
) -> str:
    """Registra a votação e apura o resultado.

    - NOMINAL: exige `votos` {parlamentar_id: 'SIM'|'NAO'|'ABSTENCAO'};
      apura por maioria simples (SIM > NAO; empate rejeita). Para tipos
      que exigem maioria absoluta (art. 178 do Regimento — PLC), a
      aprovação requer SIM de mais da metade dos MEMBROS da Câmara
      (contados pelos mandatos vigentes), não apenas dos presentes.
    - SIMBOLICA: exige `resultado_simbolico` ('APROVADA'|'REJEITADA'),
      proclamado pela Presidência sem registro individual; vedada para
      tipos que exigem maioria absoluta.

    Atualiza a situação da proposição e devolve o resultado.
    """
    (tipo_proposicao,) = banco.execute(
        "SELECT tipo FROM proposicao WHERE id = ?", (proposicao_id,)
    ).fetchone()
    exige_absoluta = tipo_proposicao in TIPOS_MAIORIA_ABSOLUTA
    pautada = banco.execute(
        "SELECT COUNT(*) FROM pauta_item WHERE sessao_id = ? AND "
        "proposicao_id = ?", (sessao_id, proposicao_id),
    ).fetchone()[0]
    if not pautada:
        raise RegraViolada("proposição não consta da ordem do dia da sessão")

    ja_votada = banco.execute(
        "SELECT COUNT(*) FROM votacao WHERE sessao_id = ? AND proposicao_id = ?",
        (sessao_id, proposicao_id),
    ).fetchone()[0]
    if ja_votada:
        raise RegraViolada("proposição já votada nesta sessão")

    if modalidade == "NOMINAL":
        if not votos:
            raise RegraViolada("votação nominal exige votos individuais")
        sim = sum(1 for valor in votos.values() if valor == "SIM")
        nao = sum(1 for valor in votos.values() if valor == "NAO")
        if exige_absoluta:
            # Membros da Câmara = mandatos da legislatura dos votantes (a
            # mais recente do primeiro votante), para não somar mandatos de
            # legislaturas diferentes. Sem mandato conhecido, conta todos.
            primeiro = next(iter(votos))
            (membros,) = banco.execute(
                """SELECT COUNT(*) FROM mandato WHERE legislatura_id =
                     (SELECT legislatura_id FROM mandato
                       WHERE parlamentar_id = ?
                       ORDER BY legislatura_id DESC LIMIT 1)""",
                (primeiro,),
            ).fetchone()
            if not membros:
                (membros,) = banco.execute(
                    "SELECT COUNT(*) FROM mandato").fetchone()
            resultado = "APROVADA" if sim > membros / 2 else "REJEITADA"
        else:
            resultado = "APROVADA" if sim > nao else "REJEITADA"
    elif modalidade == "SIMBOLICA":
        if exige_absoluta:
            raise RegraViolada(
                f"{tipo_proposicao} exige votação nominal por maioria "
                "absoluta (art. 178 do Regimento Interno)"
            )
        if resultado_simbolico not in ("APROVADA", "REJEITADA"):
            raise RegraViolada("votação simbólica exige o resultado proclamado")
        resultado = resultado_simbolico
    else:
        raise RegraViolada("modalidade deve ser NOMINAL ou SIMBOLICA")

    votacao_id = banco.execute(
        "INSERT INTO votacao (sessao_id, proposicao_id, modalidade, resultado) "
        "VALUES (?, ?, ?, ?)", (sessao_id, proposicao_id, modalidade, resultado),
    ).lastrowid
    if modalidade == "NOMINAL":
        banco.executemany(
            "INSERT INTO voto (votacao_id, parlamentar_id, valor) "
            "VALUES (?, ?, ?)",
            [(votacao_id, pid, valor) for pid, valor in votos.items()],
        )

    banco.execute(
        "UPDATE proposicao SET situacao = ? WHERE id = ?",
        (resultado, proposicao_id),
    )
    # Requerimento derivado aprovado em Plenário (arts. 111-113) aplica o
    # efeito sobre a matéria alvo (retirada/desarquivamento). Proposições
    # comuns não têm finalidade e a chamada é um no-op.
    if resultado == "APROVADA":
        _aplicar_efeito_requerimento(banco, proposicao_id)
    return resultado


def placar(banco: sqlite3.Connection, sessao_id: int,
           proposicao_id: int) -> dict:
    """Placar da votação: modalidade, resultado e votos individuais."""
    linha = banco.execute(
        "SELECT id, modalidade, resultado FROM votacao "
        "WHERE sessao_id = ? AND proposicao_id = ?",
        (sessao_id, proposicao_id),
    ).fetchone()
    if linha is None:
        raise RegraViolada("votação não encontrada")
    votacao_id, modalidade, resultado = linha
    votos = [
        {"parlamentar": nome, "partido": partido, "voto": valor}
        for nome, partido, valor in banco.execute(
            """SELECT p.nome, p.partido, v.valor FROM voto v
               JOIN parlamentar p ON p.id = v.parlamentar_id
               WHERE v.votacao_id = ? ORDER BY p.nome""", (votacao_id,),
        )
    ]
    contagem = {"SIM": 0, "NAO": 0, "ABSTENCAO": 0}
    for voto in votos:
        contagem[voto["voto"]] += 1
    return {"modalidade": modalidade, "resultado": resultado,
            "contagem": contagem, "votos": votos}


# ------------------------------------------------------------------
# Demonstração
# ------------------------------------------------------------------

def main() -> None:
    from sistema.demo import criar_banco

    banco = criar_banco()
    legislatura = criar_legislatura(banco, 1, "2025-01-01", "2028-12-31")

    # 29 gabinetes na estrutura (Anexo I) — vereadores fictícios p/ demonstração.
    bancada = [
        ("Vereador(a) Exemplo %02d" % i, ["PDX", "PYZ", "PAB"][i % 3])
        for i in range(1, 12)
    ]
    ids = [empossar(banco, nome, partido, legislatura)
           for nome, partido in bancada]

    (protocolo,) = banco.execute(
        "SELECT id FROM unidade WHERE nome = 'Coordenadoria da Secretaria-Geral'"
    ).fetchone()
    proposicao, rotulo = apresentar_proposicao(
        banco, "PL", "Institui o programa municipal de merenda orgânica",
        "2025-09-10", autor_parlamentar_id=ids[0],
        unidade_protocolo_id=protocolo,
    )

    # Instrução no setor de comissões antes da Ordem do Dia (art. 33 do
    # Regimento): o parecer é marcado com a comissão temática.
    parecer = comissoes.emitir_parecer(
        banco, proposicao, "Comissão de Educação e Cultura", "FAVORAVEL",
        "Parecer favorável à proposição.", "2025-09-15",
        relator_parlamentar_id=ids[1])
    comissoes.aprovar_parecer(banco, parecer)

    sessao, numero = convocar_sessao(banco, "ORDINARIA", "2025-09-16")
    pautar(banco, sessao, proposicao)

    votos = {pid: ("SIM" if i % 3 != 2 else "NAO")
             for i, pid in enumerate(ids)}
    resultado = votar(banco, sessao, proposicao, "NOMINAL", votos)

    print("=" * 60)
    print(f"Sessão Ordinária nº {numero}/2025 — votação de {rotulo}")
    print("=" * 60)
    apuracao = placar(banco, sessao, proposicao)
    for voto in apuracao["votos"]:
        print(f"  {voto['parlamentar']:<26} {voto['partido']:<4} {voto['voto']}")
    contagem = apuracao["contagem"]
    print(f"\n  Placar: SIM {contagem['SIM']} × NAO {contagem['NAO']} "
          f"(abstenções: {contagem['ABSTENCAO']})")
    print(f"  Resultado: {resultado}")
    banco.close()


if __name__ == "__main__":
    main()
