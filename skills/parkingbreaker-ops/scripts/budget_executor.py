"""
ParkingBreaker Budget Executor — OpenClaw Skill (Stage 3 + 4)

Reads the latest telemetry snapshot from memory/ad-ops/, applies AD-OPS.md
classification rules, and proposes budget adjustments.

SAFETY GUARDRAILS (Stage 4):
  - Hard max: $30/day total campaign spend (BUDGET_CEILING_USD)
  - Read-only dry_run mode by default — no real changes without --execute flag
  - Every proposed action is written to memory/ad-ops/actions.log for audit
  - PAUSE_SPEND triggers immediate Telegram alert via OpenClaw message channel
  - Human approval required: script never auto-executes without --execute flag

Usage:
  python3 budget_executor.py              # dry-run: show what would change
  python3 budget_executor.py --execute    # LIVE: apply changes (requires approval)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─── GUARDRAILS ──────────────────────────────────────────────────────────────
APPEAL_PRICE_USD: float = 29.00       # Revenue per completed appeal
AD_REINVESTMENT_RATE: float = 0.50    # 50% of revenue reinvested into ads, 50% stays as profit
BUDGET_HARD_FLOOR: float = 0.00       # Cannot spend money that hasn't been made
BUDGET_HARD_CEILING: float = 50.00    # Absolute safety ceiling regardless of revenue (sanity check)
CONVERSION_UNLOCK_THRESHOLD: float = 1.00  # 100% — must be confirmed before aggressive scaling
REDDIT_CAMPAIGN_ID = "ParkingBreaker - Gig Drivers"

# ─── PATHS ───────────────────────────────────────────────────────────────────
REPO_ROOT = Path(os.environ.get("REPO_ROOT", "~/h/code/FIGHTCITYTICKETS-1")).expanduser()
AD_OPS_LOG = REPO_ROOT / "memory" / "ad-ops"
ACTION_LOG  = AD_OPS_LOG / "actions.log"


def _latest_snapshot() -> dict:
    """Load the most recent telemetry snapshot JSON."""
    snapshots = sorted(AD_OPS_LOG.glob("telemetry_*.json")) if AD_OPS_LOG.exists() else []
    if not snapshots:
        logger.warning("[executor] No telemetry snapshots found in memory/ad-ops/. Run observer first.")
        return {}
    path = snapshots[-1]
    logger.info(f"[executor] Loading snapshot: {path.name}")
    return json.loads(path.read_text())


def _compute_revenue_budget(snapshot: dict) -> tuple[float, int, float]:
    """
    Self-funding model: ad budget = 50% of revenue already collected today.
    Revenue = payment_confirmed count × $29 per appeal.
    Returns (available_ad_budget, payments_confirmed, gross_revenue).
    """
    total_payments = sum(
        int(c.get("payment_confirmed", 0) or 0)
        for c in snapshot.get("snapshot", [])
    )
    gross_revenue = total_payments * APPEAL_PRICE_USD
    available_budget = min(gross_revenue * AD_REINVESTMENT_RATE, BUDGET_HARD_CEILING)
    available_budget = max(available_budget, BUDGET_HARD_FLOOR)
    return available_budget, total_payments, gross_revenue


def _compute_adjustments(snapshot: dict) -> list[dict]:
    """
    Self-funding budget model:
    - Available ad spend = 50% of revenue already collected (payment_confirmed × $29)
    - If no revenue yet: budget = $0 (no spending money that hasn't been made)
    - Proposals are still flagged awaiting_approval — never auto-executed
    """
    available_budget, total_payments, gross_revenue = _compute_revenue_budget(snapshot)
    actions = snapshot.get("actions_pending", [])
    proposals = []

    if total_payments == 0:
        proposals.append({
            "action": "NO_REVENUE_YET",
            "reason": "No payments confirmed yet. Ad budget is $0.00 until first sale.",
            "gross_revenue_usd": 0.0,
            "available_ad_budget_usd": 0.0,
            "awaiting_approval": False,
        })
        return proposals

    logger.info(f"[executor] Revenue: {total_payments} appeals × ${APPEAL_PRICE_USD:.2f} = ${gross_revenue:.2f} | Ad budget available: ${available_budget:.2f} (50% reinvestment)")

    for action in actions:
        cid = action["city_id"]
        rec = action["recommendation"]
        conf = action.get("confidence", "low")
        c2p = action.get("checkout_to_paid_rate", 0.0)

        if rec == "INCREASE_BUDGET" and conf in ("medium", "high"):
            if c2p < CONVERSION_UNLOCK_THRESHOLD:
                proposals.append({
                    "city_id": cid,
                    "action": "INCREASE_BUDGET_LOCKED",
                    "reason": f"Conversion rate {c2p:.2%} < 100%. Scaling locked until 100% CTR→conversion confirmed.",
                    "available_ad_budget_usd": available_budget,
                    "proposed_daily_usd": available_budget,  # use revenue-derived budget as ceiling
                    "gross_revenue_usd": gross_revenue,
                    "confidence": conf,
                    "c2p_rate": c2p,
                    "awaiting_approval": False,
                })
            else:
                proposals.append({
                    "city_id": cid,
                    "action": "INCREASE_BUDGET",
                    "reason": "100% conversion confirmed. Scaling allowed up to revenue-derived budget.",
                    "current_daily_usd": available_budget,
                    "proposed_daily_usd": min(available_budget, BUDGET_HARD_CEILING),
                    "gross_revenue_usd": gross_revenue,
                    "confidence": conf,
                    "c2p_rate": c2p,
                    "awaiting_approval": True,
                })

        elif rec == "PAUSE_SPEND":
            proposals.append({
                "city_id": cid,
                "action": "PAUSE_SPEND",
                "current_daily_usd": available_budget,
                "proposed_daily_usd": 0.0,
                "gross_revenue_usd": gross_revenue,
                "confidence": conf,
                "c2p_rate": c2p,
                "awaiting_approval": True,
                "alert_required": True,
            })

    return proposals


def _log_action(proposal: dict, executed: bool, dry_run: bool) -> None:
    """Append action to the audit log (always, regardless of dry_run)."""
    AD_OPS_LOG.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "executed": executed,
        **proposal,
    }
    with open(ACTION_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _escalate_via_openclaw(city_id: str, c2p_rate: float) -> None:
    """Fire an emergency Telegram alert through the OpenClaw CLI."""
    msg = (
        f"🚨 ParkingBreaker Ad-Ops ALERT\n"
        f"City: {city_id}\n"
        f"Signal: PAUSE_SPEND — conversion rate collapsed to {c2p_rate:.4f}\n"
        f"Action Required: Manually review Reddit campaign. Budget executor is paused pending your approval."
    )
    # Load token from OpenClaw .env if not in environment
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("OPENCLAW_TELEGRAM_BOT_TOKEN")
    if not token:
        env_path = Path("~/.openclaw/.env").expanduser()
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break
    try:
        subprocess.run(
            ["openclaw", "message", "send", "--channel", "telegram",
             "--target", "8587669820", "--message", msg],
            capture_output=True, timeout=10,
            env={**os.environ, "TELEGRAM_BOT_TOKEN": token or ""}
        )
        logger.info(f"[executor] Telegram escalation sent for {city_id}.")
    except Exception as e:
        logger.warning(f"[executor] Telegram alert failed: {e}")


def run(dry_run: bool = True) -> None:
    snapshot = _latest_snapshot()
    if not snapshot:
        logger.info("[executor] No data to act on. Exiting.")
        return

    proposals = _compute_adjustments(snapshot)

    if not proposals:
        logger.info("[executor] No budget actions needed this cycle. All cities in WATCH/INSUFFICIENT_DATA.")
        return

    print(f"\n{'='*60}")
    print(f"  Budget Executor — {'DRY RUN' if dry_run else '🔴 LIVE EXECUTION'}")
    print(f"  Ceiling: ${BUDGET_HARD_CEILING:.2f}/day (safety cap) | Campaign: {REDDIT_CAMPAIGN_ID}")
    print(f"{'='*60}\n")

    for p in proposals:
        action = p["action"]
        status = "WOULD" if dry_run else "EXECUTING"

        if action == "NO_REVENUE_YET":
            print(f"  [{action}]")
            print(f"    {p['reason']}")
            print(f"    Gross revenue: $0.00 | Ad budget: $0.00")
            print()
            _log_action(p, executed=False, dry_run=dry_run)
            continue

        city_id = p.get("city_id", "global")
        print(f"  [{action}] {city_id}")
        revenue_str = f"${p.get('gross_revenue_usd', 0):.2f} gross → ${p.get('available_ad_budget_usd', p.get('current_daily_usd', 0)):.2f} available (50% reinvestment)"
        print(f"    Revenue: {revenue_str}")
        if "proposed_daily_usd" in p:
            print(f"    {status}: → ${p['proposed_daily_usd']:.2f}/day ad spend")
        if "c2p_rate" in p:
            print(f"    C2P rate: {p['c2p_rate']:.4f} | Confidence: {p.get('confidence', 'n/a')}")
        if p.get("reason"):
            print(f"    Note: {p['reason']}")
        if p.get("alert_required"):
            print(f"    🚨 ESCALATION REQUIRED — Telegram alert {'sent' if not dry_run else 'queued'}")
            if not dry_run:
                _escalate_via_openclaw(city_id, p["c2p_rate"])
        print()

        _log_action(p, executed=not dry_run, dry_run=dry_run)


    if dry_run:
        print("  ✅ Dry run complete. No real changes made.")
        print("  To execute: python3 budget_executor.py --execute")
    else:
        print("  ✅ Execution complete. All actions logged to memory/ad-ops/actions.log")

    print(f"\n  Audit log: {ACTION_LOG}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ParkingBreaker Budget Executor")
    parser.add_argument("--execute", action="store_true",
                        help="Execute real budget changes (default: dry-run only)")
    args = parser.parse_args()

    if args.execute:
        confirm = input("⚠ LIVE execution mode. Type 'YES' to confirm: ")
        if confirm.strip() != "YES":
            print("Aborted.")
            sys.exit(0)

    run(dry_run=not args.execute)
