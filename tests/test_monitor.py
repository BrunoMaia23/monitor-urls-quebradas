import csv
import socket

import pytest
import requests

from monitor import cli, fontes, sitemap, sugestao, verificacao
from monitor.site_falso import SiteFalso


@pytest.fixture(scope="module")
def site():
    with SiteFalso() as s:
        yield s


def _csv(caminho, linhas):
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(linhas)
    return caminho


def test_exportacoes_com_cabecalhos_diferentes_somam_trafego(tmp_path):
    a = _csv(tmp_path / "a.csv", [("Página", "Visualizações"), ("/noticias/x.html", 10), ("/contato/", 5)])
    b = _csv(tmp_path / "b.csv", [("page", "clicks"), ("https://www.example.org/noticias/x.html?utm=1", 3)])
    assert fontes.ler([a, b]) == {"/noticias/x.html": 13, "/contato": 5}
    sem_pagina = _csv(tmp_path / "c.csv", [("coluna", "valor"), ("x", 1)])
    with pytest.raises(ValueError, match="coluna de página"):
        fontes.ler([sem_pagina])


@pytest.mark.parametrize("caminho, situacao, status, destino, saltos", [
    ("/contato", verificacao.OK, 200, None, 0),
    ("/institucional/quem-somos.html", verificacao.REDIRECIONA, 200, "/sobre/quem-somos", 1),
    ("/agenda/feira-artesanato", verificacao.CADEIA_LONGA, 200, "/eventos/feira-de-artesanato", 2),
    ("/pagina-que-sumiu", verificacao.QUEBRADA, 404, "/pagina-que-sumiu", 0),
    ("/servicos/2via.php", verificacao.QUEBRADA, 404, "/servicos/segunda-via", 1),
    ("/busca", verificacao.ERRO, 500, "/busca", 0),
    ("/loop-a", verificacao.LOOP, 301, "/loop-a", 2),
])
def test_verificacao(site, caminho, situacao, status, destino, saltos):
    with requests.Session() as sessao:
        r = verificacao.verificar(sessao, site.url, caminho)
    assert (r.situacao, r.status, r.destino, r.saltos) == (situacao, status, destino, saltos)


def test_site_fora_do_ar_e_erro_e_nao_excecao():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta = s.getsockname()[1]  # porta livre, ninguém escutando
    with requests.Session() as sessao:
        r = verificacao.verificar(sessao, f"http://127.0.0.1:{porta}", "/x", timeout=2)
    assert r.situacao == verificacao.ERRO and r.status is None and r.detalhe


def test_sitemap_simples_e_indice(site):
    assert "/sobre/historia" in sitemap.ler(f"{site.url}/sitemap.xml")
    ns = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
    arquivos = {
        "indice": f"<sitemapindex {ns}><sitemap><loc>p1</loc></sitemap><sitemap><loc>p2</loc></sitemap></sitemapindex>",
        "p1": f"<urlset {ns}><url><loc>https://www.example.org/a/</loc></url></urlset>",
        "p2": f"<urlset {ns}><url><loc>https://www.example.org/b</loc></url></urlset>",
    }
    assert sitemap.ler("indice", baixar=lambda u: arquivos[u].encode()) == {"/a", "/b"}


@pytest.mark.parametrize("quebrada, atual, minimo, maximo", [
    ("/noticias/2018/oficina-violao.html", "/noticias/oficina-de-violao", 1.0, 1.0),
    ("/cadastro/atualizar.php", "/servicos/atualizacao-cadastral", 0.5, 0.75),
    ("/promocao-de-natal-2016", "/contato", 0.0, 0.3),
])
def test_nota(quebrada, atual, minimo, maximo):
    assert minimo <= sugestao.nota(quebrada, atual) <= maximo


def test_sugestao_e_mapa_do_nginx():
    atuais = {"/noticias/oficina-de-violao", "/servicos/atualizacao-cadastral", "/contato"}
    certa = sugestao.sugerir("/noticias/2018/oficina-violao.html", atuais)
    duvida = sugestao.sugerir("/cadastro/atualizar.php", atuais)
    nada = sugestao.sugerir("/promocao-de-natal-2016", atuais)
    assert (certa.confianca, duvida.confianca, nada.confianca) == ("redirect", "revisar", "sem_sugestao")
    mapa = sugestao.nginx([certa, duvida, nada])
    assert "/noticias/2018/oficina-violao.html /noticias/oficina-de-violao;" in mapa
    assert "atualizar" not in mapa  # só o que é confiante vai para o mapa


def test_ponta_a_ponta_e_historico(tmp_path, site):
    exportacoes = cli._exportacoes(tmp_path)
    for _ in range(2):
        r = cli.monitorar(site.url, exportacoes, f"{site.url}/sitemap.xml", tmp_path / "saida")
    assert (r["contagem"][verificacao.QUEBRADA], r["confiantes"], r["revisar"]) == (7, 4, 2)
    with open(tmp_path / "saida" / "historico.csv", encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 2
