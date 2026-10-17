import json
import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from painel.llm import exigir_llm, modo_configurado
from painel.mascara import ROTULO_DOCUMENTO, ROTULO_VOTO, mascarar
from painel.pdfutil import extrair_paginas

CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
EXTENSOES = {
    ".md",
    ".py",
    ".js",
    ".css",
    ".html",
    ".json",
    ".csv",
    ".txt",
    ".svg",
    ".example",
}


def termos_proibidos():
    return [
        "trans" + "par" + "\u00ean" + "cia",
        "trans" + "par" + "encia",
        "trans" + "parency",
        "trans" + "parent",
        "hab" + "itat",
        "group" + "software",
        "group" + " com",
        "group-" + "com",
        "comunidades" + "mobile",
        "osa" + "sco",
    ]


class PrivacidadeTeste(unittest.TestCase):
    def test_mascara_cpf_e_voto(self):
        cpf = f"{123:03d}.{456:03d}.{789:03d}-{0:02d}"
        digitos = "".join(str(n) for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 0))
        texto = f"O documento {cpf} e a sequencia {digitos}. A unidade 12 votou contra a pintura."
        limpo = mascarar(texto)
        self.assertNotIn(cpf, limpo)
        self.assertNotIn(digitos, limpo)
        self.assertIn(ROTULO_DOCUMENTO, limpo)
        self.assertNotIn("unidade 12 votou", limpo)
        self.assertIn(ROTULO_VOTO, limpo)

    def test_saida_publicada_omite_voto_de_unidade(self):
        frase = "unidade 12 votou"
        fonte = (RAIZ / "examples" / "atas" / "age-2027-03-18.txt").read_text(encoding="utf-8")
        self.assertIn(frase, fonte)
        pdf = extrair_paginas((RAIZ / "examples" / "atas" / "age-2027-03-18.pdf").read_bytes())
        self.assertIn(frase, "\n".join(pdf))
        for caminho in (RAIZ / "examples" / "saida").glob("*.json"):
            texto = caminho.read_text(encoding="utf-8")
            self.assertNotIn(frase, texto, caminho.name)
            self.assertIsNone(CPF.search(texto), caminho.name)
        atas = json.loads((RAIZ / "examples" / "saida" / "atas-texto.json").read_text(encoding="utf-8"))
        self.assertIn(ROTULO_VOTO, json.dumps(atas, ensure_ascii=False))

    def test_repositorio_sem_dado_real_nem_cpf(self):
        proibidos = [termo.casefold() for termo in termos_proibidos()]
        falhas = []
        for caminho in RAIZ.rglob("*"):
            if not caminho.is_file() or ".git" in caminho.parts or "__pycache__" in caminho.parts:
                continue
            if caminho.suffix.lower() == ".png":
                bruto = caminho.read_bytes().lower()
                for termo in proibidos:
                    if termo.encode("utf-8") in bruto:
                        falhas.append(f"{caminho} contém {termo}")
                continue
            if caminho.suffix.lower() == ".pdf":
                texto = "\n".join(extrair_paginas(caminho.read_bytes())).casefold()
            elif caminho.suffix.lower() in EXTENSOES or caminho.name.startswith(".env"):
                texto = caminho.read_text(encoding="utf-8").casefold()
            else:
                continue
            if CPF.search(texto):
                falhas.append(f"{caminho} contém CPF")
            for termo in proibidos:
                if termo in texto:
                    falhas.append(f"{caminho} contém {termo}")
            if "\u2014" in texto or "\u2013" in texto:
                falhas.append(f"{caminho} contém travessão")
            post = "linkedin.com/" + "posts"
            feed = "linkedin.com/" + "feed"
            if post in texto or feed in texto:
                falhas.append(f"{caminho} contém post de LinkedIn")
        self.assertEqual(falhas, [])

    def test_modo_padrao_nao_exige_chave(self):
        self.assertEqual(modo_configurado({}), "deterministico")
        with self.assertRaises(SystemExit):
            exigir_llm({})


if __name__ == "__main__":
    unittest.main()
