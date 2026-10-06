# VoiceDesk — AI Voice + WhatsApp Receptionist for SMBs

Self-hosted AI receptionist that answers phone calls, WhatsApp, and SMS from one inbox. Books appointments, captures leads, and follows up automatically.

## Features

- **AI Voice Receptionist** — Answers every call with natural conversation (STT → LLM → TTS), books appointments into a real calendar, and captures leads.
- **WhatsApp + SMS Inbox** — Unified conversation view across phone, WhatsApp, and SMS; send replies from the dashboard.
- **Missed-Call Text-Back** — Auto-replies via SMS/WhatsApp when a call is missed (60%+ of callers dial the next provider on voicemail).
- **After-Hours Mode** — Outside business hours the AI still answers and books.
- **Vertical Script Packs** — Ready-made personas for Dental, Salon, Real Estate, Law, HVAC/Plumbing, Restaurant, plus Generic.
- **Self-Hosted, Zero Ongoing Cost** — Bring your own API keys (Twilio, Deepgram, ElevenLabs, OpenAI). No per-minute platform fees.
- **Multi-Tenant SaaS** — One install serves unlimited businesses; each gets isolated data, agent config, and usage metering.
- **Analytics Dashboard** — Calls, bookings, leads, missed calls recovered, and estimated revenue recovered.

## Architecture

```
Caller ──► Twilio Media Stream ──► /media/twilio (WebSocket)
                                          │
                                          ▼
                              Deepgram STT (Nova-2)
                                          │
                                          ▼
                              Receptionist Brain (GPT-4o-mini)
                                          │
                                          ▼
                              ElevenLabs TTS (Flash v2.5)
                                          │
                                          ▼
                              Twilio Media Stream ──► Caller
```

- **Backend**: FastAPI (Python 3.12), SQLAlchemy 2.0, PostgreSQL
- **Voice**: Pipecat 1.12 (PipelineWorker) — STT → ReceptionistProcessor → TTS
- **Telephony**: Twilio Media Streams (bring your own account)
- **WhatsApp**: Meta Cloud API
- **Frontend**: Next.js 15 + Tailwind (admin dashboard)
- **Infra**: Docker, docker-compose, PostgreSQL, GitHub Actions CI

## Quick Start (Docker)

```bash
# 1. Clone and configure
git clone <your-repo> voicedesk
cd voicedesk/voice-engine
cp .env.prod.example .env
# Edit .env with your API keys

# 2. Start
docker-compose up -d --build

# 3. Open dashboard
# http://localhost:8000  (API)
# http://localhost:3000  (admin dashboard - separate repo)
```

## API Documentation

Interactive docs at `GET /docs` (Swagger UI) and `GET /redoc` (ReDoc).

### Core Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/signup` | Create tenant + owner |
| POST | `/api/auth/login` | Get bearer token |
| GET | `/api/auth/me` | Current tenant |
| GET/POST | `/api/agent` | Agent configs |
| GET/POST | `/api/contacts` | Leads/contacts |
| GET/POST | `/api/appointments` | Bookings |
| GET | `/api/calls` | Call history |
| POST | `/api/calls/simulate` | Test a caller utterance |
| GET | `/api/conversations` | WhatsApp/SMS inbox |
| POST | `/api/conversations/{id}/messages` | Send reply |
| GET | `/api/analytics/summary` | ROI dashboard |
| GET | `/health` | Health check |

### Webhooks

| Method | Path | Description |
|--------|------|-------------|
| POST | `/telephony/voice` | Twilio voice webhook |
| POST | `/telephony/status` | Call status (triggers missed-call text-back) |
| GET/POST | `/webhooks/whatsapp` | Meta Cloud API |

## Vertical Script Packs

Each pack provides a ready-made receptionist persona:

