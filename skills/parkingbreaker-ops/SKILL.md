---
name: parkingbreaker_ops
description: Fetch per-city funnel, payment, and ad_click telemetry from ParkingBreaker FastAPI. Classify cities for Reddit budget recommendations (INCREASE_BUDGET, PAUSE_SPEND, WATCH). Human approval required before any budget execution.
version: "1.0.0"
author: "Amir Khodabakhsh"
triggers:
  - "check city performance"
  - "ParkingBreaker telemetry"
  - "Reddit budget heartbeat"
  - "get city telemetry stats"
  - "parkingbreaker observer"
user-invocable: true
metadata: {"openclaw":{"emoji":"🅿️","requires":{"bins":["python3"],"env":["PARKINGBREAKER_API_BASE","PB_INTERNAL_TOKEN"]}}}
---

# ParkingBreaker telemetry observer

## What it does

- Calls `GET {PARKINGBREAKER_API_BASE}/telemetry/stats/{city_id}` (30-day window) with optional `Authorization: Bearer {PB_INTERNAL_TOKEN}` when the backend has `PB_INTERNAL_TOKEN` set.
- Prints a table per city and flags `INCREASE_BUDGET` / `PAUSE_SPEND` for human approval (see repo `AD-OPS.md`).

## Rules

- Never print or log `PB_INTERNAL_TOKEN`.
- Never change Reddit budgets from this script — observer is read + classify only.

## Setup (operator)

1. Generate token: `python3 -c "import secrets; print(secrets.token_hex(32))"`
2. Set `PB_INTERNAL_TOKEN` on Railway API (or leave unset locally for open `/telemetry/stats`).
3. Vault:
   ```bash
   openclaw vault set PARKINGBREAKER_API_BASE https://fightcitytickets-production.up.railway.app
   openclaw vault set PB_INTERNAL_TOKEN <token>
   ```
4. Verify:
   ```bash
   curl -sS -H "Authorization: Bearer $PB_INTERNAL_TOKEN" \
     "$PARKINGBREAKER_API_BASE/telemetry/stats/us-ca-san_francisco" | python3 -m json.tool
   ```

## Run (absolute path)

One city:

```bash
python3 /home/amir/.openclaw/skills/parkingbreaker-ops/scripts/parkingbreaker_observer.py us-ca-san_francisco
```

All 63 cities:

```bash
python3 /home/amir/.openclaw/skills/parkingbreaker-ops/scripts/parkingbreaker_observer.py
```

## Canonical city IDs

63 IDs — no `us-co-denver`. Full list is in `scripts/parkingbreaker_observer.py` (`ALL_CITY_IDS`).

## Reference files in this skill

- `scripts/parkingbreaker_observer.py` — executable
- `parkingbreaker_telemetry_observer.json` — tool manifest / vault hints for alternate loaders

## Full product handoff

Repo: `FIGHTCITYTICKETS-1` — see `backend/src/routes/e5xr3.md` and root `AD-OPS.md`.
