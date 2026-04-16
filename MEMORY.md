# MEMORY.md — Omega's Long-Term Memory

_Last consolidated: 2026-04-16._

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

| Topic                    | Location                     |
| ------------------------ | ---------------------------- |
| Daily logs               | `memory/YYYY-MM-DD.md`       |
| OpenClaw setup / gateway | `memory/openclaw-gateway.md` |
| Jules sessions           | `memory/jules-sessions.md`   |
| Infrastructure state     | `memory/infrastructure.md`   |
| Product decisions        | `memory/product.md`          |

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

- Stripe: pre-revenue, health endpoint OK; needs funding to enable checkout
- Lob: $7.83 (below $15 alert threshold — ~1 letter remaining at $0.91/letter). Fund at dashboard.lob.com. **Flagged 30+ cycles, human must act.**
- `city-campaign-map.json`: 54 cities, all empty — ad budget blocked until Reddit campaign IDs populated from Ads Manager
- City JSONs: 53 operational, 13 need official address verification
- **SendGrid (2026-04-15):** DNS fully propagated ✓ — CNAMEs for em5998.parkingbreaker.com + domain keys verified. Human must: (1) verify domain in SendGrid dashboard, (2) add SENDGRID_API_KEY + SERVICE_EMAIL=support@parkingbreaker.com to Railway prod env vars. Then emails fire automatically.
- **Reddit Pixel (2026-04-15):** Client-side `rdt('track', 'Purchase')` added to success page — fires alongside server-side CAPI event. NEXT_PUBLIC_REDDIT_PIXEL_ID + REDDIT_PIXEL_ID + REDDIT_CAPI_TOKEN in .env.example.
- **Railway watchdog (2026-04-15):** `railway_watchdog.py` — consolidated health FSM with state machine, committed as utility.

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

| Pattern                                                   | Lesson                              |
| --------------------------------------------------------- | ----------------------------------- |
| Ran pulse 6h straight without doing real work             | Don't confuse checking with working |
| Said "I can't" instead of trying (DuckDuckGo worked fine) | Try first, then say can't           |
| Applied Jules patches to wrong local state twice          | Always stash before pulling         |
| Config change crashed prod backend                        | Validate locally before pushing     |
| Over-explaining                                           | Just do the work                    |

---

## Rules That Should Never Break

1. No Reddit budget mutation without `city-campaign-map.json` entry + typed human approval
2. `checkout_initiated < 5` → never make budget decisions
3. c2p crash (≥0.02 → <0.005, ≥10 checkouts) → immediate alert, not batched
4. Check `__pycache__` before prod deploys (stale bytecode causes IndentationError)
5. Never expose: `PB_INTERNAL_TOKEN`, Stripe keys, Reddit `CLIENT_SECRET`, `REFRESH_TOKEN`, Jules API key

---

_Last updated: 2026-04-16 (self-audit)_

## 2026-04-13 — Key Events

### Desktop Cleanup

- Trashed 14 files from desktop (~300MB): old source dumps, stale research docs, outdated script copies, crash artifacts
- Organized desktop into: `Desktop Launchers/`, `Reference Material/`, `openclaw/` workspace
- Regenerated `cities_all_JSON_current.md` from live city JSONs (53 cities, 114KB)

### Cron Fixes (all re-enabled)

- `Apply Approved Proposals v2` — fixed python path
- `Proposal Validator v2` — fixed python path
- `Review Queue Alert` — fixed python path
- `City: Weekly Deep Verify` — fixed python path

### City Research Worker

- Added `EXCLUDED_CITIES = {us-wa-seattle, us-dc-washington, us-fl-tampa, us-fl-miami, us-mo-kansas_city}` permanent exclusion list
- Working tree held by pre-commit hook (correct — legal deadlines require human review)

### Pre-commit Hook

- `hooks/pre-commit` correctly blocks city JSON commits with uncommitted proposals
- Holding 6 dirty JSONs (Denver, Raleigh x2, Tulsa, Portland, Seattle, Dallas)

### OpenClaw Self-Audit (2026-04-13 22:00 PDT)

- Gateway: healthy, RPC probe OK
- MemPalace: 12,240 drawers, healthy
- GitHub: authenticated as Ghostmondany
- Railway prod: UP
- Heartbeat: last ran 14:03 PDT

## Outstanding Decisions (Human Required)

### City Proposals — 31 pending

Queue: `backend/cities_generated/proposals/review/`
List: `python3 backend/scripts/human_approve_proposal.py --list`
Policy: appeal deadlines affect legal rights — human review required before commit

### High-priority pending reviews

| City     | Field                | Old → New                 | Risk |
| -------- | -------------------- | ------------------------- | ---- |
| Denver   | appeal_deadline_days | 21 → 20                   | HIGH |
| Raleigh  | letter_format        | free_form → form_required | HIGH |
| Tulsa    | appeal_deadline_days | 20 → 30                   | MED  |
| Portland | appeal_deadline_days | 14 → 30                   | MED  |
| Dallas   | letter_format        | null → form_required      | MED  |

### Reddit Ads

- 54 cities in `city-campaign-map.json`, zero campaign IDs filled
- No ad spend possible until IDs are populated from Reddit Ads Manager

### Lob Balance ⚠️

- ~$7.83 — below $15 alert threshold, ~1 letter remaining at $0.91/letter
- **Flagged 30+ cycles, human must top up at dashboard.lob.com**
- No free Lob API balance endpoint — human must check dashboard manually

## Workspace State

- `openclaw/` workspace has untracked `parkingbreaker/` sub-workspace — .gitignore updated to exclude
- `skills/lob-api/` added to .gitignore (skill install artifact)
- `.openclaw/` added to .gitignore (runtime state)
