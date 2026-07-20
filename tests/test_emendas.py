"""Testes do Bloco 3: emendas a matéria alheia (arts. 114-115)."""

import unittest

from sistema import legislativo, servicos
from sistema.demo import criar_banco
from sistema.servicos import RegraViolada


class TestEmendas(unittest.TestCase):
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

    def _protocolar_pl(self, tipo="PL"):
        rid = legislativo.criar_rascunho(
            self.banco, self.gab, tipo, "Semana do Livro",
            texto="Art. 1º ...", justificativa="Justifico.")
        legislativo.protocolar_rascunho(
            self.banco, rid, self.gab, "2026-07-01")
        return rid

    def _emendar(self, alvo, gab=None, especie="SUPRESSIVA"):
        return legislativo.apresentar_emenda(
            self.banco, gab or self.outro_gab, alvo, especie,
            "Suprima-se o art. 2º.", "Pertinente porque...", "2026-07-05")

    # --- apresentação -------------------------------------------------

    def test_emenda_de_outro_gabinete_numera_e_vincula(self):
        alvo = self._protocolar_pl()
        eid, rotulo = self._emendar(alvo)
        self.assertEqual(rotulo, "EMENDA 1/2026 ao PL 1/2026")
        (subtipo, alvo_id, autor, processo) = self.banco.execute(
            "SELECT subtipo, proposicao_alvo_id, autor_parlamentar_id, "
            "processo_id FROM proposicao WHERE id = ?", (eid,)).fetchone()
        self.assertEqual(subtipo, "SUPRESSIVA")
        self.assertEqual(alvo_id, alvo)
        self.assertEqual(autor, legislativo.parlamentar_do_gabinete(
            self.banco, self.outro_gab))
        self.assertIsNone(processo)  # acessória: junta-se à principal

    def test_numeracao_sequencial_por_ano(self):
        alvo = self._protocolar_pl()
        self._emendar(alvo)
        _, rotulo = self._emendar(alvo, gab=self.gab, especie="ADITIVA")
        self.assertTrue(rotulo.startswith("EMENDA 2/2026"))

    def test_validacoes_regimentais(self):
        alvo = self._protocolar_pl()
        casos = [
            dict(especie="INEXISTENTE"),           # espécie inválida
            dict(texto="  "),                       # texto obrigatório
            dict(justificativa=""),                 # justificativa obrigatória
        ]
        for extra in casos:
            with self.assertRaises(RegraViolada):
                legislativo.apresentar_emenda(
                    self.banco, self.outro_gab, alvo,
                    extra.get("especie", "SUPRESSIVA"),
                    extra.get("texto", "Texto."),
                    extra.get("justificativa", "Justo."), "2026-07-05")

    def test_so_projetos_recebem_emenda(self):
        rid = legislativo.criar_rascunho(
            self.banco, self.gab, "MOCAO", "Moção de aplauso",
            subtipo="APLAUSO", justificativa="Justifico.")
        legislativo.protocolar_rascunho(
            self.banco, rid, self.gab, "2026-07-01")
        with self.assertRaises(RegraViolada):
            self._emendar(rid)

    def test_rascunho_e_materia_arquivada_nao_recebem_emenda(self):
        rascunho = legislativo.criar_rascunho(
            self.banco, self.gab, "PL", "Ainda rascunho")
        with self.assertRaises(RegraViolada):
            self._emendar(rascunho)
        alvo = self._protocolar_pl()
        (processo,) = self.banco.execute(
            "SELECT processo_id FROM proposicao WHERE id = ?",
            (alvo,)).fetchone()
        servicos.arquivar_processo(self.banco, processo)
        with self.assertRaises(RegraViolada):
            self._emendar(alvo)

    # --- consulta e acompanhamento -----------------------------------

    def test_emendas_da_proposicao(self):
        alvo = self._protocolar_pl()
        self._emendar(alvo)
        (emenda,) = legislativo.emendas_da_proposicao(self.banco, alvo)
        self.assertEqual(emenda["especie"], "SUPRESSIVA")
        self.assertEqual(emenda["autor"], "Alex Freitas")
        self.assertEqual(emenda["situacao"], "EM_TRAMITACAO")

    def test_autor_da_materia_ve_emendas_recebidas(self):
        alvo = self._protocolar_pl()
        self._emendar(alvo)
        (item,) = legislativo.acompanhamento_do_gabinete(
            self.banco, self.gab, "2026-07-20")
        self.assertEqual(len(item["emendas"]), 1)
        self.assertEqual(item["emendas"][0]["autor"], "Alex Freitas")
        # emendas não contaminam a lista de requerimentos pendentes
        self.assertEqual(item["requerimentos_pendentes"], [])

    def test_autor_da_emenda_acompanha_e_so_pode_retirar(self):
        alvo = self._protocolar_pl()
        eid, _ = self._emendar(alvo)
        (item,) = legislativo.acompanhamento_do_gabinete(
            self.banco, self.outro_gab, "2026-07-20")
        self.assertEqual(item["id"], eid)
        self.assertEqual(item["alvo"], "PL 1/2026")
        self.assertEqual(item["acoes_possiveis"], ["RETIRADA"])

    def test_retirada_de_emenda_via_requerimento_derivado(self):
        alvo = self._protocolar_pl()
        eid, _ = self._emendar(alvo)
        rid, _ = legislativo.requerimento_derivado(
            self.banco, self.outro_gab, eid, "RETIRADA", "2026-07-06",
            "Retiro a emenda.")
        legislativo.despachar_requerimento(
            self.banco, rid, "DEFERIDO", "2026-07-07")
        (situacao,) = self.banco.execute(
            "SELECT situacao FROM proposicao WHERE id = ?", (eid,)).fetchone()
        self.assertEqual(situacao, "RETIRADA")

    def test_emenda_pautavel_e_votavel_com_a_materia(self):
        alvo = self._protocolar_pl()
        eid, _ = self._emendar(alvo)
        sessao, _ = legislativo.convocar_sessao(
            self.banco, "ORDINARIA", "2026-07-10")
        legislativo.pautar(self.banco, sessao, eid)  # dispensa parecer
        votos = {p: "SIM" for (p,) in self.banco.execute(
            "SELECT parlamentar_id FROM mandato")}
        self.assertEqual(
            legislativo.votar(self.banco, sessao, eid, "NOMINAL", votos),
            "APROVADA")

    def test_lista_publica_marca_emendaveis(self):
        alvo = self._protocolar_pl()
        rid = legislativo.criar_rascunho(
            self.banco, self.gab, "INDICACAO", "Pavimentação",
            subtipo="SIMPLES", justificativa="Justifico.")
        legislativo.protocolar_rascunho(
            self.banco, rid, self.gab, "2026-07-01")
        self._emendar(alvo)
        lista = legislativo.proposicoes_protocoladas(self.banco)
        por_rotulo = {p["rotulo"]: p for p in lista}
        self.assertTrue(por_rotulo["PL 1/2026"]["emendavel"])
        self.assertFalse(por_rotulo["INDICACAO 1/2026"]["emendavel"])
        # emendas não aparecem na lista de matérias
        self.assertFalse(any(p["tipo"] == "EMENDA" for p in lista))


if __name__ == "__main__":
    unittest.main()
