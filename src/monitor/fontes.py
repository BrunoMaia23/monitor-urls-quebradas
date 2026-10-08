"""As URLs antigas que ainda recebem visita, a partir das exportações das ferramentas de análise.

Cada ferramenta exporta com o seu cabeçalho (página, page, url; acessos, cliques, views...). A leitura
reconhece as variações, guarda só o caminho e soma o tráfego da mesma página vinda de fontes diferentes:
é esse número que define a ordem de correção.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

COLUNAS_PAGINA = ("pagina", "página", "page", "url", "landing page", "caminho")
COLUNAS_TRAFEGO = ("acessos", "cliques", "clicks", "views", "visualizacoes", "visualizações", "sessoes", "sessões")


def caminho(endereco: str) -> str:
    """Só o caminho: sem domínio, sem query, sem barra no fim (menos na raiz)."""
    partes = urlsplit(endereco.strip())
    c = partes.path or "/"
    return c.rstrip("/") or "/"


def ler(arquivos: list[Path]) -> Counter:
    trafego: Counter = Counter()
    for arquivo in arquivos:
        with open(arquivo, encoding="utf-8-sig", newline="") as f:
            leitor = csv.DictReader(f)
            nomes = {n.strip().lower(): n for n in leitor.fieldnames or []}
            pagina = next((nomes[c] for c in COLUNAS_PAGINA if c in nomes), None)
            numero = next((nomes[c] for c in COLUNAS_TRAFEGO if c in nomes), None)
            if pagina is None:
                raise ValueError(f"{arquivo.name}: nenhuma coluna de página ({', '.join(COLUNAS_PAGINA)})")
            for linha in leitor:
                if linha[pagina]:
                    trafego[caminho(linha[pagina])] += int(float(linha[numero] or 0)) if numero else 0
    return trafego
