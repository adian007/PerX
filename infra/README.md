# PerX infrastructure

One-command startup from this directory:

```bash
docker compose up --build
```

Development (hot reload, exposed ports):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Optional profiles:

```bash
# Traefik reverse proxy with security headers
docker compose --profile with-traefik up --build

# Local Ollama LLM
docker compose --profile with-ollama up --build
```

## Services

| Service  | Port (dev) | Description                          |
|----------|------------|--------------------------------------|
| postgres | 5432       | PostgreSQL 16 — source of truth      |
| redis    | 6379       | Budget cache, rate limits, JWT deny  |
| backend  | 8000       | FastAPI API (`/api/v1/...`)          |
| traefik  | 80/443     | Optional reverse proxy + headers     |
| ollama   | —          | Optional local LLM                   |

## Environment

Copy `../.env.example` to `../.env` before first run.

**Production:** set `ALLOW_DEMO_MODE=false`, use a strong `JWT_SECRET`, and configure VAPID keys for push notifications.

SQL migrations in `../database/migrations/` are applied on first Postgres startup via `docker-entrypoint-initdb.d`.

## Health check

```bash
curl http://localhost:8000/api/v1/health
```
