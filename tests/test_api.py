"""Testes da API REST (servidor real em thread, cliente urllib)."""

import json
import threading
import unittest
import urllib.error
import urllib.request

from sistema.api import criar_servidor_http


def requisitar(base, metodo, caminho, corpo=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    requisicao = urllib.request.Request(
        base + caminho, data=dados, method=metodo,
        headers={"Content-Type": "application/json"},
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

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()

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


if __name__ == "__main__":
    unittest.main()
