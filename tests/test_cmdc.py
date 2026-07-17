"""Testes da estrutura da CMDC conforme a Lei 3.525/2025."""

import unittest

from orgao.cmdc import (
    ANEXO_I,
    ASSESSORAMENTO_PARLAMENTAR,
    COMISSOES_PERMANENTES_ADMINISTRATIVAS,
    COORDENADORIAS,
    ORGAOS_SUPERIORES,
    SERVICOS_AUXILIARES,
    construir_cmdc,
    eh_funcao_confianca,
    total_cargos_comissionados,
    total_funcoes_gratificadas,
    total_vagas_anexo_i,
)
from orgao.modelos import Esfera, NaturezaJuridica, Poder, TipoCargo


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
        # + órgãos superiores(8) + DG(1) + coordenadorias(20) + auxiliares(8)
        # + comissões permanentes administrativas(5) = 49
        self.assertEqual(self.cmdc.total_unidades(), 49)

    def test_comissoes_permanentes_administrativas(self):
        nomes = {u.nome for _, u in self.cmdc.percorrer()}
        self.assertEqual(len(COMISSOES_PERMANENTES_ADMINISTRATIVAS), 5)
        for comissao in COMISSOES_PERMANENTES_ADMINISTRATIVAS:
            self.assertIn(comissao, nomes)


class TestAnexoI(unittest.TestCase):
    def test_totais(self):
        self.assertEqual(total_vagas_anexo_i(), 615)
        self.assertEqual(total_funcoes_gratificadas(), 13)
        self.assertEqual(total_cargos_comissionados(), 602)
        self.assertEqual(len(ANEXO_I), 49)

    def test_fc_significa_funcao_de_confianca(self):
        self.assertTrue(eh_funcao_confianca("FC-1"))
        self.assertFalse(eh_funcao_confianca("DAS-8"))

    def test_dirigentes_anexados_as_unidades(self):
        cmdc = construir_cmdc()
        # 9 órgãos superiores (incl. Diretoria-Geral) + 20 coordenadorias
        self.assertEqual(cmdc.total_cargos(), 29)
        cg = next(u for _, u in cmdc.percorrer() if u.nome == "Controladoria-Geral")
        self.assertEqual(cg.cargos[0].tipo, TipoCargo.FUNCAO_CONFIANCA)
        dg = next(u for _, u in cmdc.percorrer() if u.nome == "Diretoria-Geral")
        self.assertEqual(dg.cargos[0].tipo, TipoCargo.COMISSAO)


if __name__ == "__main__":
    unittest.main()
