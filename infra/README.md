# PerX infrastructure

One-command startup from this directory:

```bash
docker compose up --build
```

Development (hot reload, exposed ports):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile dev-frontend up --build
```

The `dev-frontend` profile starts the Vite dev server on port 5173. Omit it if you only need postgres, redis, and backend.

Optional profiles:

```bash
# Traefik reverse proxy with security headers
docker compose --profile with-traefik up --build

# Local Ollama LLM
docker compose --profile with-ollama up --build

# cv-service starts with the default stack (set CV_ENABLED=false in .env to disable backend integration)
docker compose up --build
```

CV-only (local, no Docker):

```bash
cd ../cv-service
uvicorn app.main:app --host 0.0.0.1 --port 8010
```

Upload model weights to `../cv-service/models/` (see `../cv-service/models/README.md`). Enable in backend: `CV_ENABLED=true`, `CV_SERVICE_URL=http://localhost:8010`.

## Services

| Service    | Port (dev) | Description                          |
|------------|------------|--------------------------------------|
| postgres   | 5432       | PostgreSQL 16 â€” source of truth      |
| redis      | 6379       | Budget cache, rate limits, JWT deny  |
| backend    | 8000       | FastAPI API (`/api/v1/...`)          |
| frontend   | 5173       | Vite dev server (`dev-frontend` profile) |
| cv-service | 8010       | CV analyze API (default stack)       |
| traefik    | 80/443     | Optional reverse proxy + headers     |
| ollama     | â€”          | Optional local LLM                   |

## Environment

Copy `../.env.example` to `../.env` before first run. See `../backend/README.md` for the full variable table.

**Production:** use `docker-compose.prod.yml` (see below). Set `ALLOW_DEMO_MODE=false`, a strong `JWT_SECRET`, `POSTGRES_PASSWORD`, and `INTERNAL_API_KEY`. Configure VAPID keys for push notifications.

**Computer vision:** `cv-service` is part of the default Docker stack. Set `CV_ENABLED=false` in `.env` to disable backend vision integration. Docker Compose always sets `CV_SERVICE_URL=http://cv-service:8010` inside containers. Set matching `CV_INTERNAL_KEY` on backend and cv-service in production.

SQL migrations in `../database/migrations/` are applied on first Postgres startup via `docker-entrypoint-initdb.d`.

## Production stack

From `infra/` with secrets in repo-root `.env` (copy from `../.env.example`):

```bash
docker compose --env-file ../.env -f docker-compose.prod.yml up --build -d
```

Use `--env-file ../.env` so `POSTGRES_*` variables are available for compose interpolation (repo-root `.env` is not read automatically from `infra/`).

This starts **frontend** (nginx on port 80), **backend**, **postgres**, and **redis** with:

- `ALLOW_DEMO_MODE=false`
- `restart: unless-stopped` on all services
- Healthchecks on backend, frontend, postgres, and redis
- No hardcoded database passwords — uses `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` from `.env` (compose builds `DATABASE_URL` for the backend container)

Optional profiles on the prod file:

```bash
# Traefik reverse proxy + security-headers middleware on all routers
docker compose --env-file ../.env -f docker-compose.prod.yml --profile with-traefik up --build -d
```

Verify:

```bash
curl http://localhost/api/v1/health
curl http://localhost/cv/health          # cv-service via nginx
curl http://localhost/
```

## Health check

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8010/health          # cv-service direct
curl http://localhost/cv/health            # cv-service via nginx (LAN/prod frontend)
curl http://localhost:8000/api/v1/vision/health  # requires auth + CV_ENABLED
```

## Phone / tablet on the same Wiâ€‘Fi (LAN)

Use this to open PerX on a phone while developing on your Windows PC.

### 1. Start the stack

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile dev-frontend up --build
```

Then either use the **frontend** container above, or run Vite on the host:

```bash
cd ../frontend
npm run dev
```

Vite binds to all interfaces (`host: true` in `vite.config.ts`), so the app is reachable on your LAN IP.

### 2. Find your PCâ€™s LAN IP

```powershell
ipconfig
```

Use the **IPv4 Address** under your Wiâ€‘Fi adapter (e.g. `192.168.1.42`).

### 3. Open on the phone

Same Wiâ€‘Fi network (not guest/isolated Wiâ€‘Fi):

```
http://192.168.1.42:5173
```

Do **not** use `http://localhost:5173` on the phone â€” that refers to the phone itself.

Leave `VITE_API_URL` unset so API calls go to `http://<lan-ip>:5173/api/...` and Vite proxies to the backend.

### 4. Windows Firewall

Allow inbound TCP on port **5173** (Vite). Run PowerShell **as Administrator**:

```powershell
New-NetFirewallRule -DisplayName "PerX Vite Dev" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5173
```

### 5. Verify from your PC before testing the phone

Replace `192.168.1.42` with your LAN IP:

```powershell
curl http://192.168.1.42:5173
curl http://192.168.1.42:5173/api/v1/health
```

