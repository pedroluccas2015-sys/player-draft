# Player Draft — Scouting de Clubes

Aplicativo de apoio ao departamento de futebol: observação por região, análise de desempenho e lista de interesse para contratação. Tema verde e branco, com painel de olheiros inspirado na referência do EA FC fornecida pelo usuário.

## Como rodar

### Apresentação local no Windows

1. Instale **Python 3.11 ou superior** com a opção de adicionar Python ao PATH. A instalação foi validada com Python 3.14.
2. Baixe o projeto em **Code → Download ZIP** no GitHub e extraia tudo em uma pasta gravável, ou clone o repositório.
3. Abra `Iniciar-Player-Draft.cmd`. Ele cria `.venv` e instala as dependências do backend na primeira execução.
4. Acesse **http://127.0.0.1:5000/**. Deixe a janela aberta; para parar, pressione Ctrl+C.

A interface compilada, a base de mercado e os elencos consultados acompanham este repositório em `runtime-assets.zip`, extraído automaticamente na primeira execução com bibliotecas integradas ao Python. **Node.js não é necessário para executar essa versão pronta.** A primeira instalação e as consultas de dados precisam de internet. Não são exigidas chaves de API ou arquivo `.env` nesta versão.

### Instalação manual

No Windows, na pasta principal:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python.exe -m flask --app app run --host 127.0.0.1 --port 5000
```

No Linux/macOS, na pasta principal:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd backend
../.venv/bin/python -m flask --app app run --host 127.0.0.1 --port 5000
```

Abra http://127.0.0.1:5000/. O SQLite é integrado ao Python; não precisa instalar um servidor de banco de dados. O iniciador usa Flask para apresentação local. Para hospedagem pública é necessário configurar um servidor de produção e armazenamento persistente para cache e dados.

### Bibliotecas e ferramentas

| Componente | Bibliotecas / versão declarada | Para que serve |
| --- | --- | --- |
| Backend | Flask 3.1.3 | API e entrega da interface |
| Backend | diskcache 5.6.3 | Cache de consultas e imagens |
| Backend | curl_cffi 0.16.3 | Consultas HTTP às fontes |
| Backend | pandas 3.1.0 | Agregação de estatísticas |
| Interface | React / React DOM 19.2.5 | Telas e componentes |
| Gráficos | Recharts 3.8.1 | Evolução por temporada e partida |
| Ícones | lucide-react 1.14.0 | Ícones da interface |
| Mapa | world-atlas 2.0.2 / topojson-client 3.1.0 | Países e mapa de scouting |
| Estilos | Tailwind CSS 4.2.4 / PostCSS / Autoprefixer | Compilação dos estilos |
| Desenvolvimento | Vite 8.0.10 / plugin React | Servidor de desenvolvimento e build |
| Qualidade | ESLint 10.2.1 e plugins React | Verificação do código da interface |

Versões do backend fixadas em `backend/requirements.txt`. Dependências completas da interface e versões resolvidas estão em `frontend/package.json` e `frontend/package-lock.json`; use `npm ci` para respeitar o arquivo de versões. O instalador Python também instala as dependências transitivas necessárias.

### Alterar a interface

Instale **Node.js 22.12+** (ou uma versão LTS posterior compatível), além do Python. Em `frontend`:

```bash
npm ci
npm run dev
```

Mantenha o backend na porta 5000. O Vite encaminha `/api` e os proxies de imagens para ele. Para gerar novamente a interface pronta:

```bash
npm run lint
npm run build
node --test src/competitionTotals.test.js
```

O build atualiza `frontend/dist/`, servido automaticamente pelo Flask. Para distribuir uma nova versão com a interface compilada e os dados, execute `python backend/package_runtime.py` na raiz e publique também o `runtime-assets.zip` atualizado. Para os testes do backend, entre em `backend` e use `..\.venv\Scripts\python.exe -m unittest discover -s tests -v` no Windows, ou `../.venv/bin/python -m unittest discover -s tests -v` no Linux/macOS.

### Problemas comuns

- **Python não encontrado:** confirme a instalação e o PATH; feche e reabra o terminal. Se o computador usa somente `py`, crie o ambiente com `py -m venv .venv` antes de executar o iniciador.
- **Porta 5000 ocupada:** encerre a outra execução do app. No desenvolvimento, os proxies Vite apontam para essa porta.
- **Erro de instalação:** confira Python 3.11+, internet e permissão de escrita na pasta. Não instale o projeto dentro de `Program Files`.
- **Imagem ou estatística ausente:** a cobertura depende da fonte. O app informa dados parciais; um avatar ou ausência de notas não é desempenho estimado.
- **Tela antiga após atualizar:** pare a execução anterior, extraia a versão nova inteira e recarregue o navegador com Ctrl+F5.

