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

Regras violadas retornam 422 com a mensagem legal; recurso ausente, 404.

Uso:
    python -m sistema.api               # sobe em http://127.0.0.1:8000
    python -m sistema.api --porta 8080
"""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sistema import legislativo, servicos
from sistema.demo import criar_banco
from sistema.servicos import RegraViolada


class Recurso404(Exception):
    pass


class Aplicacao:
    """Rotas e acesso ao banco (uma conexão SQLite protegida por lock)."""

    def __init__(self, caminho_banco: str = ":memory:"):
        self.banco = criar_banco(caminho_banco, multithread=True)
        self.trava = threading.Lock()

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
        tid = servicos.tramitar(
            self.banco, processo_id, dados["unidade_destino_id"],
            dados.get("despacho", ""), dados["data_envio"],
        )
        self.banco.commit()
        return {"id": tid}

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
        item = legislativo.pautar(self.banco, sessao_id, dados["proposicao_id"])
        self.banco.commit()
        return {"id": item}

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


ROTAS = [
    ("GET", r"^/organograma$", lambda app, m, d: app.organograma()),
    ("GET", r"^/unidades$", lambda app, m, d: app.unidades()),
    ("GET", r"^/cargos$", lambda app, m, d: app.cargos()),
    ("GET", r"^/servidores$", lambda app, m, d: app.servidores()),
    ("POST", r"^/servidores$", lambda app, m, d: app.criar_servidor(d)),
    ("POST", r"^/provimentos$", lambda app, m, d: app.nomear(d)),
    ("POST", r"^/provimentos/(\d+)/exoneracao$",
     lambda app, m, d: app.exonerar(int(m.group(1)), d)),
    ("POST", r"^/processos$", lambda app, m, d: app.autuar(d)),
    ("GET", r"^/processos/(\d+)$",
     lambda app, m, d: app.processo(int(m.group(1)))),
    ("POST", r"^/processos/(\d+)/tramitacoes$",
     lambda app, m, d: app.tramitar(int(m.group(1)), d)),
    ("POST", r"^/folhas$", lambda app, m, d: app.calcular_folha(d)),
    ("GET", r"^/folhas/(\d+)$", lambda app, m, d: app.folha(int(m.group(1)))),
    ("GET", r"^/parlamentares$", lambda app, m, d: app.parlamentares()),
    ("POST", r"^/parlamentares$", lambda app, m, d: app.empossar(d)),
    ("POST", r"^/legislaturas$", lambda app, m, d: app.criar_legislatura(d)),
    ("POST", r"^/proposicoes$", lambda app, m, d: app.apresentar_proposicao(d)),
    ("POST", r"^/sessoes$", lambda app, m, d: app.convocar_sessao(d)),
    ("POST", r"^/sessoes/(\d+)/pauta$",
     lambda app, m, d: app.pautar(int(m.group(1)), d)),
    ("POST", r"^/sessoes/(\d+)/votacoes$",
     lambda app, m, d: app.votar(int(m.group(1)), d)),
    ("GET", r"^/sessoes/(\d+)/votacoes/(\d+)$",
     lambda app, m, d: app.placar(int(m.group(1)), int(m.group(2)))),
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
            for verbo, padrao, acao in ROTAS:
                if verbo != metodo:
                    continue
                m = re.match(padrao, self.path.split("?")[0])
                if m:
                    try:
                        with aplicacao.trava:
                            return self._responder(200, acao(aplicacao, m, corpo))
                    except RegraViolada as erro:
                        aplicacao.banco.rollback()
                        return self._responder(422, {"erro": str(erro)})
                    except Recurso404:
                        return self._responder(404, {"erro": "não encontrado"})
                    except KeyError as erro:
                        aplicacao.banco.rollback()
                        return self._responder(
                            400, {"erro": f"campo obrigatório: {erro.args[0]}"})
            self._responder(404, {"erro": "rota inexistente"})

        def do_GET(self):
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
    print("Rotas:", ", ".join(sorted({f"{v} {p}" for v, p, _ in ROTAS})))
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        servidor.shutdown()


if __name__ == "__main__":
    main()
