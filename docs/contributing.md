# Contributing to Beacon

## Prerequisites

- Python 3.11+
- Node.js 20+
- `make`

## Getting Started

```bash
git clone https://github.com/vexorlabs/beacon
cd beacon
make install
make dev
```

Open `http://localhost:5173`.

## Common Commands

| Command | Purpose |
|---|---|
| `make dev` | backend + frontend |
| `make dev-backend` | backend only (`7474`) |
| `make dev-frontend` | frontend only (`5173`) |
| `make stop` | stop dev servers |
| `make test` | backend + sdk tests |
| `make lint` | black/isort/eslint checks |
| `make format` | black + isort autofix |
| `make db-reset` | delete `~/.beacon/traces.db` |

## Branch + Commit Conventions

- Branch prefixes: `feat/`, `fix/`, `docs/`, `refactor/`
- Conventional commits: `feat(backend): ...`, `fix(frontend): ...`, etc.

## Code Style

Python:
- type hints on all signatures
- `black` + `isort --profile black`
- use `logging`, not `print()`

TypeScript:
- strict typing (`strict: true`)
- avoid `any`
- no `console.log()` in committed code

See `docs/conventions.md` for full details.

## Security + Safety

- never commit secrets or `.env`
- never commit `~/.beacon/traces.db`
- prefer in-memory SQLite for tests

## Useful Docs

- `docs/architecture.md`
- `docs/api-contracts.md`
- `docs/data-model.md`
- `docs/backend.md`
- `docs/frontend.md`
- `docs/sdk.md`
