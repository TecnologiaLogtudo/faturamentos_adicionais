# Usa a imagem oficial do Playwright (versão equivalente a que você usa no package.json)
# Isso evita erros de "biblioteca compartilhada ausente" ao abrir o Chromium.
FROM node:20-alpine AS frontend
WORKDIR /frontend
COPY webapp/static ./static
RUN mkdir -p dist && cp -a static/. dist/

FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

# Define o diretório de trabalho no container
WORKDIR /app

# Copia o arquivo de requisitos e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o restante do código para o container
COPY . .

# Copia o build do frontend para facilitar deploys que sirvam os assets estáticos
COPY --from=frontend /frontend/dist /app/dist

# Variáveis de ambiente úteis
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Inicia o servidor Python FastAPI (Ajuste "webapp.server:app" se o nome do seu arquivo principal for outro)
CMD ["uvicorn", "webapp.server:app", "--host", "0.0.0.0", "--port", "8000"]
