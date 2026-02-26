# Security Policy

## Supported Versions

Beacon is currently pre-v1.0. Security fixes are applied to the `main` branch only.

| Version | Supported |
|---------|-----------|
| main (pre-1.0) | ✅ |

## Reporting a Vulnerability

**Please do not file a public GitHub issue for security vulnerabilities.**

Report security issues privately to: **security@vexorlabs.com**

Include in your report:
- **Title:** One-sentence summary of the vulnerability
- **Severity:** Critical / High / Medium / Low
- **Impact:** What an attacker could do if this is exploited
- **Component:** Which part of Beacon is affected (SDK, backend, frontend)
- **Steps to reproduce:** Shortest deterministic path to trigger the issue
- **Environment:** OS, Python version, Node version, Beacon version/commit

We will acknowledge receipt within 48 hours and aim to provide a fix or mitigation within 14 days for critical issues.

## Scope

### In Scope
- The `beacon-sdk` Python package (`sdk/`)
- The `beacon-sdk` JS/TS package (`sdk-js/`)
- The `beacon-backend` FastAPI service (`backend/`)
- The `beacon-ui` React frontend (`frontend/`)
- The pre-commit hooks and CI scripts

### Out of Scope
- Vulnerabilities in third-party dependencies (report to the dependency maintainer)
- Issues requiring physical access to the developer's machine
- Social engineering attacks

## Security Model

Beacon is a **local-first developer tool**. It is designed to run on a developer's local machine and is not intended to be exposed to the internet.

By design:
- The backend has **no authentication** — it trusts all connections to `localhost:7474`
- The backend stores traces in `~/.beacon/traces.db` with filesystem permissions only
- The backend only calls external LLM APIs (OpenAI, Anthropic, Google) during replay and analysis operations, using keys from your environment

**Do not expose Beacon's backend port (7474) to a public network.** It is designed for localhost only.

## Known Limitations

- Trace data (including LLM prompts and completions) is stored in plaintext in SQLite at `~/.beacon/traces.db`. If your prompts contain sensitive data, ensure the file is protected with appropriate filesystem permissions.
- The replay feature sends prompt data to external LLM APIs. Be aware of what data you are sending.
