#!/usr/bin/env python3
"""Sobe o painel de demonstração com os dados fictícios de examples/.

Uso: python demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from painel.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
