"""Perguntas com citação. Sem fonte publicada, a resposta é uma recusa."""

from __future__ import annotations

import re

from painel.texto import brl, chave, data_extenso, tokens

RECUSA_PRIVACIDADE = (
    "Não respondo sobre voto de unidade, inadimplência ou dado pessoal. "
    "O painel só mostra resultado agregado e o que a gestão publicou."
)
RECUSA_JURIDICA = (
    "Não interpreto norma e não dou orientação jurídica. "
    "Só mostro trechos dos documentos publicados."
)
RECUSA_SEM_FONTE = "Não há fonte nos documentos publicados para responder isso."

_PRIVACIDADE = re.compile(
    r"inadimpl|devedor|quem votou|votou contra|votou a favor|"
    r"voto de cada|unidade\s+\d+\s+votou|\bcpf\b|"
    r"quem (registrou|abriu|reportou)",
    re.IGNORECASE,
)
_JURIDICO = re.compile(
    r"process|juridic|advogad|indeniz|ilegal",
    re.IGNORECASE,
)


def classificar_recusa(pergunta: str) -> str | None:
    base = chave(pergunta)
    if _PRIVACIDADE.search(base):
        return "privacidade"
    if _JURIDICO.search(base):
        return "juridico"
    return None


def _citacao_ata(decisao: dict) -> dict:
    return {
        "rotulo": f"{decisao['arquivo']}, página {decisao['pagina']}",
        "arquivo": decisao["arquivo"],
        "pagina": decisao["pagina"],
        "linha": None,
        "trecho": decisao["trecho"],
    }


def _citacao_despesa(linha: dict) -> dict:
    return {
        "rotulo": f"Balancete {linha['arquivo']}, {linha['documento']}, linha {linha['linha']}",
        "arquivo": linha["arquivo"],
        "pagina": None,
        "linha": linha["linha"],
        "trecho": f"{linha['historico']} ({brl(linha['valor_centavos'])})",
    }


def montar_indice(painel: dict) -> list[dict]:
    indice: list[dict] = []
    for decisao in painel["decisoes"]:
        if decisao["revisao"] != "confirmada":
            continue
        texto = " ".join(
            [
                decisao["assunto"],
                decisao["trecho"],
                decisao["resultado"],
                decisao["votacao_texto"],
                decisao["assembleia_titulo"],
            ]
        )
        indice.append(
            {
                "tipo": "decisao",
                "texto": texto,
                "citacao": _citacao_ata(decisao),
                "ref": decisao,
            }
        )
    for obra in painel["obras"]:
        for gasto in obra["gastos"]:
            texto = " ".join(
                [obra["titulo"], gasto["historico"], gasto["fornecedor"], gasto["categoria"]]
            )
            indice.append(
                {
                    "tipo": "despesa",
                    "texto": texto,
                    "citacao": _citacao_despesa(gasto),
                    "ref": gasto,
                    "obra": obra,
                }
            )
        texto_obra = " ".join(
            [
                obra["titulo"],
                obra["status_rotulo"],
                obra.get("responsavel") or "",
                obra.get("nota") or "",
            ]
        )
        indice.append(
            {
                "tipo": "obra",
                "texto": texto_obra,
                "citacao": {
                    "rotulo": f"Registro da obra {obra['titulo']}",
                    "arquivo": "obras.json",
                    "pagina": None,
                    "linha": None,
                    "trecho": obra.get("nota") or obra["status_rotulo"],
                },
                "ref": obra,
            }
        )
    for mudanca in painel["mudancas"]:
        texto = " ".join(
            [mudanca["titulo"], mudanca["antes"], mudanca["depois"], mudanca["fonte"]]
        )
        indice.append(
            {
                "tipo": "mudanca",
                "texto": texto,
                "citacao": {
                    "rotulo": mudanca["fonte"],
                    "arquivo": "mudancas.json",
                    "pagina": None,
                    "linha": None,
                    "trecho": f"Antes: {mudanca['antes']} Depois: {mudanca['depois']}",
                },
                "ref": mudanca,
            }
        )
    for ocorrencia in painel["ocorrencias"]:
        texto = " ".join(
            [
                ocorrencia["titulo"],
                ocorrencia["area"],
                ocorrencia["descricao"],
                ocorrencia["atualizacao"],
                ocorrencia["status_rotulo"],
            ]
        )
        indice.append(
            {
                "tipo": "ocorrencia",
                "texto": texto,
                "citacao": {
                    "rotulo": f"Ocorrência {ocorrencia['id']}, área comum",
                    "arquivo": "ocorrencias.json",
                    "pagina": None,
                    "linha": None,
                    "trecho": ocorrencia["descricao"],
                },
                "ref": ocorrencia,
            }
        )
    for clausula in painel.get("regimento", []):
        indice.append(
            {
                "tipo": "regimento",
                "texto": f"{clausula['titulo']} {clausula['texto']}",
                "citacao": {
                    "rotulo": f"Regimento fictício, {clausula['titulo']}",
                    "arquivo": "regimento.txt",
                    "pagina": None,
                    "linha": clausula["numero"],
                    "trecho": clausula["texto"],
                },
                "ref": clausula,
            }
        )
    return indice


