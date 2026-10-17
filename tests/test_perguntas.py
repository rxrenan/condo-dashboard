import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from painel.perguntas import responder
from painel.pipeline import executar


class PerguntasTeste(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.painel = executar(RAIZ, Path(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_valor_aprovado_cita_a_ata(self):
        resposta = responder("Qual o valor aprovado para a pintura da garagem?", self.painel)
        self.assertFalse(resposta["recusa"])
        self.assertIn("R$ 45.000,00", resposta["resposta"])
        self.assertIn(TRECHO(self), resposta["resposta"])
        self.assertEqual(resposta["citacoes"][0]["pagina"], 2)
        self.assertEqual(resposta["citacoes"][0]["arquivo"], "age-2027-03-18.pdf")

    def test_soma_confirmada_nao_inclui_sugestao(self):
        resposta = responder("Quanto já foi confirmado na pintura da garagem?", self.painel)
        self.assertFalse(resposta["recusa"])
        self.assertIn("R$ 18.000,00", resposta["resposta"])
        self.assertIn("3 lançamentos", resposta["resposta"])
        self.assertNotIn("3.400", resposta["resposta"])
        rotulos = " ".join(item["rotulo"] for item in resposta["citacoes"])
        self.assertIn("NF-3101", rotulos)
        self.assertIn("NF-3108", rotulos)
        self.assertIn("NF-3214", rotulos)
        self.assertNotIn("NF-3220", rotulos)

    def test_playground_cita_o_adiamento(self):
        resposta = responder("A reforma do playground foi aprovada?", self.painel)
        self.assertIn("adiada", resposta["resposta"])
        self.assertIn("sem aprovação de valor", resposta["resposta"])
        self.assertEqual(resposta["citacoes"][0]["pagina"], 3)

    def test_mudanca_com_fonte(self):
        resposta = responder("Qual o horário de mudança?", self.painel)
        self.assertIn("Terça a sábado, das 8h às 17h", resposta["resposta"])
        self.assertTrue(resposta["citacoes"])

    def test_recusas(self):
        inadimplente = responder("Quem está inadimplente?", self.painel)
        self.assertTrue(inadimplente["recusa"])
        self.assertEqual(inadimplente["motivo"], "privacidade")
        self.assertEqual(inadimplente["citacoes"], [])

        voto = responder("A unidade 12 votou em quê?", self.painel)
        self.assertEqual(voto["motivo"], "privacidade")

        juridico = responder("O síndico pode ser processado pelo atraso?", self.painel)
        self.assertEqual(juridico["motivo"], "juridico")
        self.assertIn("Não interpreto norma", juridico["resposta"])

        franca = responder("Qual a capital da França?", self.painel)
        self.assertEqual(franca["motivo"], "sem_fonte")

        pendente = responder("Quando começa a dedetização nova?", self.painel)
        self.assertEqual(pendente["motivo"], "sem_fonte")

    def test_pergunta_vazia(self):
        resposta = responder("   ", self.painel)
        self.assertTrue(resposta["recusa"])
        self.assertEqual(resposta["motivo"], "vazia")


def TRECHO(caso):
    return caso.painel["decisoes"][3]["trecho"] if False else (
        "Fica aprovada a pintura da garagem dos blocos A e B, pelo valor de até "
        "R$ 45.000,00, em quatro etapas, no prazo de sessenta dias."
    )


if __name__ == "__main__":
    unittest.main()
