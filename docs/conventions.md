# Coding Conventions

Repository-wide style and workflow rules.

---

## General Rules

1. No debug noise in committed code (`print`, `console.log`, commented-out blocks).
2. Use explicit names.
3. Handle errors intentionally.
4. Never commit secrets, `.env`, or local DB artifacts.

---

## Python (SDK + Backend)

### Formatting
- `black` (line length 88)
- `isort --profile black`

### Typing
- type hints on all function signatures
- no implicit `Any`
- prefer `|` unions over `Optional`/`Union`

### Backend Structure
- routers handle HTTP concerns only
- service layer handles business logic and DB access
- SQLAlchemy 2.x patterns (`select`, sessions passed in)

### Tests
- pytest
- in-memory SQLite for backend tests
- mock external network calls

---

## TypeScript (Frontend)

### Type Safety
- `strict: true`
- avoid `any`
- document unavoidable type assertions

### Architecture
- route-level composition in `pages/`
- shared app state in Zustand stores (`store/*`)
- API access centralized in `lib/api.ts`
- WebSocket access centralized in `lib/ws.ts`

### Components
- feature components in `components/<Feature>/`
- `components/ui/` is reserved for shadcn/ui primitives
- avoid editing shadcn primitives directly unless intentional and repo-wide

### Error Handling
- normalize HTTP errors in API client
- surface user-relevant failures in UI state/components

---

## Git Conventions

### Branch Prefixes
- `feat/`
- `fix/`
- `docs/`
- `refactor/`

### Commits
Use Conventional Commits:

```text
feat(sdk): add replay helper
fix(backend): handle unknown provider
docs(frontend): update router docs
```

---

## Do Not Commit

- `.env`
- `node_modules/`
- `__pycache__/`
- `*.pyc`
- `~/.beacon/traces.db`

---

## Locked Decisions (MVP)

- SQLite only
- no authentication layer
- React Flow for graph rendering
- Monaco for prompt editing
- Zustand for client state
- backend port `7474`, frontend port `5173`
