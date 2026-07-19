"""Testes do schema e da carga inicial do sistema."""

import unittest

from sistema.demo import criar_banco


class TestBancoSistema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.banco = criar_banco()

    @classmethod
    def tearDownClass(cls):
        cls.banco.close()

    def _um(self, sql):
        return self.banco.execute(sql).fetchone()[0]

    def test_unidades_carregadas(self):
        # 49 unidades da estrutura da Lei 3.525 + 29 gabinetes (roster).
        self.assertEqual(self._um("SELECT COUNT(*) FROM unidade"), 78)
        self.assertEqual(
            self._um("SELECT COUNT(*) FROM unidade "
                     "WHERE nome LIKE 'Gabinete do(a)%'"), 29
        )
        self.assertEqual(
            self._um("SELECT COUNT(*) FROM unidade WHERE grau = 2"), 20
        )
        # Órgãos políticos ficam fora da hierarquia de graus (art. 2º, p.u.)
        self.assertEqual(
            self._um("SELECT COUNT(*) FROM unidade "
                     "WHERE tipo = 'POLITICO' AND grau IS NULL"), 3
        )

    def test_hierarquia_integra(self):
        # Só a Mesa Diretora não tem pai.
        self.assertEqual(
            self._um("SELECT COUNT(*) FROM unidade WHERE unidade_pai_id IS NULL"), 1
        )
        self.assertEqual(
            self.banco.execute(
                "SELECT nome FROM unidade WHERE unidade_pai_id IS NULL"
            ).fetchone()[0],
            "Mesa Diretora",
        )

    def test_anexo_i_totais(self):
        self.assertEqual(self._um("SELECT SUM(quantidade_vagas) FROM cargo"), 615)
        self.assertEqual(
            self._um("SELECT SUM(quantidade_vagas) FROM cargo "
                     "WHERE tipo = 'FUNCAO_CONFIANCA'"), 13
        )

    def test_simbolos_fc_sao_funcao_confianca(self):
        self.assertEqual(
            self._um("SELECT COUNT(*) FROM simbolo WHERE codigo LIKE 'FC-%' "
                     "AND natureza != 'FUNCAO_CONFIANCA'"), 0
        )

    def test_rubricas_da_lei(self):
        self.assertEqual(
            self._um("SELECT percentual_max FROM rubrica WHERE codigo = 'GAL'"), 150
        )
        self.assertEqual(
            self._um("SELECT percentual_max FROM rubrica WHERE codigo = 'GRAT-COM'"),
            40,
        )
        self.assertEqual(
            self._um("SELECT incorporavel FROM rubrica WHERE codigo = 'GRAT-COM'"), 0
        )

    def test_dirigentes_com_lotacao(self):
        self.assertEqual(
            self._um("SELECT COUNT(*) FROM cargo "
                     "WHERE unidade_lotacao_id IS NOT NULL"), 29
        )

    def test_fluxo_processo_e_tramitacao(self):
        c = self.banco.cursor()
        c.execute("INSERT INTO processo (numero, ano, tipo, assunto, data_autuacao) "
                  "VALUES (1, 2026, 'ADMINISTRATIVO', 'Teste', '2026-01-05')")
        pid = c.lastrowid
        origem = c.execute("SELECT id FROM unidade WHERE nome = "
                           "'Coordenadoria da Secretaria-Geral'").fetchone()[0]
        destino = c.execute("SELECT id FROM unidade WHERE nome = "
                            "'Diretoria-Geral'").fetchone()[0]
        c.execute("INSERT INTO tramitacao (processo_id, unidade_origem_id, "
                  "unidade_destino_id, data_envio) VALUES (?, ?, ?, '2026-01-06')",
                  (pid, origem, destino))
        self.assertEqual(
            self._um(f"SELECT COUNT(*) FROM tramitacao WHERE processo_id = {pid}"), 1
        )
        self.banco.rollback()

    def test_folha_gal_respeita_teto(self):
        # Simulação: GAL de 150% sobre DAS-8 — valor esperado 23.887,50
        base = self._um("SELECT retribuicao_base FROM simbolo WHERE codigo='DAS-8'")
        teto = self._um("SELECT percentual_max FROM rubrica WHERE codigo='GAL'")
        self.assertAlmostEqual(base * teto / 100, 23887.50)


if __name__ == "__main__":
    unittest.main()
