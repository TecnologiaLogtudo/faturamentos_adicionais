# Atualizado para a versão baseada no Ubuntu 24.04 (Noble) recomendada na documentação
FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

# Define o diretório de trabalho no container
WORKDIR /app

# Copia o arquivo de requisitos e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium

# Copia todo o restante do código para o container
COPY . .

# Copia os assets estáticos do frontend sem depender de estágio Node
RUN mkdir -p /app/dist && cp -a /app/webapp/static/. /app/dist/

# Conforme recomendado para Web Scraping/Crawling, ajustamos as permissões
# e alternamos para o usuário não-root 'pwuser' para manter o sandbox do Chromium ativado
RUN mkdir -p /app/webapp/uploads && \
    chown -R pwuser:pwuser /app

USER pwuser

# Variáveis de ambiente úteis
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Inicia o servidor Python FastAPI (Ajuste "webapp.server:app" se o nome do seu arquivo principal for outro)
CMD ["uvicorn", "webapp.server:app", "--host", "0.0.0.0", "--port", "8000"]
