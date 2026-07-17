"""Testes da estrutura da CMDC conforme a Lei 3.525/2025."""

import unittest

from orgao.cmdc import (
    ASSESSORAMENTO_PARLAMENTAR,
    COORDENADORIAS,
    ORGAOS_SUPERIORES,
    SERVICOS_AUXILIARES,
    construir_cmdc,
)
from orgao.modelos import Esfera, NaturezaJuridica, Poder


class TestCMDC(unittest.TestCase):
    def setUp(self):
        self.cmdc = construir_cmdc()

    def test_identificacao(self):
        self.assertEqual(self.cmdc.sigla, "CMDC")
        self.assertEqual(self.cmdc.poder, Poder.LEGISLATIVO)
        self.assertEqual(self.cmdc.esfera, Esfera.MUNICIPAL)
        self.assertEqual(
            self.cmdc.natureza_juridica, NaturezaJuridica.ADMINISTRACAO_DIRETA
        )
        self.assertIn("3.525/2025", self.cmdc.base_legal_criacao.numero)

    def test_mesa_diretora_no_topo(self):
        self.assertEqual(self.cmdc.unidade_topo.nome, "Mesa Diretora")

    def test_graus_da_lei_3525(self):
        # 1º grau: 8 órgãos superiores listados + Diretoria-Geral = 9
        self.assertEqual(len(ORGAOS_SUPERIORES) + 1, 9)
        # 2º grau: 20 coordenadorias/diretoria administrativa
        self.assertEqual(len(COORDENADORIAS), 20)
        # 3º e 4º graus presentes
        self.assertEqual(len(ASSESSORAMENTO_PARLAMENTAR), 4)
        self.assertEqual(len(SERVICOS_AUXILIARES), 8)

    def test_diretoria_geral_subordinada_a_presidencia(self):
        nomes = {u.nome for _, u in self.cmdc.percorrer()}
        self.assertIn("Diretoria-Geral", nomes)
        presidencia = next(
            u for _, u in self.cmdc.percorrer() if u.nome == "Presidência"
        )
        self.assertIn(
            "Diretoria-Geral", [s.nome for s in presidencia.subunidades]
        )

    def test_coordenadorias_sob_diretoria_geral(self):
        dg = next(u for _, u in self.cmdc.percorrer() if u.nome == "Diretoria-Geral")
        nomes = [s.nome for s in dg.subunidades]
        self.assertEqual(len(nomes), 20)
        self.assertIn("Coordenadoria de Recursos Humanos", nomes)
        self.assertIn("Coordenadoria de Licitações e Contratos", nomes)

    def test_servicos_auxiliares_sob_diretoria_administrativa(self):
        da = next(
            u for _, u in self.cmdc.percorrer()
            if u.nome == "Diretoria Administrativa"
        )
        self.assertEqual(len(da.subunidades), len(SERVICOS_AUXILIARES))

    def test_total_unidades(self):
        # Mesa(1) + Presidência(1) + Gabinetes(1) + assessorias(4)
        # + órgãos superiores(8) + DG(1) + coordenadorias(20) + auxiliares(8) = 44
        self.assertEqual(self.cmdc.total_unidades(), 44)


if __name__ == "__main__":
    unittest.main()
