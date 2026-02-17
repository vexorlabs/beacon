# Skill: merge-pr

**Phase:** 3 of 3 — Squash Merge
**Trigger:** `/merge-pr <PR_NUMBER>`
**Prerequisite:** Both `/review-pr` and `/prepare-pr` must have completed. All four artifacts must exist.

---

## Purpose

Squash and merge the PR into `main` with correct attribution. Verify it lands cleanly. Clean up the worktree.

---

## Forbidden Actions

- Do NOT use `gh pr merge --auto`
- Do NOT use `git push --force` to `main`
- Do NOT merge if any required artifact is missing
- Do NOT merge if CI is failing
- Do NOT merge if the PR status is anything other than OPEN

---

## Prerequisites Check

```bash
PR=$1
WORKTREE=".worktrees/pr-${PR}"

# Verify all artifacts exist
test -f "${WORKTREE}/.local/review.md"   || { echo "ERROR: missing review.md — run /review-pr first"; exit 1; }
test -f "${WORKTREE}/.local/review.json" || { echo "ERROR: missing review.json"; exit 1; }
test -f "${WORKTREE}/.local/prep.md"     || { echo "ERROR: missing prep.md — run /prepare-pr first"; exit 1; }

# Check PR is still open
STATUS=$(gh pr view ${PR} --json state -q .state)
[[ "${STATUS}" == "OPEN" ]] || { echo "ERROR: PR is ${STATUS}, not OPEN"; exit 1; }

# Check CI status
CI=$(gh pr view ${PR} --json statusCheckRollup -q '.statusCheckRollup[] | select(.conclusion != "SUCCESS") | .name' 2>/dev/null || echo "")
[[ -z "${CI}" ]] || { echo "ERROR: CI failing on: ${CI}"; exit 1; }
```

---

## Steps

### Step 1: Get author info for attribution

```bash
AUTHOR=$(gh pr view ${PR} --json author -q .author.login)
echo "PR author: ${AUTHOR}"
```

### Step 2: Squash merge

```bash
# Get current HEAD SHA for safety
HEAD_SHA=$(gh pr view ${PR} --json headRefOid -q .headRefOid)

gh pr merge ${PR} \
  --squash \
  --match-head-commit "${HEAD_SHA}" \
  --body "$(cat ${WORKTREE}/.local/prep.md)"
```

The commit message should follow Conventional Commits format. Set it explicitly:

```bash
# Construct a clean squash commit message
TITLE=$(gh pr view ${PR} --json title -q .title)
gh pr merge ${PR} \
  --squash \
  --match-head-commit "${HEAD_SHA}" \
  --subject "${TITLE}" \
  --body "Co-authored-by: ${AUTHOR} <${AUTHOR}@users.noreply.github.com>"
```

### Step 3: Verify merge landed

```bash
FINAL_STATUS=$(gh pr view ${PR} --json state -q .state)
[[ "${FINAL_STATUS}" == "MERGED" ]] || { echo "ERROR: PR state is ${FINAL_STATUS}, expected MERGED"; exit 1; }
echo "PR #${PR} successfully merged."
```

### Step 4: Clean up worktree

```bash
git worktree remove ".worktrees/pr-${PR}" --force
git branch -D "pr-${PR}" 2>/dev/null || true
```

---

## Output

Print on completion:
```
PR #<number> merged successfully.
State: MERGED
Worktree cleaned up.
```

If anything fails, print the error clearly and exit non-zero. Do not attempt to recover automatically — surface the error to the maintainer.
