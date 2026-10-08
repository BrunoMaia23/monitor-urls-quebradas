"""As URLs atuais do site, pelo sitemap (inclusive sitemap índice, que aponta para outros)."""
from __future__ import annotations

import xml.etree.ElementTree as ET

import requests

from .fontes import caminho

NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _baixar(url: str) -> bytes:
    resposta = requests.get(url, timeout=30)
    resposta.raise_for_status()
    return resposta.content


def ler(url: str, limite_de_arquivos: int = 50, baixar=_baixar) -> set[str]:
    caminhos: set[str] = set()
    pendentes, lidos = [url], 0
    while pendentes and lidos < limite_de_arquivos:
        raiz = ET.fromstring(baixar(pendentes.pop(0)))
        lidos += 1
        if raiz.tag.endswith("sitemapindex"):
            pendentes += [loc.text.strip() for loc in raiz.iterfind("s:sitemap/s:loc", NS)]
        else:
            caminhos |= {caminho(loc.text) for loc in raiz.iterfind("s:url/s:loc", NS)}
    return caminhos
