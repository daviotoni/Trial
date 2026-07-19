"""Testes da API REST (servidor real em thread, cliente urllib)."""

import json
import threading
import unittest
import urllib.error
import urllib.request

from sistema.api import criar_servidor_http


TOKEN_PADRAO = None  # definido no setUpClass (login como admin)


def requisitar(base, metodo, caminho, corpo=None, token=None):
    """token=None usa o token padrão (admin); token=False envia sem token."""
    dados = json.dumps(corpo).encode() if corpo is not None else None
    cabecalhos = {"Content-Type": "application/json"}
    efetivo = TOKEN_PADRAO if token is None else (token or None)
    if efetivo:
        cabecalhos["Authorization"] = f"Bearer {efetivo}"
    requisicao = urllib.request.Request(
        base + caminho, data=dados, method=metodo, headers=cabecalhos,
    )
    try:
        with urllib.request.urlopen(requisicao) as resposta:
            return resposta.status, json.loads(resposta.read())
    except urllib.error.HTTPError as erro:
        return erro.code, json.loads(erro.read())


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servidor = criar_servidor_http(porta=0)
        cls.base = f"http://127.0.0.1:{cls.servidor.server_address[1]}"
        cls.thread = threading.Thread(target=cls.servidor.serve_forever,
                                      daemon=True)
        cls.thread.start()
        global TOKEN_PADRAO
        _, sessao = requisitar(cls.base, "POST", "/login",
                               {"login": "admin", "senha": "cmdc@2026"},
                               token=False)
        TOKEN_PADRAO = sessao["token"]

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()

    def test_pagina_web(self):
        with urllib.request.urlopen(self.base + "/") as resposta:
            self.assertEqual(resposta.status, 200)
            self.assertIn("text/html", resposta.headers["Content-Type"])
            corpo = resposta.read().decode("utf-8")
        self.assertIn("Sistema de Gestão — Câmara Municipal de Duque de Caxias",
                      corpo)

    def test_organograma(self):
        codigo, corpo = requisitar(self.base, "GET", "/organograma")
        self.assertEqual(codigo, 200)
        self.assertEqual(corpo["nome"], "Mesa Diretora")
        nomes_filhos = {u["nome"] for u in corpo["subunidades"]}
        self.assertIn("Presidência", nomes_filhos)

    def test_cargos_com_vagas(self):
        codigo, corpo = requisitar(self.base, "GET", "/cargos")
        self.assertEqual(codigo, 200)
        total = sum(c["vagas"] for c in corpo)
        self.assertEqual(total, 615)

    def test_fluxo_completo(self):
        # Servidor → nomeação → processo → tramitação → folha.
        codigo, servidor = requisitar(self.base, "POST", "/servidores", {
            "nome": "Teste da Silva", "vinculo": "COMISSIONADO",
            "data_admissao": "2025-09-01",
        })
        self.assertEqual(codigo, 200)

        cargos = requisitar(self.base, "GET", "/cargos")[1]
        diretor_geral = next(c for c in cargos
                             if c["denominacao"] == "Diretor-Geral")
        unidades = requisitar(self.base, "GET", "/unidades")[1]
        dg = next(u for u in unidades if u["nome"] == "Diretoria-Geral")

        codigo, _ = requisitar(self.base, "POST", "/provimentos", {
            "servidor_id": servidor["id"], "cargo_id": diretor_geral["id"],
            "unidade_id": dg["id"], "ato": "Portaria 1/2025",
            "data_inicio": "2025-09-01",
        })
        self.assertEqual(codigo, 200)

        # Segunda nomeação no mesmo cargo de 1 vaga → 422 com a regra.
        codigo, erro = requisitar(self.base, "POST", "/provimentos", {
            "servidor_id": servidor["id"], "cargo_id": diretor_geral["id"],
            "unidade_id": dg["id"], "ato": "Portaria 2/2025",
            "data_inicio": "2025-09-02",
        })
        self.assertEqual(codigo, 422)
        self.assertIn("vaga", erro["erro"])

        codigo, processo = requisitar(self.base, "POST", "/processos", {
            "tipo": "ADMINISTRATIVO", "assunto": "Aquisição de computadores",
            "unidade_origem_id": dg["id"], "data_autuacao": "2025-09-05",
        })
        self.assertEqual(codigo, 200)
        self.assertRegex(processo["numero"], r"^\d+/2025$")

        destino = next(u for u in unidades
                       if u["nome"] == "Coordenadoria de Licitações e Contratos")
        codigo, _ = requisitar(
            self.base, "POST", f"/processos/{processo['id']}/tramitacoes",
            {"unidade_destino_id": destino["id"], "despacho": "Licitar",
             "data_envio": "2025-09-06"},
        )
        self.assertEqual(codigo, 200)

        codigo, detalhe = requisitar(self.base, "GET",
                                     f"/processos/{processo['id']}")
        self.assertEqual(codigo, 200)
        self.assertEqual(len(detalhe["tramitacoes"]), 1)
        self.assertEqual(detalhe["tramitacoes"][0]["para"],
                         "Coordenadoria de Licitações e Contratos")

        codigo, folha = requisitar(self.base, "POST", "/folhas", {
            "competencia": "2025-09", "percentual_gal": 100,
        })
        self.assertEqual(codigo, 200)
        # Diretor-Geral DAS-8: 15.925 + GAL 100% = 31.850
        self.assertAlmostEqual(folha["total"], 31850.0)

        codigo, detalhe = requisitar(self.base, "GET", f"/folhas/{folha['id']}")
        self.assertEqual(codigo, 200)
        rubricas = {item["rubrica"] for item in detalhe["itens"]}
        self.assertEqual(rubricas, {"VENC", "GAL"})

    def test_gal_acima_do_teto(self):
        codigo, erro = requisitar(self.base, "POST", "/folhas", {
            "competencia": "2030-01", "percentual_gal": 200,
        })
        self.assertEqual(codigo, 422)
        self.assertIn("teto", erro["erro"])

    def test_recurso_inexistente(self):
        self.assertEqual(requisitar(self.base, "GET", "/processos/9999")[0], 404)
        self.assertEqual(requisitar(self.base, "GET", "/nada")[0], 404)

    def test_campo_obrigatorio_ausente(self):
        codigo, erro = requisitar(self.base, "POST", "/servidores",
                                  {"nome": "Sem vínculo"})
        self.assertEqual(codigo, 400)
        self.assertIn("vinculo", erro["erro"])

    def test_fluxo_legislativo(self):
        _, legislatura = requisitar(self.base, "POST", "/legislaturas", {
            "numero": 9, "inicio": "2025-01-01", "fim": "2028-12-31"})
        ids = [
            requisitar(self.base, "POST", "/parlamentares", {
                "nome": f"Vereador API {i}", "partido": "PXX",
                "legislatura_id": legislatura["id"]})[1]["id"]
            for i in range(3)
        ]
        _, proposicao = requisitar(self.base, "POST", "/proposicoes", {
            "tipo": "PR", "ementa": "Altera o Regimento",
            "data": "2025-10-01", "autor_parlamentar_id": ids[0]})
        self.assertEqual(proposicao["rotulo"], "PR 1/2025")

        _, sessao = requisitar(self.base, "POST", "/sessoes", {
            "tipo": "EXTRAORDINARIA", "data": "2025-10-05"})

        # Matéria de mérito (PR) precisa de parecer de comissão antes da pauta.
        codigo, bloqueio = requisitar(self.base, "POST",
                                      f"/sessoes/{sessao['id']}/pauta",
                                      {"proposicao_id": proposicao["id"]})
        self.assertEqual(codigo, 422)
        self.assertIn("parecer", bloqueio["erro"])

        # Distribui relatoria, emite e aprova o parecer.
        _, relatoria = requisitar(self.base, "POST", "/relatorias", {
            "proposicao_id": proposicao["id"],
            "comissao": "Comissão de Legislação, Justiça e Redação Final",
            "relator_parlamentar_id": ids[0], "data": "2025-10-02",
            "prazo": "2025-10-04"})
        _, parecer = requisitar(
            self.base, "POST", f"/relatorias/{relatoria['id']}/parecer",
            {"tipo": "FAVORAVEL", "ementa": "Favorável.", "data": "2025-10-03"})
        codigo, _ = requisitar(
            self.base, "POST", f"/pareceres/{parecer['id']}/aprovacao", {})
        self.assertEqual(codigo, 200)

        codigo, lista = requisitar(
            self.base, "GET", f"/proposicoes/{proposicao['id']}/pareceres")
        self.assertEqual(codigo, 200)
        self.assertEqual(lista[0]["situacao"], "APROVADO")

        codigo, _ = requisitar(self.base, "POST",
                               f"/sessoes/{sessao['id']}/pauta",
                               {"proposicao_id": proposicao["id"]})
        self.assertEqual(codigo, 200)

        codigo, votacao = requisitar(
            self.base, "POST", f"/sessoes/{sessao['id']}/votacoes",
            {"proposicao_id": proposicao["id"], "modalidade": "NOMINAL",
             "votos": {str(ids[0]): "SIM", str(ids[1]): "SIM",
                       str(ids[2]): "NAO"}})
        self.assertEqual(codigo, 200)
        self.assertEqual(votacao["resultado"], "APROVADA")

        codigo, placar = requisitar(
            self.base, "GET",
            f"/sessoes/{sessao['id']}/votacoes/{proposicao['id']}")
        self.assertEqual(codigo, 200)
        self.assertEqual(placar["contagem"]["SIM"], 2)

        # Votar de novo a mesma matéria na mesma sessão → 422.
        codigo, _ = requisitar(
            self.base, "POST", f"/sessoes/{sessao['id']}/votacoes",
            {"proposicao_id": proposicao["id"], "modalidade": "SIMBOLICA",
             "resultado_simbolico": "APROVADA"})
        self.assertEqual(codigo, 422)

    def test_fluxo_processual(self):
        # Rito configurado é público (transparência).
        codigo, tipos = requisitar(self.base, "GET", "/tipos-processo")
        self.assertEqual(codigo, 200)
        codigos = {t["codigo"] for t in tipos}
        self.assertIn("PL", codigos)
        self.assertIn("COMPRA", codigos)

        codigo, etapas = requisitar(
            self.base, "GET", "/tipos-processo/COMPRA/etapas")
        self.assertEqual(codigo, 200)
        self.assertEqual(etapas[0]["unidade"],
                         "Coordenadoria da Secretaria-Geral")

        # Autua um processo, vincula ao rito e encaminha automaticamente.
        _, proc = requisitar(self.base, "POST", "/processos", {
            "tipo": "ADMINISTRATIVO", "assunto": "Compra de material",
            "unidade_origem_id": etapas[0]["unidade_id"],
            "data_autuacao": "2025-09-10"})
        codigo, _ = requisitar(
            self.base, "POST", f"/processos/{proc['id']}/tipo",
            {"tipo": "COMPRA"})
        self.assertEqual(codigo, 200)

        codigo, prox = requisitar(
            self.base, "GET", f"/processos/{proc['id']}/proxima-etapa")
        self.assertEqual(codigo, 200)
        self.assertEqual(prox["unidade"], "Diretoria-Geral")

        codigo, etapa = requisitar(
            self.base, "POST", f"/processos/{proc['id']}/tramitar-fluxo",
            {"data_envio": "2025-09-10"})
        self.assertEqual(codigo, 200)
        self.assertEqual(etapa["unidade"], "Diretoria-Geral")

        # Competências de uma unidade são consulta pública.
        codigo, comps = requisitar(
            self.base, "GET",
            f"/unidades/{etapas[0]['unidade_id']}/competencias")
        self.assertEqual(codigo, 200)

    def test_acesso_por_unidade_e_posse(self):
        _, unidades = requisitar(self.base, "GET", "/unidades")
        gabs = [u for u in unidades if u["nome"].startswith("Gabinete do(a)")]
        gab_a, gab_b = gabs[0], gabs[1]
        secretaria = next(u for u in unidades
                          if u["nome"] == "Coordenadoria da Secretaria-Geral")

        # Dois usuários de gabinete (ambos com área LEGISLATIVO).
        for login, uid in (("gab.a", gab_a["id"]), ("gab.b", gab_b["id"])):
            requisitar(self.base, "POST", "/usuarios", {
                "login": login, "senha": "senha123", "perfil": "LEGISLATIVO",
                "unidade_id": uid})
        _, sa = requisitar(self.base, "POST", "/login",
                           {"login": "gab.a", "senha": "senha123"}, token=False)
        _, sb = requisitar(self.base, "POST", "/login",
                           {"login": "gab.b", "senha": "senha123"}, token=False)

        # /me revela unidade e áreas.
        codigo, eu = requisitar(self.base, "GET", "/me", token=sa["token"])
        self.assertEqual(codigo, 200)
        self.assertEqual(eu["areas"], ["LEGISLATIVO"])
        self.assertTrue(eu["unidade"].startswith("Gabinete do(a)"))

        # Gabinete NÃO tem alçada de PROTOCOLO → 403 ao autuar.
        codigo, _ = requisitar(self.base, "POST", "/processos", {
            "tipo": "LEGISLATIVO", "assunto": "PL do gabinete",
            "unidade_origem_id": gab_a["id"], "data_autuacao": "2025-09-10"},
            token=sa["token"])
        self.assertEqual(codigo, 403)

        # Admin autua um processo com origem no gabinete A.
        _, proc = requisitar(self.base, "POST", "/processos", {
            "tipo": "LEGISLATIVO", "assunto": "Posse teste",
            "unidade_origem_id": gab_a["id"], "data_autuacao": "2025-09-10"})

        # Gabinete B (mesma área, mas não detém) → 403 por POSSE.
        codigo, _ = requisitar(
            self.base, "POST", f"/processos/{proc['id']}/tramitacoes",
            {"unidade_destino_id": secretaria["id"], "data_envio": "2025-09-11"},
            token=sb["token"])
        self.assertEqual(codigo, 403)

        # Gabinete A (detém) → encaminha com sucesso.
        codigo, _ = requisitar(
            self.base, "POST", f"/processos/{proc['id']}/tramitacoes",
            {"unidade_destino_id": secretaria["id"], "data_envio": "2025-09-11"},
            token=sa["token"])
        self.assertEqual(codigo, 200)

    def test_caixa_do_setor(self):
        _, unidades = requisitar(self.base, "GET", "/unidades")
        gab = next(u for u in unidades
                   if u["nome"].startswith("Gabinete do(a)"))
        requisitar(self.base, "POST", "/usuarios", {
            "login": "gab.caixa", "senha": "senha123", "perfil": "LEGISLATIVO",
            "unidade_id": gab["id"]})
        # Admin autua um PL com origem no gabinete e vincula o rito.
        _, proc = requisitar(self.base, "POST", "/processos", {
            "tipo": "LEGISLATIVO", "assunto": "PL na caixa",
            "unidade_origem_id": gab["id"], "data_autuacao": "2025-09-10"})
        requisitar(self.base, "POST", f"/processos/{proc['id']}/tipo",
                   {"tipo": "PL"})
        # O gabinete vê o processo na sua caixa, com a próxima etapa.
        _, s = requisitar(self.base, "POST", "/login",
                          {"login": "gab.caixa", "senha": "senha123"},
                          token=False)
        codigo, caixa = requisitar(self.base, "GET", "/caixa", token=s["token"])
        self.assertEqual(codigo, 200)
        assuntos = {p["assunto"] for p in caixa}
        self.assertIn("PL na caixa", assuntos)
        item = next(p for p in caixa if p["assunto"] == "PL na caixa")
        self.assertEqual(item["proxima_unidade"],
                         "Coordenadoria da Secretaria-Geral")

    def test_minhas_proposicoes_acompanha_apos_encaminhar(self):
        _, unidades = requisitar(self.base, "GET", "/unidades")
        gab = next(u for u in unidades
                   if u["nome"].startswith("Gabinete do(a)"))
        requisitar(self.base, "POST", "/usuarios", {
            "login": "gab.acomp", "senha": "senha123", "perfil": "LEGISLATIVO",
            "unidade_id": gab["id"]})
        _, proc = requisitar(self.base, "POST", "/processos", {
            "tipo": "LEGISLATIVO", "assunto": "PL para acompanhar",
            "unidade_origem_id": gab["id"], "data_autuacao": "2025-09-10"})
        requisitar(self.base, "POST", f"/processos/{proc['id']}/tipo",
                   {"tipo": "PL"})
        _, s = requisitar(self.base, "POST", "/login",
                          {"login": "gab.acomp", "senha": "senha123"},
                          token=False)
        tk = s["token"]

        # Antes de encaminhar: aparece nas proposições, localizado no gabinete.
        _, lista = requisitar(self.base, "GET", "/minhas-proposicoes", token=tk)
        item = next(p for p in lista if p["assunto"] == "PL para acompanhar")
        self.assertTrue(item["localizacao"].startswith("Gabinete do(a)"))

        # Gabinete encaminha pelo rito (sai da caixa dele).
        requisitar(self.base, "POST",
                   f"/processos/{proc['id']}/tramitar-fluxo",
                   {"data_envio": "2025-09-11"}, token=tk)

        # Continua nas proposições, agora localizado na Secretaria-Geral.
        _, lista2 = requisitar(self.base, "GET", "/minhas-proposicoes", token=tk)
        item2 = next(p for p in lista2 if p["assunto"] == "PL para acompanhar")
        self.assertEqual(item2["localizacao"], "Coordenadoria da Secretaria-Geral")
        # E saiu da caixa (não está mais no gabinete).
        _, caixa = requisitar(self.base, "GET", "/caixa", token=tk)
        self.assertNotIn("PL para acompanhar",
                         {p["assunto"] for p in caixa})

    def test_trava_fina_por_competencia(self):
        _, unidades = requisitar(self.base, "GET", "/unidades")
        gab = next(u for u in unidades
                   if u["nome"].startswith("Gabinete do(a)"))
        _, leg = requisitar(self.base, "POST", "/legislaturas", {
            "numero": 30, "inicio": "2025-01-01", "fim": "2028-12-31"})
        requisitar(self.base, "POST", "/usuarios", {
            "login": "gab.trava", "senha": "senha123", "perfil": "LEGISLATIVO",
            "unidade_id": gab["id"]})
        _, s = requisitar(self.base, "POST", "/login",
                          {"login": "gab.trava", "senha": "senha123"},
                          token=False)
        tk = s["token"]

        # /me revela a competência de ação do gabinete.
        _, eu = requisitar(self.base, "GET", "/me", token=tk)
        self.assertEqual(eu["acoes"], ["APRESENTAR_PROPOSICAO"])

        # Gabinete PODE apresentar proposição (competência dele).
        codigo, _ = requisitar(self.base, "POST", "/proposicoes", {
            "tipo": "PL", "ementa": "PL do gabinete", "data": "2025-10-01"},
            token=tk)
        self.assertEqual(codigo, 200)

        # Mas NÃO pode convocar sessão (ato da Presidência/Mesa) → 403.
        codigo, erro = requisitar(self.base, "POST", "/sessoes", {
            "tipo": "ORDINARIA", "data": "2025-10-05"}, token=tk)
        self.assertEqual(codigo, 403)
        self.assertIn("competência", erro["erro"])

    def test_escrita_sem_login_retorna_401(self):
        codigo, erro = requisitar(self.base, "POST", "/processos", {
            "tipo": "ADMINISTRATIVO", "assunto": "X",
            "unidade_origem_id": 1, "data_autuacao": "2026-01-01",
        }, token=False)
        self.assertEqual(codigo, 401)
        self.assertIn("login", erro["erro"])

    def test_login_invalido(self):
        codigo, _ = requisitar(self.base, "POST", "/login",
                               {"login": "admin", "senha": "errada"},
                               token=False)
        self.assertEqual(codigo, 401)

    def test_perfil_sem_alcada_retorna_403(self):
        # Admin cria usuário do Protocolo; ele não pode operar Compras.
        codigo, _ = requisitar(self.base, "POST", "/usuarios", {
            "login": "maria.protocolo", "senha": "senha-forte",
            "perfil": "PROTOCOLO"})
        self.assertEqual(codigo, 200)
        _, sessao = requisitar(self.base, "POST", "/login",
                               {"login": "maria.protocolo",
                                "senha": "senha-forte"}, token=False)
        codigo, erro = requisitar(self.base, "POST", "/fornecedores",
                                  {"razao_social": "X"},
                                  token=sessao["token"])
        self.assertEqual(codigo, 403)
        self.assertIn("PROTOCOLO", erro["erro"])
        # Mas pode autuar processo (área dele) — e a autuação funciona.
        codigo, _ = requisitar(self.base, "POST", "/processos", {
            "tipo": "ADMINISTRATIVO", "assunto": "Da alçada do protocolo",
            "unidade_origem_id": 1, "data_autuacao": "2026-01-02",
        }, token=sessao["token"])
        self.assertEqual(codigo, 200)

    def test_auditoria_registra_login_do_operador(self):
        codigo, _ = requisitar(self.base, "POST", "/contratacoes", {
            "modalidade": "PREGAO", "objeto": "Auditar operador",
            "valor_estimado": 1000, "unidade_demandante_id": 1,
            "data": "2026-01-03"})
        self.assertEqual(codigo, 200)
        codigo, trilha = requisitar(self.base, "GET", "/auditoria")
        self.assertEqual(codigo, 200)
        self.assertEqual(trilha[0]["usuario"], "admin")

    def test_consultas_publicas_sem_login(self):
        for rota in ("/organograma", "/cargos", "/painel",
                     "/transparencia/pendencias"):
            self.assertEqual(
                requisitar(self.base, "GET", rota, token=False)[0], 200,
                f"rota pública falhou: {rota}")


if __name__ == "__main__":
    unittest.main()
