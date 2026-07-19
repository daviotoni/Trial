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

    def criar_usuario(self, dados):
        try:
            uid = autenticacao.criar_usuario(
                self.banco, dados["login"], dados["senha"], dados["perfil"],
                dados.get("servidor_id"), dados.get("unidade_id"))
        except ValueError as erro:
            raise RegraViolada(str(erro))
        self.banco.commit()
        return {"id": uid}

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
        condicoes, valores = [], []
        if filtros.get("situacao"):
            condicoes.append("situacao = ?")
            valores.append(filtros["situacao"][0])
        if filtros.get("ano"):
            condicoes.append("ano = ?")
            valores.append(int(filtros["ano"][0]))
        clausula = ("WHERE " + " AND ".join(condicoes)) if condicoes else ""
        return [
            {"id": pid, "numero": f"{numero}/{ano}", "tipo": tipo,
             "assunto": assunto, "situacao": situacao, "data": data}
            for pid, numero, ano, tipo, assunto, situacao, data in
            self.banco.execute(
                f"SELECT id, numero, ano, tipo, assunto, situacao, "
                f"data_autuacao FROM processo {clausula} "
                f"ORDER BY ano DESC, numero DESC LIMIT 100", valores)
        ]

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
            "SELECT numero, ano, tipo, assunto, situacao, data_autuacao "
            "FROM processo WHERE id = ?", (processo_id,)
        ).fetchone()
        if linha is None:
            raise Recurso404
        numero, ano, tipo, assunto, situacao, autuacao = linha
        trilha = [
            {"de": origem, "para": destino, "despacho": despacho, "data": data}
            for origem, destino, despacho, data in self.banco.execute(
                """SELECT o.nome, d.nome, t.despacho, t.data_envio
                   FROM tramitacao t
                   JOIN unidade o ON o.id = t.unidade_origem_id
                   JOIN unidade d ON d.id = t.unidade_destino_id
                   WHERE t.processo_id = ? ORDER BY t.id""", (processo_id,)
            )
        ]
        return {"id": processo_id, "numero": f"{numero}/{ano}", "tipo": tipo,
                "assunto": assunto, "situacao": situacao,
                "data_autuacao": autuacao, "tramitacoes": trilha}

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
            self.banco, self.query_atual.get("referencia", [""])[0])

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
        proposicao_id, rotulo = legislativo.apresentar_proposicao(
            self.banco, dados["tipo"], dados["ementa"], dados["data"],
            dados.get("autor_parlamentar_id"),
            dados.get("unidade_protocolo_id"),
        )
        self.banco.commit()
        return {"id": proposicao_id, "rotulo": rotulo}

    def convocar_sessao(self, dados):
        sessao_id, numero = legislativo.convocar_sessao(
            self.banco, dados["tipo"], dados["data"],
        )
        self.banco.commit()
        return {"id": sessao_id, "numero": numero}

    def pautar(self, sessao_id: int, dados):
        item = legislativo.pautar(
            self.banco, sessao_id, dados["proposicao_id"],
            urgencia=bool(dados.get("urgencia", False)))
        self.banco.commit()
        return {"id": item}

    # ------------------------ comissões ----------------------------

    def distribuir_relatoria(self, dados):
        rid = comissoes.distribuir_relatoria(
            self.banco, dados["proposicao_id"], dados["comissao"],
            dados["relator_parlamentar_id"], dados["data"],
            dados.get("prazo"),
        )
        self.banco.commit()
        return {"id": rid}

    def emitir_parecer(self, relatoria_id: int, dados):
        pid = comissoes.emitir_parecer(
            self.banco, relatoria_id, dados["tipo"], dados["ementa"],
            dados["data"],
        )
        self.banco.commit()
        return {"id": pid}

    def aprovar_parecer(self, parecer_id: int):
        comissoes.aprovar_parecer(self.banco, parecer_id)
        self.banco.commit()
        return {"id": parecer_id, "situacao": "APROVADO"}

    def pareceres(self, proposicao_id: int):
        return comissoes.pareceres(self.banco, proposicao_id)

    def relatorias_em_atraso(self):
        return comissoes.relatorias_em_atraso(
            self.banco, self.query_atual.get("referencia", [""])[0])

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


