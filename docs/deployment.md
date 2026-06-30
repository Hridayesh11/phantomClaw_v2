# Deployment Guide

PhantomClaw v3 is designed to be environment-agnostic, running locally for development and containerized for future production environments.

## Environment Variables

The application relies strictly on environment variables for configuration.
`utils/config.py` uses Pydantic `BaseSettings` to validate these on startup.

**Backend (`/.env`)**
```env
OPENAI_API_KEY=sk-xxxx
OPENAI_MODEL=gpt-4o
UPSTOX_API_KEY=xxxx
UPSTOX_API_SECRET=xxxx
UPSTOX_REDIRECT_URI=https://127.0.0.1:8000/callback
LOG_LEVEL=INFO
FASTAPI_URL=http://localhost:8000
DATABASE_URL=sqlite:///phantomclaw.db
PAPER_BROKERAGE_FEE_PCT=0.001
PAPER_SLIPPAGE_PCT=0.0005
```

**Frontend (`/frontend/.env.local`)**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Backend Setup (Local)
1. Create a virtual environment: `python -m venv .venv`
2. Activate it: `source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows)
3. Install dependencies: `pip install -r requirements.txt`
4. Run Uvicorn: `uvicorn api.main:app --host 0.0.0.0 --port 8000`

## Frontend Setup (Local)
1. Navigate to frontend: `cd frontend`
2. Install dependencies: `npm install`
3. Run dev server: `npm run dev`

## Production Deployment & Docker Readiness
While currently configured for bare-metal execution, the stateless nature of the FastAPI backend and the static-generation capabilities of Next.js make PhantomClaw completely Docker-ready.

### Reverse Proxy Considerations
In a production deployment, a reverse proxy (e.g., Nginx or Traefik) must sit in front of both services to:
- Terminate SSL/TLS (crucial for Upstox OAuth callbacks).
- Route `/api/*` traffic to the internal Uvicorn port.
- Serve the Next.js standalone build.

### Future Cloud Deployment
- **Database:** The SQLite file must be migrated to a managed PostgreSQL instance (e.g., AWS RDS) to prevent data loss in ephemeral container environments.
- **Secrets:** API keys should be injected at runtime via AWS Secrets Manager or HashiCorp Vault, overriding local `.env` files.
