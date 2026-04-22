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
- **Injeção de JavaScript** — executa código JS na página e retorna o resultado
- Sessões persistentes com gerenciamento automático de cookies
- Suporte a proxy HTTP — simples ou autenticado com usuário, zona, senha e afins
- Screenshots de página completa (PNG em base64)
- Endpoint `/v1` compatível com FlareSolverr
- Pronto para Docker

### Início rápido

**Via imagem publicada (recomendado):**

```bash
docker run -d -p 9191:9191 ghcr.io/leonardowg/header-harvest:latest
```

Porta customizada:

```bash
docker run -d -p 8080:8080 -e PORT=8080 ghcr.io/leonardowg/header-harvest:latest
```

**Via código-fonte:**

```bash
docker compose up --build -d
```

Servidor rodando em `http://localhost:9191`.

### API

#### `GET /` — Status

```bash
curl http://localhost:9191/
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

**Listar / destruir sessões**

```bash
curl -X POST http://localhost:9191/v1 -H "Content-Type: application/json" \
  -d '{"cmd": "sessions.list"}'

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
| `waitInSeconds` | int | `0` | Aguarda N segundos após o page load — use para páginas que renderizam conteúdo via JS após o carregamento |
| `returnScreenshot` | bool | `false` | Retorna screenshot da página completa (base64 PNG) |
| `returnOnlyCookies` | bool | `false` | Retorna apenas cookies, sem body nem headers |
| `javaScript` | string | `null` | Função JS executada na página após o carregamento |
| `cookies` | list | `null` | Cookies customizados a injetar |
| `headers` | dict | `null` | Headers extras para o request |
| `postData` | string | `null` | Body para `request.post` |

#### Formato da resposta

```json
{
  "status": "ok",
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
| `PROXY_URL` | _(vazio)_ | Proxy global — sobrescrito por sessão |

### Estrutura do projeto

```
├── server.py              # Servidor FastAPI + Playwright
├── requirements.txt
├── dockerfile
├── compose.yml
├── examples/
│   ├── client.py          # Classe HeaderHarvest
│   └── test.py            # Exemplo de uso
└── LICENSE
```

### HeaderHarvest vs FlareSolverr

| Funcionalidade | FlareSolverr | HeaderHarvest |
|---|---|---|
| Headers completos | Não | Todos |
| Interceptação de tokens de auth | Não | Sim (XHR/fetch) |
| Injeção de JavaScript | Não | Sim |
| waitInSeconds | Sim | Sim |
| returnOnlyCookies | Sim | Sim |
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
- **JavaScript injection** — run JS on the page and return the result
- Persistent sessions with automatic cookie management
- HTTP proxy support — plain or authenticated with user, zone, password, etc.
- Full-page screenshots (base64 PNG)
- FlareSolverr-compatible `/v1` endpoint — drop-in replacement
- Docker ready

### Quickstart

**From published image (recommended):**

```bash
docker run -d -p 9191:9191 ghcr.io/leonardowg/header-harvest:latest
```

Custom port:

```bash
docker run -d -p 8080:8080 -e PORT=8080 ghcr.io/leonardowg/header-harvest:latest
```

**From source:**

```bash
docker compose up --build -d
```

Server runs on `http://localhost:9191`.

### API

#### `GET /` — Status

```bash
curl http://localhost:9191/
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

**List / destroy sessions**

```bash
curl -X POST http://localhost:9191/v1 -H "Content-Type: application/json" \
  -d '{"cmd": "sessions.list"}'

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
| `waitInSeconds` | int | `0` | Wait N seconds after page load — use for pages that render content via JS after load |
| `returnScreenshot` | bool | `false` | Return full-page screenshot (base64 PNG) |
| `returnOnlyCookies` | bool | `false` | Return only cookies, skip body and headers |
| `javaScript` | string | `null` | JS function evaluated on the page after load |
| `cookies` | list | `null` | Custom cookies to inject |
| `headers` | dict | `null` | Extra request headers |
| `postData` | string | `null` | Body for `request.post` |

#### Response format

```json
{
  "status": "ok",
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
| `PROXY_URL` | _(empty)_ | Global proxy — overridden per session |

### Project Structure

```
├── server.py              # FastAPI + Playwright server
├── requirements.txt
├── dockerfile
├── compose.yml
├── examples/
│   ├── client.py          # HeaderHarvest class
│   └── test.py            # Usage example
└── LICENSE
```

### HeaderHarvest vs FlareSolverr

| Feature | FlareSolverr | HeaderHarvest |
|---|---|---|
| Full response headers | Partial | All |
| Auth token interception | No | Yes (XHR/fetch) |
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
