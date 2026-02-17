## Summary

<!-- 2–4 bullet points describing what this PR does. Be specific. -->

-
-

## Change Type

<!-- Check all that apply -->

- [ ] `feat` — New feature
- [ ] `fix` — Bug fix
- [ ] `refactor` — Refactoring (no behavior change)
- [ ] `docs` — Documentation only
- [ ] `test` — Tests only
- [ ] `chore` — Build, CI, tooling
- [ ] `perf` — Performance improvement

## Scope

<!-- Which component(s) does this touch? -->

- [ ] `sdk` — Python instrumentation SDK
- [ ] `backend` — FastAPI backend
- [ ] `frontend` — React UI
- [ ] `docs` — Documentation
- [ ] `ci` — CI/CD pipelines
- [ ] `deps` — Dependency updates

## What Was NOT Changed

<!-- Explicitly state what this PR does not touch. Helps reviewers stay focused. -->

This PR does not change:
-

## Testing

<!-- How did you verify this works? -->

- [ ] Backend: `cd backend && pytest tests/ -v` passes
- [ ] Frontend: `cd frontend && npm run typecheck && npm run lint` passes
- [ ] Manual test: describe what you ran and what you saw

**Manual test description:**

<!-- e.g. "Ran the hello_world.py example, confirmed span appeared in UI with correct attributes" -->

## Security Impact

<!-- AI agents and contributors: answer these honestly -->

- **Does this PR add or modify network endpoints?** Yes / No
- **Does this PR handle user-supplied input?** Yes / No
- **Does this PR touch API key handling or environment variable reading?** Yes / No
- **Does this PR read or write files on disk?** Yes / No

If any answer is Yes, describe the security considerations:

## Breaking Changes

- [ ] This PR introduces a breaking change

If checked, describe what breaks and how users should migrate:

## AI Assistance

- [ ] This PR was written with AI assistance (Claude, Codex, etc.)

If checked: briefly describe what was AI-generated vs human-reviewed.
