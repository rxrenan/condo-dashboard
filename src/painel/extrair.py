"""Extrai deliberações de uma ata com trecho citado e página.

O modo determinístico entende um layout fixo: bloco DELIBERAÇÃO, com
Assunto, Trecho, Votação agregada e Resultado. Fora desse layout, a demo
não inventa item. O modo com modelo está em `llm.py` e não publica sozinho.
"""

from __future__ import annotations

import re
from pathlib import Path

from painel.mascara import contem_voto_de_unidade
from painel.pdfutil import extrair_paginas, paginas_de_txt
from painel.texto import MESES_NOME, chave, normalizar_espaco, sem_acento

BLOCO = re.compile(
    r"DELIBERAÇÃO\s+(?P<numero>\d+)\s+"
    r"Assunto:\s*(?P<assunto>.+?)\s+"
    r"Trecho:\s*(?P<trecho>.+?)\s+"
    r"Votação agregada:\s*(?P<votacao>.+?)\s+"
    r"Resultado:\s*(?P<resultado>APROVADO|REJEITADO)\b"
)
DATA = re.compile(r"Data:\s+(\d{1,2}) de ([A-Za-zÀ-ÿ]+) de (\d{4})")
VOTOS = re.compile(r"(\d+) a favor, (\d+) contra e (\d+) absten", re.IGNORECASE)
DINHEIRO = re.compile(r"R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})")
SEM_VALOR = re.compile(r"sem aprova[cç][aã]o de valor", re.IGNORECASE)


def centavos_de_brl(token: str) -> int:
    inteiro, frac = token.replace(".", "").split(",")
    return int(inteiro) * 100 + int(frac)


def valor_aprovado_no_trecho(trecho: str) -> int | None:
    if SEM_VALOR.search(trecho):
        return None
    achado = DINHEIRO.search(trecho)
    if not achado:
        return None
    return centavos_de_brl(achado.group(1))


def _data_iso(documento: str) -> str:
    achado = DATA.search(documento)
    if not achado:
        raise ValueError("ata sem data")
    dia, mes_nome, ano = achado.groups()
    mes = MESES_NOME.get(sem_acento(mes_nome).lower())
    if not mes:
        raise ValueError(f"mês desconhecido: {mes_nome}")
    return f"{int(ano):04d}-{mes:02d}-{int(dia):02d}"


def _tipo_assembleia(documento: str) -> tuple[str, str]:
    base = sem_acento(documento).upper()
    if "EXTRAORDINARIA" in base:
        return "age", "Assembleia geral extraordinária"
    if "ORDINARIA" in base:
        return "ago", "Assembleia geral ordinária"
    raise ValueError("ata sem tipo de assembleia")


def extrair_documento(paginas: list[str], arquivo: str) -> list[dict]:
    if not paginas:
        raise ValueError(f"{arquivo} sem páginas")
    normalizadas = [normalizar_espaco(pagina) for pagina in paginas]
    documento = normalizar_espaco(" ".join(paginas))
    codigo, titulo = _tipo_assembleia(documento)
    data = _data_iso(documento)
    decisoes: list[dict] = []
    vistos: set[str] = set()
    for numero_pagina, pagina in enumerate(normalizadas, start=1):
        for bloco in BLOCO.finditer(pagina):
            trecho = normalizar_espaco(bloco.group("trecho"))
            assunto = normalizar_espaco(bloco.group("assunto"))
            if trecho not in pagina:
                raise ValueError(f"trecho não está na página {numero_pagina} de {arquivo}")
            if contem_voto_de_unidade(trecho) or contem_voto_de_unidade(assunto):
                raise ValueError("deliberação contém voto de unidade")
            votos = VOTOS.search(bloco.group("votacao"))
            if not votos:
                raise ValueError(f"votação agregada ilegível em {arquivo}")
            a_favor, contra, abstencoes = (int(v) for v in votos.groups())
            numero = int(bloco.group("numero"))
            identificador = f"{codigo}-{data}-d{numero:02d}"
            if identificador in vistos:
                raise ValueError(f"deliberação repetida: {identificador}")
            vistos.add(identificador)
            resultado = bloco.group("resultado").lower()
            decisoes.append(
                {
                    "id": identificador,
                    "assembleia": codigo.upper(),
                    "assembleia_titulo": titulo,
                    "data": data,
                    "numero": numero,
                    "assunto": assunto,
                    "trecho": trecho,
                    "pagina": numero_pagina,
                    "arquivo": arquivo,
                    "votacao": {
                        "a_favor": a_favor,
                        "contra": contra,
                        "abstencoes": abstencoes,
                    },
                    "votacao_texto": normalizar_espaco(bloco.group("votacao")),
                    "resultado": resultado,
                    "resultado_rotulo": "Aprovado" if resultado == "aprovado" else "Rejeitado",
                    "valor_aprovado_centavos": valor_aprovado_no_trecho(trecho),
                }
            )
    if not decisoes:
        raise ValueError(f"nenhuma deliberação em {arquivo}")
    return decisoes


def extrair_pdf(caminho: Path) -> list[dict]:
    paginas = extrair_paginas(caminho.read_bytes())
    return extrair_documento(paginas, caminho.name)


def extrair_txt(caminho: Path) -> list[dict]:
    paginas = paginas_de_txt(caminho.read_text(encoding="utf-8"))
    return extrair_documento(paginas, caminho.with_suffix(".pdf").name)


def extrair_pasta(pasta: Path) -> list[dict]:
    decisoes: list[dict] = []
    for pdf in sorted(pasta.glob("*.pdf")):
        decisoes.extend(extrair_pdf(pdf))
    if not decisoes:
        raise FileNotFoundError(f"nenhum PDF em {pasta}")
    return sorted(decisoes, key=lambda item: (item["data"], item["numero"], item["id"]))


def texto_publicado_de_atas(pasta: Path) -> list[dict]:
    """Páginas com voto de unidade mascarado, para auditoria da saída."""
    from painel.mascara import mascarar

    saida = []
    for pdf in sorted(pasta.glob("*.pdf")):
        paginas = [mascarar(pagina) for pagina in extrair_paginas(pdf.read_bytes())]
        saida.append({"arquivo": pdf.name, "paginas": paginas})
    return saida
