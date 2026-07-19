"""Testes de acesso por unidade (Fase 2): áreas por setor e posse do processo."""

import unittest

from sistema import autenticacao, servicos
from sistema.autenticacao import AcessoNegado
from sistema.demo import criar_banco


class TestAcessoPorUnidade(unittest.TestCase):
    def setUp(self):
        self.banco = criar_banco()

    def tearDown(self):
        self.banco.close()

    def _uid(self, nome):
        return self.banco.execute(
            "SELECT id FROM unidade WHERE nome = ?", (nome,)).fetchone()[0]

    def _usuario(self, login, perfil, unidade_nome=None):
        uid = self._uid(unidade_nome) if unidade_nome else None
        autenticacao.criar_usuario(self.banco, login, "senha123", perfil,
                                   unidade_id=uid)
        return autenticacao.autenticar(self.banco, login, "senha123")

    # --- áreas por setor --------------------------------------------

    def test_gabinete_so_opera_legislativo(self):
        gab = "Gabinete do(a) Vereador(a) Chiquinho Caipira"
        u = self._usuario("ver.chiquinho", "LEGISLATIVO", gab)
        self.assertEqual(
            autenticacao.areas_do_usuario(self.banco, u), {"LEGISLATIVO"})
        autenticacao.exigir(self.banco, u, "LEGISLATIVO")  # não levanta
        with self.assertRaises(AcessoNegado):
            autenticacao.exigir(self.banco, u, "COMPRAS")

    def test_secretaria_geral_opera_protocolo(self):
        u = self._usuario("prot1", "PROTOCOLO", "Coordenadoria da Secretaria-Geral")
        self.assertEqual(
            autenticacao.areas_do_usuario(self.banco, u), {"PROTOCOLO"})
        with self.assertRaises(AcessoNegado):
            autenticacao.exigir(self.banco, u, "LEGISLATIVO")

    def test_cpl_opera_compras(self):
        u = self._usuario("cpl1", "COMPRAS", "Comissão Permanente de Licitação")
        self.assertIn("COMPRAS", autenticacao.areas_do_usuario(self.banco, u))

    def test_rh_opera_pessoal_e_folha(self):
        u = self._usuario("rh1", "RH", "Coordenadoria de Recursos Humanos")
        self.assertEqual(
            autenticacao.areas_do_usuario(self.banco, u), {"PESSOAL", "FOLHA"})

    def test_admin_e_superusuario(self):
        u = self._usuario("adm", "ADMIN")  # sem unidade
        self.assertEqual(
            autenticacao.areas_do_usuario(self.banco, u), set(autenticacao.AREAS))

    def test_perfil_legado_sem_unidade(self):
        # Compatibilidade: sem lotação, a alçada vem do perfil.
        u = self._usuario("leg", "CONTROLE")
        self.assertEqual(
            autenticacao.areas_do_usuario(self.banco, u),
            {"CONTROLE", "TRANSPARENCIA", "FOLHA"})

    # --- posse do processo ------------------------------------------

    def test_posse_so_o_setor_que_detem_age(self):
        a = "Coordenadoria da Secretaria-Geral"
        b = "Diretoria-Geral"
        user_a = self._usuario("ua", "PROTOCOLO", a)
        user_b = self._usuario("ub", "PROTOCOLO", b)
        pid, _ = servicos.autuar_processo(
            self.banco, "ADMINISTRATIVO", "Teste posse", self._uid(a),
            "2025-09-10")

        # Processo está em A: só A age.
        autenticacao.exigir_posse(self.banco, user_a, pid)  # ok
        with self.assertRaises(AcessoNegado):
            autenticacao.exigir_posse(self.banco, user_b, pid)

        # Encaminha para B: agora só B age.
        servicos.tramitar(self.banco, pid, self._uid(b), "segue", "2025-09-11")
        autenticacao.exigir_posse(self.banco, user_b, pid)  # ok
        with self.assertRaises(AcessoNegado):
            autenticacao.exigir_posse(self.banco, user_a, pid)

    def test_admin_ignora_posse(self):
        a = "Coordenadoria da Secretaria-Geral"
        admin = self._usuario("adm2", "ADMIN")
        pid, _ = servicos.autuar_processo(
            self.banco, "ADMINISTRATIVO", "X", self._uid(a), "2025-09-10")
        autenticacao.exigir_posse(self.banco, admin, pid)  # não levanta


if __name__ == "__main__":
    unittest.main()
