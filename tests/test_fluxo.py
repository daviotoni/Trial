"""Testes do módulo de fluxo processual (competências, tipos e ritos)."""

import unittest

from sistema import fluxo, servicos
from sistema.demo import criar_banco
from sistema.servicos import RegraViolada


class TestFluxo(unittest.TestCase):
    def setUp(self):
        self.banco = criar_banco()

    def tearDown(self):
        self.banco.close()

    def _uid(self, nome):
        return self.banco.execute(
            "SELECT id FROM unidade WHERE nome = ?", (nome,)).fetchone()[0]

    # --- competências ------------------------------------------------

    def test_competencias_persistidas_do_cmdc(self):
        # A Presidência tem competências da Lei 3.525 no banco.
        presidencia = self._uid("Presidência")
        comps = fluxo.competencias_da_unidade(self.banco, presidencia)
        self.assertTrue(comps)
        self.assertTrue(fluxo.unidade_tem_competencia(self.banco, presidencia))

    # --- ritos semeados ---------------------------------------------

    def test_ritos_semeados(self):
        etapas_pl = fluxo.etapas(self.banco, "PL")
        self.assertEqual(etapas_pl[0]["unidade"], "Gabinetes de Vereadores")
        self.assertEqual(etapas_pl[-1]["unidade"], "Presidência")
        etapas_compra = fluxo.etapas(self.banco, "COMPRA")
        self.assertEqual(etapas_compra[-1]["unidade"],
                         "Coordenadoria de Publicações e Transparência")

    def test_definir_tipo_e_adicionar_etapa(self):
        fluxo.definir_tipo(self.banco, "OFICIO", "Ofício", "ADMINISTRATIVO")
        fluxo.adicionar_etapa(
            self.banco, "OFICIO", self._uid("Coordenadoria da Secretaria-Geral"),
            "Protocolo", prazo_dias=2)
        fluxo.adicionar_etapa(
            self.banco, "OFICIO", self._uid("Presidência"), "Assinatura")
        etapas = fluxo.etapas(self.banco, "OFICIO")
        self.assertEqual([e["ordem"] for e in etapas], [1, 2])

    def test_tipo_inexistente(self):
        with self.assertRaises(RegraViolada):
            fluxo.etapas(self.banco, "INEXISTENTE")

    # --- navegação do rito ------------------------------------------

    def test_proxima_etapa_do_inicio(self):
        origem = self._uid("Gabinetes de Vereadores")
        pid, _ = servicos.autuar_processo(
            self.banco, "LEGISLATIVO", "PL teste", origem, "2025-09-10")
        fluxo.vincular_tipo(self.banco, pid, "PL")
        prox = fluxo.proxima_etapa(self.banco, pid)
        # Está no gabinete (etapa 1); a próxima é o protocolo (etapa 2).
        self.assertEqual(prox["unidade"], "Coordenadoria da Secretaria-Geral")

    def test_processo_sem_rito_nao_tem_proxima(self):
        origem = self._uid("Diretoria-Geral")
        pid, _ = servicos.autuar_processo(
            self.banco, "ADMINISTRATIVO", "Sem rito", origem, "2025-09-10")
        self.assertIsNone(fluxo.proxima_etapa(self.banco, pid))

    def test_tramitar_pelo_fluxo_encaminha_e_calcula_prazo(self):
        origem = self._uid("Coordenadoria da Secretaria-Geral")
        pid, _ = servicos.autuar_processo(
            self.banco, "ADMINISTRATIVO", "Compra teste", origem, "2025-09-10")
        fluxo.vincular_tipo(self.banco, pid, "COMPRA")
        etapa = fluxo.tramitar_pelo_fluxo(self.banco, pid, "2025-09-10")
        # Etapa 1 é o próprio protocolo; a partir dele, segue para a Diretoria.
        self.assertEqual(etapa["unidade"], "Diretoria-Geral")
        (prazo,) = self.banco.execute(
            "SELECT prazo FROM tramitacao WHERE id = ?",
            (etapa["tramitacao_id"],)).fetchone()
        self.assertEqual(prazo, "2025-09-13")  # +3 dias

    def test_rito_completo_ate_o_fim(self):
        origem = self._uid("Gabinetes de Vereadores")
        pid, _ = servicos.autuar_processo(
            self.banco, "LEGISLATIVO", "PL completo", origem, "2025-09-10")
        fluxo.vincular_tipo(self.banco, pid, "PL")
        passos = 0
        while fluxo.proxima_etapa(self.banco, pid) is not None:
            etapa = fluxo.tramitar_pelo_fluxo(self.banco, pid, "2025-09-11")
            servicos.receber_tramitacao(
                self.banco, etapa["tramitacao_id"], "2025-09-11")
            passos += 1
            self.assertLess(passos, 20, "rito não deveria ser infinito")
        # 7 etapas no rito PL; parte da etapa 1, então 6 encaminhamentos.
        self.assertEqual(passos, 6)


if __name__ == "__main__":
    unittest.main()