## Top 5 por liga e filtros geográficos

- Todas as posições: cinco maiores notas disponíveis na liga.
- Goleiros, defensores, meio-campistas e atacantes: consulta filtrada na fonte antes de ordenar e limitar a cinco. O filtro não reaproveita apenas os cinco jogadores da lista geral.
- Critério de participação: pelo menos uma partida. Notas ausentes/inválidas são excluídas; empates usam partidas e identificador. O corte antigo de 50% das partidas foi removido para atender ao ranking solicitado por nota.
- Se a temporada mais recente não tiver notas, é indicada explicitamente a temporada anterior disponível. Não são inventados atletas para completar cinco quando a fonte não tem dados suficientes.
- Testes reais: sete ligas x cinco recortes (geral/G/D/M/F), 35 de 35 respostas com cinco atletas ordenados por nota.
- América do Sul: Argentina, Bolívia, Brasil, Chile, Colômbia, Equador, Guiana, Paraguai, Peru, Suriname, Uruguai e Venezuela. Guiana e Suriname foram incluídas pelo critério geográfico, embora participem da CONCACAF.
- África: Egito (Premier League), Marrocos (Botola Pro), Argélia (Ligue 1) e África do Sul (Premiership).
- O catálogo de mercado é complementado com elencos Sofascore da principal liga em cada um dos 45 países disponíveis. Validação real: 45/45 buscas HTTP 200 com atletas; 22.654 registros de elenco em 745 clubes consultados. Não é um censo de todos os jogadores de todas as divisões.
- Guiana: 40 jogadores em 2 dos 10 clubes; Suriname: 62 em 3 dos 11 clubes. Demais elencos não foram disponibilizados pela fonte. A resposta informa consultas parciais; não são preenchidas com jogadores inventados.
- Elencos consultados a cada 6 horas e preservados em `backend/data/leagues/`. Falhas de atualização preservam a última consulta e geram aviso. O pacote já contém a consulta de 23/10/2026.
- Verificação final: 41 testes de backend + 2 de agregação no frontend aprovados; compilação e ESLint aprovados.

## Gols por competição no dossiê

- A tabela aparece em **Geral** e em cada temporada. Geral agrupa gols, jogos e assistências por competição, mostrando os anos incluídos, o escudo e a nota ponderada por partidas. Selecionar uma temporada mostra apenas seus números e mantém o acesso ao mapa de calor.
- Escudos são consultados com a imagem normal sobre fundo claro, tipo real da imagem, validação da resposta e cache de 6 horas. Imagens inválidas usam símbolo local de competição; não desaparecem silenciosamente.
- Verificação real Neymar: Geral com 11 competições; 2026 com Brasileirão (8 gols), Sul-Americana (2), Copa do Brasil (0) e Paulista (0), total 10. Os 11 escudos retornaram HTTP 200 com PNG. Os gráficos e animações foram preservados.
- Estatísticas detalhadas dependem da competição e do atleta. Uma amostra dos 16 mercados sul-americanos/africanos encontrou o campeonato nos dados estatísticos de 15 atletas; o atleta do Suriname tinha dados de outras competições, sem estatísticas dessa liga. Ausência de publicação não é preenchida como desempenho zero.


## Atualização de interface

- Menu renomeado para **Rede de Scout**.
- Nova tela inicial com logo vetorial Player Draft, nome e botão **Iniciar**.
- Retratos carregados nas listas de destaques, resultados, busca, comparação e elencos. A imagem de reserva é encontrada independentemente da abertura do dossiê, sem consultar todas as estatísticas para mostrar uma foto. Validação de identidade mantida; se nenhuma fonte tiver foto válida, usa avatar local.
- Somente o dossiê dos atletas recuperou o estilo original do repositório: foto com nota, blocos de informações, tipografia forte em itálico, grandes cartões arredondados, linha grossa e pontos destacados.
- Preservados os gráficos de evolução geral, gols/assistências e notas por partida da temporada selecionada.
- Animações de entrada, desenho das curvas/barras e contagem dos dados ao trocar temporadas; desativadas com preferência de movimento reduzido.
- As demais telas mantêm o estilo novo para clubes.
- Conferidos no navegador: tela inicial, acesso ao app, fotos dos cinco destaques do Brasileirão, dossiê e troca de temporada. Consultas independentes das seis fotos verificadas retornaram HTTP 200.
- Compilação e ESLint aprovados; resultados atuais dos testes constam na seção de verificação.

