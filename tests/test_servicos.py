"""Testes das regras de negócio (Lei 3.525/2025 e Lei 1.506/2000)."""

import unittest

from sistema import servicos
from sistema.cenario import montar_cenario
from sistema.demo import criar_banco
from sistema.servicos import RegraViolada


class TestRegrasDePessoal(unittest.TestCase):
    def setUp(self):
        self.banco = criar_banco()
        self.banco.execute(
            "INSERT INTO servidor (id, nome, vinculo, data_admissao, "
            "vencimento_base) VALUES (100, 'Efetivo Antigo', 'EFETIVO', "
            "'2015-01-01', 4000)"
        )
        self.banco.execute(
            "INSERT INTO servidor (id, nome, vinculo, data_admissao) VALUES "
            "(101, 'Comissionado Novo', 'COMISSIONADO', '2025-09-01')"
        )
        self.banco.execute(
            "INSERT INTO servidor (id, nome, vinculo, data_admissao, "
            "vencimento_base) VALUES (102, 'Efetivo Recente', 'EFETIVO', "
            "'2024-06-01', 4000)"
        )

    def tearDown(self):
        self.banco.close()

    def _cargo(self, denominacao):
        return self.banco.execute(
            "SELECT id FROM cargo WHERE denominacao = ?", (denominacao,)
        ).fetchone()[0]

    def test_nomeacao_respeita_vagas(self):
        cargo = self._cargo("Diretor-Geral")  # 1 vaga
        servicos.nomear(self.banco, 101, cargo, 1, "P1", "2025-09-01")
        with self.assertRaises(RegraViolada):
            servicos.nomear(self.banco, 100, cargo, 1, "P2", "2025-09-02")

    def test_funcao_confianca_exige_efetivo(self):
        cargo = self._cargo("Controlador-Geral")  # FC-1
        with self.assertRaises(RegraViolada):
            servicos.nomear(self.banco, 101, cargo, 1, "P1", "2025-09-01")

    def test_funcao_confianca_exige_dois_anos(self):
        cargo = self._cargo("Controlador-Geral")
        with self.assertRaises(RegraViolada):
            servicos.nomear(self.banco, 102, cargo, 1, "P1", "2025-09-01")
        # Efetivo com 10 anos de casa pode.
        provimento = servicos.nomear(self.banco, 100, cargo, 1, "P2", "2025-09-01")
        self.assertGreater(provimento, 0)

    def test_exoneracao_libera_vaga(self):
        cargo = self._cargo("Diretor-Geral")
        provimento = servicos.nomear(self.banco, 101, cargo, 1, "P1", "2025-09-01")
        self.assertEqual(servicos.vagas_disponiveis(self.banco, cargo), 0)
        servicos.exonerar(self.banco, provimento, "2025-12-31")
        self.assertEqual(servicos.vagas_disponiveis(self.banco, cargo), 1)


class TestProtocolo(unittest.TestCase):
    def setUp(self):
        self.banco = criar_banco()

    def tearDown(self):
        self.banco.close()

    def test_numeracao_sequencial_por_ano(self):
        _, n1 = servicos.autuar_processo(self.banco, "ADMINISTRATIVO", "A", 1,
                                         "2026-01-05")
        _, n2 = servicos.autuar_processo(self.banco, "ADMINISTRATIVO", "B", 1,
                                         "2026-02-01")
        _, n3 = servicos.autuar_processo(self.banco, "LEGISLATIVO", "C", 1,
                                         "2027-01-10")
        self.assertEqual((n1, n2, n3), ("1/2026", "2/2026", "1/2027"))

    def test_tramitacao_encadeada(self):
        pid, _ = servicos.autuar_processo(self.banco, "ADMINISTRATIVO", "A", 1,
                                          "2026-01-05")
        servicos.tramitar(self.banco, pid, 2, "segue", "2026-01-06")
        servicos.tramitar(self.banco, pid, 3, "segue", "2026-01-07")
        origens = [linha[0] for linha in self.banco.execute(
            "SELECT unidade_origem_id FROM tramitacao WHERE processo_id = ? "
            "ORDER BY id", (pid,)
        )]
        self.assertEqual(origens, [1, 2])  # cada envio parte do destino anterior


