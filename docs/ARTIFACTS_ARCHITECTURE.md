
# Arquitetura de Artefatos — Logs, Screenshots, Traces e Exports

Este documento descreve, de forma centralizada, como o projeto gera, persiste, serve e permite o download dos artefatos (screenshots, vídeos, traces, planilhas e outros) exibidos na tela "Logs".

## 1. Visão geral
- Geração: controlada por `core/automation/*` (workflows + `playwright_controller`).
- Persistência: metadados em banco (`job_artifacts`), arquivos físicos em `webapp/exports` (artefatos) e `webapp/uploads` (uploads iniciais / planilhas). 
- Servir/Download: endpoints em `webapp/server.py` (listagem `/api/results/files`, download `/api/results/files/{id}/download`, admin `/api/admin/...`).
- UI: `webapp/static/app.js` e `webapp/static/index.html` exibem logs em tempo real (SSE) e links de download.

## 2. Ferramentas principais
- Playwright (Python): captura de screenshots, gravação de vídeo, tracing.
- FastAPI / Starlette: API, streaming SSE, `FileResponse` para downloads.
- SQLAlchemy + SQLite/Postgres: persistência dos metadados (`webapp/models.py`).
- Openpyxl / pandas: manipulação e export de planilhas (CSV/XLSX).
- Docker + docker-compose: orquestração; volumes para `uploads` e `exports`.

## 3. Geração de artefatos (fluxo)
1. Job criado e executado por `JobRunner` (em `webapp/server.py` ou serviço correspondente).
2. `JobRunner` inicia Playwright via `PlaywrightController.start()` com `record_video_dir` apontando para `ARTIFACTS_DIR / job_id`.
3. Durante execução, em erros ou pontos definidos, são capturados:
   - `page.screenshot()` → arquivo `.png` no diretório do job.
   - Vídeo `.webm` gerado pelo Playwright `record_video_dir`.
   - Tracing via Playwright `tracing.start()/stop()` → `trace.zip`.
4. Planilhas finais: `SpreadsheetWriter` salva XLSX/CSV em `EXPORT_DIR` e `JobRunner._record_artifact()` registra metadado em DB.

## 4. Persistência (onde gravar e como)
- Metadados: tabela `job_artifacts` em `webapp/models.py` (campos principais: `id`, `job_id`, `type`, `file_path`, `created_at`).
- Arquivos físicos:
  - Uploads iniciais: `webapp/uploads/` (Upload endpoint `/api/files`).
  - Artefatos por job: `webapp/exports/jobs/{job_id}/...` (screenshots, videos, trace.zip).
  - Exports/relatórios: `webapp/exports/resultados_{job_id}.xlsx` ou em `webapp/exports/`.

## 5. Resolução de caminhos (lógica importante)
Função chave: `_resolve_artifact_disk_path(file_path, job_id)` em `webapp/server.py`. Estratégias tentadas:
1. Usa o caminho gravado em DB diretamente (`raw_path`).
2. Se relativo, tenta `ROOT / raw_path`.
3. Tenta `ARTIFACTS_DIR / job_id / raw_path.name` (procura pelo nome do arquivo dentro do job).
4. Compatibilidade com paths legacy de container (prefixes `/app/exports/jobs/` ou `/app/webapp/exports/jobs/`).

Se nenhum candidato existir, o endpoint marca `available: false` e download retorna 404.

## 6. Endpoints relevantes
- `POST /api/files` — upload de planilhas (salva em `UPLOAD_DIR`).
- `POST /api/jobs` — cria/agenda job (inicia `JobRunner`).
- `GET /api/jobs/{job_id}/logs/stream` — SSE para logs em tempo real.
- `GET /api/results/files` — lista arquivos de resultado (filtra por tipos de planilha).
- `GET /api/results/files/{artifact_id}/download` — baixa planilhas (usa `_resolve_artifact_disk_path`).
- Admin: `/api/admin/jobs/{job_id}/artifacts` e `/api/admin/artifacts/{artifact_id}/file` para screenshots/traces.

