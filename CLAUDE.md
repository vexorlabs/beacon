# Beacon — Claude Code Instructions

> Full AI agent instructions live in **`AGENTS.md`**. Read that file first.
> This file exists because Claude Code reads `CLAUDE.md` automatically at session start.

---

## Quick Reference

**What is this?** An open-source, local-first debugging platform for AI agents. "Chrome DevTools for AI Agents."

**Tech stack:** Python/FastAPI/SQLite backend · Vite/React/TypeScript/React Flow/Monaco frontend · beacon-sdk Python instrumentation package

**Backend port:** 7474 · **Frontend port:** 5173

**Run backend:** `cd backend && uvicorn app.main:app --reload --port 7474`
**Run frontend:** `cd frontend && npm run dev`

---

## Locked-In Decisions (Do Not Change)

1. SQLite only (no PostgreSQL for MVP)
2. No authentication (intentional)
3. OTEL span format for all trace data
4. React Flow for graph rendering (not D3.js)
5. Monaco Editor for prompt editing (not CodeMirror)
6. Zustand for frontend state (not Redux)
7. shadcn/ui copy-paste (never `npm install` component libraries)
8. Port 7474 (backend), 5173 (frontend)

---

## Key Rules

- Python: type hints everywhere, no implicit `Any`, `black` + `isort` formatting
- TypeScript: `strict: true`, no `any`, no `console.log` in commits
- Never commit `.env`, API keys, or `~/.beacon/traces.db`
- Multi-agent safety: do not `git stash`, do not switch branches unless asked

---

## Full Context

Read these in order:
1. `AGENTS.md` — Complete instructions, repo structure, all rules
2. `VISION.md` — Project vision and philosophy
3. `docs/architecture.md` — System design
4. `docs/roadmap.md` — What to build next
5. `docs/conventions.md` — Code style
6. `docs/api-contracts.md` — API specs
7. `docs/data-model.md` — Database schema
