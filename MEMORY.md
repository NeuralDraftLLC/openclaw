# MEMORY.md — Omega's Long-Term Memory

_Last consolidated: 2026-04-09._

## Default Memory: MemPalace

**MemPalace is the canonical long-term memory.** It lives at `~/.mempalace/palace` and is accessed via MCP tools prefixed `mempalace__`.

When Amir asks about history, past decisions, or "what we said" across time or channels:
- Call `mempalace__mempalace_status` to check palace health
- Call `mempalace__mempalace_search` to query durable memories
- The `mempalace-sync` hook automatically mines `memory/` into MemPalace before compaction

**MEMORY.md and `memory/` are the working log** — raw session data. MemPalace is the authoritative long-term store.

## About This File

MEMORY.md is an **index** pointing to durable facts, patterns, and lessons learned — not a primary store.
Raw session logs live in `memory/YYYY-MM-DD.md`. Review and distill from those into this file and the palace.

## Index

| Topic | Location |
|---|---|
| Daily logs | `memory/YYYY-MM-DD.md` |
| OpenClaw setup / gateway | `memory/openclaw-gateway.md` |
| Jules sessions | `memory/jules-sessions.md` |
| Infrastructure state | `memory/infrastructure.md` |
| Product decisions | `memory/product.md` |

---

## Durable Facts (Always Remember)

### Omega Identity
- Name: Omega Ω
- One agent, all responsibilities
- Owner: Amir (he/him, America/Los_Angeles)

### Repo & Production
- Repo: `/home/amir/Desktop/openclaw`
- Railway: auto-deploys on push to `main`
- Redis: `redis://redis:6379/0` — Railway uses its own URL; override in prod

### Business State
- Stripe: ~-$0.06 (blocks checkout — needs funding)
- Lob: ~$7.83 (below $15 alert threshold)
- `city-campaign-map.json`: all empty — ad budget blocked until campaign IDs filled
- City JSONs: 53 operational, 13 need official address verification

### Infrastructure
- Production: `fightcitytickets-production.up.railway.app`
- Frontend: `frontend-production-023c.up.railway.app`
- GoDaddy DNS for `parkingbreaker.com` (ns27.domaincontrol.com)
- Railway Edge still routes parkingbreaker.com even when app is "deactivated"

### Jules
- Dashboard: jules.google.com
- API key: `/home/amir/homebase/code/inkspider/.env`
- ~25+ pending sessions (most stuck Awaiting User Feedback)
- Rule: stash local changes before pulling; don't overwrite uncommitted work

### openclaw Workspace
- Has uncommitted MiniMax stream wrapper changes — do NOT upgrade without stashing first

---

## Patterns to Remember

| Pattern | Lesson |
|---|---|
| Ran pulse 6h straight without doing real work | Don't confuse checking with working |
| Said "I can't" instead of trying (DuckDuckGo worked fine) | Try first, then say can't |
| Applied Jules patches to wrong local state twice | Always stash before pulling |
| Config change crashed prod backend | Validate locally before pushing |
| Over-explaining | Just do the work |

---

## Rules That Should Never Break

1. No Reddit budget mutation without `city-campaign-map.json` entry + typed human approval
2. `checkout_initiated < 5` → never make budget decisions
3. c2p crash (≥0.02 → <0.005, ≥10 checkouts) → immediate alert, not batched
4. Check `__pycache__` before prod deploys (stale bytecode causes IndentationError)
5. Never expose: `PB_INTERNAL_TOKEN`, Stripe keys, Reddit `CLIENT_SECRET`, `REFRESH_TOKEN`, Jules API key
