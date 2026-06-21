# PerX Frontend

React + TypeScript + Vite PWA for the PerX employee benefits portal. Primary UI locale is Albanian (`sq-AL`); the AI chat stays in English for Gemma.

## Prerequisites

- Node.js 20+
- Backend API on port **8000** (see repo root / `infra/README.md`)

## Install

```bash
cd frontend
npm install
```

## Development

Start the Vite dev server (binds to all interfaces for LAN access):

```bash
npm run dev
# or explicitly for phones/tablets on the same Wi‑Fi:
npm run dev:lan
```

Open [http://localhost:5173](http://localhost:5173).

### API proxy

Leave `VITE_API_URL` **unset** in dev. The app calls `/api/v1/...` on the same origin and Vite proxies to the backend:

| Setting | Default proxy target |
|---------|----------------------|
| `VITE_API_PROXY_TARGET` | `http://127.0.0.1:8000` |

Example with Docker backend on another host:

```powershell
$env:VITE_API_PROXY_TARGET="http://192.168.1.42:8000"
npm run dev:lan
```

Start the backend locally if needed:

```bash
cd ../backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### LAN / mobile testing

1. Run `npm run dev:lan` (or `npm run dev` — both use `host: true` in `vite.config.ts`).
2. Find your PC LAN IP (`ipconfig` on Windows).
3. On your phone, open `http://<LAN-IP>:5173` (not `localhost`).
4. Allow inbound TCP **5173** in Windows Firewall if the phone cannot connect.

See `../infra/README.md` for full LAN deployment notes (Docker, production preview, firewall rules).

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Vite dev server on `:5173` |
| `npm run dev:lan` | Same as dev, explicit `--host` |
| `npm run build` | Typecheck + production build |
| `npm run preview` | Serve production build locally |
| `npm run lint` | ESLint |
| `npm run test` | Vitest (watch) |
| `npm run test:run` | Vitest single run |

## PWA / offline

Production builds register a service worker via `vite-plugin-pwa`. GET responses for perks, wishlist, and budget use **network-first** caching with a short timeout so recently viewed data stays available offline.

The employee shell shows an offline banner when `navigator.onLine` is false.

## i18n

- UI strings: `src/i18n/sq-AL.ts` via `t()` / `tf()` from `src/i18n/index.ts`
- Chat prompts/responses: `src/i18n/chat-en.ts` (English, for Gemma)

## Project layout

```
src/
  api/          fetch wrappers (client.ts)
  components/   UI, layout, editorial cards
  hooks/        React Query data hooks
  i18n/         Albanian locale + helpers
  portals/      employee / employer / provider pages
  stores/       Zustand auth + local demo state
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL` | Optional absolute API base. Leave empty in dev to use the Vite proxy. |
| `VITE_API_PROXY_TARGET` | Backend URL for the dev/preview proxy (default `http://127.0.0.1:8000`). |
