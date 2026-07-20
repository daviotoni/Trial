"""Testes da recusa formal da Presidência e recurso à CLJRF (art. 88, §1º)."""

import unittest

from sistema import legislativo
from sistema.api import Aplicacao
from sistema.autenticacao import AcessoNegado
from sistema.demo import criar_banco
from sistema.servicos import RegraViolada


class TestRecusa(unittest.TestCase):
    def setUp(self):
        self.banco = criar_banco()
        self.gab = self.banco.execute(
            "SELECT id FROM unidade WHERE nome LIKE "
            "'Gabinete do(a) Vereador(a) Chiquinho%'").fetchone()[0]
        self.outro_gab = self.banco.execute(
            "SELECT id FROM unidade WHERE nome LIKE "
            "'Gabinete do(a) Vereador(a) Alex%'").fetchone()[0]

    def tearDown(self):
        self.banco.close()

    def _protocolar_pl(self):
        rid = legislativo.criar_rascunho(
            self.banco, self.gab, "PL", "Semana do Livro",
            texto="Art. 1º ...", justificativa="Justifico.")
        legislativo.protocolar_rascunho(
            self.banco, rid, self.gab, "2026-07-01")
        return rid

    def _situacao(self, pid):
        return self.banco.execute(
            "SELECT situacao, (SELECT situacao FROM processo "
            "WHERE id = processo_id) FROM proposicao WHERE id = ?",
            (pid,)).fetchone()

    def _recusa(self, pid):
        return self.banco.execute(
            "SELECT situacao, decisao FROM recusa WHERE proposicao_id = ?",
            (pid,)).fetchone()

    # --- recusa -------------------------------------------------------

    def test_recusa_arquiva_e_registra(self):
        pid = self._protocolar_pl()
        rotulo = legislativo.recusar_proposicao(
            self.banco, pid, "Matéria estranha à ementa.", "2026-07-02")
        self.assertEqual(rotulo, "PL 1/2026")
        self.assertEqual(self._situacao(pid), ("RECUSADA", "ARQUIVADO"))
        self.assertEqual(self._recusa(pid), ("RECUSADA", None))

    def test_recusa_exige_fundamentacao(self):
        pid = self._protocolar_pl()
        with self.assertRaises(RegraViolada):
            legislativo.recusar_proposicao(self.banco, pid, "  ", "2026-07-02")

    def test_requerimento_nao_e_recusado(self):
        pid = self._protocolar_pl()
        req, _ = legislativo.requerimento_derivado(
            self.banco, self.gab, pid, "RETIRADA", "2026-07-02", "Retiro.")
        with self.assertRaises(RegraViolada):
            legislativo.recusar_proposicao(
                self.banco, req, "Motivo.", "2026-07-03")

    def test_nao_recusa_duas_vezes(self):
        pid = self._protocolar_pl()
        legislativo.recusar_proposicao(self.banco, pid, "M1.", "2026-07-02")
        with self.assertRaises(RegraViolada):
            legislativo.recusar_proposicao(
                self.banco, pid, "M2.", "2026-07-03")

    def test_recusada_sai_da_lista_de_recebimento(self):
        pid = self._protocolar_pl()
        self.assertIn(
            pid, [p["id"] for p in
                  legislativo.proposicoes_para_recebimento(self.banco)])
        legislativo.recusar_proposicao(self.banco, pid, "M.", "2026-07-02")
        self.assertNotIn(
            pid, [p["id"] for p in
                  legislativo.proposicoes_para_recebimento(self.banco)])

    def test_recusada_nao_entra_em_pauta(self):
        pid = self._protocolar_pl()
        legislativo.recusar_proposicao(self.banco, pid, "M.", "2026-07-02")
        sessao, _ = legislativo.convocar_sessao(
            self.banco, "ORDINARIA", "2026-07-10")
        with self.assertRaises(RegraViolada):
            legislativo.pautar(self.banco, sessao, pid, urgencia=True)

    # --- recurso ------------------------------------------------------

    def test_recurso_muda_para_em_recurso(self):
        pid = self._protocolar_pl()
        legislativo.recusar_proposicao(self.banco, pid, "M.", "2026-07-02")
        legislativo.recorrer_da_recusa(
            self.banco, pid, self.gab, "A ementa abrange.", "2026-07-03")
        self.assertEqual(self._situacao(pid)[0], "EM_RECURSO")
        self.assertEqual(self._recusa(pid)[0], "EM_RECURSO")
        self.assertIn(pid, [r["id"] for r in
                            legislativo.recursos_pendentes(self.banco)])

    def test_so_o_autor_recorre(self):
        pid = self._protocolar_pl()
        legislativo.recusar_proposicao(self.banco, pid, "M.", "2026-07-02")
        with self.assertRaises(RegraViolada):
            legislativo.recorrer_da_recusa(
                self.banco, pid, self.outro_gab, "Razões.", "2026-07-03")

    def test_recurso_exige_razoes(self):
        pid = self._protocolar_pl()
        legislativo.recusar_proposicao(self.banco, pid, "M.", "2026-07-02")
        with self.assertRaises(RegraViolada):
            legislativo.recorrer_da_recusa(
                self.banco, pid, self.gab, "  ", "2026-07-03")

    def test_recurso_so_de_recusa_pendente(self):
        pid = self._protocolar_pl()  # nem foi recusada
        with self.assertRaises(RegraViolada):
            legislativo.recorrer_da_recusa(
                self.banco, pid, self.gab, "Razões.", "2026-07-03")

    # --- decisão da CLJRF --------------------------------------------

    def test_recurso_provido_reverte_e_desarquiva(self):
        pid = self._protocolar_pl()
        legislativo.recusar_proposicao(self.banco, pid, "M.", "2026-07-02")
        legislativo.recorrer_da_recusa(
            self.banco, pid, self.gab, "Razões.", "2026-07-03")
        self.assertEqual(
            legislativo.decidir_recurso(
                self.banco, pid, True, "2026-07-04", "Procede."),
            "PROVIDO")
        self.assertEqual(self._situacao(pid), ("EM_TRAMITACAO",
                                               "EM_TRAMITACAO"))
        self.assertEqual(self._recusa(pid), ("REVERTIDA", "PROVIDO"))

    def test_recurso_negado_mantem_recusa(self):
        pid = self._protocolar_pl()
        legislativo.recusar_proposicao(self.banco, pid, "M.", "2026-07-02")
        legislativo.recorrer_da_recusa(
            self.banco, pid, self.gab, "Razões.", "2026-07-03")
        self.assertEqual(
            legislativo.decidir_recurso(
                self.banco, pid, False, "2026-07-04"),
            "NEGADO")
        self.assertEqual(self._situacao(pid), ("RECUSADA", "ARQUIVADO"))
        self.assertEqual(self._recusa(pid), ("MANTIDA", "NEGADO"))

    def test_decisao_so_de_recurso_pendente(self):
        pid = self._protocolar_pl()
        legislativo.recusar_proposicao(self.banco, pid, "M.", "2026-07-02")
        with self.assertRaises(RegraViolada):  # ainda não recorreu
            legislativo.decidir_recurso(self.banco, pid, True, "2026-07-04")

    # --- acompanhamento do autor -------------------------------------

    def test_acompanhamento_mostra_recusa_e_oferece_recurso(self):
        pid = self._protocolar_pl()
        legislativo.recusar_proposicao(
            self.banco, pid, "Estranha à ementa.", "2026-07-02")
        (item,) = [i for i in legislativo.acompanhamento_do_gabinete(
            self.banco, self.gab, "2026-07-20") if i["id"] == pid]
        self.assertTrue(item["recurso_disponivel"])
        self.assertEqual(item["recusa"]["situacao"], "RECUSADA")
        self.assertIn("RECUSADA", [a["tipo"] for a in item["alertas"]])
        # matéria recusada não oferece requerimento comum
        self.assertEqual(item["acoes_possiveis"], [])

    # --- alçadas na API ----------------------------------------------

    def test_api_gates(self):
        app = Aplicacao(":memory:")
        rid = legislativo.criar_rascunho(
            app.banco, self.gab, "PL", "X", texto="Art. 1º",
            justificativa="J.")
        # gab do Chiquinho é 50 no seed em memória
        gab = app.banco.execute(
            "SELECT id FROM unidade WHERE nome LIKE '%Chiquinho%'"
        ).fetchone()[0]
        rid = legislativo.criar_rascunho(
            app.banco, gab, "PL", "X", texto="Art. 1º", justificativa="J.")
        legislativo.protocolar_rascunho(app.banco, rid, gab, "2026-07-01")
        app.banco.commit()

        gabinete = {"login": "gab", "perfil": "LEGISLATIVO",
                    "unidade_id": gab}
        presidencia = app.banco.execute(
            "SELECT id FROM unidade WHERE nome = 'Presidência'").fetchone()[0]
        comissoes = app.banco.execute(
            "SELECT id FROM unidade WHERE nome = "
            "'Comissões Permanentes'").fetchone()[0]

        # gabinete não recusa (só Presidência despacha)
        app.usuario_atual = gabinete
        with self.assertRaises(AcessoNegado):
            app.recusar_proposicao(rid, {"motivo": "M."})

        # Presidência recusa
        app.usuario_atual = {"login": "pres", "perfil": "LEGISLATIVO",
                             "unidade_id": presidencia}
        app.recusar_proposicao(rid, {"motivo": "Estranha à ementa."})

        # autor recorre
        app.usuario_atual = gabinete
        app.recorrer_da_recusa(rid, {"razoes": "Abrange sim."})

        # gabinete não decide recurso (é da CLJRF/comissões)
        with self.assertRaises(AcessoNegado):
            app.decidir_recurso(rid, {"provido": True})

        # comissões decide
        app.usuario_atual = {"login": "com", "perfil": "LEGISLATIVO",
                             "unidade_id": comissoes}
        resposta = app.decidir_recurso(rid, {"provido": True})
        self.assertEqual(resposta["resultado"], "PROVIDO")


if __name__ == "__main__":
    unittest.main()
