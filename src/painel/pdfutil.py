"""PDF mínimo, só com a biblioteca padrão.

A demo grava a ata fictícia em PDF e lê o texto de volta. Não é OCR de
imagem. Ata escaneada de verdade precisaria de um motor de OCR, ainda
[A CONFIRMAR].
"""

from __future__ import annotations

import re
from pathlib import Path

MARCADOR = re.compile(r"^=== PÁGINA (\d+) ===\s*$", re.MULTILINE)
STRING_PDF = re.compile(r"\((?:\\.|[^\\)])*\)\s*Tj|T\*")


def paginas_de_txt(texto: str) -> list[str]:
    marcas = list(MARCADOR.finditer(texto))
    if not marcas:
        raise ValueError("ata sem marcador de página")
    paginas: list[str] = []
    for indice, marca in enumerate(marcas):
        numero = int(marca.group(1))
        if numero != indice + 1:
            raise ValueError(f"páginas fora de ordem: encontrei {numero}")
        inicio = marca.end()
        fim = marcas[indice + 1].start() if indice + 1 < len(marcas) else len(texto)
        paginas.append(texto[inicio:fim].strip("\n"))
    return paginas


def quebrar(linha: str, largura: int = 84) -> list[str]:
    palavras = linha.split()
    if not palavras:
        return [""]
    linhas: list[str] = []
    atual = ""
    for palavra in palavras:
        tentativa = palavra if not atual else f"{atual} {palavra}"
        if len(tentativa) <= largura:
            atual = tentativa
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def linhas_de_pagina(pagina: str) -> list[str]:
    linhas: list[str] = []
    for bruta in pagina.splitlines():
        if not bruta.strip():
            linhas.append("")
            continue
        linhas.extend(quebrar(bruta.strip()))
    return linhas or [""]


def escapar_pdf(texto: str) -> str:
    bruto = texto.encode("cp1252")
    saida: list[str] = []
    for byte in bruto:
        if byte == 0x5C:
            saida.append("\\\\")
        elif byte == 0x28:
            saida.append("\\(")
        elif byte == 0x29:
            saida.append("\\)")
        elif 32 <= byte <= 126:
            saida.append(chr(byte))
        else:
            saida.append(f"\\{byte:03o}")
    return "".join(saida)


def _decodificar_string(bruta: str) -> str:
    saida = bytearray()
    indice = 0
    while indice < len(bruta):
        char = bruta[indice]
        if char == "\\" and indice + 1 < len(bruta):
            proximo = bruta[indice + 1]
            if proximo in "01234567":
                fim = indice + 1
                while fim < len(bruta) and fim < indice + 4 and bruta[fim] in "01234567":
                    fim += 1
                saida.append(int(bruta[indice + 1 : fim], 8))
                indice = fim
                continue
            mapa = {"n": 10, "r": 13, "t": 9, "b": 8, "f": 12, "(": 40, ")": 41, "\\": 92}
            saida.append(mapa.get(proximo, ord(proximo)))
            indice += 2
            continue
        saida.append(ord(char))
        indice += 1
    return saida.decode("cp1252")


def _stream(linhas: list[str]) -> str:
    comandos = ["BT", "/F1 11 Tf", "48 790 Td", "15 TL"]
    for linha in linhas:
        comandos.append(f"({escapar_pdf(linha)}) Tj")
        comandos.append("T*")
    comandos.append("ET")
    conteudo = "\n".join(comandos) + "\n"
    tamanho = len(conteudo.encode("latin-1"))
    return f"<< /Length {tamanho} >>\nstream\n{conteudo}endstream"


def montar_pdf(paginas: list[list[str]]) -> bytes:
    if not paginas:
        raise ValueError("PDF sem páginas")
    objetos: dict[int, str] = {
        1: "<< /Type /Catalog /Pages 2 0 R >>",
        3: "<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman /Encoding /WinAnsiEncoding >>",
    }
    kids: list[int] = []
    proximo = 4
    for linhas in paginas:
        id_pagina = proximo
        id_conteudo = proximo + 1
        proximo += 2
        kids.append(id_pagina)
        objetos[id_conteudo] = _stream(linhas)
        objetos[id_pagina] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Contents {id_conteudo} 0 R "
            f"/Resources << /Font << /F1 3 0 R >> >> >>"
        )
    refs = " ".join(f"{kid} 0 R" for kid in kids)
    objetos[2] = f"<< /Type /Pages /Count {len(paginas)} /Kids [{refs}] >>"
    return _serializar(objetos)


def _serializar(objetos: dict[int, str]) -> bytes:
    saida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for numero in range(1, max(objetos) + 1):
        offsets.append(len(saida))
        corpo = objetos[numero]
        saida.extend(f"{numero} 0 obj\n{corpo}\nendobj\n".encode("latin-1"))
    xref = len(saida)
    total = max(objetos) + 1
    saida.extend(f"xref\n0 {total}\n".encode("ascii"))
    saida.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        saida.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    saida.extend(
        f"trailer << /Size {total} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(saida)


def extrair_paginas(pdf: bytes) -> list[str]:
    paginas: list[str] = []
    for bloco in re.finditer(rb"stream\r?\n(.*?)\r?\n?endstream", pdf, re.DOTALL):
        cru = bloco.group(1).decode("latin-1")
        if "Tj" not in cru:
            continue
        linhas: list[str] = []
        atual: list[str] = []
        for achado in STRING_PDF.finditer(cru):
            token = achado.group(0)
            if token.startswith("("):
                interno = token[: token.rfind(")")][1:]
                atual.append(_decodificar_string(interno))
            else:
                linhas.append("".join(atual))
                atual = []
        if atual:
            linhas.append("".join(atual))
        paginas.append("\n".join(linhas).strip("\n"))
    if not paginas:
        raise ValueError("PDF sem texto extraível")
    return paginas


def gravar_pdf_de_txt(txt: Path, pdf: Path | None = None) -> Path:
    destino = pdf or txt.with_suffix(".pdf")
    paginas = paginas_de_txt(txt.read_text(encoding="utf-8"))
    linhas = [linhas_de_pagina(pagina) for pagina in paginas]
    destino.write_bytes(montar_pdf(linhas))
    return destino


def garantir_pdfs(pasta: Path) -> list[Path]:
    gerados: list[Path] = []
    for txt in sorted(pasta.glob("*.txt")):
        gerados.append(gravar_pdf_de_txt(txt))
    if not gerados:
        raise FileNotFoundError(f"nenhuma ata em {pasta}")
    return gerados
