"""Testes do Bloco 1 do módulo do gabinete: catálogo, rascunhos e protocolo."""

import unittest

from sistema import fluxo, legislativo
from sistema.demo import criar_banco
from sistema.servicos import RegraViolada


class TestGabinete(unittest.TestCase):
    def setUp(self):
        self.banco = criar_banco()
        self.gab = self.banco.execute(
            "SELECT id FROM unidade WHERE nome = "
            "'Gabinete do(a) Vereador(a) Chiquinho Caipira'").fetchone()[0]
        self.outro_gab = self.banco.execute(
            "SELECT id FROM unidade WHERE nome LIKE 'Gabinete do(a)%' "
            "AND id <> ? LIMIT 1", (self.gab,)).fetchone()[0]

    def tearDown(self):
        self.banco.close()

    # --- seed da 20ª legislatura ------------------------------------

    def test_seed_29_vereadores_com_mandato(self):
        (parlamentares,) = self.banco.execute(
            "SELECT COUNT(*) FROM parlamentar").fetchone()
        (mandatos,) = self.banco.execute(
            "SELECT COUNT(*) FROM mandato WHERE gabinete_unidade_id "
            "IS NOT NULL").fetchone()
        self.assertEqual(parlamentares, 29)
        self.assertEqual(mandatos, 29)

    def test_parlamentar_do_gabinete(self):
        pid = legislativo.parlamentar_do_gabinete(self.banco, self.gab)
        (nome,) = self.banco.execute(
            "SELECT nome FROM parlamentar WHERE id = ?", (pid,)).fetchone()
        self.assertEqual(nome, "Chiquinho Caipira")

    # --- rascunho ----------------------------------------------------

    def test_rascunho_sem_numero_e_invisivel_ao_publico(self):
        rid = legislativo.criar_rascunho(
            self.banco, self.gab, "PL", "Institui a Semana do Livro")
        numero, situacao = self.banco.execute(
            "SELECT numero, situacao FROM proposicao WHERE id = ?",
            (rid,)).fetchone()
        self.assertIsNone(numero)
        self.assertEqual(situacao, "RASCUNHO")
        # não conta no painel público
        from sistema import transparencia
        self.assertEqual(transparencia.painel(self.banco)["proposicoes"], 0)

    def test_rascunho_exige_ementa(self):
        with self.assertRaises(RegraViolada):
            legislativo.criar_rascunho(self.banco, self.gab, "PL", "   ")

    def test_rascunho_de_outro_gabinete_protegido(self):
        rid = legislativo.criar_rascunho(
            self.banco, self.gab, "PL", "Matéria do Chiquinho")
        for operacao in (
            lambda: legislativo.atualizar_rascunho(
                self.banco, rid, self.outro_gab, ementa="hackeada"),
            lambda: legislativo.excluir_rascunho(
                self.banco, rid, self.outro_gab),
            lambda: legislativo.protocolar_rascunho(
                self.banco, rid, self.outro_gab, "2025-09-10"),
        ):
            with self.assertRaises(RegraViolada):
                operacao()

    def test_editar_e_excluir_rascunho(self):
        rid = legislativo.criar_rascunho(
            self.banco, self.gab, "PL", "Versão 1")
        legislativo.atualizar_rascunho(
            self.banco, rid, self.gab, ementa="Versão 2",
            justificativa="Justifico.")
        rascunhos = legislativo.rascunhos_do_setor(self.banco, self.gab)
        self.assertEqual(rascunhos[0]["ementa"], "Versão 2")
        legislativo.excluir_rascunho(self.banco, rid, self.gab)
        self.assertEqual(
            legislativo.rascunhos_do_setor(self.banco, self.gab), [])

    # --- protocolo ---------------------------------------------------

    def _rascunho_completo(self, tipo="PL", **extras):
        return legislativo.criar_rascunho(
            self.banco, self.gab, tipo, "Institui a Semana do Livro",
            texto="Art. 1º Fica instituída...", justificativa="Justifico.",
            **extras)

    def test_protocolo_numera_autua_e_define_autor(self):
        rid = self._rascunho_completo()
        _, rotulo = legislativo.protocolar_rascunho(
            self.banco, rid, self.gab, "2025-09-10")
        self.assertEqual(rotulo, "PL 1/2025")
        autor, processo_id, situacao = self.banco.execute(
            "SELECT autor_parlamentar_id, processo_id, situacao "
            "FROM proposicao WHERE id = ?", (rid,)).fetchone()
        self.assertEqual(situacao, "EM_TRAMITACAO")
        self.assertEqual(
            autor, legislativo.parlamentar_do_gabinete(self.banco, self.gab))
        # processo autuado com origem no gabinete e vinculado ao rito PL
        origem, tipo_processo = self.banco.execute(
            "SELECT unidade_origem_id, tipo_processo_id FROM processo "
            "WHERE id = ?", (processo_id,)).fetchone()
        self.assertEqual(origem, self.gab)
        self.assertIsNotNone(tipo_processo)
        prox = fluxo.proxima_etapa(self.banco, processo_id)
        self.assertEqual(prox["unidade"], "Coordenadoria da Secretaria-Geral")

    def test_protocolo_exige_justificativa(self):
        rid = legislativo.criar_rascunho(
            self.banco, self.gab, "PL", "Sem justificativa",
            texto="Art. 1º ...")
        with self.assertRaises(RegraViolada):
            legislativo.protocolar_rascunho(
                self.banco, rid, self.gab, "2025-09-10")

    def test_projeto_exige_texto_articulado(self):
        rid = legislativo.criar_rascunho(
            self.banco, self.gab, "PELO", "Emenda à LOM",
            justificativa="Justifico.")
        with self.assertRaises(RegraViolada):
            legislativo.protocolar_rascunho(
                self.banco, rid, self.gab, "2025-09-10")

    def test_indicacao_exige_subtipo(self):
        rid = legislativo.criar_rascunho(
            self.banco, self.gab, "INDICACAO", "Pavimentação da rua X",
            justificativa="Justifico.")
        with self.assertRaises(RegraViolada):
            legislativo.protocolar_rascunho(
                self.banco, rid, self.gab, "2025-09-10")
        # com subtipo, protocola (indicação não exige texto articulado)
        legislativo.atualizar_rascunho(
            self.banco, rid, self.gab, subtipo="SIMPLES")
        _, rotulo = legislativo.protocolar_rascunho(
            self.banco, rid, self.gab, "2025-09-10")
        self.assertEqual(rotulo, "INDICACAO 1/2025")

    def test_subtipo_invalido_bloqueado(self):
        with self.assertRaises(RegraViolada):
            legislativo.criar_rascunho(
                self.banco, self.gab, "MOCAO", "Moção X",
                subtipo="INEXISTENTE")

    def test_rascunho_nao_entra_em_pauta(self):
        rid = self._rascunho_completo()
        sessao, _ = legislativo.convocar_sessao(
            self.banco, "ORDINARIA", "2025-09-16")
        with self.assertRaises(RegraViolada):
            legislativo.pautar(self.banco, sessao, rid, urgencia=True)


if __name__ == "__main__":
    unittest.main()
