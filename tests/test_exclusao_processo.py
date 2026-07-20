"""Testes da exclusão de processos (ato privativo do administrador)."""

import unittest

from sistema import comissoes, legislativo, servicos
from sistema.api import Aplicacao
from sistema.autenticacao import AcessoNegado
from sistema.demo import criar_banco
from sistema.servicos import RegraViolada


class TestExclusaoProcesso(unittest.TestCase):
    def setUp(self):
        self.banco = criar_banco()
        self.gab = self.banco.execute(
            "SELECT id FROM unidade WHERE nome LIKE "
            "'Gabinete do(a) Vereador(a) Chiquinho%'").fetchone()[0]

    def tearDown(self):
        self.banco.close()

    def _protocolar_pl(self):
        rid = legislativo.criar_rascunho(
            self.banco, self.gab, "PL", "Semana do Livro",
            texto="Art. 1º ...", justificativa="Justifico.")
        legislativo.protocolar_rascunho(
            self.banco, rid, self.gab, "2026-07-01")
        (processo,) = self.banco.execute(
            "SELECT processo_id FROM proposicao WHERE id = ?",
            (rid,)).fetchone()
        return rid, processo

    def _contar(self, tabela, campo, valor):
        return self.banco.execute(
            f"SELECT COUNT(*) FROM {tabela} WHERE {campo} = ?",
            (valor,)).fetchone()[0]

    def test_exclui_processo_simples_com_trilha_de_auditoria(self):
        pid, rotulo = servicos.autuar_processo(
            self.banco, "ADMINISTRATIVO", "Autuação de teste", 40,
            "2026-07-01")
        servicos.tramitar(self.banco, pid, 17, "Segue.", "2026-07-02")
        resumo = servicos.excluir_processo(
            self.banco, pid, "admin", "2026-07-20T10:00:00")
        self.assertEqual(resumo["numero"], rotulo)
        self.assertEqual(self._contar("processo", "id", pid), 0)
        self.assertEqual(self._contar("tramitacao", "processo_id", pid), 0)
        (detalhes,) = self.banco.execute(
            "SELECT detalhes FROM auditoria WHERE tabela = 'processo' AND "
            "registro_id = ? AND operacao = 'DELETE'", (pid,)).fetchone()
        self.assertIn("Autuação de teste", detalhes)

    def test_exclui_proposicao_vinculada_com_pauta_votos_e_pareceres(self):
        rid, processo = self._protocolar_pl()
        parecer = comissoes.emitir_parecer(
            self.banco, rid, "Comissão de Educação e Cultura", "FAVORAVEL",
            "Favorável.", "2026-07-02")
        comissoes.aprovar_parecer(self.banco, parecer)
        sessao, _ = legislativo.convocar_sessao(
            self.banco, "ORDINARIA", "2026-07-10")
        legislativo.pautar(self.banco, sessao, rid)
        votos = {p: "SIM" for (p,) in self.banco.execute(
            "SELECT parlamentar_id FROM mandato")}
        legislativo.votar(self.banco, sessao, rid, "NOMINAL", votos)

        resumo = servicos.excluir_processo(
            self.banco, processo, "admin", "2026-07-20T10:00:00")
        self.assertEqual(resumo["proposicoes_excluidas"], 1)
        self.assertEqual(self._contar("proposicao", "id", rid), 0)
        for tabela in ("pauta_item", "votacao", "parecer"):
            self.assertEqual(self._contar(tabela, "proposicao_id", rid), 0)
        (votos_orfaos,) = self.banco.execute(
            "SELECT COUNT(*) FROM voto v LEFT JOIN votacao vt "
            "ON vt.id = v.votacao_id WHERE vt.id IS NULL").fetchone()
        self.assertEqual(votos_orfaos, 0)

    def test_requerimento_derivado_perde_so_o_vinculo(self):
        rid, processo = self._protocolar_pl()
        req, _ = legislativo.requerimento_derivado(
            self.banco, self.gab, rid, "RETIRADA", "2026-07-03", "Retiro.")
        servicos.excluir_processo(
            self.banco, processo, "admin", "2026-07-20T10:00:00")
        alvo, situacao = self.banco.execute(
            "SELECT proposicao_alvo_id, situacao FROM proposicao "
            "WHERE id = ?", (req,)).fetchone()
        self.assertIsNone(alvo)               # vínculo removido
        self.assertEqual(situacao, "EM_TRAMITACAO")  # requerimento vive

    def test_processo_de_contratacao_nao_e_excluido(self):
        pid, _ = servicos.autuar_processo(
            self.banco, "ADMINISTRATIVO", "Compra de material", 40,
            "2026-07-01")
        self.banco.execute(
            "INSERT INTO contratacao (modalidade, numero, ano, objeto, "
            "processo_id) VALUES ('PREGAO', 1, 2026, 'Material', ?)", (pid,))
        with self.assertRaises(RegraViolada):
            servicos.excluir_processo(
                self.banco, pid, "admin", "2026-07-20T10:00:00")

    def test_processo_inexistente(self):
        with self.assertRaises(RegraViolada):
            servicos.excluir_processo(
                self.banco, 99999, "admin", "2026-07-20T10:00:00")

    # --- alçada na API: privativo do ADMIN ---------------------------

    def test_api_exige_admin(self):
        app = Aplicacao(":memory:")
        pid, _ = servicos.autuar_processo(
            app.banco, "ADMINISTRATIVO", "Teste", 40, "2026-07-01")
        app.banco.commit()
        app.usuario_atual = {"login": "protocolo", "perfil": "PROTOCOLO",
                             "unidade_id": 40}
        with self.assertRaises(AcessoNegado):
            app.excluir_processo(pid)
        app.usuario_atual = {"login": "admin", "perfil": "ADMIN"}
        resposta = app.excluir_processo(pid)
        self.assertTrue(resposta["excluido"])


if __name__ == "__main__":
    unittest.main()
