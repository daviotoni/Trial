"""Testes da gestão de usuários: editar acesso, desativar e excluir."""

import unittest

from sistema import autenticacao
from sistema.api import Aplicacao
from sistema.autenticacao import AcessoNegado
from sistema.demo import criar_banco


class TestGestaoExclusivaDoAdmin(unittest.TestCase):
    """A gestão de acessos/logins é privativa do administrador."""

    def setUp(self):
        self.app = Aplicacao(":memory:")
        self.app.banco.commit()

    def test_setor_nao_admin_nao_gere_usuarios(self):
        # TI (antes tinha USUARIOS) e qualquer outro setor: sem acesso.
        ti = self.app.banco.execute(
            "SELECT id FROM unidade WHERE nome = "
            "'Coordenadoria de Tecnologia da Informação e Comunicação'"
        ).fetchone()[0]
        self.assertEqual(
            self.app.banco.execute(
                "SELECT COUNT(*) FROM unidade_area WHERE area = 'USUARIOS'"
            ).fetchone()[0], 0)
        self.app.usuario_atual = {"login": "ti", "perfil": "LEGISLATIVO",
                                  "unidade_id": ti}
        for chamada in (
            lambda: self.app.listar_usuarios(),
            lambda: self.app.criar_usuario({"login": "x", "senha": "senha1234",
                                            "unidade_id": ti}),
            lambda: self.app.editar_usuario(1, {"ativo": 0}),
            lambda: self.app.excluir_usuario(1),
        ):
            with self.assertRaises(AcessoNegado):
                chamada()

    def test_admin_gere_normalmente(self):
        self.app.usuario_atual = {"login": "admin", "perfil": "ADMIN"}
        antes = len(self.app.listar_usuarios())
        self.app.criar_usuario({"login": "novo", "senha": "senha1234",
                                "unidade_id": 50})
        self.assertEqual(len(self.app.listar_usuarios()), antes + 1)


class TestGestaoUsuarios(unittest.TestCase):
    def setUp(self):
        self.banco = criar_banco()
        autenticacao.garantir_admin_inicial(self.banco)
        self.gab = self.banco.execute(
            "SELECT id FROM unidade WHERE nome LIKE "
            "'Gabinete do(a) Vereador(a) Chiquinho%'").fetchone()[0]
        self.outro_gab = self.banco.execute(
            "SELECT id FROM unidade WHERE nome LIKE 'Gabinete do(a)%' "
            "AND id <> ?", (self.gab,)).fetchone()[0]
        self.uid = autenticacao.criar_usuario(
            self.banco, "gab.teste", "senha1234", "LEGISLATIVO",
            unidade_id=self.gab)

    def tearDown(self):
        self.banco.close()

    def _admin_id(self):
        return self.banco.execute(
            "SELECT id FROM usuario WHERE login = 'admin'").fetchone()[0]

    # --- edição de acesso -------------------------------------------

    def test_trocar_setor_muda_o_acesso(self):
        login = autenticacao.atualizar_usuario(
            self.banco, self.uid, unidade_id=self.outro_gab)
        self.assertEqual(login, "gab.teste")
        (unidade,) = self.banco.execute(
            "SELECT unidade_id FROM usuario WHERE id = ?",
            (self.uid,)).fetchone()
        self.assertEqual(unidade, self.outro_gab)

    def test_trocar_para_setor_inexistente_bloqueado(self):
        with self.assertRaises(ValueError):
            autenticacao.atualizar_usuario(
                self.banco, self.uid, unidade_id=99999)

    def test_redefinir_senha(self):
        autenticacao.atualizar_usuario(
            self.banco, self.uid, senha="novaSenha99")
        self.assertIsNone(autenticacao.autenticar(
            self.banco, "gab.teste", "senha1234"))
        self.assertIsNotNone(autenticacao.autenticar(
            self.banco, "gab.teste", "novaSenha99"))

    def test_senha_curta_bloqueada(self):
        with self.assertRaises(ValueError):
            autenticacao.atualizar_usuario(self.banco, self.uid, senha="curta")

    def test_desativar_impede_login_e_reativar_devolve(self):
        autenticacao.atualizar_usuario(self.banco, self.uid, ativo=0)
        self.assertIsNone(autenticacao.autenticar(
            self.banco, "gab.teste", "senha1234"))
        autenticacao.atualizar_usuario(self.banco, self.uid, ativo=1)
        self.assertIsNotNone(autenticacao.autenticar(
            self.banco, "gab.teste", "senha1234"))

    def test_edicao_vazia_bloqueada(self):
        with self.assertRaises(ValueError):
            autenticacao.atualizar_usuario(self.banco, self.uid)

    def test_editar_usuario_inexistente(self):
        with self.assertRaises(ValueError):
            autenticacao.atualizar_usuario(self.banco, 99999, ativo=0)

    # --- exclusão e proteção do último admin ------------------------

    def test_excluir_usuario(self):
        login = autenticacao.excluir_usuario(self.banco, self.uid)
        self.assertEqual(login, "gab.teste")
        self.assertIsNone(self.banco.execute(
            "SELECT 1 FROM usuario WHERE id = ?", (self.uid,)).fetchone())

    def test_ultimo_admin_nao_pode_ser_excluido_nem_desativado(self):
        admin = self._admin_id()
        with self.assertRaises(ValueError):
            autenticacao.excluir_usuario(self.banco, admin)
        with self.assertRaises(ValueError):
            autenticacao.atualizar_usuario(self.banco, admin, ativo=0)

    def test_admin_extra_libera_a_remocao_do_primeiro(self):
        autenticacao.criar_usuario(
            self.banco, "admin2", "senha1234", "ADMIN")
        login = autenticacao.excluir_usuario(self.banco, self._admin_id())
        self.assertEqual(login, "admin")

    # --- sessões derrubadas quando o acesso muda --------------------

    def test_sessoes_do_login_sao_encerradas(self):
        sessoes = autenticacao.Sessoes()
        token = sessoes.abrir({"login": "gab.teste", "perfil": "LEGISLATIVO"})
        outro = sessoes.abrir({"login": "admin", "perfil": "ADMIN"})
        sessoes.encerrar_do_login("gab.teste")
        self.assertIsNone(sessoes.usuario(token))
        self.assertIsNotNone(sessoes.usuario(outro))


if __name__ == "__main__":
    unittest.main()
