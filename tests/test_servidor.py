import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from painel.pipeline import executar
from painel.servidor import criar_servidor


class ServidorTeste(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.painel = executar(RAIZ, Path(cls.tmp.name))
        cls.srv = criar_servidor(cls.painel, "127.0.0.1", 0)
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.tmp.cleanup()

    def _get(self, caminho):
        with urllib.request.urlopen(self.base + caminho) as resposta:
            return resposta.status, resposta.read()

    def test_paginas_e_api(self):
        status, html = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("Painel do condomínio".encode("utf-8"), html)
        status, _ = self._get("/app.css")
        self.assertEqual(status, 200)
        status, js = self._get("/app.js")
        self.assertEqual(status, 200)
        for rotulo in ("Início", "Obras", "Decisões", "Ocorrências", "Mudanças", "Perguntas"):
            self.assertIn(rotulo.encode("utf-8"), js)
        status, corpo = self._get("/api/saude")
        self.assertEqual(json.loads(corpo)["modo"], "deterministico")

    def test_visoes(self):
        _, morador = self._get("/api/painel?visao=morador")
        _, conselho = self._get("/api/painel?visao=conselho")
        texto_morador = morador.decode("utf-8")
        texto_conselho = conselho.decode("utf-8")
        self.assertNotIn("dedetização", texto_morador)
        self.assertNotIn("Mão de obra em reformas", texto_morador)
        self.assertNotIn('"termos"', texto_morador)
        self.assertIn("dedetização", texto_conselho)
        self.assertIn("Mão de obra em reformas", texto_conselho)
        self.assertNotIn('"termos"', texto_conselho)

    def test_pergunta(self):
        pedido = urllib.request.Request(
            self.base + "/api/perguntas",
            data=json.dumps({"pergunta": "Quanto já foi confirmado na pintura da garagem?"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(pedido) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
        self.assertIn("R$ 18.000,00", dados["resposta"])
        self.assertFalse(dados["recusa"])


if __name__ == "__main__":
    unittest.main()
