Verify the current working tree following the protocol in `.agents/skills/verify/SKILL.md`.

Read that file first for the full instructions. Then:

1. Identify what files have changed (staged, unstaged, and untracked)
2. Run all applicable checks (tests, typecheck, lint, format)
3. Scan for prohibited patterns (debug statements, hardcoded secrets)
4. Print the verification summary with pass/fail status for each check

This is a **pre-commit verification**. Do not commit, push, or create PRs.
