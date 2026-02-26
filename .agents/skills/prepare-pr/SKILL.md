# Skill: prepare-pr

**Phase:** 2 of 3 — Fix and Prepare
**Trigger:** `/prepare-pr <PR_NUMBER>`
**Prerequisite:** `/review-pr <PR_NUMBER>` must have been run first. `.local/review.json` must exist.

---

## Purpose

Resolve all BLOCKER and IMPORTANT findings from the review phase. Update stale documentation. Update the CHANGELOG. Push a clean, ready-to-merge state to the PR branch.

---

## Forbidden Actions

- Do NOT run `gh pr merge` or any merge command
- Do NOT `git stash`
- Do NOT push directly to `main`
- Do NOT force-push unless the maintainer explicitly asks
- Do NOT skip fixing BLOCKER findings (they are non-negotiable)

---

## Setup

```bash
PR=$1
cd .worktrees/pr-${PR}   # Use the worktree created by review-pr

# Verify review artifacts exist
test -f .local/review.json || { echo "ERROR: run /review-pr ${PR} first"; exit 1; }
```

---

## Steps

### Step 1: Read the review
```bash
cat .local/review.md
cat .local/review.json
```

Note all BLOCKER and IMPORTANT findings. These must all be fixed before proceeding.

### Step 2: Fix BLOCKERs (mandatory)

For each BLOCKER finding:
1. Read the file and understand the context
2. Make the fix
3. Run relevant tests to confirm the fix works
4. Note the fix in `.local/prep.md`

Do not mark a BLOCKER as resolved unless tests pass.

### Step 3: Fix IMPORTANTs (mandatory)

Same process as BLOCKERs. All IMPORTANT findings must be resolved.

### Step 4: Fix MINORs (optional, use judgement)

Fix minor issues if they are quick and clearly correct. Skip if complex or opinionated.

### Step 5: Update stale documentation

Read `doc_gaps` from `.local/review.json`. For each documentation gap:

1. Read the current doc file to understand its structure and tone
2. Make targeted updates — do not rewrite entire sections, just fix what's inaccurate or missing
3. Keep the same formatting, heading levels, and conventions the doc already uses
4. If a doc gap requires information you don't have (e.g., design rationale), add a `<!-- TODO: ... -->` comment rather than guessing

Common documentation updates:
- Adding a new router/endpoint to the lists in `AGENTS.md` and `docs/backend.md`
- Adding a new integration to `docs/sdk.md`
- Updating schema descriptions in `docs/data-model.md`
- Adding new API endpoints to `docs/api-contracts.md`
- Updating component lists in `docs/frontend.md`

Note each doc update in `.local/prep.md`.

### Step 6: Update CHANGELOG

```bash
# Add an entry under [Unreleased] in CHANGELOG.md
# Format: "- feat(sdk): add @observe decorator with async support"
# Every PR must have at least one CHANGELOG entry
```

### Step 7: Verify

```bash
# Backend
cd backend && pytest tests/ -v

# Frontend type check
cd frontend && npm run typecheck

# Confirm no debug output
grep -r "print(" backend/app/ sdk/beacon_sdk/ --include="*.py" | grep -v "# " || true
grep -r "console.log(" frontend/src/ --include="*.ts" --include="*.tsx" || true
```

All tests must pass before proceeding.

### Step 8: Commit changes

Use descriptive, Conventional Commit messages. Commit each logical change separately.

```bash
# Example: code fix
git add backend/app/routers/spans.py
git commit -m "fix(backend): handle duplicate span_id gracefully on ingestion"

# Example: doc updates
git add docs/backend.md AGENTS.md
git commit -m "docs: update reference docs to reflect new router"

git add CHANGELOG.md
git commit -m "docs: update changelog for PR #${PR}"
```

### Step 9: Push

```bash
# Get the current remote SHA first (safety check)
REMOTE_SHA=$(gh pr view ${PR} --json headRefOid -q .headRefOid)
echo "Remote SHA: ${REMOTE_SHA}"

# Push
git push origin HEAD
```

### Step 10: Produce output

Write `.local/prep.md`:
```markdown
# PR Preparation: #<number>

## Fixes Applied
- [x] BLOCKER: <description> — fixed in <commit>
- [x] IMPORTANT: <description> — fixed in <commit>
- [ ] MINOR: <description> — skipped (reason)

## Documentation Updated
- [x] <doc file> — <what was updated>
- [ ] <doc file> — skipped (<reason>)

## CHANGELOG Updated
Yes — added entry: "<changelog entry>"

## Tests
Backend: PASSED (<n> passed, <n> warnings)
Frontend typecheck: PASSED

## Ready
PR is ready for /merge-pr
```

---

## Output

Print on completion:
```
Preparation complete. All blockers resolved.
Tests: PASSED
PR is ready for /merge-pr <PR_NUMBER>
```