## 7. Docker / Volumes
- `docker-compose.yml` original usa volumes nomeados (`uploads_data`, `exports_data`). Isso mantém os dados dentro do Docker-managed volume — não aparecem no diretório `webapp/exports` do host.
- Para debug ou acesso direto, usar bind-mounts no `docker-compose.yml`:
  ```yaml
  volumes:
    - ./webapp/uploads:/app/webapp/uploads
    - ./webapp/exports:/app/webapp/exports
  ```
- Se já existirem dados no volume nomeado e você alterar para bind, será necessário copiar os dados do volume para o host (via `docker run --rm -v <volume>:/data -v ${PWD}:/backup alpine sh -c "cp -r /data/* /backup/exports_from_volume/"`).

## 8. Frontend — como acessa os arquivos
- A UI usa `EventSource('/api/jobs/{job_id}/logs/stream')` para logs em tempo real e monta links de download usando endpoints da API.
- Se a UI mostrar `available: false`, significa que `_resolve_artifact_disk_path` não encontrou o arquivo físico.

## 9. Scripts e funções centrais (onde olhar)
- `webapp/server.py`:
  - `JobRunner.run()` — orquestra execução, captura e grava artifacts.
  - `_record_artifact()` — insere registro em `job_artifacts`.
  - `_resolve_artifact_disk_path()` — resolve path no disco.
  - Endpoints de listagem e download de arquivos.
- `core/automation/playwright_controller.py` — APIs de screenshot, tracing e video.
- `core/services/spreadsheet_writer.py` — export CSV/XLSX.
- `webapp/models.py` — esquema das tabelas (principalmente `job_artifacts`).

## 10. Checklist de verificação (passos rápidos)
1. Verificar registros: `SELECT id, job_id, type, file_path FROM job_artifacts WHERE job_id = '{JOB_ID}';` (usar `webapp.db` ou o Postgres configurado).
2. Confirmar se `file_path` aponta para arquivo absoluto no host ou para o path dentro do volume/container.
3. Se for volume Docker, listar o conteúdo do volume dentro do container (`docker-compose exec backend ls -la /app/webapp/exports/jobs/{JOB_ID}`).
4. Se `available: false`, inspecionar `_resolve_artifact_disk_path` para ver quais candidatos foram testados (logs de debug podem ser adicionados temporariamente).
5. Verificar permissões do arquivo (processo do container deve ter permissão de leitura).

## 11. Comandos úteis
- Listar artifacts via API (local):
  ```bash
  curl -sS http://localhost:8000/api/results/files | jq .
  ```
- Baixar um artifact:
  ```bash
  curl -OJ "http://localhost:8000/api/results/files/{ARTIFACT_ID}/download"
  ```
- Copiar dados de volume Docker para host:
  ```bash
  docker run --rm -v faturamentos-backend_exports_data:/data -v ${PWD}:/backup alpine \
    sh -c "cp -r /data/* /backup/exports_from_volume/ || true"
  ```

## 12. Recomendações para correção rápida
- Se os arquivos não aparecem no host: configurar bind-mounts temporariamente no `docker-compose.yml` (conforme seção 7) e reiniciar o serviço.
- Se arquivos estão no volume mas não aparecem: copiar o conteúdo do volume para o host e ajustar `file_path` no DB ou garantir que `_resolve_artifact_disk_path` possa resolver o path atual.
- Para ambiente distribuído: garantir que `DATABASE_URL` e `ARTIFACTS_DIR` apontem para recursos compartilhados (ex.: S3, NFS) ou usar um storage centralizado.

## 13. Observações finais
- A regra central: a API só serve arquivos que realmente existam no disco onde o processo do webapp roda. Metadados no DB sem o arquivo físico resultam em `available: false` e 404 em downloads.
- Mantenha consistência entre as variáveis de ambiente (`BASE_PATH`, `DATABASE_URL`, `PLAYWRIGHT_HEADLESS`) e a configuração de volumes para evitar mismatch de paths.

---
Arquivo gerado automaticamente para documentação de diagnóstico.
