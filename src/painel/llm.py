"""Modo opcional com modelo de linguagem.

Não roda na demo. Não publica no painel. A saída, se alguém chamar,
fica num arquivo bruto para uma pessoa comparar com o modo determinístico.
O fornecedor e o modelo de um piloto são [A CONFIRMAR].
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path


def carregar_env(caminho: Path) -> None:
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave = chave.strip()
        valor = valor.strip().strip('"').strip("'")
        if chave and chave not in os.environ:
            os.environ[chave] = valor


def modo_configurado(env: dict | None = None) -> str:
    ambiente = env if env is not None else os.environ
    modo = ambiente.get("PAINEL_MODO", "deterministico").strip().lower()
    if modo in {"", "deterministico"}:
        return "deterministico"
    if modo == "llm":
        return "llm"
    raise ValueError(f"PAINEL_MODO desconhecido: {modo}")


def exigir_llm(env: dict | None = None) -> tuple[str, str, str]:
    ambiente = env if env is not None else os.environ
    faltando = [
        nome
        for nome in ("PAINEL_LLM_API_KEY", "PAINEL_LLM_MODEL", "PAINEL_LLM_BASE_URL")
        if not ambiente.get(nome, "").strip()
    ]
    if faltando:
        raise SystemExit("Modo com modelo sem configuração: " + ", ".join(faltando))
    return (
        ambiente["PAINEL_LLM_API_KEY"].strip(),
        ambiente["PAINEL_LLM_MODEL"].strip(),
        ambiente["PAINEL_LLM_BASE_URL"].strip(),
    )


def chamar_chat(base_url: str, api_key: str, model: str, system: str, user: str, timeout: int = 60) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    corpo = json.dumps(
        {
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
    ).encode("utf-8")
    pedido = urllib.request.Request(
        url,
        data=corpo,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))
    return dados["choices"][0]["message"]["content"]


def extrair_com_modelo(raiz: Path, env: dict | None = None) -> Path:
    """Chama o modelo e grava a resposta bruta. Não altera o painel publicado."""
    chave, model, base = exigir_llm(env)
    prompt = (raiz / "prompts" / "extrair-decisoes.md").read_text(encoding="utf-8")
    atas = []
    for txt in sorted((raiz / "examples" / "atas").glob("*.txt")):
        atas.append(f"\n\n# {txt.name}\n" + txt.read_text(encoding="utf-8"))
    bruto = chamar_chat(base, chave, model, prompt, "".join(atas))
    destino = raiz / "examples" / "saida" / "llm-decisoes.bruto.txt"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(bruto, encoding="utf-8")
    return destino
