# Manual do Usuário - LogTudo Automação: Faturamentos Adicionais v1

Bem-vindo ao manual do usuário do sistema **LogTudo - Faturamentos adicionais v1**. Este sistema foi desenvolvido para automatizar o processo de faturamentos adicionais, realizando a leitura de planilhas e a inserção/coleta de dados de forma automatizada (Web Scraping) com acompanhamento em tempo real.

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Configurações Iniciais](#2-configurações-iniciais)
3. [Processamento de Planilhas](#3-processamento-de-planilhas)
4. [Acompanhamento de Logs](#4-acompanhamento-de-logs)
5. [Resultados e Exportação](#5-resultados-e-exportação)
6. [Boas Práticas e Solução de Problemas](#6-boas-práticas-e-solução-de-problemas)

---

## 1. Visão Geral

O sistema é dividido em três abas principais, acessíveis pelo menu lateral esquerdo:
- **Processamento:** Onde você envia a planilha, mapeia as colunas, controla a execução e acompanha os logs ao vivo.
- **Configurações:** Onde você insere suas credenciais de acesso ao sistema alvo e ajusta os tempos de espera (delays) da automação.
- **Resultados:** Onde você visualiza o resumo da execução, busca detalhes de notas fiscais específicas e exporta os resultados finais.

---

## 2. Configurações Iniciais

Antes de iniciar qualquer processamento, é obrigatório configurar suas credenciais e preferências.

1. Navegue até a aba **Configurações**.
2. No painel **Credenciais**, preencha:
   - **Usuário:** Seu login de acesso ao sistema integrado.
   - **Senha:** Sua senha de acesso.
   - **UF:** Selecione o estado correspondente à operação (Bahia, Ceará ou Pernambuco).
   - **Timeout (ms):** Tempo máximo de espera para o carregamento de páginas (padrão: 30000 ms ou 30 segundos).
3. No painel **Delays (Tempo de Espera)**, você pode ajustar a velocidade da automação (valores em milissegundos). Se a internet estiver lenta, é recomendável aumentar esses valores:
   - **Pausa:** Tempo entre o processamento de uma nota e outra.
   - **Rede:** Tempo de espera por respostas do servidor.
   - **Interação:** Tempo de espera entre cliques na tela.
   - **Digitação:** Velocidade com que o robô digita os textos.
4. Clique no botão **Salvar**. *(As configurações ficam salvas localmente no seu navegador).*

---

## 3. Processamento de Planilhas

Com as configurações salvas, você pode iniciar o trabalho em lote.

### 3.1. Enviando o Arquivo
1. Vá para a aba **Processamento**.
2. No painel **Arquivo**, clique em **Selecionar planilha** ou arraste seu arquivo (`.xlsx`, `.xls`, `.csv`).
3. O sistema fará a leitura e exibirá o número de linhas e colunas encontradas.

### 3.2. Mapeamento de Colunas
Para que o robô saiba onde encontrar cada informação, você deve mapear as colunas da sua planilha. O sistema tentará fazer isso automaticamente, mas você deve revisar:
- **Nota Fiscal:** A coluna que contém o número da nota.
- **Tipo ADC:** A coluna que indica o tipo de adicional.
- **Valor CTE:** A coluna do valor.
- **Senha Ravex:** A coluna contendo a senha.
- **Transporte:** A coluna com os dados do transporte.
- **Saída CTE:** A coluna **onde o robô irá salvar o número do CT-e gerado**.

*Atenção: Se uma linha da planilha já possuir um valor na coluna de "Saída CTE", o robô a identificará como já processada e irá pular para a próxima, evitando duplicidade.*

### 3.3. Iniciando a Automação
1. Verifique na tabela de **Pré-visualização** se os dados carregaram corretamente.
2. (Opcional) Ative a chave **Executar Envios** caso deseje que a automação efetive a gravação no sistema destino (se desativada, a automação pode rodar em modo de teste/simulação, dependendo da configuração da plataforma).
3. Clique no botão **Iniciar**. O status mudará de "Parado" para "Rodando".

---

## 4. Acompanhamento de Logs

Durante a execução, você pode monitorar cada passo do robô na mesma tela de **Processamento**:

- **Controle:** Mostra a porcentagem de conclusão, qual nota está sendo processada no momento e permite **Pausar**, **Retomar** ou **Parar** a automação.
- **Logs ao Vivo:** Exibe as mensagens em tempo real:
  - 🔵 **INFO:** Passos normais (ex: "Realizando login...", "Processando nota X").
  - 🟢 **SUCCESS:** Ações concluídas com êxito (ex: "CT-e gerado: 12345").
  - 🟡 **WARNING:** Alertas ou tentativas de recuperação de erros conhecidos.
  - 🔴 **ERROR:** Falhas (ex: "Senha inválida", "Sistema indisponível").
  
*Dica:* Você pode usar o filtro suspendo acima dos logs para mostrar apenas mensagens de `ERROR` ou `SUCCESS`.

---

## 5. Resultados e Exportação

Após a conclusão (ou se você parar o processo), você deve extrair o relatório de sucesso e erros.

1. Vá para a aba **Resultados**.
2. No topo, confira o **Resumo**: Total de Sucessos, Erros, Pendentes e a Taxa de sucesso (%).
3. Na tabela **Detalhamento**, você pode usar o campo de busca para encontrar rapidamente uma NF ou CT-e.
4. Para baixar a planilha consolidada (contendo os números de CT-e gerados e as mensagens de erro), clique em **Exportar XLSX** ou **Exportar CSV**.

---

## 6. Boas Práticas e Solução de Problemas

- **Planilha Vazia ou Travada:** Certifique-se de que a planilha não possui formatações complexas, macros ou senhas. Utilize formatos `.xlsx` simples.
- **Muitos Erros de "Timeout":** Isso significa que o sistema alvo (Ravex/Sefaz) está demorando muito para responder. Vá em Configurações e aumente o valor de **Rede (ms)** e **Timeout (ms)**.
- **Parada Inesperada:** Se o sistema travar, você pode clicar em **Parar**. O sistema salvará automaticamente o progresso atual. Ao reiniciar com a mesma planilha, o robô irá pular as notas que já possuem um CT-e preenchido.
- **Proteção de Dados:** Nunca compartilhe sua planilha exportada com terceiros sem autorização, pois ela contém seus dados de faturamento e senhas operacionais.
