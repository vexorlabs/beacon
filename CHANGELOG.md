# Changelog

All notable changes to Beacon will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Beacon uses [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- feat(backend): FastAPI backend with span ingestion (`POST /v1/spans`), span detail (`GET /v1/spans/{id}`), health check, SQLAlchemy models (Trace, Span, ReplayRun), WebSocket manager for real-time broadcasting
- feat(sdk): `beacon-sdk` Python package with `@observe` decorator (sync + async), `BeaconTracer`, `HttpSpanExporter`, ContextVar-based trace context propagation
- feat(sdk): `hello_world.py` example for end-to-end validation
- test(backend): 14 pytest tests for span ingestion, trace upsert, error handling
- test(sdk): 40 pytest tests covering models, context, tracer, decorators, exporters
- Initial project documentation: architecture, data model, API contracts, SDK design, backend design, frontend design, roadmap, conventions
- `AGENTS.md` — primary AI agent instruction file (Codex/Claude/Gemini compatible)
- `CLAUDE.md` — Claude Code session bootstrap (points to AGENTS.md)
- `VISION.md` — project philosophy and north-star question
- `SECURITY.md` — vulnerability reporting policy
- `.gitignore` — Python, Node, macOS, secrets
- `.env.example` — documented environment variables
- GitHub issue templates (bug report, feature request)
- GitHub PR template
- `.agents/skills/` — three-phase PR workflow (review → prepare → merge)
- `.claude/commands/` — Claude Code slash commands for PR workflow
- Pre-commit hooks (`.pre-commit-config.yaml` + `git-hooks/pre-commit`)
- `.vscode/` — shared editor settings and extension recommendations

---

<!-- Versions will be added here as they are released -->
