# HeaderHarvest

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat&logo=fastapi&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-1.44-2EAD33?style=flat&logo=playwright&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)

> 🇧🇷 [Português](#português) | 🇺🇸 [English](#english)

---

## Português

API REST compatível com FlareSolverr, construída com **Python + Playwright**, focada em capturar **headers HTTP completos** de qualquer página — incluindo tokens de autenticação disparados pelo próprio JavaScript da página.

Construí isso porque a maioria dos scrapers só captura headers parciais e perde completamente tokens como `Authorization` ou `x-api-key` que aparecem em sub-requests XHR/fetch. Esses tokens são essenciais quando você precisa replicar chamadas de API para extração de dados adequada.

### Funcionalidades

- Captura completa de headers de resposta
- **Interceptação de tokens de auth** em sub-requests (`Authorization`, `x-api-key`, `x-auth-token`, `x-access-token`)
- **Headers customizados** — passe `captureHeaders` para interceptar qualquer header adicional dinamicamente
- **Injeção de JavaScript** — executa código JS na página e retorna o resultado
- **`waitUntil` configurável** — controla quando a navegação é considerada concluída (`load`, `domcontentloaded`, `networkidle`, `commit`)
- **Bloqueio de recursos** — bloqueie imagens, fontes e CSS para cargas mais rápidas quando só precisar de headers
- **Proxy por request** — configure proxy individualmente, sem precisar de sessão
- Sessões persistentes com gerenciamento automático de cookies
- Suporte a proxy HTTP — simples ou autenticado com usuário, zona, senha e afins
- Screenshots de página completa (PNG em base64)
- Endpoint `/v1` compatível com FlareSolverr
- Endpoint `/health` com diagnóstico técnico (PID, uptime, browser, concorrência, sessões)
- Limite de concorrência configurável (`MAX_CONCURRENT`)
- Pronto para Docker

### Início rápido

**Via imagem publicada (recomendado)**

```bash
docker run -d -p 9191:9191 ghcr.io/darkkon2713/header-harvest:latest
```

**Via Docker Compose (build local)**

```bash
docker compose up --build -d
```

Servidor rodando em `http://localhost:9191`.

### API

#### `GET /` — Status

```bash
curl http://localhost:9191/
```

#### `GET /health` — Diagnóstico técnico

```bash
curl http://localhost:9191/health
```

```json
{
  "status": "ok",
  "pid": 12345,
  "uptime": "2h 14m 37s",
  "browser": { "state": "connected", "version": "124.0.6367.82" },
  "proxy": null,
  "concurrency": { "max": 100, "active": 3, "free": 97 },
  "sessions": {
    "count": 1,
    "items": [
      {
        "id": "minha_sessao",
        "pages": 1,
        "proxy": "none",
        "createdAt": 1714400000000,
        "lastUsedAt": 1714401234000,
        "lastUrl": "https://alvo.com",
        "requestCount": 7
      }
    ]
  }
}
```

Útil como healthcheck no Docker Compose:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9191/health"]
  interval: 30s
  timeout: 5s
  retries: 3
```

#### `POST /v1` — Comandos

**Criar sessão** (proxy definido uma vez, vale para todos os requests da sessão)

```bash
curl -X POST http://localhost:9191/v1 \
  -H "Content-Type: application/json" \
  -d '{"cmd": "sessions.create", "session": "minha_sessao", "proxy": "http://host:porta"}'
```

**GET com captura de headers**

```bash
curl -X POST http://localhost:9191/v1 \
  -H "Content-Type: application/json" \
  -d '{
    "cmd": "request.get",
    "url": "https://alvo.com",
    "session": "minha_sessao",
    "maxTimeout": 60000,
    "waitInSeconds": 3,
    "returnScreenshot": false,
    "returnOnlyCookies": false,
    "javaScript": "() => document.title"
  }'