| Key | Business Type | Services |
|-----|---------------|----------|
| `dental` | Dental Practice | Cleaning, Check-up, Whitening, Emergency |
| `salon` | Hair & Beauty Salon | Cut, Colour, Blow-dry, Treatment |
| `real_estate` | Real Estate Agency | Viewing, Valuation, Selling |
| `law` | Law Firm | Consultation, Family, Conveyancing |
| `hvac` | HVAC / Plumbing | Emergency, Boiler, Leak, Installation |
| `restaurant` | Restaurant | Table booking, Large party, Takeaway |
| `generic` | Generic Business | Enquiry, Booking |

Select a vertical on tenant creation or in the admin dashboard — the AI receives the greeting, system prompt, business hours, services list, and FAQs tailored to that trade.

## Configuration (Environment)

| Variable | Required | Description |
|----------|----------|-------------|
| `ENV` | Yes | `dev` or `prod` |
| `SECRET_KEY` | Yes | 64+ char random string |
| `PUBLIC_BASE_URL` | Yes | e.g. `https://api.yourdomain.com` |
| `DATABASE_URL` | Yes | PostgreSQL URL |
| `TELEPHONY_PROVIDER` | Yes | `twilio` or `mock` |
| `TWILIO_ACCOUNT_SID` | If Twilio | |
| `TWILIO_AUTH_TOKEN` | If Twilio | |
| `TWILIO_PHONE_NUMBER` | If Twilio | E.164 format |
| `STT_PROVIDER` | Yes | `deepgram`, `whisper`, `mock` |
| `DEEPGRAM_API_KEY` | If Deepgram | |
| `LLM_PROVIDER` | Yes | `openai`, `anthropic`, `ollama`, `mock` |
| `OPENAI_API_KEY` | If OpenAI | |
| `LLM_MODEL` | If LLM | e.g. `gpt-4o-mini` |
| `TTS_PROVIDER` | Yes | `elevenlabs`, `openai`, `mock` |
| `ELEVENLABS_API_KEY` | If ElevenLabs | |
| `ELEVENLABS_VOICE_ID` | If ElevenLabs | e.g. `21m00Tcm4TlvDq8ikWAM` |
| `WHATSAPP_VERIFY_TOKEN` | If WhatsApp | |
| `WHATSAPP_ACCESS_TOKEN` | If WhatsApp | |
| `WHATSAPP_PHONE_NUMBER_ID` | If WhatsApp | |

## Deployment

```bash
# 1. Build and push image
docker build -t yourname/voicedesk:1.0.0 .
docker push yourname/voicedesk:1.0.0

# 2. On server
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 3. Run migrations
docker-compose exec api alembic upgrade head
```

## Testing

```bash
# Unit + integration
pytest -q

# Lint
ruff check app tests

# Type check
mypy app
```

## Marketplace Submission Checklist

- [ ] ZIP root has no loose files; structure: `Documentation/`, `Source/`, `Database/`, `Preview/`
- [ ] Full unencrypted source included
- [ ] Public English PDF/HTML docs (install, features, customization, troubleshooting, credits)
- [ ] Live demo on own server, watermarked
- [ ] Cover image 3:2 @ 2340x1560 (min 1170x780)
- [ ] 3+ preview screenshots
- [ ] Title ≤100 chars Title Case; ≤2 main keywords; ≤15 tags; correct category
- [ ] No blacklisted words in title/tags
- [ ] Security pass: no secrets, no eval, no CDN hotlinks, escaping
- [ ] Every asset owned/licensed for resale; credits listed
- [ ] Category requirements met (Laravel strict `===`, Flask/FastAPI standards)
- [ ] Version pinned; server requirements documented
- [ ] No offensive content, no famous-people photos, no malware

## License

This product is sold under a commercial license. See `LICENSE` and `EULA.md`.

## Support

- Documentation: `Documentation/VoiceDesk_User_Guide.pdf` and `Documentation/VoiceDesk_Admin_Guide.pdf`
- Email: support@yourdomain.com
- Issues: GitHub Issues (private repo for buyers)

## Changelog

See `CHANGELOG.md`.
