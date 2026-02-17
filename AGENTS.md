# Beacon — AI Agent Instructions

> **Primary instructions file for all AI coding agents** (Claude, Codex, Gemini, etc.)
> Claude Code users: `CLAUDE.md` exists at repo root and points here.

---

## What Is Beacon?

Beacon is an **open-source, local-first observability and debugging platform for AI agents**. Think "Chrome DevTools for AI Agents."

The core problem: debugging AI agents is a nightmare because existing tools only trace LLM calls, missing the full picture of what the agent does (browser clicks, file writes, shell commands). Beacon provides a **unified trace** that captures both LLM reasoning and computer-use actions in a single interactive view.

**Key differentiators:**
- Unified trace: LLM calls + browser actions + file ops + shell commands in one graph
- Time-travel debugging: click any node, inspect state, edit the prompt, replay that single step
- Local-first: zero cloud dependency, developer's machine only (for now)
- Framework-agnostic: works with LangChain, CrewAI, custom agents via monkey-patching

Full vision: `VISION.md`
Full architecture: `docs/architecture.md`

---

## Repo Structure

```
beacon/
├── AGENTS.md                  # You are here (primary for Codex + all agents)
├── CLAUDE.md                  # Claude Code reads this — points here
├── VISION.md                  # Project vision and philosophy
├── SECURITY.md                # Security reporting
├── CHANGELOG.md               # Version history
├── README.md                  # Public-facing overview
├── LICENSE
│
├── .agents/                   # AI agent workflow skills
│   └── skills/
│       ├── review-pr/         # Phase 1: read-only PR review
│       ├── prepare-pr/        # Phase 2: fix and prepare PR
│       └── merge-pr/          # Phase 3: squash merge
│
├── .claude/commands/          # Claude Code slash commands (versioned prompts)
│   ├── review-pr.md
│   ├── prepare-pr.md
│   └── merge-pr.md
│
├── .github/
│   ├── workflows/             # CI/CD pipelines
│   ├── ISSUE_TEMPLATE/        # Bug + feature templates
│   └── pull_request_template.md
│
├── git-hooks/                 # Pre-commit hook scripts
│   └── pre-commit
│
├── docs/                      # Architecture and design docs
│   ├── architecture.md
│   ├── data-model.md
│   ├── api-contracts.md
│   ├── sdk.md
│   ├── backend.md
│   ├── frontend.md
│   ├── roadmap.md
│   └── conventions.md
│
├── sdk/                       # Python instrumentation SDK (pip package)
│   ├── beacon_sdk/
│   │   ├── __init__.py
│   │   ├── tracer.py
│   │   ├── decorators.py
│   │   ├── context.py
│   │   ├── exporters.py
│   │   └── integrations/
│   │       ├── langchain.py
│   │       ├── openai.py
│   │       ├── anthropic.py
│   │       └── playwright.py
│   ├── tests/
│   └── pyproject.toml
│
├── backend/                   # FastAPI backend
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── routers/
│   │   │   ├── traces.py
│   │   │   ├── spans.py
│   │   │   └── replay.py
│   │   ├── ws/
│   │   │   └── manager.py
│   │   └── services/
│   └── pyproject.toml
│
└── frontend/                  # Vite + React UI
    ├── src/
    │   ├── components/
    │   │   ├── ui/            # shadcn/ui (DO NOT edit)
    │   │   ├── TraceList/
    │   │   ├── TraceGraph/
    │   │   ├── SpanDetail/
    │   │   └── TimeTravel/
    │   ├── lib/
    │   │   ├── api.ts
    │   │   ├── ws.ts
    │   │   └── types.ts
    │   └── store/
    │       └── trace.ts
    ├── package.json
    └── vite.config.ts
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| SDK | Python 3.11+ | AI/ML ecosystem |
| Backend | FastAPI + Uvicorn | Async-native, auto-docs |
| Database | SQLite (SQLAlchemy) | Zero-config, local-first |
| Real-time | WebSockets (FastAPI) | Live span streaming |
| Frontend | Vite + React 18 + TypeScript | Fast dev, type safety |
| Graph viz | React Flow (`@xyflow/react`) | Interactive graphs |
| Code editor | Monaco Editor | VS Code quality in browser |
| UI components | shadcn/ui + Tailwind CSS | Copy-paste, no npm bloat |
| State | Zustand | Simpler than Redux |
| Trace standard | OpenTelemetry (OTEL) | Industry standard |

---

## Core Concepts

### Span
A single unit of work. Every agent action (LLM call, tool use, browser click, file write) produces one span.

Fields: `span_id`, `trace_id`, `parent_span_id`, `span_type`, `name`, `status`, `start_time`, `end_time`, `attributes`

### SpanType
```
llm_call | tool_use | agent_step | browser_action | file_operation | shell_command | chain | custom
```

### Trace
All spans sharing a `trace_id` from one agent run. Displayed as an interactive DAG in the UI.

Full schema: `docs/data-model.md`
Full API: `docs/api-contracts.md`

---

## Mandatory Rules (Never Violate)

### Python
- Type hints on **all** function signatures — no exceptions
- No implicit `Any`. Import `Any` explicitly and only when type is genuinely unstructured
- Use `|` unions (Python 3.10+), not `Optional[X]` or `Union[X, Y]`
- Run `black` + `isort --profile black` before committing
- Never `print()` for debugging — use `logging`
- Tests use in-memory SQLite — never touch `~/.beacon/traces.db`

### TypeScript
- `strict: true` in tsconfig — no exceptions
- No `any`. Use `unknown` + type narrowing
- No type assertions (`as SomeType`) without an explanatory comment
- Never `console.log()` in committed code
- No npm installs for UI components — use `npx shadcn@latest add <component>`

### Git
- Never commit `.env` files, `__pycache__/`, `node_modules/`, `*.pyc`, `~/.beacon/traces.db`
- Branch names: `feat/`, `fix/`, `docs/`, `refactor/` prefix
- Commits follow Conventional Commits: `feat(sdk):`, `fix(backend):`, etc.
- **Multi-agent safety**: do not `git stash`, do not switch branches unless explicitly asked

### Security
- Never add API keys, passwords, or secrets to code or config files
- Read all secrets from environment variables
- Run `detect-secrets scan` before committing if you've added new strings

---

## Locked-In Architecture Decisions

Do not change these without updating `docs/architecture.md`:

1. **SQLite only** — no PostgreSQL for MVP
2. **No authentication** — intentional for local-first dev tool
3. **OTEL span format** — all spans must conform to the OTEL spec
4. **React Flow for graphs** — not D3.js directly
5. **Monaco for code editing** — not CodeMirror or textarea
6. **Zustand for state** — not Redux or Context API
7. **shadcn/ui components** — copy-paste, never `npm install` component libraries
8. **Port 7474** for backend, **5173** for frontend

---

## Running the Project

```bash
# Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 7474

# Frontend
cd frontend
npm run dev   # http://localhost:5173

# SDK (development)
cd sdk
pip install -e ".[dev]"
```

Backend auto-docs: `http://localhost:7474/docs`

---

## PR Workflow (AI-Assisted)

Use the `.agents/skills/` system for PRs. Three phases:

1. `/review-pr` — read-only analysis, produces `review.md` + `review.json`
2. `/prepare-pr` — fix BLOCKER/IMPORTANT findings, update CHANGELOG
3. `/merge-pr` — squash merge with correct attribution

See `.agents/skills/*/SKILL.md` for full instructions per phase.

---

## Where to Start on Any Feature

1. Check `docs/roadmap.md` for current phase
2. Read the relevant design doc (`docs/backend.md`, `docs/frontend.md`, `docs/sdk.md`)
3. Check `docs/api-contracts.md` if touching API boundaries
4. Check `docs/data-model.md` if touching the database
5. Follow `docs/conventions.md` for style
