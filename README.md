# monitor-urls-quebradas

[![testes](https://github.com/BrunoMaia23/monitor-urls-quebradas/actions/workflows/testes.yml/badge.svg)](https://github.com/BrunoMaia23/monitor-urls-quebradas/actions/workflows/testes.yml)

Depois que um site muda de estrutura, as URLs antigas continuam recebendo visita: estão em favoritos,
em links de outros sites e nos resultados de busca. Este monitor pega as páginas antigas que ainda têm
tráfego, testa cada uma, ordena as quebradas pelo número de acessos e sugere para onde cada uma deveria
redirecionar. Foi um projeto do time em que eu trabalhei, depois de uma migração do site; este
repositório refaz a ideia do zero, com um site de mentira num servidor local e exportações fictícias.

*In English: a post-migration broken-URL monitor. Reads old URLs and their traffic from analytics
exports, follows each redirect hop by hop (chains, loops, redirects to dead pages), ranks broken pages by
traffic, and suggests 301 targets from the current sitemap, with a confidence level and an nginx map for
the confident ones. Synthetic data, local fake site.*

## O que ele faz

1. **Páginas antigas.** Lê as exportações das ferramentas de análise, cada uma com o seu cabeçalho
   (página ou page, visualizações ou clicks), fica só com o caminho e soma o tráfego da mesma página
   vindo de fontes diferentes.
2. **Teste.** Segue os redirects um a um, em vez de deixar a biblioteca seguir sozinha, para classificar
   o que acontece: página ok, redirect certo, cadeia longa de redirects, loop, erro de servidor, página
   quebrada e o caso mais traiçoeiro, o redirect que já existe mas leva para uma página que também sumiu.
3. **Sitemap.** Lê as URLs atuais do site, inclusive quando o sitemap é um índice de outros sitemaps.
4. **Sugestão.** Para cada quebrada, a URL atual mais parecida pelas palavras do caminho. Palavra parecida
   conta ("cadastro" e "cadastral"), número e extensão não contam. Nota alta vira redirect sugerido, nota
   média vai para revisão, e nota baixa fica sem sugestão, porque mandar o usuário para a página errada é
   pior que um 404.
5. **Saída.** CSV com o status de cada página, CSV com as sugestões, um `map` do nginx só com as
   sugestões confiantes (para alguém revisar e aplicar) e uma linha por execução num histórico, para
   acompanhar a curva de quebradas caindo.

## A demo

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m monitor demo
```

```
[site]        site novo de mentira num servidor local

[fontes]      2 exportações, 14 páginas antigas, 5.010 acessos no período
[sitemap]     12 URLs atuais
[verificação] ok 2 | redireciona 2 | cadeia longa 1 | quebrada 7 | erro 1 | loop 1
[prioridade]  quebradas, da mais acessada para a menos:
    1.100  /noticias/2018/oficina-violao.html         -> /noticias/oficina-de-violao (1,0, redirect)
      900  /servicos/2via.php                         -> /servicos/segunda-via-de-boleto (0,7, revisar)
           o redirect atual leva a /servicos/segunda-via, que não existe
      530  /noticias/2020/inauguracao-nova-sede.php   -> /noticias/nova-sede-inaugurada (1,0, redirect)
      260  /sobre/nossa-historia.html                 -> /sobre/historia (0,8, redirect)
      190  /eventos/2017/sarau-poesia                 -> /eventos/sarau-de-poesia (1,0, redirect)
      150  /cadastro/atualizar.php                    -> /servicos/atualizacao-cadastral (0,72, revisar)
       60  /promocao-de-natal-2016                    sem sugestão
   atenção: /agenda/feira-artesanato chega em /eventos/feira-de-artesanato depois de 2 redirects
   atenção: /busca responde com erro (500)
   atenção: /loop-a entra em loop de redirect
[saída]       urls_validadas.csv, redirects_sugeridos.csv, redirects_nginx.conf (4 redirects, 2 para revisar) e uma linha a mais em historico.csv
```

Contra um site de verdade: `python -m monitor verificar --base https://www.example.org --sitemap
https://www.example.org/sitemap.xml exportacao_1.csv exportacao_2.csv`.

## No projeto real

As páginas antigas vêm direto das APIs do Google Analytics e do Search Console, além de exportações
manuais, e o processo roda no Airflow depois da migração do site, gravando o histórico a cada execução.

## Testes

`pytest` sobe o site de mentira e cobre a leitura das exportações com cabeçalhos diferentes, cada
situação de URL (ok, redirect, cadeia, quebrada direta e por redirect, erro 500, loop, servidor fora do
ar), sitemap simples e índice, a nota de semelhança, a sugestão com o mapa do nginx e o histórico
crescendo uma linha por execução.
