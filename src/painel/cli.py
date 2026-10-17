"""Linha de comando da demo."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from painel.llm import carregar_env, extrair_com_modelo
from painel.pipeline import executar
from painel.servidor import servir

RAIZ = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Painel do condomínio, demo com dados fictícios")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-serve", action="store_true", help="só gera examples/saida e encerra")
    parser.add_argument(
        "--llm",
        action="store_true",
        help="também chama um modelo e grava a resposta bruta, sem publicar",
    )
    args = parser.parse_args(argv)
    carregar_env(RAIZ / ".env")
    if args.llm or os.environ.get("PAINEL_MODO", "").strip().lower() == "llm":
        extrair_com_modelo(RAIZ)
        print("Resposta bruta do modelo em examples/saida/llm-decisoes.bruto.txt")
        print("O painel publicado continua sendo o modo determinístico.")
    painel = executar(RAIZ)
    obras = len(painel["obras"])
    decisoes = len(painel["decisoes"])
    print(f"Saída em {RAIZ / 'examples' / 'saida'}")
    print(f"{decisoes} decisões, {obras} obras, dados fictícios")
    if args.no_serve:
        return 0
    servir(painel, args.host, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
