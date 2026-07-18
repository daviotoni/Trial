"""Testes de compras/contratos (Lei 14.133/2021) e transparência."""

import unittest

from sistema import compras, transparencia
from sistema.demo import criar_banco
from sistema.servicos import RegraViolada


class TestCompras(unittest.TestCase):
    def setUp(self):
        self.banco = criar_banco()
        self.fornecedor = compras.cadastrar_fornecedor(
            self.banco, "Alfa Serviços Ltda", "00.000.000/0001-00")

    def tearDown(self):
        self.banco.close()

    def _contratacao_homologada(self, valor=50000):
        cid, _ = compras.abrir_contratacao(
            self.banco, "PREGAO", "Serviços de limpeza", valor, 1, "2026-02-01")
        compras.homologar(self.banco, cid, "2026-02-15")
        return cid

    def test_dispensa_respeita_limite(self):
        # Acima do limite do art. 75, II → bloqueia.
        with self.assertRaises(RegraViolada):
            compras.abrir_contratacao(
                self.banco, "DISPENSA", "Compra grande", 80000, 1, "2026-02-01")
        # Abaixo do limite → passa.
        cid, numero = compras.abrir_contratacao(
            self.banco, "DISPENSA", "Compra pequena", 30000, 1, "2026-02-01")
        self.assertEqual(numero, "DISPENSA 1/2026")

    def test_abertura_autua_processo(self):
        cid, _ = compras.abrir_contratacao(
            self.banco, "PREGAO", "Objeto X", 10000, 1, "2026-02-01")
        (processo_id,) = self.banco.execute(
            "SELECT processo_id FROM contratacao WHERE id = ?", (cid,)
        ).fetchone()
        self.assertIsNotNone(processo_id)

    def test_contrato_exige_homologacao(self):
        cid, _ = compras.abrir_contratacao(
            self.banco, "PREGAO", "Objeto Y", 10000, 1, "2026-02-01")
        with self.assertRaises(RegraViolada):
            compras.celebrar_contrato(self.banco, cid, self.fornecedor,
                                      9000, "2026-03-01")
        compras.homologar(self.banco, cid, "2026-02-15")
        contrato = compras.celebrar_contrato(
            self.banco, cid, self.fornecedor, 9000, "2026-03-01")
        self.assertGreater(contrato, 0)

    def test_empenhos_nao_excedem_contrato(self):
        cid = self._contratacao_homologada()
        contrato = compras.celebrar_contrato(
            self.banco, cid, self.fornecedor, 10000, "2026-03-01")
        compras.empenhar(self.banco, 6000, "1ª parcela", "2026-03-05", contrato)
        with self.assertRaises(RegraViolada):
            compras.empenhar(self.banco, 5000, "2ª parcela", "2026-04-05",
                             contrato)
        _, numero = compras.empenhar(self.banco, 4000, "2ª parcela",
                                     "2026-04-05", contrato)
        self.assertEqual(numero, "2/2026")

    def test_revogacao_bloqueia_contrato(self):
        cid = self._contratacao_homologada()
        compras.revogar(self.banco, cid, "2026-02-20")
        with self.assertRaises(RegraViolada):
            compras.celebrar_contrato(self.banco, cid, self.fornecedor,
                                      9000, "2026-03-01")

    def test_auditoria_registra_operacoes(self):
        cid = self._contratacao_homologada()
        compras.celebrar_contrato(self.banco, cid, self.fornecedor,
                                  9000, "2026-03-01")
        trilha = transparencia.trilha_auditoria(self.banco)
        operacoes = [(e["tabela"], e["operacao"]) for e in trilha]
        self.assertIn(("contratacao", "INSERT"), operacoes)
        self.assertIn(("contratacao", "UPDATE"), operacoes)
        self.assertIn(("contrato", "INSERT"), operacoes)


class TestTransparencia(unittest.TestCase):
    def setUp(self):
        self.banco = criar_banco()

    def tearDown(self):
        self.banco.close()

    def test_pendencias_e_publicacao(self):
        fornecedor = compras.cadastrar_fornecedor(self.banco, "Beta Ltda")
        cid, _ = compras.abrir_contratacao(
            self.banco, "PREGAO", "Objeto Z", 10000, 1, "2026-02-01")
        compras.homologar(self.banco, cid, "2026-02-15")
        contrato = compras.celebrar_contrato(
            self.banco, cid, fornecedor, 9000, "2026-03-01")

        pendencias = transparencia.pendencias_publicacao(self.banco)
        self.assertEqual(len(pendencias["contratos"]), 1)

        transparencia.publicar(self.banco, "contrato", f"contrato:{contrato}",
                               "2026-03-02", "https://transparencia.exemplo")
        pendencias = transparencia.pendencias_publicacao(self.banco)
        self.assertEqual(len(pendencias["contratos"]), 0)

    def test_painel(self):
        numeros = transparencia.painel(self.banco)
        self.assertEqual(numeros["unidades"], 49)
        self.assertEqual(numeros["vagas_anexo_i"], 615)
        self.assertEqual(numeros["contratos"], 0)


if __name__ == "__main__":
    unittest.main()
