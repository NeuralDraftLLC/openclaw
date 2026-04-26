# CRON.md — OpenClaw Pipeline Cron Setup

Canonical install guide for all scheduled pipeline jobs. Job definitions live in `cron/jobs.json` — this file is the human-readable setup walkthrough.

---

## Job Overview

| Job ID | Schedule | What it does |
|---|---|---|
| `parkingbreaker_observer` | Every 4h at :00 | Fetches Railway telemetry, writes `latest.delta.json` + `heartbeat-state.json` |
| `business_pulse` | Every 4h at :00 offset +2h | Stripe < $50 / Lob < $15 finance alerts |
| `budget_executor_dryrun` | Daily 06:00 | AD-OPS dry-run — **never** `--execute` without approval |
| `city_recertification_monthly` | 1st of month 03:00 | Full compute gate sweep across all roster cities |

---

## Prerequisites

### 1. Log directory
```bash
mkdir -p ~/.openclaw/logs
```

### 2. Env file (source in crontab)
Create `~/.openclaw/cron/env.sh`:
```bash
export RAILWAY_API_TOKEN="<your railway token>"
export FIGHTCITYTICKETS_API_URL="https://fightcitytickets-production.up.railway.app"
export STRIPE_SECRET_KEY="<sk_live_...>"
export LOB_API_KEY="<lob_live_...>"
export REDDIT_CLIENT_ID="<reddit_client_id>"
export REDDIT_CLIENT_SECRET="<reddit_client_secret>"
export REDDIT_REFRESH_TOKEN="<reddit_refresh_token>"
export DATABASE_URL="<postgresql://...>"
```
Then `chmod 600 ~/.openclaw/cron/env.sh`.

---

## Crontab Install

Run `crontab -e` and paste:

```crontab
# === OpenClaw Pipeline Jobs ===
# Source env for all jobs
SHELL=/bin/bash
BASH_ENV=~/.openclaw/cron/env.sh

# parkingbreaker_observer — every 4h at :00
0 */4 * * * python3 ~/.openclaw/skills/parkingbreaker-ops/scripts/parkingbreaker_observer.py >> ~/.openclaw/logs/parkingbreaker_observer.log 2>&1

# business_pulse — every 4h offset +2h (02:00, 06:00, 10:00, 14:00, 18:00, 22:00)
0 2,6,10,14,18,22 * * * bash ~/homebase/code/FIGHTCITYTICKETS-1/backend/scripts/business-pulse.sh >> ~/.openclaw/logs/business_pulse.log 2>&1

# budget_executor_dryrun — daily 06:00 (NEVER add --execute without Telegram approval)
0 6 * * * python3 ~/.openclaw/skills/parkingbreaker-ops/scripts/budget_executor.py --dry-run >> ~/.openclaw/logs/budget_executor_dryrun.log 2>&1

# city_recertification_monthly — 1st of month 03:00
0 3 1 * * cd ~/homebase/code/FIGHTCITYTICKETS-1/backend && PYTHONPATH=src python3 src/scheduler.py --job city_recertification_monthly >> ~/.openclaw/logs/city_recertification_monthly.log 2>&1
```

---

## Timing Logic

```
Hour 00:00  → observer runs   (writes fresh delta)
Hour 02:00  → business_pulse  (reads fresh snapshot from observer)
Hour 04:00  → observer runs
Hour 06:00  → business_pulse + budget_executor_dryrun (same hour — pulse first)
Hour 08:00  → observer runs
...
1st of month 03:00 → city recert (quiet window, between observer runs)
```

The 2h offset between `observer` (:00) and `business_pulse` (:00 +2h) ensures pulse always reads a fresh snapshot, never a stale one.

---

## Manual Test Commands

Run any job by hand before trusting the cron:

```bash
# Test observer
python3 ~/.openclaw/skills/parkingbreaker-ops/scripts/parkingbreaker_observer.py
cat ~/homebase/code/FIGHTCITYTICKETS-1/memory/ad-ops/latest.delta.json

# Test business pulse
bash ~/homebase/code/FIGHTCITYTICKETS-1/backend/scripts/business-pulse.sh

# Test budget dry-run
python3 ~/.openclaw/skills/parkingbreaker-ops/scripts/budget_executor.py --dry-run

# Test city recert (dry)
cd ~/homebase/code/FIGHTCITYTICKETS-1/backend
PYTHONPATH=src python3 src/scheduler.py --job city_recertification_monthly --dry-run
```

---

## Log Tailing

```bash
# Live tail all logs
tail -f ~/.openclaw/logs/*.log

# Last 50 lines of a specific job
tail -n 50 ~/.openclaw/logs/parkingbreaker_observer.log
tail -n 50 ~/.openclaw/logs/budget_executor_dryrun.log
```

---

## Safety Rules

1. **`budget_executor.py` — `--dry-run` only.** Never add `--execute` to the crontab entry. Promotion to live execution requires explicit Telegram confirmation from the owner.
2. **`city_recertification_monthly` — read-only stubs until `_write_to_production()` is wired.** The job is safe to run; all three action stubs are no-ops until replaced.
3. **Never run `batch_research_cities.py` on cron.** MiniMax research jobs are expensive and must be triggered manually.
4. **`parkingbreaker_observer` must succeed before heartbeat.** If you see `HEARTBEAT_OK` but the delta file is >4h old, the observer cron is broken — check `parkingbreaker_observer.log`.
5. **P0 escalations bypass cooldown.** Any `notify_priority: P0` in the delta fires immediately regardless of `per_city_action` cooldown.

---

## Verifying the Observer Output

After the observer runs, confirm these files are fresh (mtime < 4h):

```bash
ls -la ~/homebase/code/FIGHTCITYTICKETS-1/memory/ad-ops/latest.delta.json
ls -la ~/homebase/code/FIGHTCITYTICKETS-1/memory/heartbeat-state.json
```

If `latest.delta.json` is missing, the heartbeat will fall back to the newest `telemetry_*.json` per HEARTBEAT.md §1 — this is expected on first run.
