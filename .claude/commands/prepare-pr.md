Prepare pull request #$ARGUMENTS for merge by fixing all BLOCKER and IMPORTANT findings from the review phase.

Read `.agents/skills/prepare-pr/SKILL.md` for the full protocol. Then:

1. Verify `.worktrees/pr-$ARGUMENTS/.local/review.json` exists (run `/review-pr $ARGUMENTS` first if not)
2. Read all findings from `review.json` and `review.md`
3. Fix every BLOCKER finding — all must be resolved before proceeding
4. Fix every IMPORTANT finding — all must be resolved before proceeding
5. Update `CHANGELOG.md` with an entry for this PR
6. Run tests: `cd backend && pytest tests/ -v` and `cd frontend && npm run typecheck`
7. Commit all changes with Conventional Commit messages
8. Push to the PR branch
9. Write `.local/prep.md` documenting what was fixed
10. Print "PR is ready for /merge-pr $ARGUMENTS"

Do NOT run `gh pr merge`. That is the maintainer's decision via `/merge-pr`.
