# Vision

## The Core Problem

Debugging AI agents is a nightmare.

Unlike traditional software that follows deterministic logic, agents are non-deterministic. Given the same input, an agent might take a different path, use a different tool, or produce a different output. This makes debugging with traditional tools nearly impossible.

Worse, existing observability tools only trace LLM calls. They miss the crucial context of what the agent actually *did* — the browser clicks, file writes, shell commands. When your agent fails, you're left sifting through raw LLM logs trying to piece together what went wrong. You're debugging by guesswork.

## Our Answer

Beacon is the **first true interactive debugger for AI agents**.

Not a monitoring platform. Not an evaluation suite. A debugger. The same relationship VS Code has to running code, Beacon has to running agents.

It provides a unified, interactive view of an agent's complete execution — from high-level reasoning to low-level computer-use actions — so developers can stop guessing and start debugging.

## The North Star Question

> *Does this make it easier and faster for a developer to debug their AI agent?*

Every feature decision, every architectural choice, every UX detail should be measured against this question. If the answer is no, we don't build it.

## What We Are

- A **local-first developer tool** — runs on your machine, zero cloud dependency
- A **debugger** — interactive, real-time, step-through
- **Framework-agnostic** — works with LangChain, CrewAI, AutoGen, LlamaIndex, and any Python or JavaScript agent
- **Open source** — MIT, free forever for local use

## What We Are Not (For Now)

- A production monitoring platform (that's LangSmith's job)
- An evaluation / scoring system (that's Braintrust's job)
- A team collaboration tool (future)
- An enterprise platform (future)

These are not flaws. They are intentional scope boundaries that keep the MVP focused.

## Differentiators

| Feature | Why It Matters |
|---------|---------------|
| **Unified trace (LLM + computer-use)** | No other tool shows LLM calls and browser/file/shell actions in one graph |
| **Time-travel debugging** | Step backward through any agent run and inspect state at any point |
| **Prompt editor + replay** | Edit any LLM prompt and re-run just that step — without re-running the whole agent |
| **Local-first** | Zero signup, zero cloud, zero latency. It just works |
| **Open source** | Developers trust tools they can read and audit |

## Positioning

```
Existing Tracers (LangSmith, Helicone)
  → "What did the LLM say?" (LLM I/O logging)

Evaluation Platforms (Braintrust, Galileo)
  → "Did it work?" (post-hoc quality scoring)

Beacon
  → "Why is it failing, right now?" (real-time, interactive debugging)
```

LangSmith is our complement, not our competition. Developers use Beacon during development to build a reliable agent, then LangSmith in production to monitor it at scale.

## The Roadmap

Phases 1–9 are complete (MVP through AI-powered debugging). See [docs/roadmap.md](docs/roadmap.md) for the full roadmap and current status.

## Success Metrics

- A developer can install `beacon-sdk`, run their agent, and see a trace in the UI in **under 5 minutes**
- Zero issues filed that say "I couldn't figure out how to set it up"
