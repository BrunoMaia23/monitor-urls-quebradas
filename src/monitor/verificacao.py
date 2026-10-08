"""Status de cada URL, seguindo os redirects um a um para ver a cadeia inteira.

Seguir o redirect por conta própria, em vez de deixar a biblioteca fazer, é o que permite separar:
redirect que chega numa página (ok), cadeia longa (funciona, mas cada salto custa), loop, e redirect
que termina numa página quebrada.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import requests

OK, REDIRECIONA, CADEIA_LONGA, QUEBRADA, ERRO, LOOP = (
    "ok", "redireciona", "cadeia_longa", "quebrada", "erro", "loop")


@dataclass(frozen=True)
class Resultado:
    caminho: str
    situacao: str
    status: int | None
    destino: str | None = None
    saltos: int = 0
    detalhe: str = ""


def verificar(sessao: requests.Session, base: str, caminho: str, max_saltos: int = 5, timeout: float = 10) -> Resultado:
    url = urljoin(base, caminho)
    vistos = {url}
    for saltos in range(max_saltos + 1):
        try:
            resposta = sessao.head(url, allow_redirects=False, timeout=timeout)
            if resposta.status_code == 405:  # servidor que não aceita HEAD
                resposta = sessao.get(url, allow_redirects=False, timeout=timeout)
        except requests.RequestException as exc:
            return Resultado(caminho, ERRO, None, detalhe=type(exc).__name__)
        status = resposta.status_code
        if 300 <= status < 400 and "Location" in resposta.headers:
            url = urljoin(url, resposta.headers["Location"])
            if url in vistos:
                return Resultado(caminho, LOOP, status, urlsplit(url).path, saltos + 1)
            vistos.add(url)
            continue
        destino = urlsplit(url).path
        if status >= 500:
            return Resultado(caminho, ERRO, status, destino, saltos)
        if status >= 400:
            return Resultado(caminho, QUEBRADA, status, destino, saltos, "redirect para página quebrada" if saltos else "")
        situacao = OK if saltos == 0 else REDIRECIONA if saltos == 1 else CADEIA_LONGA
        return Resultado(caminho, situacao, status, destino if saltos else None, saltos)
    return Resultado(caminho, LOOP, None, detalhe=f"mais de {max_saltos} saltos")


def verificar_todos(base: str, caminhos: list[str], paralelo: int = 8) -> list[Resultado]:
    with requests.Session() as sessao, ThreadPoolExecutor(max_workers=paralelo) as pool:
        return list(pool.map(lambda c: verificar(sessao, base, c), caminhos))
