# SUPERPOWERS.md — Omega Powers (Cursor + OpenClaw)

> Omega = agent id `main`, all responsibilities. See `AGENTS.md` for full identity and session startup order.

---

## 1. Cursor Composer + Agent Mode

- Multi-file autonomous edits, parallel execution.
- Activate: Composer (Cmd+I) or chat Agent mode.
- Recommended flow: **Plan mode first, then Agent execution** — for complex changes.
- Best for: city JSON batch work, pipeline fixes, multi-file refactors.

## 2. MCP Servers (Model Context Protocol)

- Connect Cursor to external tools (GitHub, filesystem, Stripe, Railway, Postgres, etc.).
- Project config: [`.cursor/mcp.json`](.cursor/mcp.json). Global: `~/.cursor/mcp.json`.
- After editing `mcp.json`, reload the Cursor window.

## 3. Rules Engine (`.cursor/rules/*.mdc`)

- Project-specific guardrails auto-applied to every Cursor session.
- Active rules in this workspace:
  - `omega-execution.mdc` — execution posture, commit-first, tools-first.
  - `agent-core.mdc` — identity, session order, boundaries.
  - `agent-adops.mdc` — ad budget rules and APPROVE tokens.
  - `agent-telemetry.mdc` — backend telemetry instrumentation.
  - `agent-frontend.mdc` — city selection, `city_id` sourcing.
  - `design-system.mdc` — UI patterns.

## 4. OpenClaw Native Powers

- **Always-on:** Telegram alerts, persistent heartbeat checks, scheduled cron.
- **Skills enabled:** `parkingbreaker-ops` (telemetry observer), `reddit-budget` (Reddit Ads execution).
- **Background:** gateway runs as a systemd user service; survives logout.
- **MCP servers:** Stripe webhook, Chase OAuth, Adzviser Reddit Ads, Maton (Gmail/Notion).

## 5. Multi-Model Switching

| Model                  | Use case                                         |
| ---------------------- | ------------------------------------------------ |
| MiniMax M2.7 Highspeed | Default for OpenClaw agents (cost + speed)       |
| Claude 4 Opus/Sonnet   | Deep reasoning, architecture decisions in Cursor |
| Grok 4 / Codex 5       | Speed + tool use in Cursor                       |
| Gemini 2.5             | Multimodal (images, documents)                   |

## 6. Memory System

- `SOUL.md` + `USER.md` — identity and context.
- `MEMORY.md` — long-term memory index.
- `memory/YYYY-MM-DD.md` — daily raw logs appended after each session.
- `memory/jules-sessions.md` — Jules session tracking (if Jules is used).

## 7. Parallel Work + Hooks

- Cursor Agent: run independent tasks in parallel via Composer.
- OpenClaw cron: telemetry heartbeat (every 4h), city address lint (daily).
- GitHub PR review: use GitHub MCP or `gh` CLI.

## 8. Human-in-the-Loop

- **Only escalate** on: Reddit budget changes, destructive operations, production schema changes.
- **Approval format:** `APPROVE INCREASE <city_id> $<amount>` or `APPROVE PAUSE <city_id>` — per `AD-OPS.md`.
- Telegram is the escalation channel (OpenClaw Telegram plugin already configured).

---

Default Omega mode: Use all powers aggressively. Commit first on non-destructive work. Within boundaries — this repo only, no secrets, AD-OPS approval token for Reddit spend.
