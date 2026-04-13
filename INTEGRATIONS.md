# INTEGRATIONS.md — Omega Integration Reference

> Omega = agent id `main`. All skills and MCP servers listed here are already installed or documented for this workspace.

---

## Cursor MCP Servers

**Project config:** [`.cursor/mcp.json`](.cursor/mcp.json) — Cursor loads this on startup. After any edit, **reload the Cursor window**.

```json
{
  "mcpServers": {
    "stitch": {
      "url": "https://stitch.googleapis.com/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_ACCESS_TOKEN>",
        "X-Goog-User-Project": "<YOUR_PROJECT_ID>"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/home/amir/homebase/code/FIGHTCITYTICKETS-1"
      ]
    }
  }
}
```

**Note:** Replace `stitch` headers with real values before use. `github` and `filesystem` are stdio servers; they require no token for public repos but `GITHUB_PERSONAL_ACCESS_TOKEN` is recommended for private repo access — set as an environment variable, not in this file.

### Adding a new MCP server

1. Add entry to `.cursor/mcp.json` (stdio or URL type).
2. Reload Cursor window.
3. Verify with a test query (e.g. "list files in backend/src").

---

## OpenClaw Configuration

**Config file:** `~/.openclaw/openclaw.json`

### MCP servers (Stripe + others)

OpenClaw only supports **stdio** MCP (`command` / `args`) or **remote** MCP (`url` + optional `headers`, with `transport` `sse` or `streamable-http`). There is no special `"type": "webhook"` entry — webhooks are separate from MCP tools.

