# Kora Backend

FastAPI service for the Revenue Intelligence Platform: auth, organizations, document ingestion and AI-driven financial/qualitative extraction, derived metrics, investment scoring, coverage and validation findings, portfolio analytics, semantic search, and retrieval-augmented chat.

## Environment Setup

This project uses **Python 3.12+**, **FastAPI**, and **uv** for dependency management.

- **Install uv**

```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
```

- **Install dependencies**

```bash
  uv sync
```

- **Copy `.env.example` to `.env`**

```bash
  cp .env.example .env
```

- **Configure required variables**

  At minimum, update the following values in `.env` before running the application:

  | Variable              | Description                                             |
  |------------------------|----------------------------------------------------------|
  | `SECRET_KEY`           | A strong, unique secret (e.g. generate one with `openssl rand -hex 32`) |
  | `POSTGRES_PASSWORD`    | Your local PostgreSQL password                          |
  | `OPENROUTER_API_KEY`   | A valid [OpenRouter](https://openrouter.ai) API key      |

  > Placeholder values (e.g. `generate_a_real_secret_here`, `your_openrouter_api_key_here`) are rejected at startup by validation in `app/config.py`.

## Database

PostgreSQL with the [`pgvector`](https://github.com/pgvector/pgvector) extension (used for document-chunk embeddings powering semantic search and chat). The easiest way to run it locally is the `pgvector/pgvector` Docker image, matching what `docker-compose.production.yml` uses in production:

```bash
docker run -d --name kora-db -p 5432:5432 \
  -e POSTGRES_DB=kora_db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=<your-password> \
  pgvector/pgvector:pg16
```

Migrations are managed with Alembic:

```bash
uv run alembic upgrade head
```

## AI / OpenRouter

All LLM calls (document extraction, chat, embeddings) go through [OpenRouter](https://openrouter.ai)'s OpenAI-compatible API, configured via these `.env` variables:

| Variable                    | Description                                                        |
|-------------------------------|----------------------------------------------------------------------|
| `OPENROUTER_API_KEY`          | Your OpenRouter API key                                              |
| `OPENROUTER_BASE_URL`         | Defaults to `https://openrouter.ai/api/v1`                           |
| `OPENROUTER_CHAT_MODEL`       | Model used for extraction and chat completions (default `openai/gpt-4o-mini`) |
| `OPENROUTER_EMBEDDING_MODEL`  | Model used to embed document chunks (default `openai/text-embedding-3-small`) |
| `EMBEDDING_DIMENSIONS`        | Must match the embedding model's output dimensions (default `1536`)  |
| `OPENROUTER_SITE_URL`         | Optional, sent as `HTTP-Referer` per OpenRouter's attribution convention |
| `OPENROUTER_APP_NAME`         | Optional, sent as `X-Title`                                          |

## Configuration

All configuration is centralized in `app/config.py` using `pydantic-settings`.

- **`get_settings()`**

  A cached accessor, wrapped with `functools.lru_cache`, that returns a singleton `Settings` instance. Because it is cached, the `.env` file and environment variables are parsed only once per process, and the same instance is reused everywhere — including as a FastAPI dependency:

```python
  from fastapi import Depends
  from app.config import Settings, get_settings

  @app.get("/info")
  def info(settings: Settings = Depends(get_settings)):
      return {"app_name": settings.APP_NAME, "env": settings.APP_ENV}
```

- **`DATABASE_URL`**

  A computed property built automatically from the individual `POSTGRES_*` fields (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`). It produces a ready-to-use PostgreSQL DSN:

```python
  settings = get_settings()
  print(settings.DATABASE_URL)
```

- **Configuration loading**

  Settings are loaded from environment variables first, falling back to values defined in `.env`. All values are validated and type-checked at startup — invalid or placeholder values (such as a default `SECRET_KEY` or `OPENROUTER_API_KEY`) raise a clear validation error immediately, preventing misconfigured deployments. `validate_settings_or_exit()` additionally enforces production-only invariants (no `DEBUG=true`, no wildcard CORS origin, a database must be configured) before the app starts accepting requests.

## Running Locally

**Development** (auto-reload):

```bash
uv run fastapi dev app/main.py --port 8000
```

> On Windows, if auto-reload stops picking up changes, stop the process and restart it — this is a known `fastapi dev`/WatchFiles reliability issue on Windows, not a code problem. If the startup banner fails with a console-encoding error, run with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` set first.

**Production:**

```bash
uv run fastapi run app/main.py
```

Once running, the application is available at:

- App: `http://localhost:8000`
- Interactive docs (Swagger UI): `http://localhost:8000/docs`
- Alternative docs (ReDoc): `http://localhost:8000/redoc`

## API Overview

Routers are registered in `app/main.py`, grouped by the tags shown in `/docs`:

| Tag | Router | Covers |
|---|---|---|
| `auth` | `app/api/v1/auth.py` | Registration, login, current-user identity |
| `organizations` | `app/api/v1/organizations.py` | Organizations, memberships, roles, invitations |
| `documents` | `app/api/v1/documents.py` | Upload, AI analysis/extraction, financial facts, scoring, indexing, report export |
| `dashboard` | `app/api/v1/dashboard.py` | Per-organization aggregate statistics |
| `portfolio` | `app/api/v1/portfolio.py` | Portfolio-wide analytics across all analyzed companies |
| `search` | `app/api/v1/search.py` | Semantic search over indexed document chunks |
| `chat` | `app/api/v1/chat.py` | Retrieval-augmented, tool-calling chat over indexed documents |
| `health` | `app/api/v1/health.py` | Liveness/readiness probes |

Business logic lives in `app/services/`, one service per concern (e.g. `financial_analysis_service.py`, `coverage_service.py`, `validation_service.py`, `investment_scoring_service.py`, `chat_v2_service.py`, `report_export_service.py`); `app/models/` holds the SQLAlchemy ORM models and `app/schemas/` the Pydantic request/response schemas.

## Testing

```bash
uv run pytest
```

Tests live in `backend/tests/` (`services/` for unit tests against individual services, `integration/` for end-to-end API tests, `fixtures/` for shared test data).
