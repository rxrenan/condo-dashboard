"""Junta ata, balancete, obras, ocorrências e mudanças num único painel."""

from __future__ import annotations

import copy
import csv
import json
import re
from pathlib import Path

from painel.despesas import ler_balancetes, ler_confirmacoes, marcar
from painel.extrair import extrair_pasta, texto_publicado_de_atas
from painel.mascara import mascarar
from painel.pdfutil import garantir_pdfs
from painel.resumo import montar_resumo
from painel.texto import STATUS_OBRA, STATUS_OCORRENCIA, brl

CAMPOS_PROIBIDOS = {"relator", "autor", "unidade", "cpf", "nome", "morador", "votante"}
CLAUSULA = re.compile(
    r"CLÁUSULA\s+(\d+)\.\s*(.+?)\n(.+?)(?=\nCLÁUSULA\s+\d+\.|\Z)",
    re.DOTALL,
)


def ler_json(caminho: Path):
    return json.loads(caminho.read_text(encoding="utf-8"))


def escrever(caminho: Path, dados) -> None:
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _ler_revisao_decisoes(caminho: Path) -> dict[str, str]:
    with caminho.open(encoding="utf-8", newline="") as handle:
        leitor = csv.DictReader(handle)
        if set(leitor.fieldnames or ()) != {"id", "estado"}:
            raise ValueError("revisao/decisoes.csv com colunas inesperadas")
        mapa: dict[str, str] = {}
        for row in leitor:
            identificador = row["id"].strip()
            estado = row["estado"].strip()
            if estado not in {"confirmada", "pendente"}:
                raise ValueError(f"estado de decisão inválido: {estado}")
            if identificador in mapa:
                raise ValueError(f"revisão repetida: {identificador}")
            mapa[identificador] = estado
        return mapa


def _validar_ocorrencia(item: dict) -> dict:
    proibidos = CAMPOS_PROIBIDOS.intersection(item)
    if proibidos:
        raise ValueError(f"ocorrência com campo pessoal: {', '.join(sorted(proibidos))}")
    if item["status"] not in STATUS_OCORRENCIA:
        raise ValueError(f"status de ocorrência inválido: {item['status']}")
    item = dict(item)
    item["status_rotulo"] = STATUS_OCORRENCIA[item["status"]]
    item["titulo"] = mascarar(item["titulo"])
    item["descricao"] = mascarar(item["descricao"])
    item["atualizacao"] = mascarar(item["atualizacao"])
    return item


def _ler_regimento(caminho: Path) -> list[dict]:
    texto = caminho.read_text(encoding="utf-8").strip()
    clausulas = []
    for numero, titulo, corpo in CLAUSULA.findall(texto):
        clausulas.append(
            {
                "numero": int(numero),
                "titulo": f"Cláusula {numero}. {titulo.strip()}",
                "texto": mascarar(re.sub(r"\s+", " ", corpo).strip()),
            }
        )
    if not clausulas:
        raise ValueError("regimento sem cláusulas")
    return clausulas


def _aplicar_revisao(decisoes: list[dict], revisao: dict[str, str]) -> list[dict]:
    ids = {item["id"] for item in decisoes}
    faltando = sorted(ids - set(revisao))
    sobrando = sorted(set(revisao) - ids)
    if faltando:
        raise ValueError("decisão sem revisão do conselho: " + ", ".join(faltando))
    if sobrando:
        raise ValueError("revisão sem decisão: " + ", ".join(sobrando))
    saida = []
    for item in decisoes:
        copia = dict(item)
        copia["revisao"] = revisao[item["id"]]
        copia["trecho"] = mascarar(copia["trecho"])
        copia["assunto"] = mascarar(copia["assunto"])
        saida.append(copia)
    return saida


def _montar_obras(obras: list[dict], decisoes: list[dict], despesas: list[dict]) -> list[dict]:
    por_id = {item["id"]: item for item in decisoes}
    usadas: set[str] = set()
    montadas = []
    for bruta in obras:
        if bruta["status"] not in STATUS_OBRA:
            raise ValueError(f"status de obra inválido: {bruta['status']}")
        decisao = por_id.get(bruta["decisao_id"])
        if not decisao:
            raise ValueError(f"{bruta['id']} aponta para decisão inexistente")
        if decisao["revisao"] != "confirmada":
            raise ValueError(f"{bruta['id']} aponta para decisão ainda não confirmada")
        if bruta["decisao_id"] in usadas:
            raise ValueError(f"decisão vinculada a mais de uma obra: {bruta['decisao_id']}")
        usadas.add(bruta["decisao_id"])
        citado = decisao["valor_aprovado_centavos"]
        registrado = bruta["orcamento_aprovado_centavos"]
        if citado != registrado:
            raise ValueError(
                f"orçamento de {bruta['id']} ({registrado}) diverge da ata ({citado})"
            )
        gastos = [item for item in despesas if item["publicada"] and item["projeto_id"] == bruta["id"]]
        sugestoes = [
            item
            for item in despesas
            if item["revisao"] == "sugerida" and item["projeto_id"] == bruta["id"]
        ]
        realizado = sum(item["valor_centavos"] for item in gastos)
        obra = {
            "id": bruta["id"],
            "titulo": bruta["titulo"],
            "status": bruta["status"],
            "status_rotulo": STATUS_OBRA[bruta["status"]],
            "etapa_atual": bruta["etapa_atual"],
            "etapas_total": bruta["etapas_total"],
            "etapas": bruta["etapas"],
            "responsavel": bruta["responsavel"],
            "orcamento_aprovado_centavos": registrado,
            "orcamento_aprovado_texto": brl(registrado) if registrado is not None else "Sem valor aprovado",
            "realizado_centavos": realizado,
            "realizado_texto": brl(realizado),
            "decisao_id": bruta["decisao_id"],
            "decisao": {
                "id": decisao["id"],
                "assembleia": decisao["assembleia"],
                "assembleia_titulo": decisao["assembleia_titulo"],
                "data": decisao["data"],
                "pagina": decisao["pagina"],
                "arquivo": decisao["arquivo"],
                "assunto": decisao["assunto"],
                "trecho": decisao["trecho"],
                "resultado": decisao["resultado"],
                "resultado_rotulo": decisao["resultado_rotulo"],
                "votacao": decisao["votacao"],
                "votacao_texto": decisao["votacao_texto"],
                "revisao": decisao["revisao"],
            },
            "gastos": gastos,
            "sugestoes": sugestoes,
            "sugestoes_ocultas": len(sugestoes),
            "fotos": bruta.get("fotos", []),
            "nota": bruta.get("nota"),
            "termos": bruta["termos"],
        }
        montadas.append(obra)
    return montadas


