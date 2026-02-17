Review the pull request #$ARGUMENTS following the protocol in `.agents/skills/review-pr/SKILL.md`.

Read that file first for the full instructions. Then:

1. Fetch the PR with `gh pr view $ARGUMENTS` and `gh pr diff $ARGUMENTS`
2. Check out the PR branch in an isolated worktree at `.worktrees/pr-$ARGUMENTS`
3. Perform all 8 review steps from the skill file
4. Write `.local/review.md` and `.local/review.json` to the worktree
5. Print the TL;DR verdict and finding counts

This is a **read-only phase**. Make no code changes. Make no commits. Do not merge.
