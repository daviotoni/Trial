"""Testes do módulo legislativo (proposições, sessões, votações)."""

import unittest

from sistema import legislativo
from sistema.demo import criar_banco
from sistema.servicos import RegraViolada


class TestLegislativo(unittest.TestCase):
    def setUp(self):
        self.banco = criar_banco()
        self.legislatura = legislativo.criar_legislatura(
            self.banco, 1, "2025-01-01", "2028-12-31")
        self.vereadores = [
            legislativo.empossar(self.banco, f"Vereador {i}", "PXX",
                                 self.legislatura)
            for i in range(1, 6)
        ]

    def tearDown(self):
        self.banco.close()

    def _proposicao_pautada(self):
        proposicao, _ = legislativo.apresentar_proposicao(
            self.banco, "PL", "Ementa teste", "2025-09-10",
            autor_parlamentar_id=self.vereadores[0])
        sessao, _ = legislativo.convocar_sessao(self.banco, "ORDINARIA",
                                                "2025-09-16")
        legislativo.pautar(self.banco, sessao, proposicao)
        return sessao, proposicao

    def test_numeracao_por_tipo_e_ano(self):
        _, r1 = legislativo.apresentar_proposicao(
            self.banco, "PL", "A", "2025-02-01")
        _, r2 = legislativo.apresentar_proposicao(
            self.banco, "PL", "B", "2025-03-01")
        _, r3 = legislativo.apresentar_proposicao(
            self.banco, "PDL", "C", "2025-03-01")
        _, r4 = legislativo.apresentar_proposicao(
            self.banco, "PL", "D", "2026-01-01")
        self.assertEqual((r1, r2, r3, r4),
                         ("PL 1/2025", "PL 2/2025", "PDL 1/2025", "PL 1/2026"))

    def test_proposicao_com_protocolo_autua_processo(self):
        (unidade,) = self.banco.execute(
            "SELECT id FROM unidade WHERE nome = "
            "'Coordenadoria da Secretaria-Geral'").fetchone()
        proposicao, _ = legislativo.apresentar_proposicao(
            self.banco, "PL", "Com processo", "2025-09-10",
            unidade_protocolo_id=unidade)
        (processo_id,) = self.banco.execute(
            "SELECT processo_id FROM proposicao WHERE id = ?",
            (proposicao,)).fetchone()
        self.assertIsNotNone(processo_id)
        (tipo,) = self.banco.execute(
            "SELECT tipo FROM processo WHERE id = ?", (processo_id,)).fetchone()
        self.assertEqual(tipo, "LEGISLATIVO")

    def test_votacao_nominal_aprova_por_maioria(self):
        sessao, proposicao = self._proposicao_pautada()
        votos = dict.fromkeys(self.vereadores[:3], "SIM")
        votos.update(dict.fromkeys(self.vereadores[3:], "NAO"))
        resultado = legislativo.votar(self.banco, sessao, proposicao,
                                      "NOMINAL", votos)
        self.assertEqual(resultado, "APROVADA")
        apuracao = legislativo.placar(self.banco, sessao, proposicao)
        self.assertEqual(apuracao["contagem"], {"SIM": 3, "NAO": 2,
                                                "ABSTENCAO": 0})
        (situacao,) = self.banco.execute(
            "SELECT situacao FROM proposicao WHERE id = ?",
            (proposicao,)).fetchone()
        self.assertEqual(situacao, "APROVADA")

    def test_empate_rejeita(self):
        sessao, proposicao = self._proposicao_pautada()
        votos = {self.vereadores[0]: "SIM", self.vereadores[1]: "NAO",
                 self.vereadores[2]: "ABSTENCAO"}
        self.assertEqual(
            legislativo.votar(self.banco, sessao, proposicao, "NOMINAL", votos),
            "REJEITADA")

    def test_nao_vota_fora_da_pauta(self):
        proposicao, _ = legislativo.apresentar_proposicao(
            self.banco, "PL", "Fora da pauta", "2025-09-10")
        sessao, _ = legislativo.convocar_sessao(self.banco, "ORDINARIA",
                                                "2025-09-16")
        with self.assertRaises(RegraViolada):
            legislativo.votar(self.banco, sessao, proposicao, "SIMBOLICA",
                              resultado_simbolico="APROVADA")

    def test_nao_vota_duas_vezes(self):
        sessao, proposicao = self._proposicao_pautada()
        legislativo.votar(self.banco, sessao, proposicao, "SIMBOLICA",
                          resultado_simbolico="APROVADA")
        with self.assertRaises(RegraViolada):
            legislativo.votar(self.banco, sessao, proposicao, "SIMBOLICA",
                              resultado_simbolico="APROVADA")

    def test_nominal_exige_votos(self):
        sessao, proposicao = self._proposicao_pautada()
        with self.assertRaises(RegraViolada):
            legislativo.votar(self.banco, sessao, proposicao, "NOMINAL")

    def _plc_pautado(self):
        proposicao, _ = legislativo.apresentar_proposicao(
            self.banco, "PLC", "Altera a Lei Orgânica", "2025-09-10")
        sessao, _ = legislativo.convocar_sessao(self.banco, "ORDINARIA",
                                                "2025-09-16")
        legislativo.pautar(self.banco, sessao, proposicao)
        return sessao, proposicao

    def test_plc_exige_maioria_absoluta(self):
        # 5 membros; 2 SIM × 1 NAO aprovaria por maioria simples,
        # mas PLC exige SIM > 2,5 (art. 178 do Regimento).
        sessao, proposicao = self._plc_pautado()
        votos = {self.vereadores[0]: "SIM", self.vereadores[1]: "SIM",
                 self.vereadores[2]: "NAO"}
        self.assertEqual(
            legislativo.votar(self.banco, sessao, proposicao, "NOMINAL", votos),
            "REJEITADA")

    def test_plc_aprovado_com_maioria_absoluta(self):
        sessao, proposicao = self._plc_pautado()
        votos = dict.fromkeys(self.vereadores[:3], "SIM")  # 3 de 5 membros
        self.assertEqual(
            legislativo.votar(self.banco, sessao, proposicao, "NOMINAL", votos),
            "APROVADA")

    def test_plc_nao_admite_votacao_simbolica(self):
        sessao, proposicao = self._plc_pautado()
        with self.assertRaises(RegraViolada):
            legislativo.votar(self.banco, sessao, proposicao, "SIMBOLICA",
                              resultado_simbolico="APROVADA")

    def test_lista_de_comissoes_regimentais(self):
        self.assertEqual(len(legislativo.COMISSOES_PERMANENTES_REGIMENTAIS), 20)


if __name__ == "__main__":
    unittest.main()