```

**GET com headers customizados** (`captureHeaders` intercepta em requests e responses durante todo o carregamento)

```bash
curl -X POST http://localhost:9191/v1 \
  -H "Content-Type: application/json" \
  -d '{
    "cmd": "request.get",
    "url": "https://alvo.com",
    "session": "minha_sessao",
    "waitInSeconds": 3,
    "captureHeaders": ["visitortoken", "x-custom-token"]
  }'
```

**GET aguardando SPA renderizar** (`networkidle` espera a rede estabilizar)

```bash
curl -X POST http://localhost:9191/v1 \
  -H "Content-Type: application/json" \
  -d '{
    "cmd": "request.get",
    "url": "https://alvo.com",
    "session": "minha_sessao",
    "waitUntil": "networkidle"
  }'
```

**GET com bloqueio de recursos** (mais rápido quando só precisa de headers)

```bash
curl -X POST http://localhost:9191/v1 \
  -H "Content-Type: application/json" \
  -d '{
    "cmd": "request.get",
    "url": "https://alvo.com",
    "blockResources": ["image", "stylesheet", "font"]
  }'
```

**POST**

```bash
curl -X POST http://localhost:9191/v1 \
  -H "Content-Type: application/json" \
  -d '{
    "cmd": "request.post",
    "url": "https://alvo.com/api",
    "session": "minha_sessao",
    "postData": "campo1=valor1&campo2=valor2"
  }'
```

**Listar / destruir / exportar cookies de sessões**

```bash
curl -X POST http://localhost:9191/v1 -H "Content-Type: application/json" \
  -d '{"cmd": "sessions.list"}'

curl -X POST http://localhost:9191/v1 -H "Content-Type: application/json" \
  -d '{"cmd": "sessions.get_cookies", "session": "minha_sessao"}'

curl -X POST http://localhost:9191/v1 -H "Content-Type: application/json" \
  -d '{"cmd": "sessions.destroy", "session": "minha_sessao"}'
```

#### Parâmetros de request

| Parâmetro | Tipo | Padrão | Descrição |
|---|---|---|---|
| `cmd` | string | — | Comando (`request.get`, `request.post`, etc.) |
| `url` | string | — | URL alvo |
| `session` | string | — | ID da sessão |
| `maxTimeout` | int | `60000` | Timeout em ms |
| `waitInSeconds` | int | `0` | Aguarda N segundos após o page load — use para páginas que renderizam conteúdo via JS; `captureHeaders` continua capturando durante esse período |
| `waitUntil` | string | `"load"` | Quando considerar a navegação concluída: `"load"`, `"domcontentloaded"`, `"networkidle"`, `"commit"` |
| `blockResources` | list | `null` | Tipos de recurso a bloquear para cargas mais rápidas (ex: `["image", "stylesheet", "font", "media"]`) |
| `proxy` | string | — | Proxy para este request (efêmero, sem sessão — sobrescreve `PROXY_URL`) |
| `returnScreenshot` | bool | `false` | Retorna screenshot da página completa (base64 PNG) |
| `returnOnlyCookies` | bool | `false` | Retorna apenas cookies, sem body nem headers |
| `javaScript` | string | `null` | Função JS executada na página após o carregamento |
| `captureHeaders` | list | `null` | Headers adicionais a interceptar em todos os sub-requests — busca tanto nos headers de saída quanto nos de resposta (ex: `["visitortoken", "x-custom-token"]`) |
| `cookies` | list | `null` | Cookies customizados a injetar |
| `headers` | dict | `null` | Headers extras para o request |
| `postData` | string | `null` | Body para `request.post` |

#### Formato da resposta

```json
{
  "status": "ok",
  "startTimestamp": 1714400000000,
  "solution": {
    "url": "https://alvo.com",
    "status": 200,
    "headers": {
      "content-type": "text/html; charset=utf-8",
      "set-cookie": "...",
      "authorization": "Bearer eyJ..."
    },
    "cookies": [{ "name": "session", "value": "...", "domain": "alvo.com" }],
    "userAgent": "Mozilla/5.0 ...",
    "title": "Título da Página",
    "response": "<html>...</html>",
    "screenshot": null,
    "javaScriptResult": null
  }
}
```

> `headers` combina os headers de resposta com tokens interceptados dos sub-requests da página.
> `javaScriptResult` contém o valor retornado pela função `javaScript` passada no request.

### Cliente Python

```python
from client import HeaderHarvest

