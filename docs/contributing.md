# Contributing to Beacon

## Prerequisites

- Python 3.11+
- Node.js 20+
- `make`

## Getting Started

```bash
git clone https://github.com/vexorlabs/beacon
cd beacon
make install   # creates venv, installs backend + SDK + frontend deps
make dev       # starts backend (:7474) and frontend (:5173)
```

Open [http://localhost:5173](http://localhost:5173) to see the UI.

## Project Structure

```
backend/    Python/FastAPI backend + SQLite database
sdk/        beacon-sdk Python package (instrumentation + integrations)
frontend/   React/TypeScript UI (Vite, React Flow, Monaco)
docs/       Architecture, API contracts, data model, conventions
```

## Development

| Command | What it does |
|---|---|
| `make dev` | Start backend + frontend together |
| `make dev-backend` | Backend only (port 7474) |
| `make dev-frontend` | Frontend only (port 5173) |
| `make stop` | Kill both servers |
| `make test` | Run backend + SDK pytest tests |
| `make lint` | Check formatting (black, isort, eslint) |
| `make format` | Auto-format Python code |
| `make db-reset` | Delete `~/.beacon/traces.db` |
| `make clean` | Remove venvs, node_modules, build artifacts |

The SDK is installed in editable mode (`pip install -e`), so changes to `sdk/` are picked up immediately.

## Code Style

**Python:**
- Formatted with `black` + `isort` (run `make format`)
- Type hints on all function signatures — no implicit `Any`
- No `print()` statements in committed code (use `logging`)

**TypeScript:**
- `strict: true` in tsconfig
- No `any` types
- No `console.log` in committed code

See [conventions.md](./conventions.md) for the full style guide.

## PR Guidelines

1. **Branch naming:** `username/short-description`
2. **Commit messages:** Conventional Commits style (`feat:`, `fix:`, `docs:`, `refactor:`)
3. **Tests pass:** `make test` must pass before submitting
4. **No secrets:** Never commit `.env`, API keys, or `~/.beacon/traces.db`

## Further Reading

- [Architecture](./architecture.md) — system design and data flow
- [Data Model](./data-model.md) — database schema
- [API Contracts](./api-contracts.md) — REST and WebSocket specs
- [Conventions](./conventions.md) — full code style guide
