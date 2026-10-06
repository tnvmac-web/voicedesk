# Changelog

All notable changes to VoiceDesk are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-05

### Added
- **Multi-tenant AI Receptionist Backend** (FastAPI + SQLAlchemy 2.0 + PostgreSQL)
  - Tenant signup/login with bcrypt + JWT auth
  - Per-tenant agent configuration (greeting, prompt, vertical, features)
  - Contacts/leads management with channel tracking (voice/WhatsApp/SMS)
  - Appointment booking with calendar source tracking
  - Call history with transcripts, summaries, outcomes
  - Unified WhatsApp/SMS inbox with send/receive
  - Analytics dashboard (calls, bookings, leads, revenue recovered)
- **Voice Engine (Pipecat 1.12)**
  - Mock STT/TTS for zero-key development
  - Deepgram Nova-2 streaming STT integration
  - ElevenLabs Flash v2.5 TTS integration
  - OpenAI GPT-4o-mini / Anthropic Claude / Ollama LLM backends
  - ReceptionistProcessor: intent detection + booking/lead side effects
  - PipelineWorker/WorkerRunner (current Pipecat 1.12 API)
- **Telephony & Messaging**
  - Twilio Media Streams WebSocket endpoint (`/media/twilio`)
  - Twilio voice webhook + status callback (missed-call text-back)
  - WhatsApp Cloud API webhook (verify + inbound)
  - Missed-call auto-reply (SMS/WhatsApp) + after-hours mode
- **Vertical Script Packs (7 built-in)**
  - Dental, Salon, Real Estate, Law, HVAC/Plumbing, Restaurant, Generic
  - Greeting, system prompt, business hours, services, FAQs per vertical
- **Multi-tenancy from day one**
  - Tenant isolation at DB level; per-tenant agent, contacts, calls, appointments
  - Usage metering (minutes, calls) per tenant
- **Production Infrastructure**
  - Multi-stage Dockerfile (builder + runtime)
  - docker-compose.yml (PostgreSQL + API)
  - .env.prod.example with all production variables
  - alembic.ini for database migrations
  - GitHub Actions CI (lint, type-check, test, docker build)
- **Testing & Quality**
  - 21 tests passing (auth, agents, contacts, appointments, calls, inbox, analytics, voice pipeline)
  - Ruff linting (clean) + mypy type checking configured
  - PipelineWorker/WorkerRunner integration (Pipecat 1.12 current API)

### Changed
- Replaced deprecated `PipelineTask`/`PipelineRunner` with `PipelineWorker`/`WorkerRunner` per Pipecat 1.12+
- Switched from passlib+bcrypt to direct `bcrypt>=4.0` for password hashing
- Moved from SQLite dev default to PostgreSQL production default

### Security
- bcrypt password hashing (no passlib shim)
- JWT HS256 tokens with configurable expiry
- No secrets in source; all via environment variables
- Provider keys never logged; mock fallbacks for zero-key dev

## [0.9.0] - 2026-10-04

### Added
- Core FastAPI backend with auth, tenants, agents, contacts, appointments
- Pipecat voice pipeline with mock STT/TTS
- Receptionist brain (rule-based intent + optional LLM phrasing)
- WhatsApp webhook + unified inbox
- Telephony webhooks (voice + status)

### Changed
- Migrated from SQLite to PostgreSQL for production readiness

## [0.1.0] - 2026-10-01

### Added
- Initial project scaffold (FastAPI, SQLAlchemy, Pydantic Settings)
- Basic tenant + user models
- SQLite dev database