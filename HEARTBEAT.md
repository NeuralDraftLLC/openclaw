# HEARTBEAT.md — ParkingBreaker telemetry router

Chain: `AGENTS.md` → this file → `memory/ad-ops/latest.delta.json` + `memory/heartbeat-state.json` → `AD-OPS.md` policy. Observer / budget scripts implement AD-OPS; they run on a schedule (cron), not inside every model turn.

## Every run (delta-first)

1. Read `~/h/code/FIGHTCITYTICKETS-1/memory/ad-ops/latest.delta.json` (create path if missing — until scripts emit it, fall back to newest `telemetry_*.json` and compare `snapshot_hash` or file mtime to `adOps.lastSnapshotHash` in `memory/heartbeat-state.json`).
2. Compare `snapshot_hash` to `state.adOps.lastSnapshotHash`.
3. If unchanged, no `actions_pending` requiring narration, and no `needs_investigation` → reply exactly `HEARTBEAT_OK`. Done.
4. Else, for each row in `delta.actions_pending`:
   - Respect `adOps.cooldownsSeconds.perCityAction` and `lastAlertedCityAction` (key: `"city_id:recommendation"`).
   - If `notify_priority` is `P0`, bypass per-city cooldown (`escalationP0` is 0).
   - If `blocked_reason` is set, surface it and do **not** propose Reddit spend changes.
   - If `approval_required` and `blocked_reason` is null, use `telegram_message` verbatim when alerting (see `AD-OPS.md`).
5. Update `adOps.lastSnapshotHash`, `adOps.lastDeltaSeenAt`, and `lastAlertedCityAction` after alerts.

## Budget dry-run (not every heartbeat)

Run only when `AD-OPS.md` / delta indicates review, or `lastBudgetDryRunAt` is older than `cooldownsSeconds.budgetDryRun`:

```bash
python3 ~/.openclaw/skills/parkingbreaker-ops/scripts/budget_executor.py
```

Never use `--execute` without explicit human approval.

## Rotated sanity (one secondary check per run)

After incrementing `rotation.runCounter` in `memory/heartbeat-state.json`:

- `runCounter % 3 == 0` → Railway: `curl -s https://fightcitytickets-production.up.railway.app/health` (record in `lastChecks.railway`).
- `runCounter % 6 == 0` → pytest only if FIGHTCITYTICKETS repo is dirty or `git rev-parse HEAD` differs from `rotation.lastPytestSha`:

  ```bash
  python3 -m pytest backend/tests/ -q --tb=short
  ```

  (Run from `~/homebase/code/FIGHTCITYTICKETS-1` or your canonical app path.)

- Otherwise skip Railway/pytest this turn.

## Refresh cadence

`parkingbreaker_observer.py` fetches telemetry and writes snapshots; schedule it outside this file (e.g. cron every 4h). This heartbeat **reads** the delta JSON the pipeline produces — it does not replace the observer.

## Escalations (immediate, not batched)

Defined in `AD-OPS.md` (Escalation). Delta rows with `notify_priority == "P0"` bypass normal cooldown.
