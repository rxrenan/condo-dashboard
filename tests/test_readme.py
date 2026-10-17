import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


class ReadmeTeste(unittest.TestCase):
    def test_portugues(self):
        texto = (RAIZ / "README.md").read_text(encoding="utf-8")
        for titulo in (
            "## 1. Problema",
            "## 2. Solução",
            "## 3. Arquitetura",
            "## 4. Resultados",
            "Como medir",
            "## 5. Lições aprendidas",
            "## 6. Riscos e limites",
            "## 7. Próximos passos",
            "## Como rodar",
            "## Estrutura do repositório",
            "## Fontes",
            "## Aviso",
        ):
            self.assertIn(titulo, texto)
        self.assertIn("em andamento", texto)
        self._comum(texto)
        self.assertIn("LGPD", texto)
        self.assertIn("python demo.py", texto)
        problema, solucao = self._partes(texto, "## 2. Solução", "## 3. Arquitetura")
        self.assertIn("antes-depois-1600x900.png", problema)
        self.assertIn("jornada-1600x900.png", solucao)
        self.assertIn("prefers-color-scheme: dark", solucao)
        self.assertIn("pesquisa de validação com o conselho e com os moradores", texto.casefold())
        self.assertIn("possível piloto", texto.casefold())

    def test_ingles(self):
        texto = (RAIZ / "README.en.md").read_text(encoding="utf-8")
        for titulo in (
            "## 1. Problem",
            "## 2. Solution",
            "## 3. Architecture",
            "## 4. Results",
            "How to measure",
            "## 5. Lessons learned",
            "## 6. Risks and limits",
            "## 7. Next steps",
            "## How to run",
            "## Repository structure",
            "## Sources",
            "## Notice",
        ):
            self.assertIn(titulo, texto)
        self.assertIn("in progress", texto)
        self._comum(texto)
        self.assertIn("LGPD", texto)
        self.assertIn("python demo.py", texto)
        problema, solucao = self._partes(texto, "## 2. Solution", "## 3. Architecture")
        self.assertIn("antes-depois-1600x900.png", problema)
        self.assertIn("jornada-1600x900.png", solucao)
        self.assertIn("prefers-color-scheme: dark", solucao)
        self.assertIn("validation survey with the council and with residents", texto)
        self.assertIn("possible pilot", texto.lower())
        self.assertIn("unit-level", texto.lower())

    def _comum(self, texto: str):
        self.assertIn("Renan R. Rosa", texto)
        self.assertIn("Staff Product Manager", texto)
        self.assertIn("https://www.linkedin.com/in/renanrrosa", texto)
        self.assertIn("[A CONFIRMAR]", texto)
        self.assertIn("capa-repo-1280x640.png", texto)
        self.assertLess(texto.index("preview-1600x900.png"), texto.index("antes-depois-1600x900.png"))
        self.assertLess(texto.index("antes-depois-1600x900.png"), texto.index("jornada-1600x900.png"))
        self.assertIn("mock-dashboard-light-1600x1000.png", texto)
        self.assertIn("mock-dashboard-dark-1600x1000.png", texto)

    def _partes(self, texto: str, meio: str, fim: str):
        return texto.split(meio)[0], texto.split(meio)[1].split(fim)[0]


if __name__ == "__main__":
    unittest.main()
