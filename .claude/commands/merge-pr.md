Merge pull request #$ARGUMENTS following the protocol in `.agents/skills/merge-pr/SKILL.md`.

Read that file first. Then:

1. Verify all four artifacts exist in `.worktrees/pr-$ARGUMENTS/.local/`: `review.md`, `review.json`, `prep.md`
2. Verify the PR is still OPEN with `gh pr view $ARGUMENTS --json state`
3. Verify CI is passing — check all status checks
4. Get the current HEAD SHA with `gh pr view $ARGUMENTS --json headRefOid`
5. Squash merge using `gh pr merge $ARGUMENTS --squash --match-head-commit <SHA>`
6. Verify `gh pr view $ARGUMENTS --json state` returns `MERGED`
7. Clean up the worktree: `git worktree remove .worktrees/pr-$ARGUMENTS --force`
8. Print confirmation: "PR #$ARGUMENTS merged successfully."

NEVER use `gh pr merge --auto`. NEVER force-push to main. If anything is wrong, stop and report the error.
