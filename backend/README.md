# PerX Backend

FastAPI service for the PerX employee benefits platform: authentication, perks, recommendations, selections, employer workflows, chat (Ollama), vision jobs (optional cv-service), and Web Push notifications.

## Quick start

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env   # adjust DATABASE_URL, JWT_SECRET, etc.
pytest tests/ -v
uvicorn app.main:app --reload
```

Open Swagger UI at `http://localhost:8000/docs`.

With Docker (from `infra/`):

```bash
cp ../.env.example ../.env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

## Environment variables

Copy `../.env.example` to `../.env` at the repo root. Key settings from `app/config.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://perx_user:perx_secret@localhost:5432/perx` | Async Postgres connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for cache, rate limits, JWT deny list |
| `REDIS_USE_MEMORY` | `false` | In-memory Redis fallback (tests/dev) |
| `JWT_SECRET` | `change-me-in-dev-only` | HS256 signing secret — **required in production** |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `CORS_ORIGINS` | localhost dev ports | JSON array of allowed browser origins |
| `ALLOW_DEMO_MODE` | `false` | Enables `/auth/demo-info` and open internal routes when key unset |
| `INTERNAL_API_KEY` | — | Protects `/internal/*`; required when demo mode is off |
| `RECOMMENDER_WARM_THRESHOLD` | `10` | Interactions before warm recommender mode |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `OLLAMA_MODEL` | `gemma2:2b` | Model for chat and explanations |
| `OLLAMA_TIMEOUT_SECONDS` | `5.0` | Ollama HTTP timeout |
| `OLLAMA_FORCE_FAIL` | `false` | Force template fallbacks (tests/demos) |
| `OLLAMA_MAX_RETRIES` | `0` | Retries for Ollama generate calls |
| `VAPID_PRIVATE_KEY` | — | Web Push private key (optional) |
| `VAPID_PUBLIC_KEY` | — | Web Push public key (optional) |
| `VAPID_CLAIMS_EMAIL` | `mailto:admin@perx.local` | VAPID contact claim |
| `CV_ENABLED` | `true` | Use cv-service; set `false` when service unavailable |
| `CV_SERVICE_URL` | `http://localhost:8010` | cv-service base URL |
| `CV_INTERNAL_KEY` | — | Shared secret sent as `X-CV-Internal-Key` |
| `CV_MAX_IMAGE_BYTES` | `5000000` | Max upload size for vision jobs |
| `CV_RESULT_TTL_SECONDS` | `3600` | Vision job result cache TTL |
| `CV_REQUEST_TIMEOUT_SECONDS` | `8.0` | cv-service HTTP timeout |
| `RECONCILE_ENABLED` | `false` | Background budget reconcile loop |
| `RECONCILE_INTERVAL_SECONDS` | `300` | Reconcile interval when enabled |

## API overview

| Area | Prefix | Notes |
|------|--------|-------|
| Health | `/api/v1/health` | Liveness probe |
| Auth | `/api/v1/auth/*` | Register, login, refresh, logout, push subscription |
| Employee | `/api/v1/me/*` | Profile, onboarding, budget, wishlist |
| Recommendations | `/api/v1/recommendations` | Cold/warm hybrid engine |
| Selections | `/api/v1/selections/*` | Quick-add, optimize plan |
| Employers | `/api/v1/employer/*` | Approvals, org management |
| Chat | `/api/v1/chat` | Ask PerX (Ollama) |
| Vision | `/api/v1/vision/*` | Async CV jobs (requires `CV_ENABLED`) |
| Internal | `/api/v1/internal/*` | LLM callback, Ollama health (key or demo mode) |

## Architecture

- **Cold start** (`interaction_count < threshold`): rules-based affinity from onboarding fields
- **Warm** (`interaction_count >= threshold`): `0.4×content + 0.4×CF + 0.2×UCB`, budget penalty ×0.1
- **LLM**: async via background tasks; template fallback when Ollama is down
- **Security**: RBAC, JWT revocation (Redis), IP/user rate limits, structured error envelope

## Tests

```bash
pytest tests/ -v
```

Requires Postgres with schema from `../database/migrations/` (or `alembic upgrade head`). CI applies SQL migrations automatically.

## ALS retrain script

```bash
python -m scripts.retrain_als
```

Reads `scripts/fixtures/interactions.json`, trains ALS via `implicit`, writes `scripts/output/cf_scores_by_employee.json`.
