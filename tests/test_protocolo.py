"""Testes do módulo do Protocolo: busca, documentos, painel e recebimento."""

import unittest

from sistema import servicos
from sistema.api import Aplicacao
from sistema.autenticacao import AcessoNegado
from sistema.demo import criar_banco
from sistema.servicos import RegraViolada


class TestProtocolo(unittest.TestCase):
    def setUp(self):
        self.banco = criar_banco()
        self.protocolo = self.banco.execute(
            "SELECT id FROM unidade WHERE nome = "
            "'Coordenadoria da Secretaria-Geral'").fetchone()[0]
        self.destino = self.banco.execute(
            "SELECT id FROM unidade WHERE nome = 'Diretoria-Geral'"
        ).fetchone()[0]

    def tearDown(self):
        self.banco.close()

    def _autuar(self, assunto="Aquisição de material", interessado="SMS"):
        pid, _ = servicos.autuar_processo(
            self.banco, "ADMINISTRATIVO", assunto, self.protocolo,
            "2026-07-20", interessado)
        return pid

    # --- P1: busca ---------------------------------------------------

    def test_busca_por_interessado_e_assunto(self):
        self._autuar("Compra de cadeiras", "Secretaria de Saúde")
        self._autuar("Reforma do plenário", "Diretoria")
        por_int = servicos.buscar_processos(self.banco, {"interessado": "saúde"})
        self.assertEqual(len(por_int), 1)
        self.assertEqual(por_int[0]["interessado"], "Secretaria de Saúde")
        por_assunto = servicos.buscar_processos(
            self.banco, {"assunto": "plenário"})
        self.assertEqual(len(por_assunto), 1)

    def test_busca_traz_localizacao_atual(self):
        pid = self._autuar()
        # sem tramitação, está na origem
        (proc,) = [p for p in servicos.buscar_processos(self.banco, {})
                   if p["id"] == pid]
        self.assertEqual(proc["localizacao"], "Coordenadoria da Secretaria-Geral")
        servicos.tramitar(self.banco, pid, self.destino, "Segue.",
                          "2026-07-21")
        (proc,) = [p for p in servicos.buscar_processos(self.banco, {})
                   if p["id"] == pid]
        self.assertEqual(proc["localizacao"], "Diretoria-Geral")

    def test_busca_por_numero_e_situacao(self):
        pid = self._autuar()
        (numero, ano) = self.banco.execute(
            "SELECT numero, ano FROM processo WHERE id = ?", (pid,)).fetchone()
        achados = servicos.buscar_processos(
            self.banco, {"numero": numero, "ano": ano})
        self.assertEqual(achados[0]["id"], pid)
        servicos.arquivar_processo(self.banco, pid)
        self.assertEqual(
            servicos.buscar_processos(self.banco, {"situacao": "ARQUIVADO"})[0]["id"],
            pid)

    # --- P2: documentos ----------------------------------------------

    def test_juntar_e_listar_documentos(self):
        pid = self._autuar()
        servicos.juntar_documento(
            self.banco, pid, "Ofício", "Ofício 1/2026", "2026-07-20", "SMS")
        servicos.juntar_documento(
            self.banco, pid, "Parecer", "Parecer 2/2026", "2026-07-21")
        docs = servicos.documentos_do_processo(self.banco, pid)
        self.assertEqual([d["titulo"] for d in docs],
                         ["Parecer 2/2026", "Ofício 1/2026"])  # mais recente 1º

    def test_juntar_exige_tipo_titulo_e_processo(self):
        pid = self._autuar()
        with self.assertRaises(RegraViolada):
            servicos.juntar_documento(self.banco, pid, "", "X", "2026-07-20")
        with self.assertRaises(RegraViolada):
            servicos.juntar_documento(self.banco, pid, "Ofício", " ",
                                      "2026-07-20")
        with self.assertRaises(RegraViolada):
            servicos.juntar_documento(self.banco, 99999, "Ofício", "X",
                                      "2026-07-20")

    # --- P3: painel e recebimento ------------------------------------

    def test_painel_conta_por_situacao_e_atraso(self):
        app = Aplicacao(":memory:")
        prot = app.banco.execute(
            "SELECT id FROM unidade WHERE nome = "
            "'Coordenadoria da Secretaria-Geral'").fetchone()[0]
        destino = app.banco.execute(
            "SELECT id FROM unidade WHERE nome = 'Diretoria-Geral'"
        ).fetchone()[0]
        pid, _ = servicos.autuar_processo(
            app.banco, "ADMINISTRATIVO", "Assunto", prot, "2026-07-01")
        # tramita com prazo vencido -> entra em atraso
        servicos.tramitar(app.banco, pid, destino, "Segue.", "2026-07-01",
                          prazo="2026-07-05")
        app.banco.commit()
        app.usuario_atual = {"login": "prot", "perfil": "PROTOCOLO",
                             "unidade_id": prot}
        painel = app.painel_protocolo()
        self.assertEqual(painel["por_situacao"].get("EM_TRAMITACAO"), 1)
        self.assertEqual(painel["total"], 1)
        self.assertEqual(len(painel["em_atraso"]), 1)

    def test_painel_exige_protocolo(self):
        app = Aplicacao(":memory:")
        gab = app.banco.execute(
            "SELECT id FROM unidade WHERE nome LIKE '%Chiquinho%'"
        ).fetchone()[0]
        app.usuario_atual = {"login": "gab", "perfil": "LEGISLATIVO",
                             "unidade_id": gab}
        # a rota é gateada em PROTOCOLO; o dispatcher aplica a área, mas
        # garantimos que um setor sem PROTOCOLO não passa pela alçada.
        from sistema import autenticacao
        with self.assertRaises(AcessoNegado):
            autenticacao.exigir(app.banco, app.usuario_atual, "PROTOCOLO")

    def test_recebimento_confirma_tramitacao(self):
        pid = self._autuar()
        tid = servicos.tramitar(self.banco, pid, self.destino, "Segue.",
                                "2026-07-21", prazo="2026-07-25")
        servicos.receber_tramitacao(self.banco, tid, "2026-07-22")
        (recebido,) = self.banco.execute(
            "SELECT data_recebimento FROM tramitacao WHERE id = ?",
            (tid,)).fetchone()
        self.assertEqual(recebido, "2026-07-22")
        # já recebida não recebe de novo
        with self.assertRaises(RegraViolada):
            servicos.receber_tramitacao(self.banco, tid, "2026-07-23")


if __name__ == "__main__":
    unittest.main()
