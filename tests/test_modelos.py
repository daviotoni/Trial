"""Testes do modelo de estrutura de órgão público."""

import unittest

from orgao import (
    Cargo,
    Competencia,
    Esfera,
    NaturezaJuridica,
    Orgao,
    Poder,
    Servidor,
    TipoCargo,
    UnidadeAdministrativa,
)
from orgao.exemplo import construir_secretaria_educacao


class TestUnidadeAdministrativa(unittest.TestCase):
    def test_hierarquia_e_contagem(self):
        raiz = UnidadeAdministrativa("Gabinete", "GAB")
        dir1 = raiz.adicionar_subunidade(UnidadeAdministrativa("Diretoria A", "DA"))
        raiz.adicionar_subunidade(UnidadeAdministrativa("Diretoria B", "DB"))
        dir1.adicionar_subunidade(UnidadeAdministrativa("Divisão A1", "DA1"))

        # 1 raiz + 2 diretorias + 1 divisão = 4
        self.assertEqual(raiz.contar_unidades(), 4)

    def test_percorrer_gera_niveis(self):
        raiz = UnidadeAdministrativa("Topo")
        filho = raiz.adicionar_subunidade(UnidadeAdministrativa("Filho"))
        filho.adicionar_subunidade(UnidadeAdministrativa("Neto"))

        niveis = [nivel for nivel, _ in raiz.percorrer()]
        self.assertEqual(niveis, [0, 1, 2])

    def test_contar_e_listar_cargos_vagos(self):
        raiz = UnidadeAdministrativa("Gabinete")
        raiz.adicionar_cargo(Cargo("Secretário", TipoCargo.COMISSAO,
                                   ocupante=Servidor("Fulano")))
        raiz.adicionar_cargo(Cargo("Assessor", TipoCargo.COMISSAO))  # vago

        self.assertEqual(raiz.contar_cargos(), 2)
        vagos = raiz.cargos_vagos()
        self.assertEqual(len(vagos), 1)
        self.assertEqual(vagos[0].denominacao, "Assessor")


class TestCargo(unittest.TestCase):
    def test_cargo_vago(self):
        self.assertTrue(Cargo("X", TipoCargo.EFETIVO).vago)
        self.assertFalse(
            Cargo("X", TipoCargo.EFETIVO, ocupante=Servidor("Alguém")).vago
        )


class TestCompetencia(unittest.TestCase):
    def test_str_com_base_legal(self):
        from orgao.modelos import BaseLegal

        comp = Competencia("Fiscalizar", BaseLegal("Lei", "1/2020", "cria fiscalização"))
        self.assertIn("Fiscalizar", str(comp))
        self.assertIn("Lei 1/2020", str(comp))


class TestExemplo(unittest.TestCase):
    def setUp(self):
        self.orgao = construir_secretaria_educacao()

    def test_identificacao(self):
        self.assertEqual(self.orgao.sigla, "SME")
        self.assertEqual(self.orgao.esfera, Esfera.MUNICIPAL)
        self.assertEqual(self.orgao.poder, Poder.EXECUTIVO)
        self.assertEqual(
            self.orgao.natureza_juridica, NaturezaJuridica.ADMINISTRACAO_DIRETA
        )

    def test_estrutura_montada(self):
        # Gabinete + 2 diretorias + 4 unidades de 3º nível = 7
        self.assertEqual(self.orgao.total_unidades(), 7)
        self.assertGreater(self.orgao.total_cargos(), 0)

    def test_topo_definido(self):
        self.assertIsNotNone(self.orgao.unidade_topo)
        self.assertEqual(self.orgao.unidade_topo.sigla, "GAB")


if __name__ == "__main__":
    unittest.main()
