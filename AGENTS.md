# Beacon — AI Agent Instructions

Primary instruction file for coding agents working in this repository.

---

## What Beacon Is

Beacon is an open-source, local-first observability/debugging platform for AI agents.

Core idea:
- capture LLM calls and computer-use actions in one trace
- inspect traces in an interactive DAG
- replay LLM steps with prompt edits
- stream spans live over WebSocket

Reference docs:
- Vision: `VISION.md`
- Architecture: `docs/architecture.md`
- API contracts: `docs/api-contracts.md`
- Data model: `docs/data-model.md`

---

## Repo Structure

```text
beacon/
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── VISION.md
├── SECURITY.md
├── docs/
├── backend/
├── sdk/           # Python SDK
├── sdk-js/        # JS/TS SDK
├── frontend/
├── .agents/
├── .claude/
├── .github/
└── git-hooks/
```

### Backend (`backend/`)
- FastAPI app in `backend/app/`
- routers: `spans`, `traces`, `replay`, `settings`, `playground`, `demo`, `stats`, `search`, `analysis`, `prompt_versions`
- services implement business logic
- WebSocket manager in `backend/app/ws/manager.py`

### Python SDK (`sdk/`)
- package: `sdk/beacon_sdk`
- integrations: `openai`, `anthropic`, `google_genai`, `crewai`, `autogen`, `llamaindex`, `ollama`, `playwright`, `subprocess_patch`, `file_patch`, `langchain`

### JS/TS SDK (`sdk-js/`)
- package: `sdk-js/src/`
- integrations: `openai`, `anthropic`, `vercel-ai`
- zero runtime dependencies, Node.js 18+

### Frontend (`frontend/`)
- React Router routes in `src/App.tsx`
- pages: Dashboard, Traces, Playground, Settings
- state: Zustand stores in `src/store/`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Python SDK | Python 3.11+ |
| JS/TS SDK | Node.js 18+, TypeScript |
| Backend | FastAPI + SQLAlchemy + SQLite |
| Realtime | FastAPI WebSockets |
| Frontend | Vite + React 19 + TypeScript |
| Graph | React Flow (`@xyflow/react`) |
| Editor | Monaco |
| UI primitives | shadcn/ui + Tailwind CSS |
| State | Zustand |

---

## Core Concepts

### Span
One unit of work. Key fields: `span_id`, `trace_id`, `parent_span_id`, `span_type`, `name`, `status`, `start_time`, `end_time`, `attributes`.

### Span Types
`llm_call | tool_use | agent_step | browser_action | file_operation | shell_command | chain | custom`

### Trace
One run, grouping spans by `trace_id`.

---

## Mandatory Rules

### Python
- type hints on all function signatures
- no implicit `Any`
- use `|` unions
- format with `black` + `isort --profile black`
- no `print()` in committed code
- backend tests use in-memory SQLite

### TypeScript
- `strict: true`
- avoid `any`
- avoid unexplained type assertions
- no `console.log()` in committed code
- do not install third-party UI component libraries; use existing shadcn/ui patterns in-repo

### Git
- never commit secrets or local DB artifacts
- branch names use `feat/`, `fix/`, `docs/`, `refactor/`
- use Conventional Commits
- multi-agent safety: do not `git stash`, do not switch branches unless requested

### Security
- no hardcoded keys/secrets
- read secrets from environment or local config files designed for that purpose
- run `detect-secrets scan` before commit if you introduced new credential-like literals

---

## Locked-In Architecture Decisions

1. SQLite only for current architecture
2. no auth layer (local-first workflow)
3. OTEL-aligned span shape
4. React Flow for graph rendering
5. Monaco for prompt editing
6. Zustand for app state
7. shadcn/ui primitives in `components/ui/`
8. backend `7474`, frontend `5173`

---

## Run Commands

```bash
make install
make dev
make dev-backend
make dev-frontend
make stop
make test
make lint
make format
```

Backend API docs: `http://localhost:7474/docs`

---

## Before Declaring Work Complete

Do not tell the user your task is finished until you have verified it actually works. "It looks correct" is not verification — running the commands and seeing them pass is.

### Required checks

Run every check relevant to what you changed:

| What you touched | What to run |
|---|---|
| Backend Python code | `cd backend && pytest tests/ -v` |
| Frontend TypeScript code | `cd frontend && npm run typecheck` |
| Python SDK code | `cd sdk && pytest tests/ -v` |
| Any Python file | `cd backend && python -m ruff check app/` or relevant path |
| Any formatting | `make format` then confirm no unstaged diffs |

If you changed both backend and frontend, run both. If you're unsure what's affected, run `make test`.

### If a check fails

Fix it. Do not report the task as done with a caveat like "tests pass except for one unrelated failure." Investigate whether your change caused it. If it's genuinely pre-existing, note the specific test name and failure so the user can confirm.

### What "done" means

You can tell the user the work is complete when:
1. All relevant checks above pass
2. There are no leftover debug `print()` or `console.log()` statements
3. Your changes match what was requested — not more, not less

---

## PR Workflow (AI-Assisted)

Use `.agents/skills/` workflows:

- `/verify` - pre-commit verification (tests, typecheck, lint, debug statements)
- `/review-pr` - read-only PR analysis and findings
- `/prepare-pr` - apply fixes, update stale docs, update changelog
- `/merge-pr` - squash merge flow

Companion prompt files are in `.claude/commands/`.

---

## Where To Start

1. `docs/roadmap.md`
2. relevant subsystem doc (`docs/backend.md`, `docs/frontend.md`, `docs/sdk.md`)
3. `docs/api-contracts.md` for API work
4. `docs/data-model.md` for schema changes
5. `docs/conventions.md` for style
