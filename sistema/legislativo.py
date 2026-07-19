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
from sistema.servicos import RegraViolada, autuar_processo

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