client = HeaderHarvest(server="http://localhost:9191/v1")
session_id = client.create_session(proxy="http://usuario:senha@host:porta")

try:
    # request simples
    res = client.get("https://alvo.com", session_id)
    sol = res.get("solution", {})
    print(sol.get("headers", {}))   # headers completos + tokens interceptados

    # com JS injection para extrair dados da página
    res = client.get(
        "https://alvo.com",
        session_id,
        wait_seconds=3,
        js_code="() => [...document.querySelectorAll('.product')].map(e => e.innerText)"
    )
    print(res.get("solution", {}).get("javaScriptResult"))

    # com screenshot
    res = client.get("https://alvo.com", session_id, screenshot=True)
    import base64
    screenshot_b64 = res.get("solution", {}).get("screenshot")
    if screenshot_b64:
        with open("screenshot.png", "wb") as f:
            f.write(base64.b64decode(screenshot_b64))

    # só cookies (mais rápido)
    res = client.get("https://alvo.com", session_id, only_cookies=True)

finally:
    client.session_destroyer(session_id)
```

### Proxy

O proxy é configurado **uma vez na criação da sessão** e aplicado automaticamente em todos os requests.

Para requests sem sessão, passe `proxy` diretamente no body.

Suporta qualquer proxy no formato URL padrão, incluindo serviços que usam usuário, zona e senha:

```python
# Simples (IP:porta)
client.create_session(proxy="http://148.113.206.58:9999")

# Autenticado (usuário e senha)
client.create_session(proxy="http://usuario:senha@host:porta")

# Com zona (ex: serviços de proxy residencial)
client.create_session(proxy="http://usuario-zona-residential:senha@gateway.provedor.com:porta")
```

Via variável de ambiente (proxy global, vale para todas as sessões):

```yaml
# compose.yml
environment:
  - PROXY_URL=http://usuario:senha@host:porta
