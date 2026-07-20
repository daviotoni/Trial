"""Testes do Bloco 4 do módulo do gabinete: acompanhamento rico,
requerimentos derivados (arts. 107-113) e despacho do Presidente
(arts. 108-110 do Regimento Interno)."""

import unittest

from sistema import comissoes, legislativo, servicos
from sistema.demo import criar_banco
from sistema.servicos import RegraViolada


class TestBloco4(unittest.TestCase):
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

    # ------------------------------------------------------------------
    # utilitários
    # ------------------------------------------------------------------

    def _protocolar_pl(self, ementa="Semana do Livro"):
        rid = legislativo.criar_rascunho(
            self.banco, self.gab, "PL", ementa,
            texto="Art. 1º ...", justificativa="Justifico.")
        legislativo.protocolar_rascunho(
            self.banco, rid, self.gab, "2026-07-01")
        return rid

    def _situacao(self, proposicao_id):
        return self.banco.execute(
            "SELECT situacao, (SELECT situacao FROM processo "
            "WHERE id = processo_id) FROM proposicao WHERE id = ?",
            (proposicao_id,)).fetchone()

    def _parecer_aprovado(self, proposicao_id):
        parecer = comissoes.emitir_parecer(
            self.banco, proposicao_id,
            "Comissão de Educação e Cultura", "FAVORAVEL",
            "Favorável.", "2026-07-02")
        comissoes.aprovar_parecer(self.banco, parecer)

    def _aprovar_em_plenario(self, proposicao_id, data="2026-07-10"):
        sessao, _ = legislativo.convocar_sessao(
            self.banco, "ORDINARIA", data)
        legislativo.pautar(self.banco, sessao, proposicao_id)
        votos = {p: "SIM" for (p,) in self.banco.execute(
            "SELECT parlamentar_id FROM mandato")}
        return legislativo.votar(
            self.banco, sessao, proposicao_id, "NOMINAL", votos)

    # ------------------------------------------------------------------
    # requerimentos derivados: espécie e validações
    # ------------------------------------------------------------------

    def test_retirada_sem_parecer_vai_a_despacho_do_presidente(self):
        alvo = self._protocolar_pl()
        rid, rotulo = legislativo.requerimento_derivado(
            self.banco, self.gab, alvo, "RETIRADA", "2026-07-03",
            "Reavaliação da matéria.")
        subtipo, finalidade = self.banco.execute(
            "SELECT subtipo, finalidade FROM proposicao WHERE id = ?",
            (rid,)).fetchone()
        self.assertEqual(subtipo, "DESPACHO_PRESIDENTE")  # art. 110, I
        self.assertEqual(finalidade, "RETIRADA")
        self.assertTrue(rotulo.startswith("REQUERIMENTO "))

    def test_retirada_com_parecer_vai_a_plenario(self):
        alvo = self._protocolar_pl()
        self._parecer_aprovado(alvo)
        rid, _ = legislativo.requerimento_derivado(
            self.banco, self.gab, alvo, "RETIRADA", "2026-07-03",
            "Reavaliação.")
        (subtipo,) = self.banco.execute(
            "SELECT subtipo FROM proposicao WHERE id = ?", (rid,)).fetchone()
        self.assertEqual(subtipo, "DELIBERACAO_PLENARIO")  # art. 111

    def test_so_o_autor_requer_sobre_a_propria_proposicao(self):
        alvo = self._protocolar_pl()
        with self.assertRaises(RegraViolada):
            legislativo.requerimento_derivado(
                self.banco, self.outro_gab, alvo, "RETIRADA",
                "2026-07-03", "Tentativa alheia.")

    def test_justificativa_obrigatoria(self):
        alvo = self._protocolar_pl()
        with self.assertRaises(RegraViolada):
            legislativo.requerimento_derivado(
                self.banco, self.gab, alvo, "RETIRADA", "2026-07-03", "  ")

    def test_duplicado_pendente_bloqueado(self):
        alvo = self._protocolar_pl()
        legislativo.requerimento_derivado(
            self.banco, self.gab, alvo, "RETIRADA", "2026-07-03", "Já pedi.")
        with self.assertRaises(RegraViolada):
            legislativo.requerimento_derivado(
                self.banco, self.gab, alvo, "RETIRADA", "2026-07-04",
                "De novo.")

    def test_desarquivamento_exige_processo_arquivado(self):
        alvo = self._protocolar_pl()
        with self.assertRaises(RegraViolada):
            legislativo.requerimento_derivado(
                self.banco, self.gab, alvo, "DESARQUIVAMENTO",
                "2026-07-03", "Ainda tramita.")

    def test_inclusao_em_pauta_exige_parecer_aprovado_para_merito(self):
        alvo = self._protocolar_pl()
        with self.assertRaises(RegraViolada):
            legislativo.requerimento_derivado(
                self.banco, self.gab, alvo, "INCLUSAO_PAUTA",
                "2026-07-03", "Quero pautar.")
        self._parecer_aprovado(alvo)
        rid, _ = legislativo.requerimento_derivado(
            self.banco, self.gab, alvo, "INCLUSAO_PAUTA",
            "2026-07-03", "Quero pautar.")
        (subtipo,) = self.banco.execute(
            "SELECT subtipo FROM proposicao WHERE id = ?", (rid,)).fetchone()
        self.assertEqual(subtipo, "DELIBERACAO_PLENARIO")

    # ------------------------------------------------------------------
    # despacho do Presidente (arts. 108-110)
    # ------------------------------------------------------------------

    def test_deferimento_retira_e_arquiva_a_materia_alvo(self):
        alvo = self._protocolar_pl()
        rid, _ = legislativo.requerimento_derivado(
            self.banco, self.gab, alvo, "RETIRADA", "2026-07-03", "Retiro.")
        legislativo.despachar_requerimento(
            self.banco, rid, "DEFERIDO", "2026-07-04", "Defiro.")
        self.assertEqual(self._situacao(alvo), ("RETIRADA", "ARQUIVADO"))
        situacao, despacho, data = self.banco.execute(
            "SELECT situacao, despacho, despacho_data FROM proposicao "
            "WHERE id = ?", (rid,)).fetchone()
        self.assertEqual((situacao, despacho, data),
                         ("DEFERIDO", "Defiro.", "2026-07-04"))
        # o processo do próprio requerimento é concluído
        (proc,) = self.banco.execute(
            "SELECT (SELECT situacao FROM processo WHERE id = processo_id) "
            "FROM proposicao WHERE id = ?", (rid,)).fetchone()
        self.assertEqual(proc, "CONCLUIDO")

    def test_indeferimento_nao_aplica_efeito(self):
        alvo = self._protocolar_pl()
        rid, _ = legislativo.requerimento_derivado(
            self.banco, self.gab, alvo, "RETIRADA", "2026-07-03", "Retiro.")
        legislativo.despachar_requerimento(
            self.banco, rid, "INDEFERIDO", "2026-07-04")
        self.assertEqual(self._situacao(alvo),
                         ("EM_TRAMITACAO", "EM_TRAMITACAO"))

    def test_despacho_so_para_especie_propria(self):
        alvo = self._protocolar_pl()
        self._parecer_aprovado(alvo)  # com parecer → deliberação
        rid, _ = legislativo.requerimento_derivado(
            self.banco, self.gab, alvo, "RETIRADA", "2026-07-03", "Retiro.")
        with self.assertRaises(RegraViolada):
            legislativo.despachar_requerimento(
                self.banco, rid, "DEFERIDO", "2026-07-04")

    def test_despacho_nao_repete(self):
        alvo = self._protocolar_pl()
        rid, _ = legislativo.requerimento_derivado(
            self.banco, self.gab, alvo, "RETIRADA", "2026-07-03", "Retiro.")
        legislativo.despachar_requerimento(
            self.banco, rid, "INDEFERIDO", "2026-07-04")
        with self.assertRaises(RegraViolada):
            legislativo.despachar_requerimento(
                self.banco, rid, "DEFERIDO", "2026-07-05")

    def test_despachos_pendentes_lista_e_esvazia(self):
        alvo = self._protocolar_pl()
        rid, rotulo = legislativo.requerimento_derivado(
            self.banco, self.gab, alvo, "RETIRADA", "2026-07-03", "Retiro.")
        pendentes = legislativo.despachos_pendentes(self.banco)
        self.assertEqual([p["rotulo"] for p in pendentes], [rotulo])
        self.assertEqual(pendentes[0]["autor"], "Chiquinho Caipira")
        legislativo.despachar_requerimento(
            self.banco, rid, "DEFERIDO", "2026-07-04")
        self.assertEqual(legislativo.despachos_pendentes(self.banco), [])

    # ------------------------------------------------------------------
    # deliberação do Plenário aplica o efeito (arts. 111-113)
    # ------------------------------------------------------------------

    def test_desarquivamento_aprovado_em_plenario_desarquiva(self):
        alvo = self._protocolar_pl()
        (processo_alvo,) = self.banco.execute(
            "SELECT processo_id FROM proposicao WHERE id = ?",
            (alvo,)).fetchone()
        servicos.arquivar_processo(self.banco, processo_alvo)

        rid, _ = legislativo.requerimento_derivado(
            self.banco, self.gab, alvo, "DESARQUIVAMENTO", "2026-07-05",
            "Retomar a matéria.")
        self.assertEqual(
            self._aprovar_em_plenario(rid), "APROVADA")
        self.assertEqual(self._situacao(alvo),
                         ("EM_TRAMITACAO", "EM_TRAMITACAO"))

    def test_requerimento_rejeitado_nao_aplica_efeito(self):
        alvo = self._protocolar_pl()
        (processo_alvo,) = self.banco.execute(
            "SELECT processo_id FROM proposicao WHERE id = ?",
            (alvo,)).fetchone()
        servicos.arquivar_processo(self.banco, processo_alvo)
        rid, _ = legislativo.requerimento_derivado(
            self.banco, self.gab, alvo, "DESARQUIVAMENTO", "2026-07-05",
            "Retomar.")
        sessao, _ = legislativo.convocar_sessao(
            self.banco, "ORDINARIA", "2026-07-10")
        legislativo.pautar(self.banco, sessao, rid)
        votos = {p: "NAO" for (p,) in self.banco.execute(
            "SELECT parlamentar_id FROM mandato")}
        legislativo.votar(self.banco, sessao, rid, "NOMINAL", votos)
        self.assertEqual(self._situacao(alvo)[1], "ARQUIVADO")

    # ------------------------------------------------------------------
    # acompanhamento rico e alertas (arts. 90 e 93-95)
    # ------------------------------------------------------------------

    def test_acompanhamento_alerta_arquivada_e_sugere_desarquivamento(self):
        alvo = self._protocolar_pl()
        (processo_alvo,) = self.banco.execute(
            "SELECT processo_id FROM proposicao WHERE id = ?",
            (alvo,)).fetchone()
        servicos.arquivar_processo(self.banco, processo_alvo)
        (item,) = legislativo.acompanhamento_do_gabinete(
            self.banco, self.gab, "2026-07-20")
        self.assertIn("ARQUIVADA", [a["tipo"] for a in item["alertas"]])
        self.assertEqual(item["acoes_possiveis"], ["DESARQUIVAMENTO"])

    def test_acompanhamento_alerta_prazo_vencido(self):
        alvo = self._protocolar_pl()
        (processo_alvo,) = self.banco.execute(
            "SELECT processo_id FROM proposicao WHERE id = ?",
            (alvo,)).fetchone()
        (destino,) = self.banco.execute(
            "SELECT id FROM unidade WHERE nome = "
            "'Coordenadoria da Secretaria-Geral'").fetchone()
        servicos.tramitar(self.banco, processo_alvo, destino,
                          "Ao protocolo.", "2026-07-02", prazo="2026-07-04")
        (item,) = legislativo.acompanhamento_do_gabinete(
            self.banco, self.gab, "2026-07-20")
        self.assertIn("PRAZO_VENCIDO", [a["tipo"] for a in item["alertas"]])
        self.assertEqual(item["localizacao"],
                         "Coordenadoria da Secretaria-Geral")

    def test_acompanhamento_alerta_parecer_contrario(self):
        alvo = self._protocolar_pl()
        parecer = comissoes.emitir_parecer(
            self.banco, alvo, "Comissão de Legislação, Justiça e Redação "
            "Final", "CONTRARIO", "Inconstitucional.", "2026-07-05")
        comissoes.aprovar_parecer(self.banco, parecer)
        (item,) = legislativo.acompanhamento_do_gabinete(
            self.banco, self.gab, "2026-07-20")
        self.assertIn("PARECER_CONTRARIO",
                      [a["tipo"] for a in item["alertas"]])

    def test_acompanhamento_acoes_por_estado(self):
        alvo = self._protocolar_pl()
        (item,) = legislativo.acompanhamento_do_gabinete(
            self.banco, self.gab, "2026-07-20")
        # PL sem parecer aprovado: pode retirar, não pode pedir pauta
        self.assertEqual(item["acoes_possiveis"], ["RETIRADA"])
        self._parecer_aprovado(alvo)
        (item,) = legislativo.acompanhamento_do_gabinete(
            self.banco, self.gab, "2026-07-20")
        self.assertEqual(item["acoes_possiveis"],
                         ["RETIRADA", "INCLUSAO_PAUTA"])

    def test_acompanhamento_mostra_requerimento_pendente_e_derivado(self):
        alvo = self._protocolar_pl()
        _, rotulo = legislativo.requerimento_derivado(
            self.banco, self.gab, alvo, "RETIRADA", "2026-07-03", "Retiro.")
        itens = legislativo.acompanhamento_do_gabinete(
            self.banco, self.gab, "2026-07-20")
        por_rotulo = {i["rotulo"]: i for i in itens}
        derivado = por_rotulo[rotulo]
        self.assertEqual(derivado["finalidade"], "RETIRADA")
        self.assertEqual(derivado["alvo"], por_rotulo_alvo(por_rotulo))
        self.assertEqual(derivado["acoes_possiveis"], [])
        alvo_item = [i for i in itens if i["id"] == alvo][0]
        self.assertEqual(alvo_item["requerimentos_pendentes"],
                         [f"{rotulo} (RETIRADA)"])


def por_rotulo_alvo(por_rotulo):
    """Rótulo do PL alvo presente no dicionário de acompanhamento."""
    return next(r for r in por_rotulo if r.startswith("PL "))


if __name__ == "__main__":
    unittest.main()