**Stripe (official MCP, stdio)** — tools like `list_customers`, `list_payment_intents`, `retrieve_balance`, etc. ([Stripe MCP docs](https://docs.stripe.com/mcp))

```json
"mcp": {
  "servers": {
    "stripe": {
      "command": "npx",
      "args": ["-y", "@stripe/mcp@latest"],
      "env": {
        "STRIPE_SECRET_KEY": "${STRIPE_SECRET_KEY}"
      }
    }
  }
}
```

Put `STRIPE_SECRET_KEY` in `~/.openclaw/.env` (restricted keys recommended). OpenClaw substitutes `${…}` when the config is loaded.

**Lob (mail / print)** — there is no first-party `@lob/mcp` npm package like Stripe. This workspace includes the **`lob_api`** skill (`skills/lob-api/`) with small Python scripts that call `https://api.lob.com/v1` using **`LOB_API_KEY`** from the environment.

### Skills (already enabled)

```json
"skills": {
  "load": { "watch": true },
  "entries": {
    "email-matters-cycle":    { "enabled": true },
    "email-matters-sitrep":   { "enabled": true },
    "email-matters-health":   { "enabled": true },
    "parkingbreaker-ops":      { "enabled": true },
    "reddit-budget":          { "enabled": true }
  }
}
```

### Telegram plugin (already enabled)

```json
"plugins": {
  "entries": {
    "telegram": { "enabled": true, "config": {} }
  }
}
```

---

## Routing — Where Jobs Land

| Job type                                          | Runtime            | Why                                            |
| ------------------------------------------------- | ------------------ | ---------------------------------------------- |
| Quick fix, telemetry tweak, small PR              | **Cursor (Omega)** | Fast; full repo context in IDE                 |
| Large feature, dependency sweeps, async work      | **Jules**          | Isolated VM; `AGENTS.md` improves plan quality |
| Scheduled checks, Telegram alerts, Jules steering | **OpenClaw**       | Persistent; human-in-the-loop for approvals    |
| City address validation                           | **OpenClaw cron**  | Daily/weekly automated                         |

---

## Jules — OpenClaw Steering

**Docs:** [Jules API](https://developers.google.com/jules/api) | [GitHub App](https://jules.google/docs)

### How it works

- Jules is a GitHub App + optional REST API.
- API base: `https://jules.googleapis.com/v1alpha/`
- Auth: `X-Goog-Api-Key` header (key in Jules settings).
- Create session: `POST /sessions` with `sourceContext` (GitHub repo), `prompt`, optional `automationMode: "AUTO_CREATE_PR"`, optional `requirePlanApproval: true`.
- Poll: `GET /sessions/{id}` — session `outputs[].pullRequest.url` when a PR exists.

### OpenClaw steers Jules (optional skill)

Thin wrapper script (create session, poll, log PR URL to `memory/YYYY-MM-DD.md`, Telegram summary).

**Secrets:** `JULES_API_KEY` in `~/.openclaw/.env` — never in this repo.

**Stash rule:** Always `git stash` before pulling Jules branches to avoid overwriting uncommitted local changes.

### Jules merge policy

**Never merge to `main` without gates.** Required before any Jules PR merge:

1. CI green on the PR branch.
2. No merge conflicts with `main`.
3. Human or policy approval (use Telegram APPROVE format per `AD-OPS.md`).
4. Production-impacting code: set `requirePlanApproval: true` when creating the Jules session.

Tools: GitHub merge queue + branch protection, or OpenClaw/cron with `gh pr merge` gated on a `ready-to-merge-jules` label.

---

## OpenClaw telemetry funnel (DB → agent → you)

ParkingBreaker exposes a **single export** for the agent — no product dashboard required:

| Step            | What                                                                                                                                                    |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Descriptive** | Event counts, API latency/error rates (`telemetry_performance`), CEO-style funnel snapshot (`telemetry_funnel` / `telemetry_outcomes`).                 |
| **Diagnostic**  | Flags low conversion vs traffic, and “tracking/landing regression” style alerts (7d vs 30d rates).                                                      |
| **Predictive**  | AD-OPS-aligned recommendations per city (`INSUFFICIENT_DATA`, `WATCH`, `PAUSE_SPEND`, `INCREASE_BUDGET`) — **read-only** until you approve in Telegram. |

**Endpoint:** `GET {API_BASE}/telemetry/openclaw/export?period_days=30&city_limit=30&perf_hours=24`  
**Auth:** same as `GET /telemetry/stats/{city_id}` — `Authorization: Bearer {PB_INTERNAL_TOKEN}` when the backend has `PB_INTERNAL_TOKEN` set.

**Raw logs / traces:** not stored in this JSON. Use **Railway logs** for app stdout; **Langfuse / OTel** for gateway/LLM traces when enabled. The export’s `ingestion_hints` field reminds the agent where each layer lives.

**OpenClaw:** poll the export on a schedule (cron/heartbeat), run your narrative + Telegram notification step in the gateway or `parkingbreaker-ops` skill — the three analysis layers are **already structured** in the response under `descriptive`, `diagnostic`, and `predictive`.

**Repo helper:** `scripts/fetch_openclaw_telemetry_export.sh` — thin `curl` wrapper (`API_BASE` + `PB_INTERNAL_TOKEN`) for hooks or cron.

---

## Railway (read-only options)

- **Railway CLI:** `railway status`, `railway logs`, `railway variables` — no token needed if logged in.
- **OpenClaw:** `parkingbreaker-ops` skill reads telemetry from the deployed app; prefer **`/telemetry/openclaw/export`** for the full three-layer bundle; no direct Railway API MCP needed for current setup.
- **Deployment:** Railway dashboard or `railway up`.

---

## Stripe (read-only)

- **Dashboard:** https://dashboard.stripe.com
- **Stripe CLI:** `stripe listen` for local webhook forwarding during development.
- **OpenClaw MCP:** Stripe webhook server configured in `openclaw.json` — handles `payment_intent.succeeded`, `charge.refunded`, `charge.dispute.created` events.
- **No production key in repo** — use Railway env vars or `.env` (gitignored).

---

## Restart Commands

```bash
# OpenClaw gateway (systemd)
systemctl --user restart openclaw-gateway.service

# Cursor — reload window (Cmd+Shift+P → "Reload Window")
```

---

## Secrets Quick Reference

| Secret               | Where                                   |
| -------------------- | --------------------------------------- |
| `JULES_API_KEY`      | Jules settings → API → ~/.openclaw/.env |
| `PB_INTERNAL_TOKEN`  | ~/.openclaw/.env                        |
| `MINIMAX_API_KEY`    | ~/.openclaw/.env                        |
| `TELEGRAM_BOT_TOKEN` | ~/.openclaw/.env                        |
| `STRIPE_*`           | Railway dashboard env vars              |
| `GITHUB_TOKEN`       | Shell env or Cursor MCP settings        |
