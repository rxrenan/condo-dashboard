"""Texto, datas e dinheiro. Sem dependências externas."""

from __future__ import annotations

import re
import unicodedata

MESES = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)

MESES_NOME = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

STATUS_OBRA = {
    "em_andamento": "Em andamento",
    "concluida": "Concluída",
    "nao_iniciada": "Não iniciada",
    "pausada": "Pausada",
}

STATUS_OCORRENCIA = {
    "aberta": "Aberta",
    "em_andamento": "Em andamento",
    "concluida": "Concluída",
}

STATUS_RESULTADO = {
    "aprovado": "Aprovado",
    "rejeitado": "Rejeitado",
}

STOP = {
    "a",
    "o",
    "os",
    "as",
    "de",
    "do",
    "da",
    "dos",
    "das",
    "e",
    "em",
    "no",
    "na",
    "nos",
    "nas",
    "um",
    "uma",
    "uns",
    "para",
    "por",
    "com",
    "sem",
    "que",
    "se",
    "ao",
    "ou",
    "nao",
    "qual",
    "quais",
    "como",
    "quando",
    "onde",
    "quanto",
    "quantos",
    "foi",
    "sao",
    "esta",
    "estao",
    "esse",
    "essa",
    "isso",
    "sobre",
    "pelo",
    "pela",
    "pelos",
    "pelas",
    "ja",
    "ate",
    "seu",
    "sua",
    "seus",
    "suas",
    "mais",
    "menos",
    "entre",
    "desde",
    "sob",
    "quem",
    "ser",
    "ter",
    "tem",
    "ha",
    "num",
    "numa",
    "the",
}


def sem_acento(texto: str) -> str:
    base = unicodedata.normalize("NFD", texto)
    return "".join(c for c in base if unicodedata.category(c) != "Mn")


def chave(texto: str) -> str:
    return sem_acento(texto).lower()


def normalizar_espaco(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def brl(centavos: int) -> str:
    sinal = "-" if centavos < 0 else ""
    valor = abs(int(centavos))
    reais, cents = divmod(valor, 100)
    inteiro = f"{reais:,}".replace(",", ".")
    return f"{sinal}R$ {inteiro},{cents:02d}"


def data_extenso(iso: str) -> str:
    ano, mes, dia = iso.split("-")
    return f"{int(dia)} de {MESES[int(mes) - 1]} de {ano}"


def data_curta(iso: str) -> str:
    ano, mes, dia = iso.split("-")
    return f"{int(dia):02d}/{int(mes):02d}/{ano}"


def tokens(texto: str) -> list[str]:
    partes = re.findall(r"[a-z0-9]+", chave(texto))
    saida: list[str] = []
    vistos: set[str] = set()
    for parte in partes:
        candidatos = [parte]
        if parte.endswith("s") and len(parte) > 4:
            candidatos.append(parte[:-1])
        for item in candidatos:
            if item in STOP or len(item) <= 2 or item in vistos:
                continue
            vistos.add(item)
            saida.append(item)
    return saida
