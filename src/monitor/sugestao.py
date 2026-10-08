"""Para cada URL quebrada, a URL atual mais parecida, com uma nota de 0 a 1.

A comparação é pelas palavras do caminho, sem acento, sem número e sem extensão (".php", ".html").
Palavra parecida conta como igual ("cadastro" e "cadastral"), e a última palavra do caminho antigo, que
costuma ser o "nome" da página, pesa mais. Nota alta vira sugestão de redirect; nota média vai para
revisão de alguém; nota baixa fica sem sugestão, porque um redirect errado é pior que um 404.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

CONFIANTE = 0.75
REVISAR = 0.5
PARECIDA = 0.8
VAZIAS = {"de", "da", "do", "e", "a", "o", "em", "no", "na", "index", "pagina", "www", "html", "php", "aspx"}


@dataclass(frozen=True)
class Sugestao:
    quebrada: str
    destino: str | None
    nota: float
    confianca: str  # redirect, revisar, sem_sugestao


def palavras(caminho: str) -> list[str]:
    texto = unicodedata.normalize("NFKD", caminho.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\.(php|html?|aspx?)$", "", texto)
    return [p for p in re.findall(r"[a-z]+", texto) if p not in VAZIAS and len(p) > 1]


def _parecida(palavra: str, outras: list[str]) -> float:
    return max(SequenceMatcher(None, palavra, o).ratio() for o in outras)


def nota(quebrada: str, atual: str) -> float:
    a, b = list(dict.fromkeys(palavras(quebrada))), list(dict.fromkeys(palavras(atual)))
    if not a or not b:
        return 0.0
    casadas = sum(1 for p in a if _parecida(p, b) >= PARECIDA)
    semelhanca = casadas / (len(a) + len(b) - casadas)
    return round(0.6 * semelhanca + 0.4 * _parecida(a[-1], b), 2)


def sugerir(quebrada: str, atuais: set[str]) -> Sugestao:
    candidatos = sorted(((nota(quebrada, a), a) for a in atuais), key=lambda na: (-na[0], na[1]))
    if not candidatos or candidatos[0][0] < REVISAR:
        return Sugestao(quebrada, None, candidatos[0][0] if candidatos else 0.0, "sem_sugestao")
    melhor, destino = candidatos[0]
    return Sugestao(quebrada, destino, melhor, "redirect" if melhor >= CONFIANTE else "revisar")


def nginx(sugestoes: list[Sugestao]) -> str:
    """As sugestões confiantes no formato de um map do nginx, prontas para alguém revisar e aplicar."""
    linhas = ["# gerado pelo monitor-urls-quebradas: revisar antes de aplicar", "map $uri $novo_destino {"]
    linhas += [f"    {s.quebrada} {s.destino};" for s in sugestoes if s.confianca == "redirect"]
    return "\n".join(linhas + ["}"]) + "\n"
