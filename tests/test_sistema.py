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

    def test_todo_setor_tem_atividade(self):
        # Invariante do modelo: cada setor com login próprio tem ao menos
        # uma atividade/área. Não são setores com login: o nó agrupador dos
        # gabinetes e os serviços auxiliares operacionais de 4º grau (copa,
        # limpeza, etc.), operados sob a coordenadoria responsável — exceto
        # o Departamento do e-Social, que tem artigo próprio. A Coordenadoria
        # de TI é setor de infraestrutura, sem área de negócio: a gestão de
        # acessos/logins é prerrogativa do administrador, não área de setor.
        from orgao.cmdc import SERVICOS_AUXILIARES
        operacionais = [s for s in SERVICOS_AUXILIARES
                        if s != "Departamento do e-Social"]
        excluidos = tuple(
            ["Gabinetes de Vereadores",
             "Coordenadoria de Tecnologia da Informação e Comunicação"]
            + operacionais)
        marcadores = ",".join("?" * len(excluidos))
        sem_area = self.banco.execute(
            f"""SELECT nome FROM unidade u
                WHERE u.nome NOT IN ({marcadores})
                  AND NOT EXISTS (SELECT 1 FROM unidade_area a
                                   WHERE a.unidade_id = u.id)""", excluidos
        ).fetchall()
        self.assertEqual(sem_area, [], f"setores sem atividade: {sem_area}")

    def test_todo_setor_tem_competencia(self):
        # Cada setor tem competência legal cadastrada (exceto o agrupador).
        sem_comp = self.banco.execute(
            """SELECT nome FROM unidade u
                WHERE u.nome <> 'Gabinetes de Vereadores'
                  AND NOT EXISTS (SELECT 1 FROM competencia c
                                   WHERE c.unidade_id = u.id)"""
        ).fetchall()
        self.assertEqual(sem_comp, [], f"setores sem competência: {sem_comp}")

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
