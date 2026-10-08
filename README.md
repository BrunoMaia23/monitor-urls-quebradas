# monitor-urls-quebradas

[![testes](https://github.com/BrunoMaia23/monitor-urls-quebradas/actions/workflows/testes.yml/badge.svg)](https://github.com/BrunoMaia23/monitor-urls-quebradas/actions/workflows/testes.yml)

Depois que um site muda de estrutura, as URLs antigas continuam recebendo visita: estão em favoritos,
em links de outros sites e nos resultados de busca. Depois de uma migração de site no trabalho, o time
montou um monitor para isso, alimentado pelas APIs do Google Analytics e do Search Console e rodando no
Airflow; eu trabalhei nele. A versão daqui roda contra um site de mentira num servidor local, com
exportações inventadas.

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

## Contra o site de mentira

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

Num site de verdade: `python -m monitor verificar --base https://www.example.org --sitemap
https://www.example.org/sitemap.xml exportacao_1.csv exportacao_2.csv`.
