# Auckland Live Rail Map (Omarchy Edition)

Local dashboard for Auckland rail using official Auckland Transport data.

## Prerequisites
- Python 3.14 (project venv in `backend/.venv`)
- Node 20+ (frontend)

## Setup

### Backend
```sh
cd backend
cp ../.env.example .env   # then edit .env and set AT_SUBSCRIPTION_KEY
# download GTFS if needed (auto-downloads on startup if missing)
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend
```sh
cd frontend
npm install
npm run dev
```
Open http://127.0.0.1:5173

## Environment variables
See `.env.example`. Required: `AT_SUBSCRIPTION_KEY` (from AT developer portal, subscribed to Realtime API product).

## Tests
```sh
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run build
```

## Stopping
Ctrl+C in each terminal. No background services installed.
