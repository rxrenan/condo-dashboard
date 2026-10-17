"""Mascaramento antes de indexar ou publicar.

A demo não traz dado real. Mesmo assim o pipeline remove CPF e voto de
unidade, se aparecerem numa ata, para o hábito existir no código.
"""

from __future__ import annotations

import re

CPF_PONTUADO = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
CPF_DIGITOS = re.compile(r"(?<!\d)\d{11}(?!\d)")
VOTO_UNIDADE = re.compile(
    r"unidade\s+\d+\s+votou[^.]*\.",
    re.IGNORECASE,
)

ROTULO_DOCUMENTO = "[documento mascarado]"
ROTULO_VOTO = "[voto de unidade omitido]."


def mascarar(texto: str) -> str:
    texto = CPF_PONTUADO.sub(ROTULO_DOCUMENTO, texto)
    texto = CPF_DIGITOS.sub(ROTULO_DOCUMENTO, texto)
    texto = VOTO_UNIDADE.sub(ROTULO_VOTO, texto)
    return texto


def contem_voto_de_unidade(texto: str) -> bool:
    return VOTO_UNIDADE.search(texto) is not None
