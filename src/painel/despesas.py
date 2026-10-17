"""Marca linhas de balancete a uma obra. Nada entra no realizado sem confirmação."""

from __future__ import annotations

import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from painel.texto import chave

FORCAS = {"especifica": 3, "apoio": 1}


def centavos_de_valor(bruto: str) -> int:
    texto = bruto.strip()
    if not texto:
        raise ValueError("valor vazio")
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    quantizado = (Decimal(texto) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(quantizado)


def ler_balancetes(pasta: Path) -> list[dict]:
    arquivos = sorted(pasta.glob("*.csv"))
    if not arquivos:
        raise FileNotFoundError(f"nenhum balancete em {pasta}")
    linhas: list[dict] = []
    documentos: set[str] = set()
    for arquivo in arquivos:
        with arquivo.open(encoding="utf-8", newline="") as handle:
            leitor = csv.DictReader(handle)
            esperadas = {"data", "documento", "historico", "categoria", "fornecedor", "valor"}
            if set(leitor.fieldnames or []) != esperadas:
                raise ValueError(f"colunas inesperadas em {arquivo.name}")
            for numero, row in enumerate(leitor, start=2):
                documento = row["documento"].strip()
                if documento in documentos:
                    raise ValueError(f"documento repetido: {documento}")
                documentos.add(documento)
                linhas.append(
                    {
                        "data": row["data"].strip(),
                        "documento": documento,
                        "historico": row["historico"].strip(),
                        "categoria": row["categoria"].strip(),
                        "fornecedor": row["fornecedor"].strip(),
                        "valor_centavos": centavos_de_valor(row["valor"]),
                        "arquivo": arquivo.name,
                        "linha": numero,
                    }
                )
    return linhas


def sugerir(linha: dict, obras: list[dict]) -> dict:
    historico = chave(linha["historico"])
    fornecedor = chave(linha["fornecedor"])
    categoria = chave(linha["categoria"])
    melhor_id = None
    melhor_pontos = 0
    melhor_motivo = "sem termo de projeto"
    empate = False
    for obra in obras:
        pontos = 0
        motivo = None
        for termo in obra["termos"]:
            texto = chave(termo["texto"])
            forca = termo["forca"]
            if forca not in ("especifica", "apoio"):
                raise ValueError(f"força de termo inválida em {obra['id']}")
            if not texto:
                continue
            if forca == "especifica" and texto in historico and pontos < 3:
                pontos = 3
                motivo = "termo específico no histórico"
            elif forca == "especifica" and texto in fornecedor and pontos < 2:
                pontos = 2
                motivo = "fornecedor coincide com a obra e o histórico é genérico"
            elif forca == "apoio" and texto in historico and pontos < 1:
                pontos = 1
                motivo = "termo de apoio no histórico"
        if pontos > melhor_pontos:
            melhor_pontos = pontos
            melhor_id = obra["id"]
            melhor_motivo = motivo or melhor_motivo
            empate = False
        elif pontos == melhor_pontos and pontos > 0:
            empate = True
    if empate:
        return {
            "projeto_id": None,
            "confianca": None,
            "motivo": "mais de uma obra possível",
            "revisar": True,
        }
    if melhor_pontos == 0:
        revisar = "reforma" in categoria
        return {
            "projeto_id": None,
            "confianca": None,
            "motivo": "categoria de reforma sem termo de projeto" if revisar else "sem termo de projeto",
            "revisar": revisar,
        }
    confianca = {3: "alta", 2: "media", 1: "baixa"}[melhor_pontos]
    return {
        "projeto_id": melhor_id,
        "confianca": confianca,
        "motivo": melhor_motivo,
        "revisar": confianca != "alta",
    }


def ler_confirmacoes(caminho: Path) -> dict[str, str]:
    if not caminho.exists():
        raise FileNotFoundError(caminho)
    with caminho.open(encoding="utf-8", newline="") as handle:
        leitor = csv.DictReader(handle)
        if set(leitor.fieldnames or ()) != {"documento", "estado"}:
            raise ValueError("confirmacoes de despesa com colunas inesperadas")
        mapa: dict[str, str] = {}
        for row in leitor:
            documento = row["documento"].strip()
            estado = row["estado"].strip()
            if estado != "confirmada":
                raise ValueError(f"estado de despesa inválido: {estado}")
            if documento in mapa:
                raise ValueError(f"confirmação repetida: {documento}")
            mapa[documento] = estado
        return mapa


def marcar(linhas: list[dict], obras: list[dict], confirmacoes: dict[str, str]) -> list[dict]:
    conhecidos = {linha["documento"] for linha in linhas}
    desconhecidos = sorted(set(confirmacoes) - conhecidos)
    if desconhecidos:
        raise ValueError(f"confirmação sem lançamento: {', '.join(desconhecidos)}")
    saida: list[dict] = []
    for linha in linhas:
        sugestao = sugerir(linha, obras)
        estado_arquivo = confirmacoes.get(linha["documento"])
        if estado_arquivo == "confirmada" and not sugestao["projeto_id"]:
            raise ValueError(
                f"{linha['documento']} foi confirmado sem obra sugerida ({sugestao['motivo']})"
            )
        if estado_arquivo == "confirmada":
            revisao = "confirmada"
        elif sugestao["projeto_id"]:
            revisao = "sugerida"
        else:
            revisao = "sem_vinculo"
        item = {
            **linha,
            "projeto_id": sugestao["projeto_id"],
            "confianca": sugestao["confianca"],
            "motivo": sugestao["motivo"],
            "revisar": sugestao["revisar"] or revisao != "confirmada",
            "revisao": revisao,
            "publicada": revisao == "confirmada",
        }
        if item["revisao"] != "confirmada":
            item["revisar"] = True if item["projeto_id"] or sugestao["revisar"] else False
        else:
            item["revisar"] = False
        saida.append(item)
    return sorted(saida, key=lambda item: (item["data"], item["documento"]))
