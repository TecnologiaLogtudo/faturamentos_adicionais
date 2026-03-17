# Estado Atual do Projeto - LogTudo Web Scraper

## Visão Geral
O projeto é uma ferramenta de automação e web scraping para o sistema **LogTudo**. Ele automatiza o processamento de Notas Fiscais, gerando números de CT-e (Conhecimento de Transporte Eletrônico) a partir de dados fornecidos em planilhas Excel ou CSV.

## Arquitetura Atual
A aplicação é híbrida, mas foca principalmente em uma interface desktop Python:

- **Linguagem:** Python 3.x
- **Interface Gráfica (GUI):** 
  - **Principal:** Tkinter (`gui/app.py`), com uma interface moderna dividida em abas (Configurações, Processamento, Logs, Resultados).
  - **Secundária/Experimental:** Existe um esqueleto de projeto Electron (`package.json`, `playwright.config.js`), mas a lógica principal está no Python.
- **Automação Web:** Playwright (`automation/playwright_controller.py`) operando em modo síncrono.
- **Gerenciamento de Dados:** 
  - Leitura: `services/excel_reader.py`
  - Escrita: `services/spreadsheet_writer.py` e atualização direta via `openpyxl`.
- **Workflows:** Localizados na pasta `automation/`, dividindo responsabilidades como login, preenchimento de nota fiscal e tratamento de erros.

## Fluxo de Trabalho
1. O usuário carrega uma planilha Excel/CSV.
2. O sistema mapeia as colunas necessárias (Nota Fiscal, Tipo ADC, Valor, etc.).
3. O usuário configura as credenciais do LogTudo.
4. A automação inicia o Playwright, faz login e processa cada linha da planilha.
5. Os resultados (CT-e) são escritos de volta na planilha original e exibidos na interface.

## Pontos de Melhoria Identificados (Para Transição para Agente IA Web)
1. **Interface:** Migrar de Tkinter para uma interface Web moderna (React/Next.js).
2. **Inteligência:** Integrar capacidades de agente de IA para lidar com mudanças dinâmicas no site e erros inesperados de forma autônoma.
3. **Escalabilidade:** Conexão com servidores MCP (Model Context Protocol) para expandir as capacidades do agente.
4. **Infraestrutura:** Possível transição para execução assíncrona do Playwright para melhor performance.

## Arquivos Chave
- `main.py`: Ponto de entrada da aplicação Python.
- `gui/app.py`: Toda a lógica da interface Tkinter.
- `automation/playwright_controller.py`: Wrapper para controle do navegador.
- `config/config.json`: Armazena credenciais e configurações de mapeamento de colunas.
