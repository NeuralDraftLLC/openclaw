# OpenClaw + ParkingBreaker Cron Roster

> Last updated: 2026-04-26  
> Managed via `~/.openclaw/cron/jobs.json` (gateway) + GitHub Actions schedules

---

## Schedule Map — All 14 Jobs, Zero Collisions

| Time (America/Los_Angeles) | Job | Mode | Delivery |
|---|---|---|---|
| `05 */2 * * *` | City Research Worker | isolated | none |
| `*/2h ~:38` | Business Pulse | main | none (alert-only) |
| `45 */2 * * *` | Railway Watchdog | isolated | none |
| `0 3 * * *` | OpenClaw CI Nightly | isolated | none |
| `0 4 * * *` | OpenClaw Self-Maintenance | isolated | none |
| `0 */4 * * *` | PB Telemetry Heartbeat | isolated | none (alert → Telegram) |
| `30 7 * * *` | Morning Clarity Brief | main | announce → Telegram |
| `0 8 * * 0` | Weekly Revenue & Momentum | main | announce → Telegram |
| `0 9 * * *` | City Governance Health Check | isolated | announce |
| `0 9 * * *` | Daily Finance Check | main | announce |
| `0 10 * * 1` | CodeQL Security Scan (via gh CLI) | isolated | none |
| `0 3 * * 1` | Programmatic SEO Generator | isolated | none |
| `0 8 1 * *` | City Monthly Full Recert | main | announce |
| `0 */4 * * *` | PB Telemetry Heartbeat | isolated | none |

---

## GitHub Actions Schedules

| Workflow | Cron (UTC) | PDT equivalent | Purpose |
|---|---|---|---|
| `ci.yml` | `0 10 * * *` | 3:00 AM daily | Nightly full matrix (Node, macOS, Android, Windows) |
| `ci.yml` | `0 8 * * 1` | 1:00 AM Monday | Weekly compat/push-only lanes (node22 etc.) |
| `codeql.yml` | `0 17 * * 1` | 10:00 AM Monday | Full security scan (JS/TS, Python, Java, Swift, Actions) |
| `stale.yml` | `17 3 * * *` | 8:17 PM daily | Mark + close stale issues/PRs |

---

## OpenClaw Gateway Jobs

### City Research Worker
- **ID:** city-research-worker  
- **Cron:** `5 */2 * * *` (America/Los_Angeles) — shifted from `:15` to `:05` to spread load  
- **Agent:** parkingbreaker / isolated  
- **Prompt:** Run `run_research_worker.sh`, reply last output line or DONE  

### Railway Watchdog
- **ID:** railway-watchdog  
- **Cron:** `45 */2 * * *` (America/Los_Angeles)  
- **Agent:** parkingbreaker / isolated  
- **Prompt:** Run `run_railway_watchdog.sh` (WATCHDOG_MAX_SECONDS=165), silent unless ERROR  

### Business Pulse
- **ID:** business-pulse  
- **Schedule:** every 2h  
- **Agent:** main  
- **Prompt:** Run `business-pulse.sh`, 3-sentence summary. Alert if public health not OK, Stripe < $50, Lob < $15. Human check-in at most once/day 8AM–11PM PDT.  

### City Governance Health Check
- **ID:** city-governance-health-check  
- **Cron:** `0 9 * * *` (America/Los_Angeles)  
- **Agent:** parkingbreaker / isolated  
- **Prompt:** Run `validate_cities.py --summary`, reply DONE or INTERVENTION_NEEDED  
- **Delivery:** announce  

### Daily Finance Check
- **ID:** daily-finance-check  
- **Cron:** `0 16 * * *` UTC = 9:00 AM PDT  
- **Agent:** main  
- **Alert thresholds:** Stripe < $50, Lob < $15 (canonical — do not deviate)  
- **Also:** morning check-in to Amir after the finance check  

### Programmatic SEO Generator
- **ID:** seo-generator  
- **Cron:** `0 3 * * 1` (America/Los_Angeles) — Monday 3:00 AM  
- **Agent:** parkingbreaker / isolated  
- **Steps:** stats dry-run → real run → CSV validation → git commit → reply SEO_DONE  

### OpenClaw Self-Maintenance
- **ID:** openclaw-self-maintenance  
- **Cron:** `0 4 * * *` (America/Los_Angeles)  
- **Agent:** parkingbreaker / isolated  
- **Steps:** cron roster review, disable jobs with consecutiveErrors ≥ 3, kill stuck subagents, append daily memory log  