## O que mudou

- Removidas a escolha inicial de seleção, a restrição de nacionalidade e a convocação automática por IA.
- Tela inicial com logo, nome Player Draft e botão Iniciar, seguida pela Rede de Scout. País selecionado significa país do clube, não elegibilidade para uma seleção.
- Busca com região, país, posição específica, valores mínimo e máximo em euros, idades mínima e máxima, contrato, pé, altura, nome/clube e ordenação. Resultados paginados, 24 por página.
- Lista de interesse sem limite de 26 vagas, persistida neste navegador; comparação de dois atletas com consulta de estatísticas antes de adicioná-los.
- Dossiê com estatísticas Sofascore de clubes, evolução geral por temporadas, gols/assistências, notas por partida na temporada selecionada, métricas por 90 minutos e mapas de calor quando disponíveis.
- Mercado Transfermarkt com valores, contrato e histórico de transferências da base pública incluída.
- Radar de ligas ESPN com resultados, próximos jogos e acesso ao elenco dos clubes; destaques por liga Sofascore.
- Imagens Sofascore, imagem de reserva Transfermarkt para correspondências confirmadas e avatar local se não houver retrato válido. Respostas de imagem de 1 pixel são rejeitadas.

## Dados e limites concretos

**Sofascore:** as consultas reais voltaram a responder HTTP 200 após remover a configuração antiga de impersonação do navegador. A disponibilidade futura depende do provedor e não pode ser garantida. Estatísticas e notas por partida ficam em cache por 15 minutos, com data/hora da consulta no dossiê. Não são criadas notas padrão de 7.0 nem estatísticas de demonstração. O período de temporadas é dinâmico, abrangendo aproximadamente os últimos seis anos conforme os rótulos da fonte. Geral agrega somente competições e temporadas carregadas, não toda a carreira. Dossiês sem correspondência ou dados indisponíveis mostram essa condição.

**Transfermarkt:** base pública derivada do projeto dcaribou/transfermarkt-datasets, datada de **6 de julho de 2026**, não uma API oficial ou cotação em tempo real. O mantenedor suspendeu a atualização dessa publicação. A consulta direta ao site retornou HTTP 202 sem conteúdo; o serviço comunitário consultado também não forneceu dados atuais. A entrega contém 50.149 perfis e 175.165 registros de transferências; a descoberta considera 22.292 atletas com participação registrada a partir da temporada 2025. Há cobertura parcial de 32 países de clubes. A base Transfermarkt não inclui esses clubes africanos, mas os elencos Sofascore agora tornam os atletas pesquisáveis nos filtros. Fora da correspondência Transfermarkt, valores em EUR publicados pelo Sofascore são usados com a fonte identificada; não são apresentados como valores Transfermarkt. Histórico de transferências segue restrito aos registros confirmados na base Transfermarkt.

**Contratos:** as faixas preservam as datas de referência do filtro (até 06/01/2027 e após 06/07/2027). A busca usa o término contratual publicado no elenco Sofascore quando disponível; cartões somente Transfermarkt usam a base de 06/07/2026. Um contrato vencido não prova que o jogador está livre hoje. O filtro de atleta sem clube exige registro explícito de clube ausente; data contratual desconhecida não é tratada como passe livre. Valores ausentes não são tratados como zero e são excluídos dos filtros de orçamento. O valor de mercado é estimativa da fonte, não preço de venda, multa rescisória ou salário.

**Associação entre fontes:** identificadores são separados. A ligação automática exige correspondência única de nome normalizado e data de nascimento. Divergências são preservadas e informadas; por exemplo, no teste Wallace Yan teve nascimento em 08/02/2005 na base Transfermarkt e 07/02/2005 no Sofascore, e não recebeu uma associação automática. Alguns jogadores, portanto, ficam sem estatísticas associadas ao cartão de mercado e devem ser buscados diretamente pelo nome no Sofascore.

**ESPN:** a consulta antiga com intervalo de datas retornava HTTP 400. Foi substituída por consultas dos meses anterior, atual e seguinte, com deduplicação. A tela mostra até seis resultados e seis próximos jogos, e consulta novamente a cada 60 segundos. Cache de 30 segundos para jogos ao vivo e de até uma hora para os demais. Falhas são exibidas, sem lista vazia disfarçada de sucesso.

