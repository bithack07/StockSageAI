# StockSage AI

Production-grade agentic stock analysis platform for NSE/BSE equities — multi-agent AI, ML predictions, portfolio tracking, and real-time analysis streaming.

## Architecture

```
├── backend/          FastAPI + LangGraph + PostgreSQL + Redis + Celery
├── mobile/           React Native + Expo (iOS & Android)
├── desktop/          Tauri v2 + React (Windows & macOS)
├── ml_training/      Unified training (XGBoost, Prophet, LSTM)
└── docs/             Deployment and operations guides
```

## Quick Start (Development)

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Fill in API keys
# Start Postgres + Redis (or use docker compose up postgres redis)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In a second terminal:

```bash
celery -A app.celery_app.celery_app worker --loglevel=info
celery -A app.celery_app.celery_app beat --loglevel=info
```

### Desktop

```bash
cd desktop
cp .env.example .env.local
npm install && npm run dev
```

### Mobile (phone or emulator)

```bash
cd mobile
npm install && npx expo start
```

1. Install **Expo Go** on your phone and scan the QR code.
2. Start the API with **`--host 0.0.0.0`** so the phone can reach your Mac:

   `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

3. Mac and phone on the **same Wi‑Fi**. The app auto-uses your LAN IP in dev.

See **[mobile/README.md](mobile/README.md)** for full install steps, emulator notes, and troubleshooting.

## Production Deployment

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for the full checklist, Docker Compose production stack, nginx, and security settings.

```bash
cd backend
docker compose -f docker-compose.prod.yml up -d --build
```

Key production settings in `.env`:

| Variable | Value |
|----------|--------|
| `ENVIRONMENT` | `production` |
| `JWT_SECRET_KEY` | `openssl rand -hex 32` |
| `ALLOWED_ORIGINS` | Your HTTPS origins (no `*`) |
| `DEBUG` | `false` |
| `ENABLE_OPENAPI` | `false` |

Health endpoints: `GET /health` (liveness), `GET /health/ready` (DB + Redis).

## API Keys (free tiers available)

| Service | .env key |
|---------|----------|
| Groq (Llama) | `GROQ_API_KEY` |
| Google Gemini | `GEMINI_API_KEY` |
| Alpha Vantage | `ALPHA_VANTAGE_KEY` |
| Finnhub | `FINNHUB_KEY` |
| NewsAPI | `NEWSAPI_KEY` |
| GNews | `GNEWS_KEY` |

## ML Training

Train all Nifty 50 models:

```bash
cd ml_training
python train_all.py
```

Artifacts are written to `backend/app/models/`.

## How It Works

1. User signs in → JWT protects REST and WebSocket analysis.
2. Search a ticker → WebSocket `/ws/analyze/{symbol}?token=...`
3. LangGraph runs Fundamental, Technical, and Sentiment agents in parallel.
4. Orchestrator synthesizes a prediction (Gemini → Groq → rule-based fallback).
5. Steps stream live to desktop/mobile; results persist in PostgreSQL + ChromaDB RAG.

## Security

- JWT authentication on all business APIs and WebSocket analysis
- Rate limiting on auth and analysis endpoints
- Password policy (8+ chars, letter + number)
- Security headers in production
- NSE market hours (weekends, holidays, session times in IST)

## Disclaimer

StockSage AI provides AI-generated analysis for educational and informational purposes only. It is not financial advice. Past performance does not guarantee future results. Always verify independently before trading.

## License

Proprietary — contact the owner for commercial licensing terms.
