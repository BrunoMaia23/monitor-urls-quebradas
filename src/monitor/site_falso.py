"""Um site novo de mentira, em HTTP local, para a demo e os testes.

Tem de tudo que aparece depois de uma migração: redirect certo, redirect em cadeia, redirect em loop,
página antiga que sumiu, redirect que leva para página que também sumiu, e erro de servidor.
"""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PAGINAS_NOVAS = ["/", "/noticias", "/noticias/festival-de-inverno", "/noticias/oficina-de-violao",
                 "/noticias/nova-sede-inaugurada", "/eventos/feira-de-artesanato", "/eventos/sarau-de-poesia",
                 "/sobre/quem-somos", "/sobre/historia", "/servicos/segunda-via-de-boleto",
                 "/servicos/atualizacao-cadastral", "/contato"]
REDIRECTS = {
    "/institucional/quem-somos.html": "/sobre/quem-somos",
    "/noticias/2019/festival-de-inverno.php": "/noticias/festival-de-inverno",
    "/agenda/feira-artesanato": "/eventos/feira-artesanato",          # 1º salto de uma cadeia
    "/eventos/feira-artesanato": "/eventos/feira-de-artesanato",       # 2º salto
    "/loop-a": "/loop-b",
    "/loop-b": "/loop-a",
    "/servicos/2via.php": "/servicos/segunda-via",                     # leva para página que sumiu
}
COM_ERRO = {"/busca"}


class SiteFalso:
    def __init__(self):
        site = self

        class Tratador(BaseHTTPRequestHandler):
            def do_HEAD(self):
                self._responder(corpo=False)

            def do_GET(self):
                self._responder(corpo=True)

            def _responder(self, corpo: bool):
                caminho = self.path.split("?")[0].rstrip("/") or "/"
                if caminho == "/sitemap.xml":
                    return self._enviar(200, site.sitemap().encode(), "application/xml", corpo)
                if caminho in REDIRECTS:
                    self.send_response(301)
                    self.send_header("Location", REDIRECTS[caminho])
                    self.end_headers()
                    return None
                if caminho in COM_ERRO:
                    return self._enviar(500, b"erro", "text/plain", corpo)
                if caminho in PAGINAS_NOVAS:
                    return self._enviar(200, b"<html>ok</html>", "text/html", corpo)
                return self._enviar(404, b"nao encontrada", "text/plain", corpo)

            def _enviar(self, status, dados, tipo, corpo):
                self.send_response(status)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                if corpo:
                    self.wfile.write(dados)

            def log_message(self, *args):
                pass

        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), Tratador)
        self.url = f"http://127.0.0.1:{self.servidor.server_address[1]}"
        self._thread = threading.Thread(target=self.servidor.serve_forever, daemon=True)

    def sitemap(self) -> str:
        urls = "".join(f"<url><loc>{self.url}{p}</loc></url>" for p in PAGINAS_NOVAS)
        return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self.servidor.shutdown()
        self.servidor.server_close()