class TestFolha(unittest.TestCase):
    def setUp(self):
        self.banco = criar_banco()
        montar_cenario(self.banco)

    def tearDown(self):
        self.banco.close()

    def _valor(self, folha_id, nome, rubrica):
        linha = self.banco.execute(
            """SELECT fi.valor FROM folha_item fi
               JOIN servidor s ON s.id = fi.servidor_id
               WHERE fi.folha_id = ? AND s.nome = ? AND fi.rubrica_codigo = ?""",
            (folha_id, nome, rubrica),
        ).fetchone()
        return linha[0] if linha else None

    def test_gal_acima_do_teto_bloqueia(self):
        with self.assertRaises(RegraViolada):
            servicos.calcular_folha(self.banco, "2025-09", percentual_gal=200)

    def test_avaliacao_de_desempenho_e_produtividade(self):
        # Paulo Sales (efetivo, Técnico Legislativo, venc. 5.200) avaliado
        # com 92 pontos → EXCELENTE → AD-PROD de 70% (Lei 3.226/2022).
        (sid,) = self.banco.execute(
            "SELECT id FROM servidor WHERE nome = 'Paulo Sales'").fetchone()
        conceito = servicos.avaliar_desempenho(
            self.banco, sid, "2025-S2", 92, "Chefia", "2025-08-30")
        self.assertEqual(conceito, "EXCELENTE")
        folha = servicos.calcular_folha(self.banco, "2025-09",
                                        percentual_gal=100)
        self.assertEqual(self._valor(folha, "Paulo Sales", "AD-PROD"), 3640.0)

    def test_avaliacao_exige_efetivo(self):
        (sid,) = self.banco.execute(
            "SELECT id FROM servidor WHERE nome = 'Marcos Vidal'").fetchone()
        with self.assertRaises(RegraViolada):
            servicos.avaliar_desempenho(self.banco, sid, "2025-S2", 90,
                                        "Chefia", "2025-08-30")

    def test_faixas_de_conceito(self):
        self.assertEqual(servicos.conceito_por_pontuacao(95),
                         ("EXCELENTE", 70))
        self.assertEqual(servicos.conceito_por_pontuacao(85),
                         ("MUITO_BOM", 50))
        self.assertEqual(servicos.conceito_por_pontuacao(75), ("BOM", 40))
        self.assertEqual(servicos.conceito_por_pontuacao(60), ("REGULAR", 20))
        self.assertEqual(servicos.conceito_por_pontuacao(30),
                         ("INSATISFATORIO", 0))

    def test_folha_do_cenario(self):
        folha = servicos.calcular_folha(self.banco, "2025-09", percentual_gal=100)
        # Comissionado puro: VENC pelo símbolo DAS-8 + GAL.
        self.assertEqual(self._valor(folha, "Marcos Vidal", "VENC"), 15925)
        self.assertEqual(self._valor(folha, "Marcos Vidal", "GAL"), 15925)
        # Efetiva em cargo em comissão: GRAT-CC de 100% do símbolo CAE-1.
        self.assertEqual(self._valor(folha, "Helena Duarte", "GRAT-CC"), 6870)
        # Presidente de comissão de licitação: GRAT-COM 40% sobre o símbolo.
        self.assertEqual(self._valor(folha, "Helena Duarte", "GRAT-COM"), 2748)
        # Técnico Legislativo: representação de 60% (art. 8º).
        self.assertEqual(self._valor(folha, "Paulo Sales", "REP-TL"), 3120)
        self.assertAlmostEqual(servicos.total_folha(self.banco, folha), 65388.0)


if __name__ == "__main__":
    unittest.main()
