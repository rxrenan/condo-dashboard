import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from painel.extrair import extrair_pasta, valor_aprovado_no_trecho
from painel.pdfutil import extrair_paginas, paginas_de_txt
from painel.pipeline import executar, filtrar_visao
from painel.texto import normalizar_espaco as norm


TRECHO_GARAGEM = (
    "Fica aprovada a pintura da garagem dos blocos A e B, pelo valor de até "
    "R$ 45.000,00, em quatro etapas, no prazo de sessenta dias."
)


class PipelineTeste(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.painel = executar(RAIZ, Path(cls.tmp.name))
        cls.despesas = json.loads((Path(cls.tmp.name) / "despesas.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_decisao_cita_a_pagina(self):
        decisao = next(item for item in self.painel["decisoes"] if item["id"] == "age-2027-03-18-d01")
        self.assertEqual(decisao["trecho"], TRECHO_GARAGEM)
        self.assertEqual(decisao["pagina"], 2)
        self.assertEqual(decisao["valor_aprovado_centavos"], 4_500_000)
        pdf = (RAIZ / "examples" / "atas" / "age-2027-03-18.pdf").read_bytes()
        pagina = norm(extrair_paginas(pdf)[1])
        self.assertIn(TRECHO_GARAGEM, pagina)

    def test_pdf_bate_com_txt(self):
        for txt in sorted((RAIZ / "examples" / "atas").glob("*.txt")):
            paginas_txt = paginas_de_txt(txt.read_text(encoding="utf-8"))
            paginas_pdf = extrair_paginas(txt.with_suffix(".pdf").read_bytes())
            self.assertEqual(len(paginas_txt), len(paginas_pdf))
            for esquerda, direita in zip(paginas_txt, paginas_pdf):
                self.assertEqual(norm(esquerda), norm(direita))

    def test_gasto_confirmado_da_garagem(self):
        obra = next(item for item in self.painel["obras"] if item["id"] == "obra-garagem")
        self.assertEqual(obra["realizado_centavos"], 1_800_000)
        self.assertEqual(obra["orcamento_aprovado_centavos"], 4_500_000)
        documentos = {item["documento"] for item in obra["gastos"]}
        self.assertEqual(documentos, {"NF-3101", "NF-3108", "NF-3214"})
        self.assertEqual(obra["sugestoes_ocultas"], 1)
        sugestao = next(item for item in self.despesas if item["documento"] == "NF-3220")
        self.assertEqual(sugestao["projeto_id"], "obra-garagem")
        self.assertEqual(sugestao["confianca"], "media")
        self.assertEqual(sugestao["revisao"], "sugerida")
        self.assertFalse(sugestao["publicada"])

    def test_linha_generica_sem_obra_nao_entra(self):
        sem_termo = next(item for item in self.despesas if item["documento"] == "NF-3228")
        self.assertIsNone(sem_termo["projeto_id"])
        self.assertTrue(sem_termo["revisar"])
        limpeza = next(item for item in self.despesas if item["documento"] == "NF-3088")
        self.assertIsNone(limpeza["projeto_id"])
        self.assertFalse(limpeza["publicada"])
        self.assertNotIn("NF-3088", {item["documento"] for item in self.painel["revisar_despesas"]})
        self.assertEqual(
            [item["documento"] for item in self.painel["revisar_despesas"]],
            ["NF-3228"],
        )

    def test_resumo_so_usa_o_que_esta_confirmado(self):
        texto = self.painel["resumo"]["texto"]
        self.assertIn("Resumo de abril de 2027", texto)
        self.assertIn("Nenhuma assembleia com decisão publicada em abril de 2027", texto)
        self.assertIn("18 de março de 2027", texto)
        self.assertIn("etapa 2 de 4", texto)
        self.assertIn("R$ 5.600,00", texto)
        self.assertIn("R$ 18.000,00", texto)
        self.assertIn("R$ 45.000,00", texto)
        self.assertIn("R$ 2.100,00", texto)
        self.assertIn("R$ 12.000,00", texto)
        self.assertIn("Ocorrências de área comum ainda sem conclusão: 2.", texto)
        self.assertNotIn("3.400", texto)
        self.assertNotIn("dedetiz", texto.lower())
        self.assertNotIn("unidade 12", texto)

    def test_visao_do_morador_esconde_pendencia(self):
        morador = filtrar_visao(self.painel, "morador")
        assuntos = " ".join(item["assunto"] for item in morador["decisoes"])
        self.assertNotIn("dedetização", assuntos)
        self.assertEqual(morador["sugestoes_despesas"], [])
        self.assertEqual(morador["revisar_despesas"], [])
        conselho = filtrar_visao(self.painel, "conselho")
        self.assertTrue(any("dedetização" in item["assunto"] for item in conselho["decisoes"]))

    def test_valor_no_trecho(self):
        self.assertEqual(valor_aprovado_no_trecho("pelo valor de até R$ 45.000,00."), 4_500_000)
        self.assertIsNone(valor_aprovado_no_trecho("sem aprovação de valor nesta data"))

    def test_duas_execucoes_iguais(self):
        with tempfile.TemporaryDirectory() as pasta:
            de_novo = executar(RAIZ, Path(pasta))
        self.assertEqual(de_novo, self.painel)

    def test_saida_commitada(self):
        commitada = json.loads((RAIZ / "examples" / "saida" / "painel.json").read_text(encoding="utf-8"))
        self.assertEqual(commitada, self.painel)

    def test_comando_demo(self):
        concluido = subprocess.run(
            [sys.executable, "demo.py", "--no-serve"],
            cwd=RAIZ,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("dados fictícios", concluido.stdout)
        self.assertEqual(extrair_pasta(RAIZ / "examples" / "atas")[0]["arquivo"].endswith(".pdf"), True)


if __name__ == "__main__":
    unittest.main()