```

### Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `PORT` | `9191` | Porta da API |
| `HEADLESS` | `false` | `true` para rodar sem janela (necessário em servidor sem display) |
| `MAX_TIMEOUT` | `60000` | Timeout padrão em ms |
| `MAX_CONCURRENT` | `100` | Número máximo de páginas abertas em paralelo |
| `PROXY_URL` | _(vazio)_ | Proxy global — sobrescrito por sessão ou por request |

### Estrutura do projeto

```
├── app/
│   ├── config.py          # Variáveis de ambiente e constantes
│   ├── state.py           # Estado global (browser, sessions, semaphore)
│   ├── utils.py           # parse_proxy, mask_proxy, format_uptime
│   ├── browser.py         # get_browser, get_or_create_session, do_request
│   ├── main.py            # FastAPI app, lifespan, exception handler
│   └── routes/
│       ├── health.py      # GET / e GET /health
│       └── v1.py          # POST /v1 (todos os comandos)
├── server.py              # Entry point (uvicorn.run)
├── requirements.txt
├── Dockerfile
├── compose.yml
├── .dockerignore
├── examples/
│   ├── client.py          # Classe HeaderHarvest
│   ├── test.py            # Exemplo de uso
│   └── requirements.txt   # requests
└── LICENSE
```

Para adicionar novos comandos: crie ou edite um arquivo em `app/routes/` e registre o router em `app/main.py`.

### HeaderHarvest vs FlareSolverr

| Funcionalidade | FlareSolverr | HeaderHarvest |
|---|---|---|
| Headers completos | Parcial | Todos |
| Interceptação de tokens de auth | Não | Sim (XHR/fetch) |
| Headers customizados a interceptar | Não | Sim (`captureHeaders`) |
| `waitUntil` configurável | Não | Sim (`load`, `networkidle`, etc.) |
| Bloqueio de recursos | Não | Sim (`blockResources`) |
| Proxy por request (sem sessão) | Não | Sim |
| Exportar cookies de sessão | Não | Sim (`sessions.get_cookies`) |
| Health check técnico | Não | Sim (`GET /health`) |
| Injeção de JavaScript | Não | Sim |
| `waitInSeconds` | Sim | Sim |
| `returnOnlyCookies` | Sim | Sim |
| Screenshots (página completa) | Não | Sim |
| Sessões | Sim | Sim |
| POST requests | Sim | Sim |
| Cookies customizados | Sim | Sim |
| Proxy por sessão | Não | Sim |
| Linguagem | Node.js | Python |

---

## English

REST API compatible with FlareSolverr, built with **Python + Playwright**, focused on capturing **complete HTTP headers** from any page — including auth tokens fired by the page's own JavaScript.

I built this because most scrapers only capture partial response headers and completely miss tokens like `Authorization` or `x-api-key` that appear in XHR/fetch sub-requests. Those tokens are essential when you need to replicate API calls for proper data extraction.

### Features

- Full response header capture
- **Auth token interception** from sub-requests (`Authorization`, `x-api-key`, `x-auth-token`, `x-access-token`)
- **Custom header capture** — pass `captureHeaders` in the request to intercept any additional header dynamically
- **JavaScript injection** — run JS on the page and return the result
- **Configurable `waitUntil`** — control when navigation is considered complete (`load`, `domcontentloaded`, `networkidle`, `commit`)
- **Resource blocking** — block images, fonts and CSS for faster loads when you only need headers
- **Per-request proxy** — set a proxy per request without needing a session
- Persistent sessions with automatic cookie management
- HTTP proxy support — plain or authenticated with user, zone, password, etc.
- Full-page screenshots (base64 PNG)
- FlareSolverr-compatible `/v1` endpoint — drop-in replacement
- `/health` endpoint with technical diagnostics (PID, uptime, browser, concurrency, sessions)
- Configurable concurrency limit (`MAX_CONCURRENT`)
- Docker ready

### Quickstart

**Using the published image (recommended)**

```bash
docker run -d -p 9191:9191 ghcr.io/darkkon2713/header-harvest:latest
```

**Via Docker Compose (local build)**

```bash
docker compose up --build -d
```

Server runs on `http://localhost:9191`.

### API

#### `GET /` — Status

```bash
curl http://localhost:9191/
```

#### `GET /health` — Technical diagnostics

```bash
curl http://localhost:9191/health
```

```json
{
  "status": "ok",
  "pid": 12345,
  "uptime": "2h 14m 37s",
  "browser": { "state": "connected", "version": "124.0.6367.82" },
  "proxy": null,
  "concurrency": { "max": 100, "active": 3, "free": 97 },
  "sessions": {
    "count": 1,
    "items": [
      {
        "id": "my_session",
        "pages": 1,
        "proxy": "none",
        "createdAt": 1714400000000,
        "lastUsedAt": 1714401234000,
        "lastUrl": "https://target.com",
        "requestCount": 7
      }
    ]
  }
}
```

Useful as a Docker Compose healthcheck:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9191/health"]
  interval: 30s
  timeout: 5s
  retries: 3
```

#### `POST /v1` — Commands

**Create session** (proxy set once, applies to all requests on that session)

```bash
curl -X POST http://localhost:9191/v1 \
  -H "Content-Type: application/json" \
  -d '{"cmd": "sessions.create", "session": "my_session", "proxy": "http://host:port"}'
```

**GET with full header capture**

```bash
curl -X POST http://localhost:9191/v1 \
  -H "Content-Type: application/json" \
  -d '{
    "cmd": "request.get",
    "url": "https://target.com",
    "session": "my_session",
    "maxTimeout": 60000,
    "waitInSeconds": 3,
    "returnScreenshot": false,
    "returnOnlyCookies": false,
    "javaScript": "() => document.title"
  }'
