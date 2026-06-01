# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is

Single **Logistika backend** (FastAPI + aiogram Telegram bot + Postgres + Redis). The driver **Frontend_bot** SPA is a separate repository and is not required for API-only development.

### First-time / local prerequisites

1. Copy env: `cp .env.example .env` and set at least `BOT_TOKEN`, `SECRET_KEY`, `DB_*`, `ADMIN` (see `README.md`).
2. **Missing `services/` package:** On current `main`, `Admin_panel/router.py` imports `services.live_location`, but `services/` may be absent. If `backend-api` crashes with `ModuleNotFoundError: No module named 'services'`, restore from git history:
   ```bash
   git checkout 2abe2d3 -- services/
   ```
3. Docker with Compose v2 (`docker compose`). API listens on **host port 8003** (container 8000).

### Start the stack (API-focused)

```bash
docker compose up -d --build db logistika-redis migrations backend-api
```

Optional: add `backend-bot` when testing Telegram flows (needs a real `BOT_TOKEN`).

### Verify

```bash
docker ps
curl http://127.0.0.1:8003/health
curl http://127.0.0.1:8003/health/db
curl http://127.0.0.1:8003/api/drivers/truck-types
```

Production-style paths use the `/api` prefix (`API_PUBLIC_PREFIX=/api` in `.env.example`).

### Lint / tests

This repo has **no** configured pytest, ruff, flake8, or CI workflows. Reasonable local checks:

- `python3 -m compileall -q config driver order users ai Admin_panel services handlers middlewares utils`
- Import/smoke: `curl` health endpoints above

### Gotchas

- **Migrations** run in a one-shot `migrations` container (`alembic upgrade head`) before `backend-api` starts.
- **Redis** is optional for some paths but required for live-location admin features and token blacklist behavior.
- **Hot reload:** `backend-api` mounts the repo at `/app`; after dependency changes in `requirements.txt`, rebuild: `docker compose up -d --build backend-api`.
- Do not commit `.env` (gitignored).
