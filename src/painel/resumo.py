"""Resumo mensal montado só com registros confirmados. Sem modelo de linguagem."""

from __future__ import annotations

from painel.texto import MESES, brl, data_extenso


def _frase_decisoes(competencia: str, decisoes: list[dict]) -> str:
    mes_num = int(competencia.split("-")[1])
    mes = MESES[mes_num - 1]
    ano = competencia.split("-")[0]
    do_mes = [
        item
        for item in decisoes
        if item["revisao"] == "confirmada" and item["data"].startswith(competencia)
    ]
    if do_mes:
        assuntos = "; ".join(item["assunto"] for item in do_mes)
        return f"Decisões publicadas em {mes} de {ano}: {assuntos}."
    publicadas = [item for item in decisoes if item["revisao"] == "confirmada"]
    if not publicadas:
        return f"Nenhuma assembleia com decisão publicada em {mes} de {ano}."
    ultima = max(publicadas, key=lambda item: item["data"])
    return (
        f"Nenhuma assembleia com decisão publicada em {mes} de {ano}. "
        f"A última publicada é a {ultima['assembleia_titulo'].lower()} de {data_extenso(ultima['data'])}."
    )


def _frase_obras(obras: list[dict]) -> str:
    frases = []
    for obra in obras:
        etapa = f"etapa {obra['etapa_atual']} de {obra['etapas_total']}"
        if obra["status"] == "nao_iniciada":
            frases.append(f"{obra['titulo']} não foi iniciada.")
        elif obra["status"] == "concluida":
            frases.append(f"{obra['titulo']} está concluída, {etapa}.")
        elif obra["status"] == "pausada":
            frases.append(f"{obra['titulo']} está pausada, {etapa}.")
        else:
            frases.append(f"{obra['titulo']} está em andamento, {etapa}.")
    return " ".join(frases)


def _gastos_do_mes(competencia: str, obra_id: str, despesas: list[dict]) -> list[dict]:
    return [
        item
        for item in despesas
        if item["publicada"]
        and item["projeto_id"] == obra_id
        and item["data"].startswith(competencia)
    ]


def _acumulado(obra_id: str, despesas: list[dict]) -> int:
    return sum(item["valor_centavos"] for item in despesas if item["publicada"] and item["projeto_id"] == obra_id)


def montar_resumo(
    *,
    competencia: str,
    decisoes: list[dict],
    obras: list[dict],
    despesas: list[dict],
    ocorrencias: list[dict],
) -> dict:
    mes_num = int(competencia.split("-")[1])
    mes = MESES[mes_num - 1]
    ano = competencia.split("-")[0]
    partes = [
        f"Resumo de {mes} de {ano}, montado só com registros confirmados.",
        _frase_decisoes(competencia, decisoes),
        _frase_obras(obras),
    ]
    gastos = []
    for obra in obras:
        do_mes = _gastos_do_mes(competencia, obra["id"], despesas)
        if not do_mes and obra["status"] == "concluida":
            continue
        if not do_mes and obra["status"] == "nao_iniciada":
            continue
        total_mes = sum(item["valor_centavos"] for item in do_mes)
        acumulado = _acumulado(obra["id"], despesas)
        if obra["orcamento_aprovado_centavos"] is None:
            teto = "sem valor aprovado na ata"
        else:
            teto = f"{brl(obra['orcamento_aprovado_centavos'])} aprovados"
        gastos.append(
            f"{obra['titulo']}: {brl(total_mes)} confirmados em {mes}, "
            f"acumulado {brl(acumulado)}, de {teto}."
        )
    if gastos:
        partes.append("Gastos por projeto: " + " ".join(gastos))
    else:
        partes.append("Nenhum gasto confirmado por projeto neste mês.")
    abertas = [
        item for item in ocorrencias if item["status"] in {"aberta", "em_andamento"}
    ]
    partes.append(f"Ocorrências de área comum ainda sem conclusão: {len(abertas)}.")
    partes.append("Itens em revisão do conselho ficam de fora deste texto.")
    fontes = []
    vistos = set()
    for item in decisoes:
        if item["revisao"] != "confirmada":
            continue
        chave_fonte = ("ata", item["arquivo"])
        if chave_fonte in vistos:
            continue
        vistos.add(chave_fonte)
        fontes.append({"tipo": "ata", "arquivo": item["arquivo"]})
    for item in despesas:
        if not item["publicada"] or not item["data"].startswith(competencia):
            continue
        chave_fonte = ("balancete", item["arquivo"])
        if chave_fonte in vistos:
            continue
        vistos.add(chave_fonte)
        fontes.append({"tipo": "balancete", "arquivo": item["arquivo"]})
    fontes.append({"tipo": "registro", "arquivo": "obras.json"})
    fontes.append({"tipo": "registro", "arquivo": "ocorrencias.json"})
    return {
        "competencia": competencia,
        "texto": " ".join(partes),
        "fontes": fontes,
    }