def _rotulo_execucao(decisao: dict, obras: list[dict]) -> tuple[str, str]:
    if decisao["revisao"] == "pendente":
        return "aguardando_revisao", "Aguardando revisão"
    if decisao["resultado"] == "rejeitado":
        return "rejeitada", "Rejeitada"
    obra = next((item for item in obras if item["decisao_id"] == decisao["id"]), None)
    if not obra:
        return "sem_obra", "Sem obra vinculada"
    return obra["status"], obra["status_rotulo"]


def executar(raiz: Path, saida: Path | None = None) -> dict:
    raiz = raiz.resolve()
    exemplos = raiz / "examples"
    destino = (saida or (exemplos / "saida")).resolve()
    destino.mkdir(parents=True, exist_ok=True)

    garantir_pdfs(exemplos / "atas")
    decisoes = _aplicar_revisao(
        extrair_pasta(exemplos / "atas"),
        _ler_revisao_decisoes(exemplos / "revisao" / "decisoes.csv"),
    )
    obras_brutas = ler_json(exemplos / "obras.json")
    despesas = marcar(
        ler_balancetes(exemplos / "balancetes"),
        obras_brutas,
        ler_confirmacoes(exemplos / "revisao" / "despesas.csv"),
    )
    ocorrencias = [_validar_ocorrencia(item) for item in ler_json(exemplos / "ocorrencias.json")]
    mudancas = ler_json(exemplos / "mudancas.json")
    regimento = _ler_regimento(exemplos / "regimento.txt")
    condominio = ler_json(exemplos / "condominio.json")
    perguntas = ler_json(exemplos / "perguntas.json")

    obras = _montar_obras(obras_brutas, decisoes, despesas)
    for decisao in decisoes:
        codigo, rotulo = _rotulo_execucao(decisao, obras)
        decisao["execucao"] = codigo
        decisao["execucao_rotulo"] = rotulo

    resumo = montar_resumo(
        competencia=condominio["competencia_resumo"],
        decisoes=decisoes,
        obras=obras,
        despesas=despesas,
        ocorrencias=ocorrencias,
    )
    sugestoes = [item for item in despesas if item["revisao"] == "sugerida"]
    revisar = [item for item in despesas if item["revisao"] == "sem_vinculo" and item["revisar"]]
    painel = {
        "meta": {
            "produto": "Painel do condomínio",
            "condominio": condominio["nome"],
            "aviso": condominio["aviso"],
            "atualizado_em": condominio["atualizado_em"],
            "modo": "deterministico",
            "competencia_resumo": condominio["competencia_resumo"],
            "visao": "conselho",
        },
        "resumo": resumo,
        "obras": obras,
        "decisoes": decisoes,
        "ocorrencias": ocorrencias,
        "mudancas": mudancas,
        "regimento": regimento,
        "sugestoes_despesas": sugestoes,
        "revisar_despesas": revisar,
        "perguntas_exemplo": perguntas,
    }
    escrever(destino / "decisoes.json", decisoes)
    escrever(destino / "despesas.json", despesas)
    escrever(destino / "resumo-mensal.json", resumo)
    escrever(destino / "atas-texto.json", texto_publicado_de_atas(exemplos / "atas"))
    escrever(destino / "painel.json", painel)
    return painel


def filtrar_visao(painel: dict, visao: str) -> dict:
    if visao not in {"morador", "conselho"}:
        raise ValueError(f"visão desconhecida: {visao}")
    copia = copy.deepcopy(painel)
    copia["meta"]["visao"] = visao
    if visao == "conselho":
        return copia
    copia["decisoes"] = [item for item in copia["decisoes"] if item["revisao"] == "confirmada"]
    for obra in copia["obras"]:
        obra["sugestoes"] = []
    copia["sugestoes_despesas"] = []
    copia["revisar_despesas"] = []
    return copia


def para_cliente(painel: dict, visao: str) -> dict:
    copia = filtrar_visao(painel, visao)
    for obra in copia["obras"]:
        obra.pop("termos", None)
    return copia
