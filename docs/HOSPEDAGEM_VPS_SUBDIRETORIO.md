# Guia de Hospedagem em VPS e Acesso via Subdiretório

Este documento descreve as orientações, variáveis e lógica embutida na versão Web da automação **LogTudo** para permitir a hospedagem num subdiretório de um domínio principal (ex: `https://meudominio.com/logtudo/`).

## 1. A Variável de Ambiente Principal

A aplicação foi projetada para se auto-configurar. Para definir o subdiretório, basta configurar a seguinte variável de ambiente no seu arquivo `.env` ou no seu gerenciador de processos (como *Supervisor* ou *Systemd*) antes de iniciar o `server.py`:

```env
BASE_PATH=/logtudo
```

Se essa variável não for definida, o sistema assumirá a raiz `/`.

---

## 2. Como a Lógica Funciona Internamente

A aplicação adapta todo o sistema dinamicamente ao detectar a variável `BASE_PATH`:

### No Backend (`server.py`)
1. **FastAPI Root Path:** A variável é injetada no parâmetro `root_path`, fazendo com que toda a API entenda o prefixo.
2. **Strip Middleware:** O `strip_base_path_middleware` é um interceptador. Quando o navegador requisita `https://meudominio.com/logtudo/api/status`, o middleware recorta a string `/logtudo` e entrega `/api/status` puro pro roteador do FastAPI.
3. **Injeção Dinâmica:** O servidor pega o arquivo estático `index.html` e substitui o placeholder `__LOGTUDO_BASE_PATH__` e os caminhos de assets estáticos (CSS/JS) no momento que o navegador acessa o site.

### No Frontend (`app.js` e `index.html`)
1. A variável injetada pelo Backend fica salva no navegador dentro do objeto window: `window.LOGTUDO_BASE_PATH`.
2. A função `withBasePath()` anexa automaticamente este prefixo em todas as chamadas `fetch()` ou rotas de manuais e links da interface, mantendo a navegação perfeitamente presa no subdiretório.

---

## 3. Como Configurar o Proxy Reverso (Nginx) na VPS

Para que isso funcione em produção, o Nginx da sua VPS deve repassar as chamadas perfeitamente para a porta do seu servidor Python (geralmente porta `8000`).

Como o próprio Python cuida de remover o prefixo através do middleware, **não é necessário fazer rewrite de URL no Nginx**. Basta passar o tráfego adiante:

No seu arquivo de configuração do site no Nginx (ex: `/etc/nginx/sites-available/meudominio`), adicione o seguinte bloco:

```nginx
server {
    listen 80;
    server_name meudominio.com;

    # Redireciona tudo que cair em /logtudo/ para o FastAPI
    location /logtudo/ {
        proxy_pass http://127.0.0.1:8000;
        
        # Repassa os cabeçalhos originais essenciais
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # IMPORTANTE para Server-Sent Events (Logs ao vivo do LogTudo)
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```

> **Nota sobre o WebSockets/SSE:** O Nginx, por padrão, bufferiza as respostas e fecha conexões lentas. Como a tela de **Logs ao Vivo** do LogTudo usa o `EventSource` (Server-Sent Events), as diretivas `proxy_buffering off` e os tempos longos de `timeout` são cruciais para a barra de progresso e log rodarem em tempo real no navegador sem desconectar.

---

## 4. Checklist de Inicialização na VPS

1. Baixe o código na VPS.
2. Instale os requerimentos do Python e as dependências do Playwright para Linux (`playwright install --with-deps chromium`).
3. Configure o arquivo `.env` incluindo `BASE_PATH=/logtudo` e `SESSION_SECRET="sua_chave_segura"`.
4. Inicie o servidor, por exemplo: `uvicorn webapp.server:app --host 127.0.0.1 --port 8000`.
5. Reinicie o Nginx: `sudo systemctl restart nginx`.
6. Acesse `https://meudominio.com/logtudo/`.