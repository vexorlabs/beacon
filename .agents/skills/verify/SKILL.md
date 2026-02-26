# Skill: verify

**Phase:** Pre-commit verification
**Trigger:** `/verify` (no arguments needed)

---

## Purpose

Verify that the current working tree is in a clean, passing state before committing or declaring work complete. This is the last gate before code leaves your hands.

---

## When to use

- Before committing a feature or bug fix
- Before telling the user your task is done
- When you're unsure if your changes broke something
- After a large refactor

---

## Steps

### Step 1: Identify what changed

```bash
git diff --name-only HEAD
git diff --name-only --cached
git ls-files --others --exclude-standard
```

Categorize changed files:
- **Backend Python** — anything under `backend/` or `sdk/`
- **Frontend TypeScript** — anything under `frontend/`
- **Documentation** — `.md` files, `docs/`
- **Config** — `Makefile`, `pyproject.toml`, `package.json`, etc.

### Step 2: Run relevant checks

Run every check that applies based on what changed. Do not skip checks to save time.

| Changed files | Command | Must pass |
|---|---|---|
| `backend/**/*.py` | `cd backend && pytest tests/ -v` | Yes |
| `sdk/**/*.py` | `cd sdk && pytest tests/ -v` | Yes |
| `frontend/**/*.{ts,tsx}` | `cd frontend && npm run typecheck` | Yes |
| Any Python file | `make lint` | Yes |
| Any file | `make format` then check for unstaged diffs | Yes |

If you changed files across multiple categories, run all applicable checks.

If unsure what's affected, run everything:
```bash
make test && make lint
```

### Step 3: Check for prohibited patterns

Scan your changes for things that should never be committed:

```bash
# Debug statements
git diff HEAD --unified=0 | grep -E '^\+.*console\.log\(' || true
git diff HEAD --unified=0 | grep -E '^\+.*print\(' || true

# Hardcoded secrets (look for suspicious strings in your diff)
git diff HEAD --unified=0 | grep -iE '^\+.*(api_key|secret|password|token)\s*=' || true
```

If any of these match, fix them before proceeding.

### Step 4: Report

Print a summary:

```
Verification complete.

Changed files: <count>
  Backend: <count> | Frontend: <count> | Docs: <count> | Other: <count>

Checks:
  Backend tests:     PASSED | FAILED | SKIPPED (no backend changes)
  SDK tests:         PASSED | FAILED | SKIPPED (no SDK changes)
  Frontend typecheck: PASSED | FAILED | SKIPPED (no frontend changes)
  Lint:              PASSED | FAILED
  Format:            CLEAN | DIRTY (files need formatting)
  Debug statements:  NONE FOUND | FOUND (<list>)

Verdict: READY TO COMMIT | NEEDS FIXES
```

---

## If checks fail

Do not just report the failure. Fix the issue, then re-run the failing check to confirm it passes. Only report a failure as pre-existing if you can demonstrate it exists on the base branch too:

```bash
# Check if a test failure is pre-existing
git stash && cd backend && pytest tests/test_specific.py -v && cd .. && git stash pop
```

---

## What this skill does NOT do

- It does not commit code (that's your decision)
- It does not push to remote
- It does not create PRs
- It does not review code quality or architecture — that's what `/review-pr` is for

This is purely mechanical verification: do the checks pass, yes or no.
