# PerX Challenge — Project Rules for AI Coding Assistants

## What We're Building
PerX is an AI-native three-sided employee benefits marketplace.
- **Employees** browse and select perks (the consumers)
- **Employers** set budgets and approve selections (the budget authority)
- **Providers** list their services on the marketplace (the suppliers)

There is also an **Admin** role for platform management.

## Stack (DO NOT deviate from these versions)
- **Backend**: Python 3.11+, FastAPI 0.111+, Pydantic v2
- **ORM**: SQLAlchemy 2.0 (async, use `AsyncSession`)
- **DB**: PostgreSQL 16, Redis 7
- **Recommendation**: scikit-surprise 1.1.3, implicit 0.7, lightgbm 4.3
- **LLM**: Ollama (local) via `httpx` — model `gemma2:2b` or `llama3.2:3b`
- **Optimizer**: PuLP 2.8 (knapsack solver)
- **Frontend**: React 18 + Vite 5, TypeScript 5, Three.js r165 via @react-three/fiber
- **Styling**: Tailwind CSS 3.4, Framer Motion 11
- **PWA**: Vite PWA Plugin (Workbox 7), Dexie.js (IndexedDB)
- **Infra**: Docker Compose, Traefik v3, Cloudflare Tunnel

## Code Style
- Python: Black formatter, isort imports, type hints everywhere, docstrings on all public functions
- TypeScript: strict mode ON, no `any`, named exports preferred over default exports
- All API responses use the envelope: `{ "data": ..., "meta": { "timestamp": ..., "request_id": ... } }`
- All errors use: `{ "error": { "code": "SNAKE_CASE_CODE", "message": "...", "details": {} } }`
- Database IDs are UUIDs (uuid4), never sequential integers (except internal join tables)
- Timestamps: always UTC, always stored as `TIMESTAMP WITH TIME ZONE`

## Key Architecture Decisions
- Auth is JWT (HS256). Access token: 15 min. Refresh token: 7 days. Role is embedded in the JWT payload as `role`.
- Budget state is dual-written: Postgres (source of truth) + Redis (fast cache). The cache key is `budget:{employer_id}:{employee_id}:{YYYY-MM}`.
- The LLM is NEVER in the critical path. All LLM calls are async fire-and-forget or background tasks.
- The recommender has two modes: `cold_start` (rules-based, instant) and `warm` (ML model, async). Switch is determined by `interaction_count >= 10`.
- Provider ranking has two modes: `bootstrap` (weighted heuristic, always available) and `ltr` (LambdaMART, requires 100+ feedback events).
- All background jobs use FastAPI `BackgroundTasks` for hackathon scope. Celery is the upgrade path.
- The 0/1 Knapsack only runs on `plan_optimize` calls (multi-perk wishlist). Single-perk `quick_add` skips it entirely.

## Directory Structure
```
perx/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── database.py          # AsyncSession factory
│   │   ├── auth/                # JWT + middleware
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── routers/             # FastAPI routers by domain
│   │   │   ├── auth.py
│   │   │   ├── employees.py
│   │   │   ├── employers.py
│   │   │   ├── providers.py
│   │   │   ├── perks.py
│   │   │   ├── recommendations.py
│   │   │   ├── budget.py
│   │   │   └── analytics.py
│   │   ├── services/            # Business logic layer
│   │   │   ├── recommendation/
│   │   │   │   ├── cold_start.py    # Rules engine + LLM wrapper
│   │   │   │   ├── hybrid.py        # MV-ICTR hybrid recommender
│   │   │   │   └── bandits.py       # UCB exploration
│   │   │   ├── optimizer/
│   │   │   │   ├── knapsack.py      # PuLP 0/1 knapsack
│   │   │   │   └── quick_add.py     # Redis balance check
│   │   │   ├── ranking/
│   │   │   │   ├── bootstrap.py     # Weighted heuristic
│   │   │   │   └── ltr.py           # LightGBM LambdaMART
│   │   │   └── notifications.py     # Push notifications (pywebpush)
│   │   └── utils/
│   │       ├── redis.py
│   │       ├── ollama.py
│   │       └── pagination.py
│   ├── alembic/                 # DB migrations
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── portals/             # Three separate portal apps
│   │   │   ├── employee/
│   │   │   ├── employer/
│   │   │   └── provider/
│   │   ├── components/
│   │   │   ├── 3d/              # Three.js / R3F components
│   │   │   │   └── BenefitGlobe.tsx
│   │   │   ├── ui/              # Reusable UI components
│   │   │   └── pwa/             # PWA-specific components
│   │   ├── hooks/
│   │   ├── stores/              # Zustand state
│   │   ├── api/                 # Typed API client (auto-generated from OpenAPI)
│   │   ├── db/                  # Dexie.js (IndexedDB for offline)
│   │   └── sw/                  # Service Worker (Workbox config)
│   ├── public/
│   │   └── manifest.json
│   ├── vite.config.ts
│   └── Dockerfile
├── infra/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── traefik/
│       └── traefik.yml
└── CLAUDE.md                    # This file
```

## What to NEVER do
- NEVER put business logic in routers. Routers call services. Services contain logic.
- NEVER use `db.commit()` inside a service — let the router/dependency handle the session lifecycle.
- NEVER call Ollama synchronously. Always use `httpx.AsyncClient` and wrap in `BackgroundTasks`.
- NEVER store raw passwords. Always bcrypt via `passlib[bcrypt]`.
- NEVER trust the frontend for budget math. Budget checks always re-run server-side.
- NEVER run the 0/1 Knapsack on a single-item selection — use `quick_add` instead.
- NEVER expose provider cost price to employees. Use `employee_price` field only.
- NEVER skip the interaction log. Every view, click, and selection MUST be logged to `perk_interactions` for the recommender.
