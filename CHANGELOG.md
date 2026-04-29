# Changelog

## [Unreleased] — 2026-04-29

### Added

- **`waitUntil` per request** — campo `waitUntil` aceita `"load"` (padrão), `"domcontentloaded"`, `"networkidle"` ou `"commit"`; essencial para SPAs que só terminam de renderizar após chamadas XHR
- **`blockResources` per request** — campo `blockResources` aceita lista de tipos (`"image"`, `"stylesheet"`, `"font"`, `"media"`, etc.) para bloquear recursos e acelerar carregamentos quando só headers importam
- **Proxy por request efêmero** — campo `proxy` em `request.get` / `request.post` sem sessão; antes só era possível via env var global ou sessão nomeada
- **`sessions.get_cookies`** — novo comando que exporta os cookies de uma sessão sem precisar fazer um request de navegação
- **`GET /health`** — endpoint de diagnóstico técnico com: PID, uptime formatado, versão do browser Chromium, estado de conexão, slots de concorrência (max/active/free) e detalhes de cada sessão ativa (proxy, `createdAt`, `lastUsedAt`, `lastUrl`, `requestCount`, páginas abertas)
- **`MAX_CONCURRENT`** — variável de ambiente para limitar o número máximo de páginas abertas em paralelo (padrão `100`); implementado via `asyncio.Semaphore`
- **`session_meta`** — registro interno de metadados por sessão: proxy mascarado, `createdAt`, `lastUsedAt`, `lastUrl`, `requestCount`
- **`_format_uptime()`** — helper que formata segundos em `Xd Xh Xm Xs`

### Fixed

- **`startTimestamp` incorreto** — o campo era calculado no final da função `do_request`; agora é capturado no início, refletindo corretamente o momento em que o request foi iniciado

### Changed

- Log de startup inclui `max_concurrent`
- `do_request` atualiza `session_meta` no bloco `finally` (sempre executa, mesmo em erro)

---

## [Unreleased] — 2026-04-29 (refactor)

### Changed

- **Reestruturação em pacote `app/`** — lógica movida de `server.py` (arquivo único) para módulos dedicados:
  - `app/config.py` — variáveis de ambiente e constantes
  - `app/state.py` — estado global mutável (`sessions`, `session_meta`, `browser`, `semaphore`, `start_time`)
  - `app/utils.py` — `parse_proxy`, `mask_proxy`, `format_uptime`
  - `app/browser.py` — `get_browser`, `get_or_create_session`, `do_request`
  - `app/main.py` — criação do `FastAPI`, lifespan, exception handler, registro de routers
  - `app/routes/health.py` — `GET /` e `GET /health`
  - `app/routes/v1.py` — `POST /v1` (todos os comandos)
- **`server.py`** reduzido a entry point: apenas configura logging e chama `uvicorn.run`
- **Dockerfile** atualizado para copiar `app/` além de `server.py`; adicionado `MAX_CONCURRENT=100` às env vars
- **`compose.yml`** adicionado `MAX_CONCURRENT=100` ao bloco `environment`
