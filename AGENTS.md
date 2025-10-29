# Repository Guidelines

## Project Structure & Module Organization
- Backend (FastAPI): `backend/app` with `api/`, `core/`, `config/`, `models/`, `services/`, `utils/`. Entry: `backend/main.py`; tests in `backend/tests`.
- Frontend (Vue 3 + Vite): `frontend/src`, static assets in `frontend/public`, build output in `frontend/dist`.
- Scripts & Research: `scripts/` contains backtesting, data and validator utilities (Python).
- Config & Docs: `.env`, `.env.example`, project docs in `docs/`, additional configs in `config/`.

## Build, Test, and Development Commands
- Backend
  - Install: `cd backend && pip install -r requirements.txt`
  - Run (dev): `cd backend && python main.py` or `uvicorn main:app --reload`
  - Test: `cd backend && pytest -q` (async tests supported); coverage: `pytest --cov=app`
  - Lint/Format/Type: `flake8`, `black .`, `mypy app`
- Frontend
  - Install: `cd frontend && npm install`
  - Dev server: `npm run dev` (proxies `/api` to `http://localhost:8000`)
  - Build/Preview: `npm run build` / `npm run preview`
  - Lint/Format/Test: `npm run lint`, `npm run format`, `npm test`

## Coding Style & Naming Conventions
- Python: 4-space indent, Black formatting, `snake_case` for files/functions, `PascalCase` classes, `UPPER_SNAKE_CASE` constants. Keep modules under `backend/app`.
- Vue/TS: ESLint + Prettier; components in `PascalCase` (e.g., `StockTable.vue`), composables as `useXxx.ts`, import via `@/` alias.
- Keep scripts self-contained in `scripts/`; avoid importing from `frontend` in backend and vice versa.

## Testing Guidelines
- Backend: place tests in `backend/tests/test_*.py`; use `pytest`/`pytest-asyncio` for async endpoints; mock external IO. Aim for coverage on services, models, and API routes.
- Frontend: write unit tests with Vitest; `*.spec.ts` near source or in `tests/`.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`. Example: `feat(api): add strategy performance endpoint`.
- PRs: include summary, linked issues, steps to test; for UI, add screenshots. Ensure CI checks pass (lint, tests, build) and update `.env.example` if config changes.

## Security & Config Tips
- Copy `.env.example` to `.env` (root and `backend/`) and fill secrets (e.g., `ANTHROPIC_AUTH_TOKEN`). Never commit real secrets or large data/results.
- Default ports: backend `8000`, frontend `5173` (proxy configured in `vite.config.js`).
