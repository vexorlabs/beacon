# Skill: review-pr

**Phase:** 1 of 3 — Read-Only Analysis
**Trigger:** `/review-pr <PR_NUMBER>`

---

## Purpose

Perform a thorough, read-only review of a pull request. Produce structured output that a human maintainer or the `prepare-pr` skill can act on. Never modify code. Never merge.

---

## Forbidden Actions

- Do NOT make any code changes
- Do NOT push any commits
- Do NOT comment on the PR (maintainer decides)
- Do NOT run `gh pr merge` or any merge command
- Do NOT `git stash` or switch branches

---

## Setup

```bash
# Fetch the PR branch into an isolated worktree
PR=$1
git fetch origin pull/${PR}/head:pr-${PR}
git worktree add .worktrees/pr-${PR} pr-${PR}
cd .worktrees/pr-${PR}
mkdir -p .local
```

---

## Review Steps

### Step 1: Read context
```bash
gh pr view ${PR} --json title,body,author,baseRefName,headRefName,files,labels
gh pr diff ${PR}
```

Read the PR title, description, and all changed files. Understand what the author intended.

### Step 2: Check scope
- Does the diff match what the PR description claims?
- Are there unexpected file changes not mentioned in the description?
- Does it touch the right component(s) for its stated purpose?

### Step 3: Architecture review
- Does this follow the patterns in `docs/conventions.md`?
- Does this conflict with any locked-in decisions in `AGENTS.md`?
- Are there any new dependencies introduced? Are they necessary?

### Step 4: Code quality
- Python: type hints present? No `any` / `Any` without justification? Black-compatible?
- TypeScript: strict mode violations? `any` usage? `console.log` left in?
- Are there debug `print()` / `console.log()` statements in committed code?

### Step 5: Security check
- Does this PR expose any new endpoints without appropriate validation?
- Does it read/write API keys or secrets from unexpected locations?
- Does it introduce any new network calls (beyond `localhost`)?
- Does it handle untrusted input safely?

### Step 6: Test coverage
- Are there tests for the new functionality?
- Do the tests use in-memory SQLite (not the real database)?
- Do the tests pass? Run them:
  ```bash
  # Backend
  cd backend && pytest tests/ -v 2>&1 | tail -30

  # Frontend
  cd frontend && npm run typecheck 2>&1 | tail -20
  ```

### Step 7: Documentation
- Is `CHANGELOG.md` updated?
- Are any new environment variables documented in `.env.example`?
- Are new API endpoints documented in `docs/api-contracts.md`?

### Step 8: Produce output

Write `.local/review.md`:

```markdown
# PR Review: #<number> — <title>

## TL;DR
READY FOR /prepare-pr | NEEDS WORK | NEEDS DISCUSSION

## A. Scope
[Does the diff match the description?]

## B. Architecture
[Any violations of conventions or locked-in decisions?]

## C. Code Quality
[Python/TypeScript issues]

## D. Security
[Security findings]

## E. Test Coverage
[Test gaps identified]

## F. Documentation
[Missing docs or CHANGELOG entries]

## G. Findings

| Severity | Location | Issue | Suggested Fix |
|----------|----------|-------|---------------|
| BLOCKER  | file:line | description | fix |
| IMPORTANT | file:line | description | fix |
| MINOR | file:line | description | fix |
| SUGGESTION | file:line | description | fix |
```

Write `.local/review.json`:
```json
{
  "pr": <number>,
  "verdict": "ready | needs_work | needs_discussion",
  "findings": [
    {
      "severity": "blocker | important | minor | suggestion",
      "file": "path/to/file.py",
      "line": 42,
      "issue": "description",
      "fix": "suggested fix"
    }
  ],
  "test_gaps": ["description of missing tests"],
  "doc_gaps": ["description of missing docs"]
}
```

---

## Severity Definitions

| Level | Meaning |
|-------|---------|
| `blocker` | Must be fixed before merge. Correctness bug, security issue, or broken tests |
| `important` | Should be fixed. Significant code quality or design issue |
| `minor` | Nice to fix but won't block merge |
| `suggestion` | Optional improvement |

---

## Cleanup

```bash
# Return to main worktree
cd ../../
# Leave the worktree in place for prepare-pr to use
```

---

## Output

Print on completion:
```
Review complete. Verdict: <verdict>
Blockers: <count> | Important: <count> | Minor: <count>
Output: .worktrees/pr-${PR}/.local/review.md
Next step: /prepare-pr ${PR}  (if needs_work) | hand to maintainer for merge decision
```