### City Monthly Full Recert
- **ID:** city-monthly-full-recert  
- **Cron:** `0 8 1 * *` (America/Los_Angeles) — 1st of month  
- **Agent:** main  
- **Steps:** JSON validation → score improvement check → commit if improved → announce diff summary  

### PB Telemetry Heartbeat
- **ID:** pb-telemetry-heartbeat  
- **Cron:** `0 */4 * * *` (America/Los_Angeles)  
- **Agent:** parkingbreaker / isolated  
- **Status:** ⚠️ was disabled (syntax error — fixed below)  
- **Fixed prompt:**
```
Run in shell:
curl -s -H "Authorization: Bearer $PB_INTERNAL_TOKEN" \
  "https://fightcitytickets-production.up.railway.app/telemetry/openclaw/export" | python3 -c "
import json, sys
d = json.load(sys.stdin)
recs = d.get('predictive', {}).get('recommendations_by_city', [])
flags = d.get('diagnostic', {}).get('flags', [])
alerts = [r for r in recs if r.get('recommendation') in ('PAUSE_SPEND', 'INCREASE_BUDGET')]
alerts += [{'flag': f} for f in flags if 'regression' in f.lower() or 'immediate' in f.lower()]
print('ALERT:', json.dumps(alerts)) if alerts else print('CLEAR')
"
If output starts with ALERT — send Telegram to 8587669820 with the alert payload.
If CLEAR — reply TELEMETRY_OK silently.
```
- **Action required locally:** set `enabled: true`, reset `consecutiveErrors: 0`

### Emergent Hygiene
- **ID:** emergent-hygiene  
- **Schedule:** every 6h  
- **Agent:** main  
- **Delivery:** `{ "mode": "none" }` ← fix: was missing mode  
- **Prompt:** narrow hygiene pass — git status, pycache cleanup, daily memory log. No Stripe/Lob/Railway/telemetry. Reply EMERGENT_OK if nothing to do.  

---

## New Jobs Added (2026-04-26)

### Morning Clarity Brief *(quality of life)*
- **ID:** morning-clarity-brief  
- **Cron:** `30 7 * * *` (America/Los_Angeles) — 7:30 AM daily  
- **Agent:** main  
- **Delivery:** announce → Telegram → 8587669820  
- **Prompt:** Check overnight memory log, last 18h git commits, cron error state. Surface ONE highest-leverage task for the day. 4–6 lines max, no markdown, plain language.  

### Weekly Revenue & Momentum Report *(quality of life)*
- **ID:** weekly-revenue-momentum  
- **Cron:** `0 8 * * 0` (America/Los_Angeles) — Sunday 8:00 AM  
- **Agent:** main  
- **Delivery:** announce → Telegram → 8587669820  
- **Prompt:** Run business-pulse.sh, check commit velocity (7 days), SEO freshness. Produce Sunday weekly review: Stripe balance + trend, Lob status, commit count, momentum assessment (forward/stalled/declining), one concrete action for next week. Under 8 lines.  

### OpenClaw CI Nightly
- **ID:** openclaw-ci-nightly  
- **Cron:** `0 3 * * *` (America/Los_Angeles)  
- **Agent:** parkingbreaker / isolated  
- **Delivery:** none  
- **Prompt:** `gh workflow run ci.yml --repo NeuralDraftLLC/openclaw --ref main` — reply CI_TRIGGERED silently or CI_FAIL with output  

### CodeQL Weekly Security Scan
- **ID:** codeql-weekly  
- **Cron:** `0 10 * * 1` (America/Los_Angeles) — Monday 10:00 AM  
- **Agent:** parkingbreaker / isolated  
- **Delivery:** none  
- **Prompt:** `gh workflow run codeql.yml --repo NeuralDraftLLC/openclaw --ref main` — reply CODEQL_TRIGGERED silently or CODEQL_FAIL with output  

---

## Local Action Required

The GitHub Actions schedules above are committed directly to the repo.
The following must be applied to `~/.openclaw/cron/jobs.json` manually or via `cron` tool:

1. **Fix `pb-telemetry-heartbeat`** — replace prompt with fixed version above, set `enabled: true`, reset `consecutiveErrors: 0`
2. **Fix `emergent-hygiene`** — set `delivery.mode: "none"` explicitly
3. **Shift `city-research-worker`** — change cron from `15 */2 * * *` to `5 */2 * * *`
4. **Add `morning-clarity-brief`** — new job object (see spec above)
5. **Add `weekly-revenue-momentum`** — new job object (see spec above)
6. **Add `openclaw-ci-nightly`** — new job object (see spec above)
7. **Add `codeql-weekly`** — new job object (see spec above)