```

**GET with custom headers** (`captureHeaders` intercepts from requests and responses throughout the entire load)

```bash
curl -X POST http://localhost:9191/v1 \
  -H "Content-Type: application/json" \
  -d '{
    "cmd": "request.get",
    "url": "https://target.com",
    "session": "my_session",
    "waitInSeconds": 3,
    "captureHeaders": ["visitortoken", "x-custom-token"]
  }'
```

**GET waiting for SPA to render** (`networkidle` waits for network to settle)

```bash
curl -X POST http://localhost:9191/v1 \
  -H "Content-Type: application/json" \
  -d '{
    "cmd": "request.get",
    "url": "https://target.com",
    "session": "my_session",
    "waitUntil": "networkidle"
  }'
```

**GET with resource blocking** (faster when you only need headers)

```bash
curl -X POST http://localhost:9191/v1 \
  -H "Content-Type: application/json" \
  -d '{
    "cmd": "request.get",
    "url": "https://target.com",
    "blockResources": ["image", "stylesheet", "font"]
  }'
```

**POST**

```bash
curl -X POST http://localhost:9191/v1 \
  -H "Content-Type: application/json" \
  -d '{
    "cmd": "request.post",
    "url": "https://target.com/api",
    "session": "my_session",
    "postData": "field1=value1&field2=value2"
  }'
```

**List / destroy / export cookies from sessions**

```bash
curl -X POST http://localhost:9191/v1 -H "Content-Type: application/json" \
  -d '{"cmd": "sessions.list"}'

curl -X POST http://localhost:9191/v1 -H "Content-Type: application/json" \
  -d '{"cmd": "sessions.get_cookies", "session": "my_session"}'

curl -X POST http://localhost:9191/v1 -H "Content-Type: application/json" \
  -d '{"cmd": "sessions.destroy", "session": "my_session"}'
```

#### Request parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `cmd` | string | — | Command (`request.get`, `request.post`, etc.) |
| `url` | string | — | Target URL |
| `session` | string | — | Session ID |
| `maxTimeout` | int | `60000` | Timeout in ms |
| `waitInSeconds` | int | `0` | Wait N seconds after page load — use for pages that render content via JS after load; `captureHeaders` keeps capturing throughout this period |
| `waitUntil` | string | `"load"` | When to consider navigation complete: `"load"`, `"domcontentloaded"`, `"networkidle"`, `"commit"` |
| `blockResources` | list | `null` | Resource types to block for faster loads (e.g. `["image", "stylesheet", "font", "media"]`) |
| `proxy` | string | — | Proxy for this request (ephemeral, no session — overrides `PROXY_URL`) |
| `returnScreenshot` | bool | `false` | Return full-page screenshot (base64 PNG) |
| `returnOnlyCookies` | bool | `false` | Return only cookies, skip body and headers |
| `javaScript` | string | `null` | JS function evaluated on the page after load |
| `captureHeaders` | list | `null` | Additional headers to intercept from all sub-requests — scans both outgoing request headers and response headers (e.g. `["visitortoken", "x-custom-token"]`) |
| `cookies` | list | `null` | Custom cookies to inject |
| `headers` | dict | `null` | Extra request headers |
| `postData` | string | `null` | Body for `request.post` |

#### Response format

```json
{
  "status": "ok",
  "startTimestamp": 1714400000000,
  "solution": {
    "url": "https://target.com",
    "status": 200,
    "headers": {
      "content-type": "text/html; charset=utf-8",
      "set-cookie": "...",
      "authorization": "Bearer eyJ..."
    },
    "cookies": [{ "name": "session", "value": "...", "domain": "target.com" }],
    "userAgent": "Mozilla/5.0 ...",
    "title": "Page Title",
    "response": "<html>...</html>",
    "screenshot": null,
    "javaScriptResult": null
  }
}
```

> `headers` merges response headers with any auth tokens intercepted from the page's sub-requests.
> `javaScriptResult` contains the return value of the `javaScript` function passed in the request.

### Python Client

```python
from client import HeaderHarvest

