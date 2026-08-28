# Kora Frontend

The Kora UI: a Next.js 15 (App Router) / React 19 application implementing the Kora design system (dark theme, Geist + JetBrains Mono, glowing accent panels — see [`docs/ui/design-system.md`](../docs/ui/design-system.md)). It talks to the backend exclusively through the typed API client in `src/lib/api-client.ts` and the per-feature hooks under `src/features/*` — there is no local business logic or sample/mock data; every screen is wired to real backend endpoints.

## Environment Setup

This project uses **Node.js** and **npm**.

- **Install dependencies**

```bash
npm install
```

- **Copy `.env.local.example` to `.env.local`**

```bash
cp .env.local.example .env.local
```

- **Configure required variables**

  | Variable | Description |
  |---|---|
  | `NEXT_PUBLIC_API_BASE_URL` | Base URL of the running FastAPI backend, no trailing slash (e.g. `http://localhost:8000`) |

  Access is validated and typed through `src/lib/env.ts`, which throws immediately at startup if `NEXT_PUBLIC_API_BASE_URL` is missing, rather than letting `undefined` silently propagate into API calls.

## Running Locally

```bash
npm run dev
```

The app runs at `http://localhost:3000` and expects the backend (see `backend/README.md`) to be running and reachable at `NEXT_PUBLIC_API_BASE_URL`.

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start the Next.js dev server |
| `npm run build` | Production build |
| `npm run start` | Serve a production build |
| `npm run lint` | Run ESLint |
| `npm run typecheck` | Run `tsc --noEmit` |

## Project structure

```
src/
├── app/                 Next.js App Router routes
│   ├── (auth)/           login, register — unauthenticated
│   └── (protected)/       documents, portfolio, members, settings, profile, accept-invitation
├── components/
│   ├── kora/              Design-system primitives (primitives.tsx) and screen components
│   └── layout/             App shell, sidebar, topbar
├── features/            One folder per domain: api.ts (typed backend calls) + hooks.ts (React Query) + components/
│   ├── auth/, documents/, organizations/, portfolio/, chat/
├── lib/                 api-client.ts (Axios instance + auth interceptor), env.ts, query-client.ts, utils.ts
└── providers.tsx        App-wide providers (React Query, toasts, auth context)
```

Each `features/<domain>` folder owns its own API calls and React Query hooks; screens under `components/kora/screens` are presentational and receive data via props from the pages in `app/(protected)/*` that call those hooks. New screens should follow this pattern rather than fetching data directly inside a screen component.

## Design system

The visual language (colors, type, spacing, and the primitive components — `Panel`, `PrimaryButton`, `GhostButton`, `Badge`, `Tabs`, `Meter`, etc. — all in `src/components/kora/primitives.tsx`) is documented in [`docs/ui/design-system.md`](../docs/ui/design-system.md). Use the existing primitives for new UI rather than reaching for raw shadcn/Radix components or one-off Tailwind classes — geometric, non-figurative glyphs are used in place of an icon library throughout.
