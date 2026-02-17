# Coding Conventions

This document defines the rules all code in this repo must follow. AI coding assistants should read this before writing any code.

---

## General Rules (All Languages)

1. **No debug output in committed code.** Remove all `print()`, `console.log()`, and similar before committing.
2. **No commented-out code.** Delete it. Git history preserves old code.
3. **No magic numbers.** Extract constants with names.
4. **Names must be explicit.** `span_start_time` not `t`. `handle_span_created` not `handler`.
5. **Errors must be handled.** Never silently swallow exceptions (except in the SDK exporter, which is explicitly documented to do so).
6. **No `.env` files committed.** Use `.env.example` with placeholder values.
7. **No API keys in code.** Read them from environment variables.

---

## Python (SDK + Backend)

### Formatting
- **Formatter:** `black` with default settings (88-char line length)
- **Import sorter:** `isort` with `--profile black`
- Run both before every commit

### Type Hints
- Type hints on **all** function signatures (parameters + return type)
- Use `from __future__ import annotations` at the top of files for forward references
- No implicit `Any`. Use `object` if type is truly unknown. Use `dict[str, Any]` with an explicit `Any` import only when the value type is genuinely unstructured (e.g., OTEL attributes)
- Use `|` syntax for unions (Python 3.10+), not `Optional[X]` or `Union[X, Y]`

```python
# Good
def create_span(span_id: str, parent_id: str | None = None) -> Span:

# Bad
def create_span(span_id, parent_id=None):
```

### Naming
| Thing | Convention | Example |
|-------|-----------|---------|
| Files | `snake_case` | `span_service.py` |
| Classes | `PascalCase` | `BeaconTracer` |
| Functions | `snake_case` | `get_current_span` |
| Variables | `snake_case` | `trace_id` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_BACKEND_URL` |
| Private | `_leading_underscore` | `_active_spans` |

### Classes vs Functions
- Prefer functions for stateless operations
- Use classes when there is meaningful state to encapsulate (`BeaconTracer`, `ConnectionManager`)
- Do not use classes purely as namespaces; use modules instead

### Pydantic Models (Backend Schemas)
- All request/response schemas in `schemas.py` are Pydantic v2 models
- Use `model_config = ConfigDict(...)` not inner `Config` class (Pydantic v2 style)
- Validators use `@field_validator` (v2 style), not `@validator`

### FastAPI Routers
- One router file per top-level resource: `spans.py`, `traces.py`, `replay.py`
- All router functions are `async`
- Use `Annotated[Session, Depends(get_db)]` for dependency injection
- Return Pydantic response models explicitly (enables OpenAPI docs)

```python
# Good
@router.get("/{trace_id}", response_model=TraceDetailResponse)
async def get_trace(
    trace_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> TraceDetailResponse:
    ...

# Bad
@router.get("/{trace_id}")
def get_trace(trace_id, db=Depends(get_db)):
    ...
```

### SQLAlchemy
- Use SQLAlchemy 2.0 style (`select()` not `query()`)
- Pass `db` sessions into service functions; do not create sessions inside services
- All database writes use explicit transactions

### Testing (pytest)
- Test files: `test_<module>.py`
- Test functions: `test_<what>_<condition>_<expectation>()`
- Use `pytest.fixture` for shared setup
- Use in-memory SQLite for all tests (`sqlite:///:memory:`)
- Never hit the network in tests; mock external calls with `pytest-mock` or `responses`

```python
# Good test name
def test_create_span_with_missing_trace_id_raises_validation_error():

# Bad test name
def test_span():
```

---

## TypeScript (Frontend)

### Formatting
- **Formatter:** Prettier with default settings
- **Linter:** ESLint with `eslint-config-react-app` or the Vite default config
- Both run on save via editor settings and on CI

### Type Safety
- `strict: true` in `tsconfig.json`. No exceptions.
- No `any`. Use `unknown` + type narrowing when type is uncertain.
- No type assertions (`as SomeType`) unless there is a comment explaining why it's safe.
- Prefer `interface` over `type` for object shapes that represent entities.
- Use `type` for unions, intersections, and computed types.

```typescript
// Good
interface Span {
  span_id: string;
  span_type: SpanType;
}

type SpanType = "llm_call" | "tool_use" | "browser_action";

// Bad
const span = response as any;
```

### Naming
| Thing | Convention | Example |
|-------|-----------|---------|
| Files (components) | `PascalCase` | `TraceGraph.tsx` |
| Files (utilities) | `camelCase` | `api.ts` |
| React components | `PascalCase` | `TraceList` |
| Hooks | `useCamelCase` | `useGraphLayout` |
| Variables | `camelCase` | `selectedSpanId` |
| Constants | `UPPER_SNAKE_CASE` | `BASE_URL` |
| Interfaces | `PascalCase` | `Span`, `TraceSummary` |
| Type aliases | `PascalCase` | `SpanType` |

### React Components
- One component per file (except small, tightly coupled sub-components)
- Component folder structure: `ComponentName/index.tsx` for the main component
- Props interfaces defined in the same file, named `ComponentNameProps`
- Export the component as the default export

```typescript
// TraceList/index.tsx
interface TraceListProps {
  traces: TraceSummary[];
  onSelectTrace: (traceId: string) => void;
}

export default function TraceList({ traces, onSelectTrace }: TraceListProps) {
  ...
}
```

### Hooks
- All data fetching via custom hooks, not directly in components
- State that is shared between components goes in the Zustand store
- Local state (UI-only, not shared) stays in `useState` within the component

### shadcn/ui Components
- Never edit files in `src/components/ui/`. If you need to customize, copy the component out and rename it.
- Add new shadcn components with `npx shadcn@latest add <component>`.

### Imports
- Use absolute imports via `"paths"` in `tsconfig.json` (e.g., `import { Span } from "@/lib/types"`)
- Order: React → third-party → local (enforced by ESLint import plugin)

### Error Handling
- All `fetch` calls must handle errors (check `res.ok`, catch network errors)
- Display user-facing errors via toast notifications (use shadcn `sonner` or `toast`)
- Never `console.error` in production code paths — handle the error or surface it to the user

---

## Git Conventions

### Branch Names
- `feat/<short-description>` — New feature
- `fix/<short-description>` — Bug fix
- `docs/<short-description>` — Documentation only
- `refactor/<short-description>` — Refactoring, no new behavior

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
Scopes: `sdk`, `backend`, `frontend`, `deps`

Examples:
```
feat(sdk): add @observe decorator with async support
fix(backend): handle duplicate span_id on ingestion
docs(frontend): document React Flow layout approach
```

### What NOT to Commit
- `.env` files
- `__pycache__/`
- `node_modules/`
- `*.pyc`
- `~/.beacon/traces.db` (the live database)
- IDE config (`.vscode/`, `.idea/`) — these go in `.gitignore`

---

## File Organization Rules

- No business logic in router files. Routers call service functions.
- No database queries in service files — pass `db` session in as a parameter.
- No imports between `sdk/` and `backend/` — they are independent packages.
- No imports between `frontend/` and `backend/` — they communicate only via HTTP/WebSocket.

---

## Do Not

- Do not add a new database (SQLite only for MVP)
- Do not add authentication (no-auth is a feature for local dev tool)
- Do not use `print()` for debugging in committed code (use `logging`)
- Do not use `console.log()` in committed frontend code
- Do not install npm packages for UI components (use shadcn copy-paste)
- Do not use `any` in TypeScript
- Do not skip type hints in Python
- Do not add external API calls to the backend (except LLM APIs in the replay service)
