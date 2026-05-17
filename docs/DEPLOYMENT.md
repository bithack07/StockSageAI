# StockSage AI — Production Deployment

## Pre-launch checklist

- [ ] Generate `JWT_SECRET_KEY`: `openssl rand -hex 32`
- [ ] Set `ENVIRONMENT=production`, `DEBUG=false`, `ENABLE_OPENAPI=false`
- [ ] Set `ALLOWED_ORIGINS` to your web/mobile/desktop origins (no `*`)
- [ ] Rotate all API keys; remove dev keys from any shared `.env` copies
- [ ] Use managed PostgreSQL (Supabase, RDS) and Redis (Upstash, ElastiCache)
- [ ] Place API behind HTTPS (nginx, Caddy, or cloud load balancer)
- [ ] Train ML models (`ml_training/train_all.py`) and mount `app/models/`
- [ ] Run Celery worker + beat for overnight data refresh and alerts

## Docker (recommended)

```bash
cd backend
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, JWT_SECRET_KEY, ENVIRONMENT=production, API keys

export POSTGRES_PASSWORD=your-strong-password
docker compose -f docker-compose.prod.yml up -d --build
```

- **Liveness:** `GET /health`
- **Readiness:** `GET /health/ready` (DB + Redis)

## Environment variables (production)

| Variable | Required | Notes |
|----------|----------|-------|
| `ENVIRONMENT` | Yes | `production` |
| `JWT_SECRET_KEY` | Yes | Min 32 chars, unique |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...` |
| `REDIS_URL` | Yes | For cache, Celery, rate limits |
| `ALLOWED_ORIGINS` | Yes | Comma-separated HTTPS origins |
| `GROQ_API_KEY` | Recommended | Agent LLM calls |
| `GEMINI_API_KEY` | Optional | Orchestrator (Groq fallback exists) |

## Clients

| Client | Config |
|--------|--------|
| Desktop | `desktop/.env.local` → `VITE_API_URL`, `VITE_WS_URL` (use `wss://` in prod) |
| Mobile | `mobile/.env` → `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_WS_URL` |
| Tauri build | `npm run tauri build` after setting production URLs |

## Security

- WebSocket `/ws/analyze/{symbol}` requires JWT (`?token=` query param)
- Auth endpoints rate-limited (login/register/refresh)
- Password policy: 8+ chars, letter + number
- OpenAPI `/docs` disabled when `ENVIRONMENT=production`

## Reverse proxy (nginx snippet)

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## CI

GitHub Actions runs backend pytest, desktop build, and mobile TypeScript check on push/PR.
