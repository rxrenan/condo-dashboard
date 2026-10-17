"""Servidor local da demo. Só escuta em loopback, sem credencial."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from painel.perguntas import responder
from painel.pipeline import para_cliente

WEB = Path(__file__).resolve().parent / "web"
MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
}


def criar_servidor(painel: dict, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, formato: str, *args) -> None:
            return

        def _enviar(self, codigo: int, corpo: bytes, content_type: str) -> None:
            self.send_response(codigo)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def _json(self, codigo: int, dados) -> None:
            corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
            self._enviar(codigo, corpo, "application/json; charset=utf-8")

        def _estatico(self, caminho: str) -> None:
            rel = caminho.lstrip("/") or "index.html"
            raiz = WEB.resolve()
            alvo = (raiz / rel).resolve()
            if not str(alvo).startswith(str(raiz)) or not alvo.is_file():
                self._enviar(404, "não encontrado".encode("utf-8"), "text/plain; charset=utf-8")
                return
            self._enviar(200, alvo.read_bytes(), MIME.get(alvo.suffix, "application/octet-stream"))

        def do_GET(self) -> None:
            url = urlparse(self.path)
            if url.path == "/api/saude":
                self._json(200, {"ok": True, "modo": "deterministico"})
                return
            if url.path == "/api/painel":
                visao = parse_qs(url.query).get("visao", ["morador"])[0]
                if visao not in {"morador", "conselho"}:
                    self._json(400, {"erro": "visão desconhecida"})
                    return
                self._json(200, para_cliente(painel, visao))
                return
            if url.path.startswith("/api/"):
                self._json(404, {"erro": "não encontrado"})
                return
            self._estatico(url.path)

        def do_POST(self) -> None:
            url = urlparse(self.path)
            if url.path != "/api/perguntas":
                self._json(404, {"erro": "não encontrado"})
                return
            tamanho = int(self.headers.get("Content-Length", "0") or 0)
            if tamanho > 4000:
                self._json(413, {"erro": "pergunta longa demais"})
                return
            try:
                corpo = json.loads(self.rfile.read(tamanho).decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json(400, {"erro": "json inválido"})
                return
            self._json(200, responder(str(corpo.get("pergunta", "")), painel))

    return ThreadingHTTPServer((host, port), Handler)


def servir(painel: dict, host: str = "127.0.0.1", port: int = 8765) -> None:
    servidor = criar_servidor(painel, host, port)
    porta = servidor.server_address[1]
    print("Painel do condomínio (demo, dados fictícios)")
    print(f"http://{host}:{porta}")
    print("Modo: determinístico, sem chave de modelo")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nencerrado")
    finally:
        servidor.server_close()
