"""API REST do sistema de gestão da CMDC (biblioteca padrão, sem dependências).

Expõe a camada de serviços (`sistema.servicos`) por HTTP/JSON:

    GET  /organograma                     árvore de unidades
    GET  /unidades                        lista de unidades
    GET  /cargos                          cargos com vagas disponíveis
    GET  /servidores                      lista de servidores
    POST /servidores                      cadastra servidor
    POST /provimentos                     nomeação (valida regras da lei)
    POST /provimentos/{id}/exoneracao     exoneração
    POST /processos                       autuação (número sequencial/ano)
    GET  /processos/{id}                  processo + trilha de tramitação
    POST /processos/{id}/tramitacoes      tramitar
    POST /folhas                          calcula folha da competência
    GET  /folhas/{id}                     itens da folha calculada
    POST /legislaturas                    abre legislatura
    GET  /parlamentares                   lista parlamentares
    POST /parlamentares                   empossa parlamentar (mandato)
    POST /proposicoes                     protocola proposição (nº por tipo/ano)
    POST /sessoes                         convoca sessão
    POST /sessoes/{id}/pauta              inclui proposição na ordem do dia
    POST /sessoes/{id}/votacoes           vota (nominal ou simbólica)
    GET  /sessoes/{id}/votacoes/{prop}    placar da votação

Autenticação e alçadas por setor (Lei 3.525/2025):
    POST /login {login, senha}  →  {token, perfil}
    POST /usuarios              cria usuário (perfil ADMIN)
    Demais escritas exigem "Authorization: Bearer <token>" e perfil com
    alçada na área (RH, PROTOCOLO, LEGISLATIVO, COMPRAS, CONTROLE, ADMIN).
    Consultas de transparência ativa (organograma, cargos, painel, placar,
    pendências) são públicas por princípio (LAI).

Regras violadas retornam 422 com a mensagem legal; sem login, 401; sem
alçada, 403; recurso ausente, 404. No primeiro uso é criado o usuário
"admin" com a senha inicial documentada em sistema/autenticacao.py.

Uso:
    python -m sistema.api               # sobe em http://127.0.0.1:8000
    python -m sistema.api --porta 8080
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PAGINA_WEB = Path(__file__).parent / "web" / "index.html"

from sistema import (
    autenticacao, comissoes, compras, fluxo, legislativo, servicos,
    transparencia,
)
from sistema.autenticacao import AcessoNegado, NaoAutenticado
from sistema.demo import criar_banco
from sistema.servicos import RegraViolada


class Recurso404(Exception):
    pass


def _hoje() -> str:
    from datetime import date
    return date.today().isoformat()


class Aplicacao:
    """Rotas e acesso ao banco (uma conexão SQLite protegida por lock)."""

    def __init__(self, caminho_banco: str = ":memory:"):
        self.banco = criar_banco(caminho_banco, multithread=True)
        self.trava = threading.Lock()
        self.sessoes = autenticacao.Sessoes()
        self.usuario_atual: dict | None = None
        self.query_atual: dict = {}
        if autenticacao.garantir_admin_inicial(self.banco):
            self.banco.commit()

    # ------------------------ autenticação --------------------------

    def login(self, dados):
        usuario = autenticacao.autenticar(
            self.banco, dados["login"], dados["senha"])
        if usuario is None:
            raise NaoAutenticado("credenciais inválidas")
        return {"token": self.sessoes.abrir(usuario),
                "perfil": usuario["perfil"]}

    def _exigir_admin(self):
        # Gerir acessos/logins é privativo do administrador — nenhum setor
        # enxerga ou opera a gestão de usuários de outro (nem a própria).
        if self.usuario_atual["perfil"] != "ADMIN":
            raise AcessoNegado(
                "a gestão de acessos e logins é privativa do administrador")

    def criar_usuario(self, dados):
        self._exigir_admin()
        # O acesso vem da unidade (setor). O 'perfil' é rótulo legado: só
        # importa distinguir ADMIN. Sem perfil e com unidade → não-admin.
        perfil = dados.get("perfil")
        unidade_id = dados.get("unidade_id")
        if not perfil:
            if unidade_id:
                perfil = "LEGISLATIVO"  # rótulo neutro; alçada vem da unidade
            else:
                raise RegraViolada("informe o setor do usuário")
        try:
            uid = autenticacao.criar_usuario(
                self.banco, dados["login"], dados["senha"], perfil,
                dados.get("servidor_id"), unidade_id)
        except ValueError as erro:
            raise RegraViolada(str(erro))
        self.banco.commit()
        return {"id": uid}

    def listar_usuarios(self):
        self._exigir_admin()
        # Inclui os desativados: a tela de gestão precisa vê-los para
        # reativar. `ativo` diferencia na interface.
        return [
            {"id": uid, "login": login, "perfil": perfil,
             "unidade": unidade, "unidade_id": unidade_id, "ativo": ativo}
            for uid, login, perfil, unidade, unidade_id, ativo in
            self.banco.execute(
                """SELECT u.id, u.login, u.perfil, un.nome, u.unidade_id,
                          u.ativo
                     FROM usuario u LEFT JOIN unidade un ON un.id = u.unidade_id
                    ORDER BY u.ativo DESC, u.login""")
        ]

    def _alvo_gestao_usuario(self, usuario_id):
        """Regra de gestão: contas ADMIN só são geridas por outro ADMIN."""
        linha = self.banco.execute(
            "SELECT perfil FROM usuario WHERE id = ?", (usuario_id,)
        ).fetchone()
        if linha is None:
            raise Recurso404()
        if linha[0] == "ADMIN" and self.usuario_atual["perfil"] != "ADMIN":
            raise AcessoNegado(
                "contas de administrador só podem ser alteradas por outro "
                "administrador")

    def editar_usuario(self, usuario_id: int, dados):
        """Edita o acesso: setor (unidade_id), senha e/ou ativo (0/1)."""
        self._exigir_admin()
        self._alvo_gestao_usuario(usuario_id)
        try:
            login = autenticacao.atualizar_usuario(
                self.banco, usuario_id,
                unidade_id=(dados["unidade_id"] if "unidade_id" in dados
                            else ...),
                senha=dados.get("senha"), ativo=dados.get("ativo"))
        except ValueError as erro:
            raise RegraViolada(str(erro))
        self.banco.commit()
        # O acesso mudou: derruba as sessões abertas desse login.
        self.sessoes.encerrar_do_login(login)
        return {"id": usuario_id, "login": login}

    def excluir_usuario(self, usuario_id: int):
        self._exigir_admin()
        self._alvo_gestao_usuario(usuario_id)
        try:
            login = autenticacao.excluir_usuario(self.banco, usuario_id)
        except ValueError as erro:
            raise RegraViolada(str(erro))
        self.banco.commit()
        self.sessoes.encerrar_do_login(login)
        return {"id": usuario_id, "login": login, "excluido": True}

    def eu(self):
        """Identidade e alçada do usuário logado (para a interface)."""
        u = self.usuario_atual
        unidade = None
        if u.get("unidade_id"):
            linha = self.banco.execute(
                "SELECT nome FROM unidade WHERE id = ?", (u["unidade_id"],)
            ).fetchone()
            unidade = linha[0] if linha else None
        return {
            "login": u["login"], "perfil": u["perfil"],
            "unidade_id": u.get("unidade_id"), "unidade": unidade,
            "areas": sorted(autenticacao.areas_do_usuario(self.banco, u)),
            "acoes": sorted(autenticacao.acoes_da_unidade(self.banco, u)),
        }

    # -------------------------- consultas --------------------------

    def organograma(self):
        linhas = self.banco.execute(
            "SELECT id, nome, sigla, grau, tipo, unidade_pai_id FROM unidade "
            "ORDER BY id"
        ).fetchall()
        nos = {
            uid: {"id": uid, "nome": nome, "sigla": sigla, "grau": grau,
                  "tipo": tipo, "subunidades": []}
            for uid, nome, sigla, grau, tipo, _ in linhas
        }
        raiz = None
        for uid, *_resto, pai in linhas:
            if pai is None:
                raiz = nos[uid]
            else:
                nos[pai]["subunidades"].append(nos[uid])
        return raiz

    def unidades(self):
        return [
            {"id": u, "nome": n, "sigla": s, "grau": g, "tipo": t}
            for u, n, s, g, t in self.banco.execute(
                "SELECT id, nome, sigla, grau, tipo FROM unidade ORDER BY id"
            )
        ]

    def cargos(self):
        return [
            {"id": cid, "denominacao": den, "tipo": tipo, "simbolo": simbolo,
             "vagas": vagas, "vagas_disponiveis": vagas - ocupadas}
            for cid, den, tipo, simbolo, vagas, ocupadas in self.banco.execute(
                """SELECT c.id, c.denominacao, c.tipo, c.simbolo_codigo,
                          c.quantidade_vagas,
                          (SELECT COUNT(*) FROM provimento p
                            WHERE p.cargo_id = c.id AND p.data_fim IS NULL)
                   FROM cargo c ORDER BY c.id"""
            )
        ]

    def servidores(self):
        return [
            {"id": sid, "nome": nome, "matricula": mat, "vinculo": vinc,
             "data_admissao": adm}
            for sid, nome, mat, vinc, adm in self.banco.execute(
                "SELECT id, nome, matricula, vinculo, data_admissao "
                "FROM servidor ORDER BY id"
            )
        ]

    def listar_processos(self, filtros):
        return servicos.buscar_processos(self.banco, filtros)

    def listar_contratacoes(self):
        return [
            {"id": cid, "numero": f"{modalidade} {numero}/{ano}",
             "objeto": objeto, "valor_estimado": valor, "situacao": situacao}
            for cid, modalidade, numero, ano, objeto, valor, situacao in
            self.banco.execute(
                "SELECT id, modalidade, numero, ano, objeto, valor_estimado, "
                "situacao FROM contratacao ORDER BY ano DESC, numero DESC "
                "LIMIT 100")
        ]

    def listar_folhas(self):
        return [
            {"id": fid, "competencia": competencia, "status": status,
             "total": total or 0}
            for fid, competencia, status, total in self.banco.execute(
                """SELECT f.id, f.competencia, f.status,
                          (SELECT SUM(valor) FROM folha_item
                            WHERE folha_id = f.id)
                   FROM folha f ORDER BY f.competencia DESC LIMIT 60""")
        ]

    def processo(self, processo_id: int):
        linha = self.banco.execute(
            """SELECT p.numero, p.ano, p.tipo, p.assunto, p.interessado,
                      p.situacao, p.data_autuacao,
                      COALESCE(
                        (SELECT ud.nome FROM tramitacao t
                           JOIN unidade ud ON ud.id = t.unidade_destino_id
                          WHERE t.processo_id = p.id
                          ORDER BY t.id DESC LIMIT 1),
                        (SELECT uo.nome FROM unidade uo
                          WHERE uo.id = p.unidade_origem_id))
                 FROM processo p WHERE p.id = ?""", (processo_id,)
        ).fetchone()
        if linha is None:
            raise Recurso404
        numero, ano, tipo, assunto, interessado, situacao, autuacao, loc = linha
        trilha = [
            {"id": tid, "de": origem, "para": destino, "despacho": despacho,
             "data": data, "prazo": prazo, "recebido_em": recebido}
            for tid, origem, destino, despacho, data, prazo, recebido in
            self.banco.execute(
                """SELECT t.id, o.nome, d.nome, t.despacho, t.data_envio,
                          t.prazo, t.data_recebimento
                   FROM tramitacao t
                   JOIN unidade o ON o.id = t.unidade_origem_id
                   JOIN unidade d ON d.id = t.unidade_destino_id
                   WHERE t.processo_id = ? ORDER BY t.id""", (processo_id,)
            )
        ]
        return {"id": processo_id, "numero": f"{numero}/{ano}", "tipo": tipo,
                "assunto": assunto, "interessado": interessado,
                "situacao": situacao, "data_autuacao": autuacao,
                "localizacao": loc, "tramitacoes": trilha,
                "documentos": servicos.documentos_do_processo(
                    self.banco, processo_id)}

    def juntar_documento(self, processo_id: int, dados):
        autenticacao.exigir(self.banco, self.usuario_atual, "PROTOCOLO")
        did = servicos.juntar_documento(
            self.banco, processo_id, dados.get("tipo", ""),
            dados.get("titulo", ""), dados.get("data") or _hoje(),
            dados.get("autor"))
        self.banco.commit()
        return {"id": did}

    def folha(self, folha_id: int):
        cab = self.banco.execute(
            "SELECT competencia, status FROM folha WHERE id = ?", (folha_id,)
        ).fetchone()
        if cab is None:
            raise Recurso404
        itens = [
            {"servidor": nome, "rubrica": rubrica, "base": base,
             "percentual": perc, "valor": valor}
            for nome, rubrica, base, perc, valor in self.banco.execute(
                """SELECT s.nome, fi.rubrica_codigo, fi.base_calculo,
                          fi.percentual, fi.valor
                   FROM folha_item fi JOIN servidor s ON s.id = fi.servidor_id
                   WHERE fi.folha_id = ? ORDER BY s.nome, fi.id""", (folha_id,)
            )
        ]
        return {"id": folha_id, "competencia": cab[0], "status": cab[1],
                "itens": itens,
                "total": servicos.total_folha(self.banco, folha_id)}

    # -------------------------- comandos ---------------------------

    def criar_servidor(self, dados):
        cursor = self.banco.execute(
            "INSERT INTO servidor (nome, matricula, vinculo, data_admissao, "
            "vencimento_base) VALUES (?, ?, ?, ?, ?)",
            (dados["nome"], dados.get("matricula"), dados["vinculo"],
             dados["data_admissao"], dados.get("vencimento_base")),
        )
        self.banco.commit()
        return {"id": cursor.lastrowid}

    def nomear(self, dados):
        provimento = servicos.nomear(
            self.banco, dados["servidor_id"], dados["cargo_id"],
            dados["unidade_id"], dados["ato"], dados["data_inicio"],
        )
        self.banco.commit()
        return {"id": provimento}

    def exonerar(self, provimento_id: int, dados):
        servicos.exonerar(self.banco, provimento_id, dados["data_fim"])
        self.banco.commit()
        return {"id": provimento_id, "encerrado_em": dados["data_fim"]}

    def autuar(self, dados):
        pid, numero = servicos.autuar_processo(
            self.banco, dados["tipo"], dados["assunto"],
            dados["unidade_origem_id"], dados["data_autuacao"],
            dados.get("interessado"),
        )
        self.banco.commit()
        return {"id": pid, "numero": numero}

    def tramitar(self, processo_id: int, dados):
        autenticacao.exigir_posse(self.banco, self.usuario_atual, processo_id)
        tid = servicos.tramitar(
            self.banco, processo_id, dados["unidade_destino_id"],
            dados.get("despacho", ""), dados["data_envio"],
            dados.get("prazo"),
        )
        self.banco.commit()
        return {"id": tid}

    def processos_em_atraso(self, dados):
        return servicos.processos_em_atraso(
            self.banco, self.query_atual.get("referencia", [""])[0] or _hoje())

    def painel_protocolo(self):
        # Dashboard operacional do balcão de protocolo.
        por_situacao = {
            situacao: total for situacao, total in self.banco.execute(
                "SELECT situacao, COUNT(*) FROM processo GROUP BY situacao")}
        recentes = servicos.buscar_processos(self.banco, {})[:8]
        em_atraso = servicos.processos_em_atraso(self.banco, _hoje())
        return {"por_situacao": por_situacao, "recentes": recentes,
                "em_atraso": em_atraso, "total": sum(por_situacao.values())}

    # -------------------- fluxo e competências ---------------------

    def tipos_processo(self):
        return [
            {"codigo": cod, "nome": nome, "dominio": dom}
            for cod, nome, dom in self.banco.execute(
                "SELECT codigo, nome, dominio FROM tipo_processo ORDER BY id")
        ]

    def etapas_do_tipo(self, codigo: str):
        return fluxo.etapas(self.banco, codigo)

    def competencias_da_unidade(self, unidade_id: int):
        return fluxo.competencias_da_unidade(self.banco, unidade_id)

    def vincular_tipo(self, processo_id: int, dados):
        fluxo.vincular_tipo(self.banco, processo_id, dados["tipo"])
        self.banco.commit()
        return {"processo_id": processo_id, "tipo": dados["tipo"]}

    def proxima_etapa(self, processo_id: int):
        prox = fluxo.proxima_etapa(self.banco, processo_id)
        return prox if prox is not None else {"proxima_etapa": None}

    def caixa(self):
        """Processos que estão AGORA na unidade do usuário logado.

        É a "caixa do setor": cada um com a próxima etapa do rito, para o
        servidor conduzir só o que está com ele.
        """
        u = self.usuario_atual
        uid = u.get("unidade_id")
        if uid:
            linhas = self.banco.execute(
                """SELECT p.id, p.numero, p.ano, p.assunto, p.data_autuacao
                     FROM processo p
                    WHERE p.situacao = 'EM_TRAMITACAO' AND COALESCE(
                      (SELECT unidade_destino_id FROM tramitacao t
                        WHERE t.processo_id = p.id ORDER BY t.id DESC LIMIT 1),
                      p.unidade_origem_id) = ?
                    ORDER BY p.id""", (uid,),
            ).fetchall()
        else:
            # Sem lotação (admin): mostra tudo que está em tramitação.
            linhas = self.banco.execute(
                "SELECT id, numero, ano, assunto, data_autuacao FROM processo "
                "WHERE situacao = 'EM_TRAMITACAO' ORDER BY id"
            ).fetchall()
        caixa = []
        for pid, numero, ano, assunto, data in linhas:
            prox = fluxo.proxima_etapa(self.banco, pid)
            caixa.append({
                "id": pid, "numero": f"{numero}/{ano}", "assunto": assunto,
                "data_autuacao": data,
                "proxima_unidade": prox["unidade"] if prox else None,
                "proxima_acao": prox["acao"] if prox else None,
            })
        return caixa

    def minhas_proposicoes(self):
        """Todas as proposições/processos ORIGINADOS pelo setor do usuário,
        onde quer que estejam agora — o acompanhamento completo.

        Diferente da caixa (o que está com o setor agora), aqui o gabinete
        vê tudo o que apresentou e a localização atual de cada um.
        """
        u = self.usuario_atual
        uid = u.get("unidade_id")
        if not uid:
            return []
        linhas = self.banco.execute(
            """SELECT p.id, p.numero, p.ano, p.assunto, p.situacao,
                      COALESCE(
                        (SELECT ud.nome FROM tramitacao t
                           JOIN unidade ud ON ud.id = t.unidade_destino_id
                          WHERE t.processo_id = p.id ORDER BY t.id DESC LIMIT 1),
                        (SELECT uo.nome FROM unidade uo
                          WHERE uo.id = p.unidade_origem_id)),
                      (SELECT pr.tipo || ' ' || pr.numero || '/' || pr.ano
                         FROM proposicao pr WHERE pr.processo_id = p.id LIMIT 1)
                 FROM processo p
                WHERE p.unidade_origem_id = ?
                ORDER BY p.id DESC""", (uid,),
        ).fetchall()
        return [
            {"id": pid, "numero": f"{numero}/{ano}", "assunto": assunto,
             "situacao": situacao, "localizacao": loc, "proposicao": prop}
            for pid, numero, ano, assunto, situacao, loc, prop in linhas
        ]

    # ------------------ gabinete: rascunhos ------------------------

    def tipos_proposicao(self):
        """Catálogo regimental das proposições (art. 87, §1º)."""
        return [
            {"codigo": codigo, "nome": meta["nome"],
             "exige_texto": meta["exige_texto"],
             "subtipos": meta["subtipos"], "base": meta["base"]}
            for codigo, meta in legislativo.CATALOGO_PROPOSICOES.items()
        ]

    def _unidade_do_usuario(self):
        uid = self.usuario_atual.get("unidade_id")
        if not uid:
            raise RegraViolada("operação exige login lotado num setor")
        return uid

    def listar_rascunhos(self):
        return legislativo.rascunhos_do_setor(
            self.banco, self._unidade_do_usuario())

    def criar_rascunho(self, dados):
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "APRESENTAR_PROPOSICAO")
        rid = legislativo.criar_rascunho(
            self.banco, self._unidade_do_usuario(), dados["tipo"],
            dados.get("ementa", ""), dados.get("subtipo"),
            dados.get("texto"), dados.get("justificativa"),
            dados.get("regime", "ORDINARIA"))
        self.banco.commit()
        return {"id": rid}

    def atualizar_rascunho(self, rascunho_id: int, dados):
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "APRESENTAR_PROPOSICAO")
        legislativo.atualizar_rascunho(
            self.banco, rascunho_id, self._unidade_do_usuario(), **dados)
        self.banco.commit()
        return {"id": rascunho_id}

    def excluir_rascunho(self, rascunho_id: int):
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "APRESENTAR_PROPOSICAO")
        legislativo.excluir_rascunho(
            self.banco, rascunho_id, self._unidade_do_usuario())
        self.banco.commit()
        return {"id": rascunho_id, "excluido": True}

    def apresentar_rascunho(self, rascunho_id: int, dados):
        # O gabinete apresenta; a numeração/autuação é do Protocolo.
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "APRESENTAR_PROPOSICAO")
        situacao = legislativo.apresentar_rascunho(
            self.banco, rascunho_id, self._unidade_do_usuario())
        self.banco.commit()
        return {"id": rascunho_id, "situacao": situacao}

    def proposicoes_apresentadas(self):
        autenticacao.exigir(self.banco, self.usuario_atual, "PROTOCOLO")
        return legislativo.proposicoes_apresentadas(self.banco)

    def autuar_proposicao(self, proposicao_id: int, dados):
        # Autuação e numeração são atos do Protocolo (art. 37); a matéria
        # nasce no Protocolo, que dá o andamento inicial.
        autenticacao.exigir(self.banco, self.usuario_atual, "PROTOCOLO")
        _, rotulo = legislativo.autuar_proposicao(
            self.banco, proposicao_id,
            legislativo._unidade_protocolo(self.banco),
            dados.get("data") or _hoje())
        self.banco.commit()
        return {"id": proposicao_id, "rotulo": rotulo}

    # ------------------- emendas (arts. 114-115) ---------------------

    def tipos_emenda(self):
        """Espécies regimentais de emenda (art. 114)."""
        return [{"codigo": codigo, "descricao": descricao}
                for codigo, descricao in
                legislativo.ESPECIES_EMENDA.items()]

    def listar_proposicoes(self):
        """Proposições protocoladas (transparência ativa; tela de emendas)."""
        return legislativo.proposicoes_protocoladas(self.banco)

    def apresentar_emenda(self, proposicao_alvo_id: int, dados):
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "APRESENTAR_PROPOSICAO")
        eid, rotulo = legislativo.apresentar_emenda(
            self.banco, self._unidade_do_usuario(), proposicao_alvo_id,
            dados["especie"], dados.get("texto", ""),
            dados.get("justificativa", ""), dados.get("data") or _hoje())
        self.banco.commit()
        return {"id": eid, "rotulo": rotulo}

    def emendas_da_proposicao(self, proposicao_id: int):
        return legislativo.emendas_da_proposicao(self.banco, proposicao_id)

    # ------------- gabinete: acompanhamento e requerimentos ----------

    def acompanhamento(self, dados):
        """Acompanhamento rico das proposições do setor (Bloco 4)."""
        referencia = self.query_atual.get("referencia", [""])[0] or \
            dados.get("referencia") or _hoje()
        return legislativo.acompanhamento_do_gabinete(
            self.banco, self._unidade_do_usuario(), referencia)

    def requerimento_derivado(self, proposicao_alvo_id: int, dados):
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "APRESENTAR_PROPOSICAO")
        rid, rotulo = legislativo.requerimento_derivado(
            self.banco, self._unidade_do_usuario(), proposicao_alvo_id,
            dados["finalidade"], dados.get("data") or _hoje(),
            dados.get("justificativa", ""))
        self.banco.commit()
        return {"id": rid, "rotulo": rotulo}

    def despachos_pendentes(self):
        autenticacao.exigir_acao(self.banco, self.usuario_atual, "DESPACHAR")
        return legislativo.despachos_pendentes(self.banco)

    # ------------- recusa da Presidência e recurso à CLJRF -----------

    def proposicoes_para_recebimento(self):
        autenticacao.exigir_acao(self.banco, self.usuario_atual, "DESPACHAR")
        return legislativo.proposicoes_para_recebimento(self.banco)

    def recusar_proposicao(self, proposicao_id: int, dados):
        autenticacao.exigir_acao(self.banco, self.usuario_atual, "DESPACHAR")
        rotulo = legislativo.recusar_proposicao(
            self.banco, proposicao_id, dados.get("motivo", ""),
            dados.get("data") or _hoje())
        self.banco.commit()
        return {"id": proposicao_id, "rotulo": rotulo, "situacao": "RECUSADA"}

    def recorrer_da_recusa(self, proposicao_id: int, dados):
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "APRESENTAR_PROPOSICAO")
        situacao = legislativo.recorrer_da_recusa(
            self.banco, proposicao_id, self._unidade_do_usuario(),
            dados.get("razoes", ""), dados.get("data") or _hoje())
        self.banco.commit()
        return {"id": proposicao_id, "situacao": situacao}

    def recursos_pendentes(self):
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "EMITIR_PARECER")
        return legislativo.recursos_pendentes(self.banco)

    def decidir_recurso(self, proposicao_id: int, dados):
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "EMITIR_PARECER")
        resultado = legislativo.decidir_recurso(
            self.banco, proposicao_id, bool(dados.get("provido")),
            dados.get("data") or _hoje(), dados.get("motivo"))
        self.banco.commit()
        return {"id": proposicao_id, "resultado": resultado}

    def despachar_requerimento(self, requerimento_id: int, dados):
        autenticacao.exigir_acao(self.banco, self.usuario_atual, "DESPACHAR")
        resultado = legislativo.despachar_requerimento(
            self.banco, requerimento_id, dados["resultado"],
            dados.get("data") or _hoje(), dados.get("texto"))
        self.banco.commit()
        return {"id": requerimento_id, "resultado": resultado}

    def apresentar_do_setor(self, dados):
        """O setor (ex.: gabinete) apresenta uma proposição de autoria própria.

        Cria a proposição numerada e autua o processo COM ORIGEM no próprio
        setor, vinculando o rito quando houver — assim a matéria entra na
        caixa do setor e pode ser encaminhada.
        """
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "APRESENTAR_PROPOSICAO")
        unidade = self.usuario_atual.get("unidade_id")
        tipo = dados["tipo"]
        proposicao_id, rotulo = legislativo.apresentar_proposicao(
            self.banco, tipo, dados["ementa"], dados["data"],
            unidade_protocolo_id=unidade)
        linha = self.banco.execute(
            "SELECT processo_id FROM proposicao WHERE id = ?", (proposicao_id,)
        ).fetchone()
        tem_rito = self.banco.execute(
            "SELECT 1 FROM tipo_processo WHERE codigo = ?", (tipo,)).fetchone()
        if linha and linha[0] and tem_rito:
            fluxo.vincular_tipo(self.banco, linha[0], tipo)
        self.banco.commit()
        return {"id": proposicao_id, "rotulo": rotulo}

    def tramitar_pelo_fluxo(self, processo_id: int, dados):
        autenticacao.exigir_posse(self.banco, self.usuario_atual, processo_id)
        etapa = fluxo.tramitar_pelo_fluxo(
            self.banco, processo_id, dados["data_envio"],
            dados.get("despacho", ""))
        self.banco.commit()
        return etapa

    def receber_tramitacao(self, tramitacao_id: int, dados):
        linha = self.banco.execute(
            "SELECT processo_id FROM tramitacao WHERE id = ?", (tramitacao_id,)
        ).fetchone()
        if linha:
            autenticacao.exigir_posse(self.banco, self.usuario_atual, linha[0])
        servicos.receber_tramitacao(self.banco, tramitacao_id,
                                    dados["data_recebimento"])
        self.banco.commit()
        return {"id": tramitacao_id}

    def excluir_processo(self, processo_id: int):
        # Ato privativo do administrador: apaga registros de vez (limpeza
        # de autuações erradas/testes) e deixa rastro na auditoria.
        if self.usuario_atual["perfil"] != "ADMIN":
            raise AcessoNegado(
                "a exclusão de processos é privativa do administrador")
        from datetime import datetime
        resumo = servicos.excluir_processo(
            self.banco, processo_id, self.usuario_atual["login"],
            datetime.now().isoformat(timespec="seconds"))
        self.banco.commit()
        return {"id": processo_id, "excluido": True, **resumo}

    def situacao_processo(self, processo_id: int, acao: str):
        {"arquivamento": servicos.arquivar_processo,
         "conclusao": servicos.concluir_processo,
         "desarquivamento": servicos.desarquivar_processo}[acao](
            self.banco, processo_id)
        self.banco.commit()
        return self.processo(processo_id)

    def situacao_folha(self, folha_id: int, acao: str):
        {"fechamento": servicos.fechar_folha,
         "pagamento": servicos.pagar_folha}[acao](self.banco, folha_id)
        self.banco.commit()
        return {"id": folha_id}

    def calcular_folha(self, dados):
        folha_id = servicos.calcular_folha(
            self.banco, dados["competencia"], dados["percentual_gal"],
        )
        self.banco.commit()
        return {"id": folha_id, "total": servicos.total_folha(self.banco, folha_id)}

    # ------------------------ legislativo --------------------------

    def parlamentares(self):
        return [
            {"id": pid, "nome": nome, "partido": partido}
            for pid, nome, partido in self.banco.execute(
                "SELECT id, nome, partido FROM parlamentar ORDER BY nome"
            )
        ]

    def empossar(self, dados):
        parlamentar_id = legislativo.empossar(
            self.banco, dados["nome"], dados.get("partido"),
            dados["legislatura_id"], dados.get("gabinete_unidade_id"),
        )
        self.banco.commit()
        return {"id": parlamentar_id}

    def criar_legislatura(self, dados):
        legislatura_id = legislativo.criar_legislatura(
            self.banco, dados["numero"], dados["inicio"], dados["fim"],
        )
        self.banco.commit()
        return {"id": legislatura_id}

    def apresentar_proposicao(self, dados):
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "APRESENTAR_PROPOSICAO")
        proposicao_id, rotulo = legislativo.apresentar_proposicao(
            self.banco, dados["tipo"], dados["ementa"], dados["data"],
            dados.get("autor_parlamentar_id"),
            dados.get("unidade_protocolo_id"),
        )
        self.banco.commit()
        return {"id": proposicao_id, "rotulo": rotulo}

    def convocar_sessao(self, dados):
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "CONVOCAR_SESSAO")
        sessao_id, numero = legislativo.convocar_sessao(
            self.banco, dados["tipo"], dados["data"],
        )
        self.banco.commit()
        return {"id": sessao_id, "numero": numero}

    def pautar(self, sessao_id: int, dados):
        autenticacao.exigir_acao(self.banco, self.usuario_atual, "PAUTAR")
        item = legislativo.pautar(
            self.banco, sessao_id, dados["proposicao_id"],
            urgencia=bool(dados.get("urgencia", False)))
        self.banco.commit()
        return {"id": item}

    # ------------------------ comissões ----------------------------

    def comissoes(self):
        """Lista as comissões temáticas (para marcar o parecer)."""
        return comissoes.comissoes(self.banco)

    def materias_para_parecer(self):
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "EMITIR_PARECER")
        return comissoes.materias_para_parecer(self.banco)

    def pareceres_por_comissao(self):
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "EMITIR_PARECER")
        comissao = self.query_atual.get("comissao", [None])[0]
        return comissoes.pareceres_por_comissao(
            self.banco, int(comissao) if comissao else None)

    def emitir_parecer(self, proposicao_id: int, dados):
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "EMITIR_PARECER")
        pid = comissoes.emitir_parecer(
            self.banco, proposicao_id, dados["comissao"], dados["tipo"],
            dados["ementa"], dados.get("data") or _hoje(),
            dados.get("relator_parlamentar_id"), dados.get("prazo"),
        )
        self.banco.commit()
        return {"id": pid}

    def aprovar_parecer(self, parecer_id: int):
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "EMITIR_PARECER")
        comissoes.aprovar_parecer(self.banco, parecer_id)
        self.banco.commit()
        return {"id": parecer_id, "situacao": "APROVADO"}

    def rejeitar_parecer(self, parecer_id: int):
        autenticacao.exigir_acao(self.banco, self.usuario_atual,
                                 "EMITIR_PARECER")
        comissoes.rejeitar_parecer(self.banco, parecer_id)
        self.banco.commit()
        return {"id": parecer_id, "situacao": "REJEITADO"}

    def pareceres(self, proposicao_id: int):
        return comissoes.pareceres(self.banco, proposicao_id)

    def votar(self, sessao_id: int, dados):
        votos = dados.get("votos")
        if votos:
            votos = {int(pid): valor for pid, valor in votos.items()}
        resultado = legislativo.votar(
            self.banco, sessao_id, dados["proposicao_id"],
            dados["modalidade"], votos, dados.get("resultado_simbolico"),
        )
        self.banco.commit()
        return {"resultado": resultado}

    def placar(self, sessao_id: int, proposicao_id: int):
        try:
            return legislativo.placar(self.banco, sessao_id, proposicao_id)
        except RegraViolada:
            raise Recurso404

    # --------------------- compras e contratos ----------------------

    def cadastrar_fornecedor(self, dados):
        fid = compras.cadastrar_fornecedor(
            self.banco, dados["razao_social"], dados.get("cnpj"))
        self.banco.commit()
        return {"id": fid}

    def _operador(self) -> str:
        return self.usuario_atual["login"] if self.usuario_atual else "sistema"

    def abrir_contratacao(self, dados):
        cid, numero = compras.abrir_contratacao(
            self.banco, dados["modalidade"], dados["objeto"],
            dados["valor_estimado"], dados["unidade_demandante_id"],
            dados["data"], dados.get("categoria", "COMPRAS_OUTROS_SERVICOS"),
            usuario=self._operador())
        self.banco.commit()
        return {"id": cid, "numero": numero}

    def homologar_contratacao(self, contratacao_id: int, dados):
        compras.homologar(self.banco, contratacao_id, dados["data"],
                          usuario=self._operador())
        self.banco.commit()
        return {"id": contratacao_id, "situacao": "HOMOLOGADA"}

    def celebrar_contrato(self, dados):
        contrato = compras.celebrar_contrato(
            self.banco, dados["contratacao_id"], dados["fornecedor_id"],
            dados["valor"], dados["inicio"], dados.get("fim"),
            usuario=self._operador())
        self.banco.commit()
        return {"id": contrato}

    def empenhar(self, dados):
        eid, numero = compras.empenhar(
            self.banco, dados["valor"], dados["descricao"], dados["data"],
            dados.get("contrato_id"), usuario=self._operador())
        self.banco.commit()
        return {"id": eid, "numero": numero}

    # ------------------ transparência e controle --------------------

    def publicar(self, dados):
        pid = transparencia.publicar(
            self.banco, dados["tipo"], dados["referencia"], dados["data"],
            dados.get("url"))
        self.banco.commit()
        return {"id": pid}

    def pendencias(self):
        return transparencia.pendencias_publicacao(self.banco)

    def auditoria(self):
        return transparencia.trilha_auditoria(self.banco)

    def painel(self):
        return transparencia.painel(self.banco)

    def saude(self):
        # Diagnóstico público: diz qual banco a instância no ar está usando.
        # 'postgres' confirma que a DATABASE_URL do Supabase está ativa e os
        # dados persistem; 'sqlite' indica que o app caiu no banco efêmero
        # (a variável não chegou ao processo). Sem segredos: só o backend e
        # contagens agregadas.
        eh_postgres = type(self.banco).__name__ == "ConexaoPostgres"
        (unidades,) = self.banco.execute(
            "SELECT COUNT(*) FROM unidade").fetchone()
        (usuarios,) = self.banco.execute(
            "SELECT COUNT(*) FROM usuario").fetchone()
        return {
            "ok": True,
            "backend": "postgres" if eh_postgres else "sqlite",
            "persistente": eh_postgres,
            "unidades": unidades,
            "usuarios": usuarios,
        }


# (método, padrão, área exigida, ação). Área None = rota pública —
# consultas de transparência ativa são abertas por princípio (LAI).
ROTAS = [
    ("POST", r"^/login$", None, lambda app, m, d: app.login(d)),
    # Gestão de acessos: rota logada ("*"), mas os handlers exigem ADMIN.
    ("POST", r"^/usuarios$", "*", lambda app, m, d: app.criar_usuario(d)),
    ("GET", r"^/usuarios$", "*", lambda app, m, d: app.listar_usuarios()),
    ("POST", r"^/usuarios/(\d+)$", "*",
     lambda app, m, d: app.editar_usuario(int(m.group(1)), d)),
    ("POST", r"^/usuarios/(\d+)/exclusao$", "*",
     lambda app, m, d: app.excluir_usuario(int(m.group(1)))),
    ("GET", r"^/me$", "*", lambda app, m, d: app.eu()),
    ("GET", r"^/caixa$", "*", lambda app, m, d: app.caixa()),
    ("GET", r"^/minhas-proposicoes$", "*",
     lambda app, m, d: app.minhas_proposicoes()),
    ("POST", r"^/minhas-proposicoes$", "LEGISLATIVO",
     lambda app, m, d: app.apresentar_do_setor(d)),
    ("GET", r"^/tipos-proposicao$", None,
     lambda app, m, d: app.tipos_proposicao()),
    ("GET", r"^/acompanhamento$", "*",
     lambda app, m, d: app.acompanhamento(d)),
    ("GET", r"^/proposicoes$", None,
     lambda app, m, d: app.listar_proposicoes()),
    ("GET", r"^/tipos-emenda$", None, lambda app, m, d: app.tipos_emenda()),
    ("POST", r"^/proposicoes/(\d+)/emendas$", "LEGISLATIVO",
     lambda app, m, d: app.apresentar_emenda(int(m.group(1)), d)),
    ("GET", r"^/proposicoes/(\d+)/emendas$", None,
     lambda app, m, d: app.emendas_da_proposicao(int(m.group(1)))),
    ("POST", r"^/proposicoes/(\d+)/requerimentos$", "LEGISLATIVO",
     lambda app, m, d: app.requerimento_derivado(int(m.group(1)), d)),
    ("GET", r"^/despachos-pendentes$", "LEGISLATIVO",
     lambda app, m, d: app.despachos_pendentes()),
    ("POST", r"^/requerimentos/(\d+)/despacho$", "LEGISLATIVO",
     lambda app, m, d: app.despachar_requerimento(int(m.group(1)), d)),
    ("GET", r"^/recebimento$", "LEGISLATIVO",
     lambda app, m, d: app.proposicoes_para_recebimento()),
    ("POST", r"^/proposicoes/(\d+)/recusa$", "LEGISLATIVO",
     lambda app, m, d: app.recusar_proposicao(int(m.group(1)), d)),
    ("POST", r"^/proposicoes/(\d+)/recurso$", "LEGISLATIVO",
     lambda app, m, d: app.recorrer_da_recusa(int(m.group(1)), d)),
    ("GET", r"^/recursos$", "LEGISLATIVO",
     lambda app, m, d: app.recursos_pendentes()),
    ("POST", r"^/proposicoes/(\d+)/recurso-decisao$", "LEGISLATIVO",
     lambda app, m, d: app.decidir_recurso(int(m.group(1)), d)),
    ("GET", r"^/rascunhos$", "*", lambda app, m, d: app.listar_rascunhos()),
    ("POST", r"^/rascunhos$", "LEGISLATIVO",
     lambda app, m, d: app.criar_rascunho(d)),
    ("POST", r"^/rascunhos/(\d+)$", "LEGISLATIVO",
     lambda app, m, d: app.atualizar_rascunho(int(m.group(1)), d)),
    ("POST", r"^/rascunhos/(\d+)/exclusao$", "LEGISLATIVO",
     lambda app, m, d: app.excluir_rascunho(int(m.group(1)))),
    ("POST", r"^/rascunhos/(\d+)/apresentacao$", "LEGISLATIVO",
     lambda app, m, d: app.apresentar_rascunho(int(m.group(1)), d)),
    ("GET", r"^/proposicoes-apresentadas$", "PROTOCOLO",
     lambda app, m, d: app.proposicoes_apresentadas()),
    ("POST", r"^/proposicoes/(\d+)/autuacao$", "PROTOCOLO",
     lambda app, m, d: app.autuar_proposicao(int(m.group(1)), d)),
    ("GET", r"^/organograma$", None, lambda app, m, d: app.organograma()),
    ("GET", r"^/unidades$", None, lambda app, m, d: app.unidades()),
    ("GET", r"^/cargos$", None, lambda app, m, d: app.cargos()),
    ("GET", r"^/servidores$", "PESSOAL", lambda app, m, d: app.servidores()),
    ("POST", r"^/servidores$", "PESSOAL", lambda app, m, d: app.criar_servidor(d)),
    ("POST", r"^/provimentos$", "PESSOAL", lambda app, m, d: app.nomear(d)),
    ("POST", r"^/provimentos/(\d+)/exoneracao$", "PESSOAL",
     lambda app, m, d: app.exonerar(int(m.group(1)), d)),
    ("POST", r"^/processos$", "PROTOCOLO", lambda app, m, d: app.autuar(d)),
    ("GET", r"^/processos$", None,
     lambda app, m, d: app.listar_processos(app.query_atual)),
    ("GET", r"^/processos/(\d+)$", None,
     lambda app, m, d: app.processo(int(m.group(1)))),
    ("POST", r"^/processos/(\d+)/documentos$", "*",
     lambda app, m, d: app.juntar_documento(int(m.group(1)), d)),
    # Encaminhar/receber é liberado pela POSSE (quem detém o processo),
    # não por área — cada setor remete o que está com ele ao seguinte.
    ("POST", r"^/processos/(\d+)/tramitacoes$", "*",
     lambda app, m, d: app.tramitar(int(m.group(1)), d)),
    ("POST", r"^/tramitacoes/(\d+)/recebimento$", "*",
     lambda app, m, d: app.receber_tramitacao(int(m.group(1)), d)),
    ("GET", r"^/processos/atrasados$", "PROTOCOLO",
     lambda app, m, d: app.processos_em_atraso(d)),
    ("GET", r"^/protocolo/painel$", "PROTOCOLO",
     lambda app, m, d: app.painel_protocolo()),
    ("GET", r"^/tipos-processo$", None,
     lambda app, m, d: app.tipos_processo()),
    ("GET", r"^/tipos-processo/([A-Za-z0-9_-]+)/etapas$", None,
     lambda app, m, d: app.etapas_do_tipo(m.group(1))),
    ("GET", r"^/unidades/(\d+)/competencias$", None,
     lambda app, m, d: app.competencias_da_unidade(int(m.group(1)))),
    ("POST", r"^/processos/(\d+)/tipo$", "PROTOCOLO",
     lambda app, m, d: app.vincular_tipo(int(m.group(1)), d)),
    ("GET", r"^/processos/(\d+)/proxima-etapa$", None,
     lambda app, m, d: app.proxima_etapa(int(m.group(1)))),
    ("POST", r"^/processos/(\d+)/tramitar-fluxo$", "*",
     lambda app, m, d: app.tramitar_pelo_fluxo(int(m.group(1)), d)),
    ("POST", r"^/processos/(\d+)/(arquivamento|conclusao|desarquivamento)$",
     "PROTOCOLO",
     lambda app, m, d: app.situacao_processo(int(m.group(1)), m.group(2))),
    # Exclusão definitiva: rota logada ("*"), mas o handler exige ADMIN.
    ("POST", r"^/processos/(\d+)/exclusao$", "*",
     lambda app, m, d: app.excluir_processo(int(m.group(1)))),
    ("POST", r"^/folhas$", "FOLHA", lambda app, m, d: app.calcular_folha(d)),
    ("GET", r"^/folhas$", "FOLHA", lambda app, m, d: app.listar_folhas()),
    ("GET", r"^/folhas/(\d+)$", "FOLHA",
     lambda app, m, d: app.folha(int(m.group(1)))),
    ("POST", r"^/folhas/(\d+)/(fechamento|pagamento)$", "FOLHA",
     lambda app, m, d: app.situacao_folha(int(m.group(1)), m.group(2))),
    ("GET", r"^/contratacoes$", None,
     lambda app, m, d: app.listar_contratacoes()),
    ("GET", r"^/parlamentares$", None, lambda app, m, d: app.parlamentares()),
    ("POST", r"^/parlamentares$", "LEGISLATIVO", lambda app, m, d: app.empossar(d)),
    ("POST", r"^/legislaturas$", "LEGISLATIVO",
     lambda app, m, d: app.criar_legislatura(d)),
    ("POST", r"^/proposicoes$", "LEGISLATIVO",
     lambda app, m, d: app.apresentar_proposicao(d)),
    ("POST", r"^/sessoes$", "LEGISLATIVO", lambda app, m, d: app.convocar_sessao(d)),
    ("POST", r"^/sessoes/(\d+)/pauta$", "LEGISLATIVO",
     lambda app, m, d: app.pautar(int(m.group(1)), d)),
    ("POST", r"^/sessoes/(\d+)/votacoes$", "LEGISLATIVO",
     lambda app, m, d: app.votar(int(m.group(1)), d)),
    ("GET", r"^/sessoes/(\d+)/votacoes/(\d+)$", None,
     lambda app, m, d: app.placar(int(m.group(1)), int(m.group(2)))),
    ("GET", r"^/comissoes$", None, lambda app, m, d: app.comissoes()),
    ("GET", r"^/materias-parecer$", "LEGISLATIVO",
     lambda app, m, d: app.materias_para_parecer()),
    ("GET", r"^/pareceres$", "LEGISLATIVO",
     lambda app, m, d: app.pareceres_por_comissao()),
    ("POST", r"^/proposicoes/(\d+)/pareceres$", "LEGISLATIVO",
     lambda app, m, d: app.emitir_parecer(int(m.group(1)), d)),
    ("POST", r"^/pareceres/(\d+)/aprovacao$", "LEGISLATIVO",
     lambda app, m, d: app.aprovar_parecer(int(m.group(1)))),
    ("POST", r"^/pareceres/(\d+)/rejeicao$", "LEGISLATIVO",
     lambda app, m, d: app.rejeitar_parecer(int(m.group(1)))),
    ("GET", r"^/proposicoes/(\d+)/pareceres$", None,
     lambda app, m, d: app.pareceres(int(m.group(1)))),
    ("POST", r"^/fornecedores$", "COMPRAS",
     lambda app, m, d: app.cadastrar_fornecedor(d)),
    ("POST", r"^/contratacoes$", "COMPRAS",
     lambda app, m, d: app.abrir_contratacao(d)),
    ("POST", r"^/contratacoes/(\d+)/homologacao$", "COMPRAS",
     lambda app, m, d: app.homologar_contratacao(int(m.group(1)), d)),
    ("POST", r"^/contratos$", "COMPRAS", lambda app, m, d: app.celebrar_contrato(d)),
    ("POST", r"^/empenhos$", "COMPRAS", lambda app, m, d: app.empenhar(d)),
    ("POST", r"^/publicacoes$", "TRANSPARENCIA", lambda app, m, d: app.publicar(d)),
    ("GET", r"^/transparencia/pendencias$", None,
     lambda app, m, d: app.pendencias()),
    ("GET", r"^/auditoria$", "CONTROLE", lambda app, m, d: app.auditoria()),
    ("GET", r"^/painel$", None, lambda app, m, d: app.painel()),
    ("GET", r"^/saude$", None, lambda app, m, d: app.saude()),
]


def criar_servidor_http(porta: int = 8000, caminho_banco: str = ":memory:",
                        host: str = "127.0.0.1"):
    aplicacao = Aplicacao(caminho_banco)

    class Handler(BaseHTTPRequestHandler):
        def _responder(self, codigo, corpo):
            dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

        def _despachar(self, metodo):
            corpo = {}
            tamanho = int(self.headers.get("Content-Length") or 0)
            if tamanho:
                try:
                    corpo = json.loads(self.rfile.read(tamanho))
                except json.JSONDecodeError:
                    return self._responder(400, {"erro": "JSON inválido"})
            autorizacao = self.headers.get("Authorization", "")
            token = autorizacao.removeprefix("Bearer ").strip() or None
            url = urlparse(self.path)
            for verbo, padrao, area, acao in ROTAS:
                if verbo != metodo:
                    continue
                m = re.match(padrao, url.path)
                if m:
                    # Todo o ciclo (ação + commit/rollback) fica dentro da
                    # trava: com uma única conexão compartilhada, transação
                    # e desfazimento não podem se misturar entre requisições
                    # (o PostgreSQL invalida a transação após qualquer erro
                    # até o rollback).
                    with aplicacao.trava:
                        try:
                            usuario = aplicacao.sessoes.usuario(token)
                            if area == "*":
                                if usuario is None:
                                    raise NaoAutenticado("operação exige login")
                            elif area is not None:
                                autenticacao.exigir(aplicacao.banco, usuario, area)
                            aplicacao.usuario_atual = usuario
                            aplicacao.query_atual = parse_qs(url.query)
                            resultado = acao(aplicacao, m, corpo)
                            aplicacao.banco.commit()
                            return self._responder(200, resultado)
                        except NaoAutenticado as erro:
                            aplicacao.banco.rollback()
                            return self._responder(401, {"erro": str(erro)})
                        except AcessoNegado as erro:
                            aplicacao.banco.rollback()
                            return self._responder(403, {"erro": str(erro)})
                        except RegraViolada as erro:
                            aplicacao.banco.rollback()
                            return self._responder(422, {"erro": str(erro)})
                        except Recurso404:
                            aplicacao.banco.rollback()
                            return self._responder(404, {"erro": "não encontrado"})
                        except sqlite3.IntegrityError as erro:
                            aplicacao.banco.rollback()
                            return self._responder(
                                422, {"erro": f"violação de integridade: {erro}"})
                        except KeyError as erro:
                            aplicacao.banco.rollback()
                            return self._responder(
                                400, {"erro": f"campo obrigatório: {erro.args[0]}"})
                        except Exception:
                            aplicacao.banco.rollback()
                            return self._responder(
                                500, {"erro": "erro interno do servidor"})
            self._responder(404, {"erro": "rota inexistente"})

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                conteudo = PAGINA_WEB.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(conteudo)))
                self.end_headers()
                self.wfile.write(conteudo)
                return
            self._despachar("GET")

        def do_POST(self):
            self._despachar("POST")

        def log_message(self, *args):  # silencia o log padrão nos testes
            pass

    servidor = ThreadingHTTPServer((host, porta), Handler)
    servidor.aplicacao = aplicacao
    return servidor


def main() -> None:
    import argparse
    import os

    parser = argparse.ArgumentParser(description="API do sistema CMDC")
    # PORT/HOST/CMDC_DB vêm do ambiente em produção (Render define PORT).
    parser.add_argument("--porta", type=int,
                        default=int(os.environ.get("PORT", 8000)))
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--banco",
                        default=os.environ.get("DATABASE_URL")
                        or os.environ.get("CMDC_DB", "cmdc.db"),
                        help="arquivo SQLite ou URL postgres:// (produção: "
                             "defina DATABASE_URL, ex. Supabase)")
    argumentos = parser.parse_args()

    servidor = criar_servidor_http(argumentos.porta, argumentos.banco,
                                   host=argumentos.host)
    print(f"API do sistema CMDC ouvindo em {argumentos.host}:{argumentos.porta}")
    print("Login inicial: admin /", autenticacao.SENHA_INICIAL_ADMIN,
          "(troque criando novos usuários via POST /usuarios)")
    print("Rotas:", ", ".join(sorted({f"{v} {p}" for v, p, _, _ in ROTAS})))
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        servidor.shutdown()


if __name__ == "__main__":
    main()
