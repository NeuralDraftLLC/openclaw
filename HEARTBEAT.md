# HEARTBEAT.md — ParkingBreaker / OpenClaw

## Active Telemetry Engine (Every 4 hours)

- **Execute:** Run `python3 ~/.openclaw/skills/parkingbreaker-ops/scripts/parkingbreaker_observer.py` to fetch city data securely and generate the historic memory snapshot.
- **Consume:** Read the newest `JSON` log inside `~/h/code/FIGHTCITYTICKETS-1/memory/ad-ops/`.
- **Analyze:** Check `actions_pending` in the JSON payload.
- **Act:** If any city shows `PAUSE_SPEND` or requires human escalation, alert the user immediately.
- **Budget Pass (dry-run):** Run `python3 ~/.openclaw/skills/parkingbreaker-ops/scripts/budget_executor.py` — review proposals and surface any `alert_required` flags to the user. Never run with `--execute` without explicit user approval.

## Quick Sanity Checks

- Railway production health: `curl -s https://fightcitytickets-production.up.railway.app/health`
- Git status: `git -C ~/homebase/code/FIGHTCITYTICKETS-1 status --short`
- Pytest: `python3 -m pytest backend/tests/ -q --tb=short`