client = HeaderHarvest(server="http://localhost:9191/v1")
session_id = client.create_session(proxy="http://user:password@host:port")

try:
    # simple request
    res = client.get("https://target.com", session_id)
    sol = res.get("solution", {})
    print(sol.get("headers", {}))   # all headers + intercepted auth tokens

    # JS injection to extract page data
    res = client.get(
        "https://target.com",
        session_id,
        wait_seconds=3,
        js_code="() => [...document.querySelectorAll('.product')].map(e => e.innerText)"
    )
    print(res.get("solution", {}).get("javaScriptResult"))

    # with screenshot
    res = client.get("https://target.com", session_id, screenshot=True)
    import base64
    screenshot_b64 = res.get("solution", {}).get("screenshot")
    if screenshot_b64:
        with open("screenshot.png", "wb") as f:
            f.write(base64.b64decode(screenshot_b64))

    # cookies only (faster)
    res = client.get("https://target.com", session_id, only_cookies=True)

finally:
    client.session_destroyer(session_id)
```

### Proxy

Proxy is configured **once at session creation** and automatically applied to all requests.

For sessionless requests, pass `proxy` directly in the request body.

Supports any proxy in standard URL format, including services that use username, zone and password:

```python
# Plain (IP:port)
client.create_session(proxy="http://148.113.206.58:9999")

# Authenticated (user + password)
client.create_session(proxy="http://user:password@host:port")

# With zone (e.g. residential proxy services)
client.create_session(proxy="http://user-zone-residential:password@gateway.provider.com:port")
```

Global proxy via environment variable (applies to all sessions by default):

```yaml
# compose.yml
environment:
  - PROXY_URL=http://user:password@host:port
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `9191` | API port |
| `HEADLESS` | `false` | Set `true` to run without a window (required on headless servers) |
| `MAX_TIMEOUT` | `60000` | Default request timeout in ms |
| `MAX_CONCURRENT` | `100` | Maximum number of browser pages open in parallel |
| `PROXY_URL` | _(empty)_ | Global proxy — overridden per session or per request |

### Project Structure

```
├── app/
│   ├── config.py          # Environment variables and constants
│   ├── state.py           # Global state (browser, sessions, semaphore)
│   ├── utils.py           # parse_proxy, mask_proxy, format_uptime
│   ├── browser.py         # get_browser, get_or_create_session, do_request
│   ├── main.py            # FastAPI app, lifespan, exception handler
│   └── routes/
│       ├── health.py      # GET / and GET /health
│       └── v1.py          # POST /v1 (all commands)
├── server.py              # Entry point (uvicorn.run)
├── requirements.txt
├── Dockerfile
├── compose.yml
├── .dockerignore
├── examples/
│   ├── client.py          # HeaderHarvest class
│   ├── test.py            # Usage example
│   └── requirements.txt   # requests
└── LICENSE
```

To add new commands: create or edit a file in `app/routes/` and register the router in `app/main.py`.

### HeaderHarvest vs FlareSolverr

| Feature | FlareSolverr | HeaderHarvest |
|---|---|---|
| Full response headers | Partial | All |
| Auth token interception | No | Yes (XHR/fetch) |
| Custom headers to intercept | No | Yes (`captureHeaders`) |
| Configurable `waitUntil` | No | Yes (`load`, `networkidle`, etc.) |
| Resource blocking | No | Yes (`blockResources`) |
| Per-request proxy (no session) | No | Yes |
| Export session cookies | No | Yes (`sessions.get_cookies`) |
| Technical health check | No | Yes (`GET /health`) |
| JavaScript injection | No | Yes |
| `waitInSeconds` | Yes | Yes |
| `returnOnlyCookies` | Yes | Yes |
| Full-page screenshots | No | Yes |
| Sessions | Yes | Yes |
| POST requests | Yes | Yes |
| Custom cookies | Yes | Yes |
| Proxy per session | No | Yes |
| Language | Node.js | Python |

---

## License

MIT — see [LICENSE](LICENSE)