### Installable PWA (optional)

The dev server loads in the mobile browser over HTTP. Full **Add to Home Screen** / service worker install requires **HTTPS** on non-localhost (e.g. Cloudflare Tunnel, mkcert, or production TLS).

For a production-like LAN test with the service worker:

```bash
cd ../frontend
npm run build
npm run preview:lan
```

Then open `http://<lan-ip>:4173` on the phone (still HTTP; HTTPS is needed for install on most devices).

## LAN testing (phones & tablets on same Wiâ€‘Fi)

Two modes â€” pick one:

| Mode | Port | Compose files |
|------|------|----------------|
| **Dev hot reload** | 5173 | `docker-compose.yml` + `docker-compose.dev.yml` (+ `--profile dev-frontend`) |
| **Single-port demo** | 80 | `docker-compose.yml` + `docker-compose.lan.yml` only |

Do **not** combine `docker-compose.dev.yml` and `docker-compose.lan.yml` â€” they both define `frontend` and conflict on ports/images.

Reach PerX from other devices at `http://<your-LAN-IP>:5173` (dev) or `http://<your-LAN-IP>` (single-port).

### 1. Environment

```powershell
# From repo root â€” set your Wiâ€‘Fi IPv4 in CORS_ORIGINS (ipconfig)
copy .env.example .env
# Edit .env: replace 192.168.1.42 with your LAN IP in CORS_ORIGINS
```

### 2. Backend

```powershell
cd infra
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile dev-frontend up --build
```

First run only â€” migrations and demo data:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend alembic upgrade head
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -m scripts.seed
```

Demo login: `john.cold@example.com` / `Demo1234`

### 3. Frontend (separate terminal)

```powershell
cd frontend
npm install
npm run dev:lan
```

Open `http://<LAN-IP>:5173` on any device on the same network. Vite proxies `/api` to the backend â€” leave `VITE_API_URL` empty.

### 4. Windows firewall

Allow inbound TCP **5173** (and **8000** only if hitting the API directly). Requires an **elevated** PowerShell from the **repo root**:

```powershell
cd D:\PerX
.\scripts\open-lan-firewall.ps1
```

Manual rules:

```powershell
New-NetFirewallRule -DisplayName "PerX Vite" -Direction Inbound -LocalPort 5173 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "PerX API" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

### 5. Single-port demo (optional)

Serve built frontend + API reverse proxy on port **80** (production nginx â€” **do not** add `docker-compose.dev.yml`; it starts Vite on 5173 and conflicts):

```powershell
cd infra
docker compose -f docker-compose.yml -f docker-compose.lan.yml up --build
```

Then open `http://<LAN-IP>` (no port suffix). No separate Vite dev server needed.

## Public demo via Cloudflare Tunnel

Expose the **single-port** stack (port 80) to the internet for demos without opening router ports. Uses Cloudflareâ€™s free quick tunnel (`trycloudflare.com`); the URL changes every time you start `cloudflared`.

### Prerequisites

- Docker stack running with LAN compose only (no `docker-compose.dev.yml`):

```powershell
cd infra
docker compose -f docker-compose.yml -f docker-compose.lan.yml up --build -d
```

- Local checks: `http://localhost/` and `http://localhost/api/v1/health`

### Install cloudflared (Windows)

```powershell
winget install Cloudflare.cloudflared --accept-package-agreements --accept-source-agreements
cloudflared --version
```

### Start quick tunnel

Point at nginx on port 80. Copy the `https://â€¦.trycloudflare.com` URL from the log line *Your quick Tunnel has been created*.

```powershell
cloudflared tunnel --url http://localhost:80
```

Run in a dedicated terminal or background; stop with Ctrl+C or `Stop-Process -Name cloudflared`.

### CORS

In repo-root `.env`, set `CORS_ORIGINS` to a JSON array that includes:

- Your current tunnel origin (e.g. `https://YOUR-SUBDOMAIN.trycloudflare.com`)
- `http://localhost`, `http://127.0.0.1`
- Any LAN origins you still use (e.g. `http://192.168.x.x`, dev port `5173`)

Restart backend:

```powershell
cd infra
docker compose -f docker-compose.yml -f docker-compose.lan.yml up -d --force-recreate backend
```

### Verify

```powershell
curl https://YOUR-SUBDOMAIN.trycloudflare.com/api/v1/health
curl https://YOUR-SUBDOMAIN.trycloudflare.com/
```

### Demo day checklist

- [ ] Docker healthy; seed done if DB was empty (`alembic upgrade head`, `python -m scripts.seed` in backend container)
- [ ] `cloudflared` running; tunnel URL saved and added to `CORS_ORIGINS`
- [ ] Backend restarted after CORS change
- [ ] Health + homepage OK on tunnel URL from this machine
- [ ] Phone on cellular (not Wiâ€‘Fi) opens tunnel URL; login works (`john.cold@example.com` / `Demo1234`)
- [ ] Note: quick tunnels are ephemeral and have no uptime SLA

