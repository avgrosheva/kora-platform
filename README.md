# Kora — Revenue Intelligence Platform

Kora is an internal due-diligence tool for evaluating companies from their financial documents. An analyst uploads a company's pitch deck, financial statements, or data-room exports; Kora extracts structured financial and qualitative facts with an LLM, computes derived metrics and an investment score, flags data-quality issues and validation findings, tracks what information is still missing, and lets the analyst ask follow-up questions in an AI chat that is grounded in the indexed source documents (retrieval-augmented, with citations back to the original text). Findings roll up across every document into per-organization coverage and portfolio views, and the whole analysis can be exported as a due-diligence report (Markdown or PDF).

## Repository layout

```
kora-platform/
├── backend/     FastAPI + PostgreSQL (pgvector) API — see backend/README.md
├── frontend/    Next.js 15 app (the Kora UI)         — see frontend/README.md
├── docs/        Architecture, UI, and product documentation
├── docker/      Container assets for deployment
└── docker-compose.production.yml
```

## How it fits together

- **Backend** (`backend/`) — a FastAPI service backed by PostgreSQL with the `pgvector` extension. It owns auth, organizations/members, document ingestion and AI-driven extraction, financial metrics and investment scoring, portfolio analytics, semantic search, and retrieval-augmented chat. LLM calls (extraction, chat, embeddings) go through [OpenRouter](https://openrouter.ai). See `backend/README.md` for setup.
- **Frontend** (`frontend/`) — a Next.js 15 / React 19 app that implements the Kora design system (dark theme, Geist + JetBrains Mono, glowing accent panels — see `docs/ui/design-system.md`) and talks to the backend exclusively through its typed API client; it holds no business logic or sample data of its own. See `frontend/README.md` for setup.

### Core workflow

1. **Upload a document** to an organization. The backend extracts text and runs it through the AI extraction pipeline to produce financial facts, qualitative facts, and source citations.
2. **Coverage** is assessed against a checklist of expected company/market fields, so an analyst can see at a glance what's still missing.
3. **Findings** (validation issues — inconsistent numbers, suspicious values, unsupported claims) are raised against the extracted facts.
4. **Derived metrics and an investment score** are computed from the verified facts.
5. A due-diligence **report** can be generated and exported (Markdown/PDF) from the above.
6. Once a document is indexed for retrieval, the analyst can **chat** with an AI assistant that answers questions grounded in the source documents, citing the passages it used.
7. Across an organization, all analyzed companies roll up into a **portfolio** view for cross-company comparison.

## Getting started

```bash
# Backend — see backend/README.md for full setup
cd backend
uv sync
cp .env.example .env   # then fill in SECRET_KEY, POSTGRES_PASSWORD, OPENROUTER_API_KEY
uv run fastapi dev app/main.py --port 8000

# Frontend — see frontend/README.md for full setup
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3000`, the backend at `http://localhost:8000` (interactive API docs at `/docs`).

## Documentation

- [`backend/README.md`](backend/README.md) — backend setup, configuration, running locally
- [`frontend/README.md`](frontend/README.md) — frontend setup, environment, scripts
- [`docs/ui/design-system.md`](docs/ui/design-system.md) — the Kora visual design system (tokens, primitives, usage)
- [`docs/architecture/`](docs/architecture/) — architecture and data-model notes
- [`docs/company/`](docs/company/) and [`docs/prd/`](docs/prd/) — earlier product/business planning documents (predate parts of the current implementation; not guaranteed to match the shipped product 1:1)

## License

See [`LICENSE`](LICENSE).
