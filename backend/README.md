# Environment Setup

This project uses **Python 3.13**, **FastAPI**, and **uv** for dependency management.

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

  | Variable            | Description                               |
  |----------------------|-------------------------------------------|
  | `SECRET_KEY`         | A strong, unique secret (e.g. generate one with `openssl rand -hex 32`) |
  | `POSTGRES_PASSWORD`  | Your local PostgreSQL password            |
  | `OPENAI_API_KEY`     | A valid OpenAI API key                    |

  > Placeholder values (e.g. `generate_a_real_secret_here`, `your_openai_api_key_here`) are rejected at startup by validation in `app/config.py`.

# Configuration

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

  Settings are loaded from environment variables first, falling back to values defined in `.env`. All values are validated and type-checked at startup — invalid or placeholder values (such as a default `SECRET_KEY` or `OPENAI_API_KEY`) raise a clear validation error immediately, preventing misconfigured deployments.

# Running Locally

**Development:**

```bash
uv run fastapi dev app/main.py
```

**Production:**

```bash
uv run fastapi run app/main.py
```

Once running, the application is available at:

- App: `http://localhost:8000`
- Interactive docs (Swagger UI): `http://localhost:8000/docs`
- Alternative docs (ReDoc): `http://localhost:8000/redoc`