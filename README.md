# Kora — AI Due-Diligence Copilot

Kora turns a company's raw pitch deck or financial documents into a structured, evidence-backed due-diligence profile — automatically extracted, automatically checked for internal inconsistencies, and always traceable back to the original source text.

It is an independently designed and built product: backend, data model, AI pipeline, and frontend design system are all original work, built end-to-end by one person.

## The problem

Early-stage due diligence is still mostly manual. An analyst opens a pitch deck, reads it, re-types the numbers into a spreadsheet, cross-checks whether the growth story actually adds up, and separately keeps a mental list of what the founder still hasn't disclosed. That process is slow, inconsistent between analysts, and easy to get wrong — a plausible-sounding deck is not the same as an internally consistent one, and it's easy to miss that "12-month runway" and "$1M/month burn" and "$6M cash" don't actually agree with each other.

Kora automates the mechanical part of that process — extraction, consistency checking, gap-finding — so a human analyst spends their time on judgment instead of data entry, while every number Kora shows stays traceable back to the sentence it came from.

## Who it's for

Kora is built for the analyst side of early-stage investing and corporate development: VC/angel analysts, individual investors, and deal teams who need to triage a stack of pitch decks and financial documents and quickly decide which ones deserve a deeper look — without a large associate team to do the first pass for them.

## How it works

**Document → Extract → Validate → Analyze → Ask → Report**

1. **Document** — an analyst uploads a pitch deck, financial statement, or data-room export (PDF, DOCX, or TXT) into an organization (a workspace shared with their team).
2. **Extract** — an LLM extracts structured financial facts (revenue, ARR, MRR, burn rate, runway, CAC, LTV, and more) and qualitative facts (business model, market, team, risks), each one tied back to the page/passage it was extracted from via a source citation — not just a number floating with no provenance.
3. **Validate** — a separate, deterministic (non-LLM) rules engine checks the extracted facts against each other: does the stated LTV:CAC ratio match what the underlying numbers actually compute to? Is a growth claim backed by more than one data point? Is a "profitable" claim contradicted by the reported net income? These checks are plain Python business logic, unit-tested, and never delegated to a model that could talk itself into a wrong answer.
4. **Analyze** — Kora assesses evidence coverage against a due-diligence checklist (company, financial, market, team), computes a category-weighted investment score from the verified facts — and deliberately withholds that score, showing no number instead of a misleading one, when coverage is too thin or critical fields are missing.
5. **Ask** — once a document is indexed, the analyst can ask an AI chat assistant follow-up questions grounded in the source documents (retrieval-augmented generation), with every answer citing the passages it drew from — including an "analytical" mode that can query the extracted financial data directly instead of only paraphrasing text.
6. **Report** — the full analysis — extracted facts, findings, coverage, score, and cited chat context — can be exported as a due-diligence report (Markdown or PDF), and every analyzed document rolls up into a per-organization portfolio view.

## Key capabilities

- AI-driven extraction of financial and qualitative facts, each with a source citation back to the original document
- Deterministic validation findings (inconsistency checks) that are always distinguished in the UI from the LLM's own document-stated facts and inferences
- A due-diligence coverage checklist that explicitly shows what's missing and why it matters, not just what was found
- An investment score that can be null by design — Kora never fabricates a number on thin evidence
- Retrieval-augmented chat with citations, plus a tool-calling mode that computes answers from real extracted data
- Exportable due-diligence reports (Markdown / PDF), with two report formats (a narrative report and an evidence-grounded report with verified facts, red flags, and founder questions)
- Multi-organization workspaces with role-based membership and portfolio-level analytics across every analyzed company

## Tech stack

**Backend** — Python 3.12, FastAPI, SQLAlchemy 2.0 (async) + Alembic, PostgreSQL with the `pgvector` extension for embeddings, JWT auth (`pwdlib`/argon2 password hashing), LLM calls (extraction, chat, embeddings) routed through [OpenRouter](https://openrouter.ai)'s OpenAI-compatible API, `pypdf`/`reportlab` for document parsing and PDF report generation. Tested with `pytest` (203 tests across services and integration).

**Frontend** — Next.js 15 (App Router) with React 19 and TypeScript, TanStack Query for server state, a custom dark-themed "Kora" component library (Radix UI primitives underneath), Tailwind CSS.

**Infrastructure** — Docker Compose (PostgreSQL/pgvector + FastAPI backend), local filesystem document storage behind a storage-backend interface designed for a future S3-compatible swap.

See [`docs/architecture.md`](docs/architecture.md) for the full system diagram and a walkthrough of how the pieces fit together, and [`docs/product-case-study.md`](docs/product-case-study.md) for the product reasoning behind the platform, including honest trade-offs and current limitations.

## Repository layout

```
kora-platform/
├── backend/     FastAPI + PostgreSQL (pgvector) API — see backend/README.md
├── frontend/    Next.js 15 app (the Kora UI)         — see frontend/README.md
├── docs/        Architecture, product, and UI documentation
├── docker/      Container assets for deployment
└── docker-compose.production.yml
```

## Getting started

```bash
# Backend — see backend/README.md for full setup
cd backend
uv sync
cp .env.example .env   # then fill in SECRET_KEY, POSTGRES_PASSWORD, OPENROUTER_API_KEY
uv run alembic upgrade head
uv run fastapi dev app/main.py --port 8000

# Frontend — see frontend/README.md for full setup
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3000`, the backend at `http://localhost:8000` (interactive API docs at `/docs`). See [backend/README.md](backend/README.md) for database setup (a local `pgvector/pgvector` Docker container is the fastest path) and required environment variables.

## Documentation

- [`docs/product-case-study.md`](docs/product-case-study.md) — the problem, the users, the product decisions, and honest trade-offs/limitations
- [`docs/architecture.md`](docs/architecture.md) — system diagram, workflow diagram, and a short walkthrough of each layer
- [`docs/portfolio-description.md`](docs/portfolio-description.md) — CV/portfolio/interview-ready descriptions of this project
- [`backend/README.md`](backend/README.md) — backend setup, configuration, running locally, API overview
- [`frontend/README.md`](frontend/README.md) — frontend setup, environment, scripts
- [`docs/ui/design-system.md`](docs/ui/design-system.md) — the Kora visual design system (tokens, primitives, usage)
- [`docs/company/`](docs/company/) and [`docs/prd/`](docs/prd/) — earlier product/business planning documents from an initial concept exploration that predates the current implementation; kept for history, not a spec of the shipped product

## License

See [`LICENSE`](LICENSE).