Não é possível afirmar que o requisito de valores/contratos/transferências atuais de **todos** os atletas foi atendido: para isso é necessária uma fonte de mercado atualizada e com cobertura adequada. Esta limitação está indicada na interface.

## Executar no Windows

1. Instale Python 3.11 ou superior, disponível no terminal como `python` (validado aqui com Python 3.14).
2. Extraia o ZIP inteiro em uma pasta gravável.
3. Execute `Iniciar-Player-Draft.cmd` com dois cliques. Na primeira execução ele cria um ambiente isolado e instala as dependências; precisa de internet.
4. Abra **http://127.0.0.1:5000/**. Mantenha a janela do servidor aberta. Encerre com Ctrl+C.

A interface compilada e o catálogo SQLite já acompanham o pacote; não é preciso Node.js para essa execução. É necessário acesso à internet para as fontes externas. O iniciador usa o servidor de desenvolvimento do Flask apenas para apresentação local; não publica o aplicativo.

## Desenvolvimento

Requer Node.js 22.12+ para Vite 8, e Python com suporte às dependências.

Na raiz:
```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Em `frontend`:
```
npm ci
npm run build
npm run lint
```

Em `backend`:
```
..\.venv\Scripts\python.exe -m flask --app app run --host 127.0.0.1 --port 5000
```

Para atualização automática da interface durante desenvolvimento, mantenha Flask na porta 5000 e execute `npm run dev` na pasta frontend; o Vite encaminha API e imagens ao Flask.

## Reproduzir o catálogo

O arquivo `backend/data/market.sqlite` é incluído. A origem e a data estão em `backend/data/SOURCE.json`. Para reconstruí-lo da publicação pública disponível:
```
cd backend
..\.venv\Scripts\python.exe sync_market.py
```
O comando baixa os CSVs publicados pelo mantenedor; **não transforma essa base suspensa em uma fonte atualizada**. Não execute a reconstrução enquanto outra instância do aplicativo estiver lendo o catálogo.

## Testes

Em `backend`:
```
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
41 testes aprovados (incluindo fotos independentes, Top 5 por posição, elencos reais, filtros financeiros e escudos): filtros combinados, limites, dados ausentes, contratos, associação inequívoca, divergências de nascimento, indisponibilidade da fonte, normalização de nomes, SQL parametrizado e remoção da API de convocação automática.

## Verificação em 23/10/2026

- Compilação de produção aprovada e ESLint sem erros/avisos. Dossiê e gráficos carregados sob demanda.
- Navegador: tela inicial, botão Iniciar, Rede de Scout, fotos dos destaques antes de abrir o dossiê, busca real, persistência da lista após recarregar, dossiê Ryan Francisco, gráfico geral, notas por partida em 2025 e histórico de transferências.
- Filtro país do clube Brasil + centroavante + idade máxima 23 + valor máximo €5 milhões: 11 atletas na base.
- Vinícius Júnior: identidade Transfermarkt 371998 / Sofascore 868812 confirmada, clube Real Madrid e estatísticas 200; 36 notas por partida no recorte La Liga 25/26 testado.
- Radar ESPN Brasileirão: seis resultados e seis próximos jogos retornados com HTTP 200.
- Ranking Sofascore: HTTP 200, cinco melhores por nota e pelo menos uma partida em cada recorte.
- Fotos: Sofascore Vinícius 200 com PNG válido; fotos ausentes/transparentes de 1 pixel são rejeitadas para usar reserva/avatar.
- Dependências frontend: a instalação informou 8 avisos de vulnerabilidade (6 altos, 1 moderado, 1 baixo); não foi feita migração ampla de dependências. Revise antes de publicar para uso externo.
- Layout tem regras para desktop e telas pequenas; a conferência visual foi feita no navegador desktop.

## Fontes

- Sofascore: https://www.sofascore.com/
- ESPN: https://www.espn.com/soccer/
- Dados de mercado e transferências: https://github.com/dcaribou/transfermarkt-datasets (publicação CC0; data explícita da base preservada).
- Dados geográficos: world-atlas / Natural Earth, renderizados localmente.

Código baseado no projeto original [DavideAlmeida2006/player-draft](https://github.com/DavideAlmeida2006/player-draft). Esta versão adapta o fluxo para scout de clubes e preserva os créditos do repositório de origem. Publicação do código no GitHub não hospeda automaticamente o backend nem transforma o aplicativo em um site acessível ao público.
