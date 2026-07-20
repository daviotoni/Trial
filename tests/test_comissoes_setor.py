"""Testes do setor de Comissões Permanentes: fila de parecer,
individualização por comissão e alçada (art. 33 do Regimento)."""

import unittest

from sistema import comissoes, legislativo
from sistema.api import Aplicacao
from sistema.autenticacao import AcessoNegado
from sistema.demo import criar_banco


class TestSetorComissoes(unittest.TestCase):
    def setUp(self):
        self.banco = criar_banco()
        self.gab = self.banco.execute(
            "SELECT id FROM unidade WHERE nome LIKE "
            "'Gabinete do(a) Vereador(a) Chiquinho%'").fetchone()[0]

    def tearDown(self):
        self.banco.close()

    def _protocolar(self, tipo="PL"):
        rid = legislativo.criar_rascunho(
            self.banco, self.gab, tipo, "Semana do Livro",
            texto="Art. 1º ...", justificativa="Justifico.")
        legislativo.protocolar_rascunho(
            self.banco, rid, self.gab, "2026-07-01")
        return rid

    # --- rename do setor --------------------------------------------

    def test_setor_chama_se_comissoes_permanentes(self):
        linha = self.banco.execute(
            "SELECT id FROM unidade WHERE nome = 'Comissões Permanentes'"
        ).fetchone()
        self.assertIsNotNone(linha)
        self.assertIsNone(self.banco.execute(
            "SELECT 1 FROM unidade WHERE nome = "
            "'Assistência às Comissões Permanentes'").fetchone())
        # mantém a ação de emitir parecer
        (acao,) = self.banco.execute(
            "SELECT acao FROM unidade_acao WHERE unidade_id = ?",
            (linha[0],)).fetchone()
        self.assertEqual(acao, "EMITIR_PARECER")

    # --- fila de matérias -------------------------------------------

    def test_materia_de_merito_entra_na_fila_e_sai_com_parecer_aprovado(self):
        rid = self._protocolar("PL")
        self.assertIn(rid, [m["id"] for m in
                            comissoes.materias_para_parecer(self.banco)])
        par = comissoes.emitir_parecer(
            self.banco, rid, "Comissão de Educação e Cultura", "FAVORAVEL",
            "Favorável.", "2026-07-02")
        # ainda na fila (parecer emitido, não aprovado)
        self.assertIn(rid, [m["id"] for m in
                            comissoes.materias_para_parecer(self.banco)])
        comissoes.aprovar_parecer(self.banco, par)
        self.assertNotIn(rid, [m["id"] for m in
                               comissoes.materias_para_parecer(self.banco)])

    def test_requerimento_nao_entra_na_fila_de_parecer(self):
        rid = self._protocolar("PL")
        req, _ = legislativo.requerimento_derivado(
            self.banco, self.gab, rid, "RETIRADA", "2026-07-02", "Retiro.")
        ids = [m["id"] for m in comissoes.materias_para_parecer(self.banco)]
        self.assertNotIn(req, ids)  # requerimento não é matéria de mérito

    # --- individualização por comissão ------------------------------

    def test_pareceres_individualizados_por_comissao(self):
        a = self._protocolar("PL")
        b = self._protocolar("PL")
        comissoes.emitir_parecer(
            self.banco, a, "Comissão de Educação e Cultura", "FAVORAVEL",
            "Favorável.", "2026-07-02")
        comissoes.emitir_parecer(
            self.banco, b, "Comissão de Finanças e Orçamento", "CONTRARIO",
            "Sem dotação.", "2026-07-02")
        educacao = self.banco.execute(
            "SELECT id FROM comissao_permanente WHERE nome = "
            "'Comissão de Educação e Cultura'").fetchone()[0]
        so_educacao = comissoes.pareceres_por_comissao(self.banco, educacao)
        self.assertEqual(len(so_educacao), 1)
        self.assertEqual(so_educacao[0]["comissao"],
                         "Comissão de Educação e Cultura")
        # sem filtro, traz os dois
        self.assertEqual(len(comissoes.pareceres_por_comissao(self.banco)), 2)

    def test_rejeitar_parecer(self):
        rid = self._protocolar("PL")
        par = comissoes.emitir_parecer(
            self.banco, rid, "Comissão de Educação e Cultura", "FAVORAVEL",
            "Favorável.", "2026-07-02")
        comissoes.rejeitar_parecer(self.banco, par)
        (situacao,) = self.banco.execute(
            "SELECT situacao FROM parecer WHERE id = ?", (par,)).fetchone()
        self.assertEqual(situacao, "REJEITADO")

    # --- alçada: só o setor de comissões ----------------------------

    def test_api_gate_emitir_parecer(self):
        app = Aplicacao(":memory:")
        gab = app.banco.execute(
            "SELECT id FROM unidade WHERE nome LIKE '%Chiquinho%'"
        ).fetchone()[0]
        rid = legislativo.criar_rascunho(
            app.banco, gab, "PL", "X", texto="Art. 1º", justificativa="J.")
        legislativo.protocolar_rascunho(app.banco, rid, gab, "2026-07-01")
        app.banco.commit()
        com = app.banco.execute(
            "SELECT id FROM unidade WHERE nome = 'Comissões Permanentes'"
        ).fetchone()[0]

        # gabinete não emite parecer
        app.usuario_atual = {"login": "gab", "perfil": "LEGISLATIVO",
                             "unidade_id": gab}
        with self.assertRaises(AcessoNegado):
            app.emitir_parecer(rid, {"comissao": 1, "tipo": "FAVORAVEL",
                                     "ementa": "X"})
        with self.assertRaises(AcessoNegado):
            app.materias_para_parecer()

        # setor de comissões emite
        app.usuario_atual = {"login": "com", "perfil": "LEGISLATIVO",
                             "unidade_id": com}
        resposta = app.emitir_parecer(
            rid, {"comissao": 1, "tipo": "FAVORAVEL", "ementa": "Favorável."})
        self.assertIn("id", resposta)


if __name__ == "__main__":
    unittest.main()
