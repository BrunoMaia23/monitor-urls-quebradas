"""URLs antigas depois da migração de um site: status, prioridade por tráfego e redirect sugerido."""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from . import fontes, sitemap, sugestao, verificacao
from .site_falso import SiteFalso

MARCADOR = ".monitor-demo"
QUEBRADAS = (verificacao.QUEBRADA,)
ORDEM = [verificacao.OK, verificacao.REDIRECIONA, verificacao.CADEIA_LONGA, verificacao.QUEBRADA,
         verificacao.ERRO, verificacao.LOOP]


def _numero(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def monitorar(base: str, exportacoes: list[Path], url_sitemap: str, saida: Path) -> dict:
    trafego = fontes.ler(exportacoes)
    print(f"[fontes]      {len(exportacoes)} exportações, {len(trafego)} páginas antigas, "
          f"{_numero(sum(trafego.values()))} acessos no período")
    atuais = sitemap.ler(url_sitemap)
    print(f"[sitemap]     {len(atuais)} URLs atuais")
    resultados = verificacao.verificar_todos(base, sorted(trafego))
    contagem = Counter(r.situacao for r in resultados)
    print("[verificação] " + " | ".join(f"{s.replace('_', ' ')} {contagem[s]}" for s in ORDEM if contagem[s]))

    quebradas = sorted((r for r in resultados if r.situacao in QUEBRADAS), key=lambda r: (-trafego[r.caminho], r.caminho))
    sugestoes = {r.caminho: sugestao.sugerir(r.caminho, atuais) for r in quebradas}
    print("[prioridade]  quebradas, da mais acessada para a menos:")
    for r in quebradas:
        s = sugestoes[r.caminho]
        alvo = f"-> {s.destino} ({str(s.nota).replace('.', ',')}, {s.confianca})" if s.destino else "sem sugestão"
        print(f"   {_numero(trafego[r.caminho]):>6}  {r.caminho:<42} {alvo}")
        if r.saltos:
            print(f"{'':<11}o redirect atual leva a {r.destino}, que não existe")
    for r in resultados:
        if r.situacao == verificacao.CADEIA_LONGA:
            print(f"   atenção: {r.caminho} chega em {r.destino} depois de {r.saltos} redirects")
        elif r.situacao == verificacao.LOOP:
            print(f"   atenção: {r.caminho} entra em loop de redirect")
        elif r.situacao == verificacao.ERRO:
            print(f"   atenção: {r.caminho} responde com erro ({r.status or r.detalhe})")

    saida.mkdir(parents=True, exist_ok=True)
    _csv(saida / "urls_validadas.csv",
         [{"caminho": r.caminho, "acessos": trafego[r.caminho], "situacao": r.situacao, "status": r.status,
           "destino": r.destino or "", "saltos": r.saltos, "detalhe": r.detalhe} for r in resultados])
    _csv(saida / "redirects_sugeridos.csv",
         [{"quebrada": s.quebrada, "acessos": trafego[s.quebrada], "destino": s.destino or "", "nota": s.nota,
           "confianca": s.confianca} for s in sugestoes.values()])
    (saida / "redirects_nginx.conf").write_text(sugestao.nginx(list(sugestoes.values())), encoding="utf-8")
    confiantes = sum(s.confianca == "redirect" for s in sugestoes.values())
    revisar = sum(s.confianca == "revisar" for s in sugestoes.values())
    historico = saida / "historico.csv"
    linha = {"executado_em": datetime.now().isoformat(timespec="seconds"), "paginas": len(resultados),
             **{s: contagem[s] for s in ORDEM}, "redirect_sugerido": confiantes, "para_revisar": revisar}
    novo = not historico.exists()
    with open(historico, "a", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linha))
        if novo:
            escritor.writeheader()
        escritor.writerow(linha)
    print(f"[saída]       urls_validadas.csv, redirects_sugeridos.csv, redirects_nginx.conf "
          f"({confiantes} redirects, {revisar} para revisar) e uma linha a mais em historico.csv")
    return {"contagem": contagem, "confiantes": confiantes, "revisar": revisar}


def _csv(caminho: Path, linhas: list[dict]) -> None:
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        if linhas:
            escritor = csv.DictWriter(f, fieldnames=list(linhas[0]))
            escritor.writeheader()
            escritor.writerows(linhas)


def _exportacoes(pasta: Path) -> list[Path]:
    analise = [("Página", "Visualizações"), ("/institucional/quem-somos.html", 640),
               ("/noticias/2019/festival-de-inverno.php", 410), ("/agenda/feira-artesanato", 220),
               ("/noticias/2018/oficina-violao.html", 980), ("/noticias/2020/inauguracao-nova-sede.php", 530),
               ("/sobre/nossa-historia.html", 260), ("/eventos/2017/sarau-poesia", 190),
               ("/servicos/2via.php", 870), ("/cadastro/atualizar.php", 150), ("/promocao-de-natal-2016", 60),
               ("/contato", 300), ("/noticias", 120)]
    busca = [("page", "clicks"), ("https://www.example.org/noticias/2018/oficina-violao.html", 120),
             ("https://www.example.org/busca?q=boleto", 90), ("https://www.example.org/loop-a", 40),
             ("https://www.example.org/servicos/2via.php", 30)]
    arquivos = []
    for nome, linhas in (("exportacao_analytics.csv", analise), ("exportacao_search_console.csv", busca)):
        with open(pasta / nome, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(linhas)
        arquivos.append(pasta / nome)
    return arquivos


def demo(pasta: Path) -> int:
    if pasta.exists():
        if not (pasta / MARCADOR).exists():
            print(f"A pasta {pasta} já existe e não foi criada pela demo; escolha outra com --pasta.")
            return 2
        shutil.rmtree(pasta)
    pasta.mkdir(parents=True)
    (pasta / MARCADOR).write_text("pasta da demo do monitor\n", encoding="utf-8")
    with SiteFalso() as site:
        print("[site]        site novo de mentira num servidor local\n")
        r = monitorar(site.url, _exportacoes(pasta), f"{site.url}/sitemap.xml", pasta / "saida")
    return 0 if (r["contagem"][verificacao.QUEBRADA], r["confiantes"], r["revisar"]) == (7, 4, 2) else 1


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="monitor-urls", description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)
    p = sub.add_parser("demo", help="roda contra um site de mentira num servidor local")
    p.add_argument("--pasta", type=Path, default=Path("demo"))
    p = sub.add_parser("verificar", help="verifica as páginas das exportações contra o site")
    p.add_argument("--base", required=True, help="endereço do site, ex.: https://www.example.org")
    p.add_argument("--sitemap", required=True)
    p.add_argument("--saida", type=Path, default=Path("saida"))
    p.add_argument("exportacoes", type=Path, nargs="+")
    a = parser.parse_args(argv)
    if a.comando == "demo":
        return demo(a.pasta)
    monitorar(a.base, a.exportacoes, a.sitemap, a.saida)
    return 0