def _pontuar(consulta: list[str], texto: str) -> tuple[float, list[str]]:
    if not consulta:
        return 0.0, []
    presentes = set(tokens(texto))
    acertos = [token for token in consulta if token in presentes]
    return len(acertos) / len(consulta), acertos


def identificar_obra(consulta: list[str], obras: list[dict]) -> dict | None:
    melhor = None
    melhor_acertos = 0
    for obra in obras:
        termos = [chave(termo["texto"]) for termo in obra.get("termos", [])]
        titulo = set(tokens(obra["titulo"]))
        acertos = 0
        for token in consulta:
            if len(token) < 4:
                continue
            if token in titulo or any(token in termo for termo in termos):
                acertos += 1
        if acertos > melhor_acertos:
            melhor = obra
            melhor_acertos = acertos
    return melhor


def _resposta_total(obra: dict, painel: dict) -> dict:
    linhas = [item for item in obra["gastos"] if item.get("publicada", True)]
    total = sum(item["valor_centavos"] for item in linhas)
    citacoes = []
    decisao = next((item for item in painel["decisoes"] if item["id"] == obra["decisao_id"]), None)
    if decisao and decisao["revisao"] == "confirmada":
        citacoes.append(_citacao_ata(decisao))
    citacoes.extend(_citacao_despesa(item) for item in linhas)
    if obra["orcamento_aprovado_centavos"] is None:
        abertura = f"A ata não traz valor aprovado para {obra['titulo']}."
    else:
        abertura = f"O valor aprovado para {obra['titulo']} é {brl(obra['orcamento_aprovado_centavos'])}."
    if linhas:
        meio = f"A soma confirmada é {brl(total)}, em {len(linhas)} lançamentos."
    else:
        meio = "Não há gasto confirmado nos balancetes publicados."
    return {
        "recusa": False,
        "motivo": None,
        "resposta": f"{abertura} {meio} Lançamentos ainda em revisão não entram na soma.",
        "citacoes": citacoes,
    }


def _resposta_de_bloco(bloco: dict) -> dict:
    if bloco["tipo"] == "decisao":
        decisao = bloco["ref"]
        texto = (
            f"Na {decisao['assembleia_titulo'].lower()} de {data_extenso(decisao['data'])}, "
            f"página {decisao['pagina']} de {decisao['arquivo']}, o trecho diz: \"{decisao['trecho']}\" "
            f"Resultado: {decisao['resultado']}. Votação agregada: {decisao['votacao_texto']}"
        )
    elif bloco["tipo"] == "mudanca":
        mudanca = bloco["ref"]
        texto = (
            f"Em {data_extenso(mudanca['data'])}, a gestão registrou: {mudanca['titulo']}. "
            f"Antes: {mudanca['antes']}. Depois: {mudanca['depois']}."
        )
    elif bloco["tipo"] == "regimento":
        clausula = bloco["ref"]
        texto = f"{clausula['titulo']}: {clausula['texto']}"
    elif bloco["tipo"] == "ocorrencia":
        ocorrencia = bloco["ref"]
        texto = (
            f"{ocorrencia['titulo']} ({ocorrencia['area']}) está {ocorrencia['status_rotulo'].lower()}. "
            f"{ocorrencia['atualizacao']}"
        )
    elif bloco["tipo"] == "obra":
        obra = bloco["ref"]
        texto = f"{obra['titulo']} está {obra['status_rotulo'].lower()}."
        if obra.get("nota"):
            texto = f"{texto} {obra['nota']}"
    else:
        texto = bloco["citacao"]["trecho"]
    return {
        "recusa": False,
        "motivo": None,
        "resposta": texto,
        "citacoes": [bloco["citacao"]],
    }


def responder(pergunta: str, painel: dict) -> dict:
    texto = (pergunta or "").strip()
    if not texto:
        return {
            "recusa": True,
            "motivo": "vazia",
            "resposta": "Escreva uma pergunta sobre os documentos publicados.",
            "citacoes": [],
        }
    recusa = classificar_recusa(texto)
    if recusa == "privacidade":
        return {"recusa": True, "motivo": recusa, "resposta": RECUSA_PRIVACIDADE, "citacoes": []}
    if recusa == "juridico":
        return {"recusa": True, "motivo": recusa, "resposta": RECUSA_JURIDICA, "citacoes": []}
    consulta = tokens(texto)
    base = chave(texto)
    pede_total = bool(re.search(r"quanto|gasto|gastos|realizado|confirmado|confirmados", base))
    if pede_total:
        obra = identificar_obra(consulta, painel["obras"])
        if obra:
            return _resposta_total(obra, painel)
    melhor = None
    melhor_pontos = 0.0
    melhor_acertos: list[str] = []
    for bloco in montar_indice(painel):
        pontos, acertos = _pontuar(consulta, bloco["texto"])
        if pontos > melhor_pontos:
            melhor = bloco
            melhor_pontos = pontos
            melhor_acertos = acertos
    if melhor is None or melhor_pontos < 0.5 or len(melhor_acertos) < 2:
        return {
            "recusa": True,
            "motivo": "sem_fonte",
            "resposta": RECUSA_SEM_FONTE,
            "citacoes": [],
        }
    return _resposta_de_bloco(melhor)
