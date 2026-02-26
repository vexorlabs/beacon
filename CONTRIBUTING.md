# Contributing to Beacon

Thanks for your interest in contributing to Beacon! This guide will help you get set up and productive.

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- `make`

## Getting Started

```bash
git clone https://github.com/vexorlabs/beacon.git
cd beacon
make install
make dev
```

Open `http://localhost:5173` to see the Beacon UI.

---

## Development Commands

| Command | Purpose |
|---------|---------|
| `make dev` | Start backend (7474) + frontend (5173) |
| `make dev-backend` | Backend only |
| `make dev-frontend` | Frontend only |
| `make test` | Run all tests (backend + SDK + JS SDK + frontend) |
| `make lint` | Run all linters (black, isort, eslint) |
| `make format` | Auto-format (black + isort) |
| `make demo` | Generate sample traces (no API keys needed) |
| `make stop` | Stop dev servers |
| `make db-reset` | Delete `~/.beacon/traces.db` |

Backend API docs: `http://localhost:7474/docs`

---

## Project Structure

```text
beacon/
├── backend/    # FastAPI + SQLite (Python)
├── frontend/   # React + Vite + TypeScript
├── sdk/        # beacon-sdk Python package
├── sdk-js/     # beacon-sdk JS/TS package
└── docs/       # Architecture, API contracts, data model, roadmap
```

---

## Finding Work

- Look for issues labeled [`good first issue`](https://github.com/vexorlabs/beacon/labels/good%20first%20issue) on GitHub
- Check the [roadmap](docs/roadmap.md) for upcoming features
- Browse [GitHub Discussions](https://github.com/vexorlabs/beacon/discussions) for ideas

---

## Branch and Commit Conventions

**Branch prefixes:**

- `feat/` — new features
- `fix/` — bug fixes
- `docs/` — documentation changes
- `refactor/` — code restructuring

**Commit messages** follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(backend): add trace export endpoint
fix(frontend): handle empty span attributes
docs: update SDK quickstart guide
```

Scope should be one of: `backend`, `frontend`, `sdk`, `sdk-js`, `docs`.

---

## Code Style

### Python

- Type hints on all function signatures — no implicit `Any`
- Format with `black` and `isort --profile black`
- Use `logging`, never `print()` for debug output
- Prefer in-memory SQLite for tests

### TypeScript

- `strict: true` — no `any` types
- No `console.log()` in committed code
- Follow existing component patterns in `frontend/src/`

See [docs/conventions.md](docs/conventions.md) for the full style guide.

---

## Testing

Run all tests before submitting a PR:

```bash
make test
```

This runs:

- `pytest backend/tests/` — backend API and service tests
- `pytest sdk/tests/` — Python SDK integration tests
- `npm --prefix frontend run test` — frontend component and store tests
- `npm --prefix sdk-js run test` — JS SDK tests

Write tests for new features. Use mocks for external API calls (OpenAI, Anthropic, etc.).

---

## Pull Request Process

1. Fork the repo and create a branch from `main`
2. Make your changes, following the code style above
3. Add or update tests as needed
4. Run `make test` and `make lint` — both must pass
5. Fill in the PR template (summary, change type, testing)
6. Link to the relevant GitHub issue if one exists

A maintainer will review your PR. We aim to respond within a few days.

---

## Security

Found a vulnerability? **Do not file a public issue.** See [SECURITY.md](SECURITY.md) for responsible disclosure instructions.

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