# (método, padrão, área exigida, ação). Área None = rota pública —
# consultas de transparência ativa são abertas por princípio (LAI).
ROTAS = [
    ("POST", r"^/login$", None, lambda app, m, d: app.login(d)),
    ("POST", r"^/usuarios$", "USUARIOS", lambda app, m, d: app.criar_usuario(d)),
    ("GET", r"^/me$", "*", lambda app, m, d: app.eu()),
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
    # Encaminhar/receber é liberado pela POSSE (quem detém o processo),
    # não por área — cada setor remete o que está com ele ao seguinte.
    ("POST", r"^/processos/(\d+)/tramitacoes$", "*",
     lambda app, m, d: app.tramitar(int(m.group(1)), d)),
    ("POST", r"^/tramitacoes/(\d+)/recebimento$", "*",
     lambda app, m, d: app.receber_tramitacao(int(m.group(1)), d)),
    ("GET", r"^/processos/atrasados$", "PROTOCOLO",
     lambda app, m, d: app.processos_em_atraso(d)),
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
    ("POST", r"^/relatorias$", "LEGISLATIVO",
     lambda app, m, d: app.distribuir_relatoria(d)),
    ("GET", r"^/relatorias/atrasadas$", "LEGISLATIVO",
     lambda app, m, d: app.relatorias_em_atraso()),
    ("POST", r"^/relatorias/(\d+)/parecer$", "LEGISLATIVO",
     lambda app, m, d: app.emitir_parecer(int(m.group(1)), d)),
    ("POST", r"^/pareceres/(\d+)/aprovacao$", "LEGISLATIVO",
     lambda app, m, d: app.aprovar_parecer(int(m.group(1)))),
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
]


def criar_servidor_http(porta: int = 8000, caminho_banco: str = ":memory:"):
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
                    try:
                        with aplicacao.trava:
                            usuario = aplicacao.sessoes.usuario(token)
                            if area == "*":
                                if usuario is None:
                                    raise NaoAutenticado("operação exige login")
                            elif area is not None:
                                autenticacao.exigir(aplicacao.banco, usuario, area)
                            aplicacao.usuario_atual = usuario
                            aplicacao.query_atual = parse_qs(url.query)
                            return self._responder(200, acao(aplicacao, m, corpo))
                    except NaoAutenticado as erro:
                        return self._responder(401, {"erro": str(erro)})
                    except AcessoNegado as erro:
                        return self._responder(403, {"erro": str(erro)})
                    except RegraViolada as erro:
                        aplicacao.banco.rollback()
                        return self._responder(422, {"erro": str(erro)})
                    except Recurso404:
                        return self._responder(404, {"erro": "não encontrado"})
                    except sqlite3.IntegrityError as erro:
                        aplicacao.banco.rollback()
                        return self._responder(
                            422, {"erro": f"violação de integridade: {erro}"})
                    except KeyError as erro:
                        aplicacao.banco.rollback()
                        return self._responder(
                            400, {"erro": f"campo obrigatório: {erro.args[0]}"})
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

    servidor = ThreadingHTTPServer(("127.0.0.1", porta), Handler)
    servidor.aplicacao = aplicacao
    return servidor


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="API do sistema CMDC")
    parser.add_argument("--porta", type=int, default=8000)
    parser.add_argument("--banco", default="cmdc.db",
                        help="arquivo SQLite (padrão: cmdc.db)")
    argumentos = parser.parse_args()

    servidor = criar_servidor_http(argumentos.porta, argumentos.banco)
    print(f"API do sistema CMDC em http://127.0.0.1:{argumentos.porta}")
    print("Login inicial: admin /", autenticacao.SENHA_INICIAL_ADMIN,
          "(troque criando novos usuários via POST /usuarios)")
    print("Rotas:", ", ".join(sorted({f"{v} {p}" for v, p, _, _ in ROTAS})))
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        servidor.shutdown()


if __name__ == "__main__":
    main()
