"""
decision_router.py — ParkingBreaker Autonomous Revenue + Trust Operating System

The brain. Not the validators. Not the research worker. The router.

Every city signal flows through here and exits as one of four action classes:
  A. AUTO_PROCEED   — safe to export / serve / spend
  B. AUTO_REPAIR    — system re-researches automatically, no human needed
  C. HUMAN_REVIEW   — true trust boundary, rare and expensive
  D. STRATEGY_ACTION — system changes revenue behavior (ad spend, pricing)

Architecture:
  telemetry → decision → action → verification → escalation
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Action Class Enum
# ---------------------------------------------------------------------------

class ActionClass(str, Enum):
    AUTO_PROCEED = "AUTO_PROCEED"
    AUTO_REPAIR = "AUTO_REPAIR"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    STRATEGY_ACTION = "STRATEGY_ACTION"


# ---------------------------------------------------------------------------
# Thresholds (tunable without code changes via env or config)
# ---------------------------------------------------------------------------

CONFIDENCE_FLOOR = 0.75           # below this → pause ads, consider repair
CONFIDENCE_REPAIR_FLOOR = 0.50    # below this → AUTO_REPAIR
CONVERSION_SCALE_THRESHOLD = 0.04  # 4% CVR → candidate for increased spend
REFUND_SPIKE_THRESHOLD = 0.08      # 8% refund rate → throttle acquisition
CHARGEBACK_THRESHOLD = 0.03        # 3% chargeback → HUMAN_REVIEW
SUPPORT_SPIKE_THRESHOLD = 5        # 5+ support complaints/week → investigate
CHECKOUT_DROP_THRESHOLD = 0.30     # 30% drop in checkout starts → watchdog
STRIPE_FAILURE_THRESHOLD = 3       # 3+ webhook failures → pause ads immediately


# ---------------------------------------------------------------------------
# Input signal shape from confidence engine + commercial telemetry
# ---------------------------------------------------------------------------

@dataclass
class CitySignal:
    city_id: str

    # Trust telemetry
    confidence_score: float = 0.0
    scoring_verdict: str = "unknown"      # ready_to_service | REPAIR | FAIL
    repair_fields: list[str] = field(default_factory=list)
    repair_tier: str = "none"             # search | deep | manual
    override_active: bool = False
    authority_drift_detected: bool = False

    # Commercial telemetry
    clicks_7d: int = 0
    checkout_starts_7d: int = 0
    paid_conversions_7d: int = 0
    refunds_7d: int = 0
    chargebacks_7d: int = 0
    support_complaints_7d: int = 0
    successful_appeal_outcomes_7d: int = 0

    # Revenue infrastructure
    stripe_webhook_failures_24h: int = 0
    checkout_start_delta_pct: float = 0.0   # negative = drop
    last_successful_payment_at: str | None = None

    # Ad ops state
    reddit_campaign_active: bool = False
    current_daily_budget_usd: float = 0.0

    # Metadata
    sampled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Output shape
# ---------------------------------------------------------------------------

@dataclass
class RouterDecision:
    city_id: str
    action_class: ActionClass
    actions: list[str]
    priority: str                           # critical | high | medium | low
    reason: str
    diagnostics: dict[str, Any] = field(default_factory=dict)
    decided_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "city_id": self.city_id,
            "state": self.action_class.value,
            "actions": self.actions,
            "priority": self.priority,
            "reason": self.reason,
            "diagnostics": self.diagnostics,
            "decided_at": self.decided_at,
        }


# ---------------------------------------------------------------------------
# Revenue metrics helpers
# ---------------------------------------------------------------------------

def _conversion_rate(signal: CitySignal) -> float:
    if signal.checkout_starts_7d == 0:
        return 0.0
    return signal.paid_conversions_7d / signal.checkout_starts_7d


def _refund_rate(signal: CitySignal) -> float:
    if signal.paid_conversions_7d == 0:
        return 0.0
    return signal.refunds_7d / signal.paid_conversions_7d


def _chargeback_rate(signal: CitySignal) -> float:
    if signal.paid_conversions_7d == 0:
        return 0.0
    return signal.chargebacks_7d / signal.paid_conversions_7d


# ---------------------------------------------------------------------------
# Escalation helpers
# ---------------------------------------------------------------------------

def _is_revenue_boundary_broken(signal: CitySignal) -> bool:
    """Checkout watchdog: never allow paid traffic into a broken checkout."""
    if signal.stripe_webhook_failures_24h >= STRIPE_FAILURE_THRESHOLD:
        return True
    if signal.checkout_start_delta_pct <= -CHECKOUT_DROP_THRESHOLD:
        return True
    return False


def _is_payment_anomaly(signal: CitySignal) -> bool:
    return _chargeback_rate(signal) >= CHARGEBACK_THRESHOLD


# ---------------------------------------------------------------------------
# Core routing logic
# ---------------------------------------------------------------------------

def route(signal: CitySignal) -> RouterDecision:
    """
    The single entry point. Consumes a CitySignal, returns a RouterDecision.

    Decision priority waterfall (highest to lowest):
      1. Revenue boundary watchdog (Stripe / checkout collapse)  → HUMAN_REVIEW / pause ads
      2. Payment anomaly (chargebacks)                           → HUMAN_REVIEW
      3. Hard trust failure with no override                     → HUMAN_REVIEW
      4. Authority drift or override hotspot active              → HUMAN_REVIEW
      5. Confidence below repair floor                           → AUTO_REPAIR
      6. Confidence below ad floor                               → STRATEGY_ACTION (pause ads)
      7. Refund spike                                            → STRATEGY_ACTION (throttle)
      8. High CVR + high trust + stable                          → STRATEGY_ACTION (scale)
      9. High confidence + low CVR (trust ok, marketing broken)  → STRATEGY_ACTION (creative)
      10. All clear                                              → AUTO_PROCEED
    """

    cvr = _conversion_rate(signal)
    refund_rate = _refund_rate(signal)
    chargeback_rate = _chargeback_rate(signal)

    diagnostics = {
        "confidence": signal.confidence_score,
        "verdict": signal.scoring_verdict,
        "cvr_7d": round(cvr, 4),
        "refund_rate_7d": round(refund_rate, 4),
        "chargeback_rate_7d": round(chargeback_rate, 4),
        "stripe_failures_24h": signal.stripe_webhook_failures_24h,
        "checkout_start_delta_pct": signal.checkout_start_delta_pct,
        "support_complaints_7d": signal.support_complaints_7d,
        "override_active": signal.override_active,
        "authority_drift": signal.authority_drift_detected,
    }

    # ── 1. Revenue boundary watchdog ────────────────────────────────────────
    if _is_revenue_boundary_broken(signal):
        reason = (
            f"Stripe webhook failures ({signal.stripe_webhook_failures_24h}) or "
            f"checkout drop ({signal.checkout_start_delta_pct:.0%}) exceeds threshold."
        )
        return RouterDecision(
            city_id=signal.city_id,
            action_class=ActionClass.HUMAN_REVIEW,
            actions=[
                "pause_reddit_ads",
                "hold_export",
                "lock_expansion_spend",
                "alert_operator_p0",
            ],
            priority="critical",
            reason=reason,
            diagnostics=diagnostics,
        )

    # ── 2. Payment anomaly ───────────────────────────────────────────────────
    if _is_payment_anomaly(signal):
        return RouterDecision(
            city_id=signal.city_id,
            action_class=ActionClass.HUMAN_REVIEW,
            actions=[
                "pause_reddit_ads",
                "hold_export",
                "alert_operator_p0",
                "queue_chargeback_review",
            ],
            priority="critical",
            reason=f"Chargeback rate {chargeback_rate:.1%} exceeds {CHARGEBACK_THRESHOLD:.1%} threshold.",
            diagnostics=diagnostics,
        )

    # ── 3. Hard trust failure ────────────────────────────────────────────────
    if signal.scoring_verdict == "FAIL" and not signal.override_active:
        return RouterDecision(
            city_id=signal.city_id,
            action_class=ActionClass.HUMAN_REVIEW,
            actions=[
                "hold_export",
                "pause_reddit_ads",
                "queue_trust_failure_review",
            ],
            priority="high",
            reason="City scored FAIL with no active override. Trust boundary requires human approval.",
            diagnostics=diagnostics,
        )

    # ── 4. Authority drift or override hotspot ───────────────────────────────
    if signal.authority_drift_detected or signal.override_active:
        actions = ["queue_manual_approval", "hold_expansion"]
        if signal.reddit_campaign_active:
            actions.append("pause_reddit_ads")
        return RouterDecision(
            city_id=signal.city_id,
            action_class=ActionClass.HUMAN_REVIEW,
            actions=actions,
            priority="high",
            reason="Authority drift detected or override hotspot active. Requires human review.",
            diagnostics=diagnostics,
        )

    # ── 5. Confidence below repair floor → AUTO_REPAIR ───────────────────────
    if signal.confidence_score < CONFIDENCE_REPAIR_FLOOR:
        actions = ["trigger_research_loop", "hold_export"]
        if signal.reddit_campaign_active:
            actions.append("pause_reddit_ads")
        return RouterDecision(
            city_id=signal.city_id,
            action_class=ActionClass.AUTO_REPAIR,
            actions=actions,
            priority="high",
            reason=f"Confidence {signal.confidence_score:.2f} below repair floor {CONFIDENCE_REPAIR_FLOOR}.",
            diagnostics=diagnostics,
        )

    # ── 6. Confidence below ad floor → pause acquisition ────────────────────
    if signal.confidence_score < CONFIDENCE_FLOOR:
        actions = ["hold_export"]
        if signal.reddit_campaign_active:
            actions.append("pause_reddit_ads")
        if signal.repair_fields:
            actions.append("trigger_research_loop")
        return RouterDecision(
            city_id=signal.city_id,
            action_class=ActionClass.STRATEGY_ACTION,
            actions=actions,
            priority="medium",
            reason=f"Confidence {signal.confidence_score:.2f} below ad floor {CONFIDENCE_FLOOR}. Pausing acquisition.",
            diagnostics=diagnostics,
        )

    # ── 7. Refund spike → throttle acquisition ───────────────────────────────
    if refund_rate >= REFUND_SPIKE_THRESHOLD:
        return RouterDecision(
            city_id=signal.city_id,
            action_class=ActionClass.STRATEGY_ACTION,
            actions=[
                "throttle_acquisition",
                "reduce_reddit_budget_50pct",
                "alert_operator_p1",
            ],
            priority="high",
            reason=f"Refund rate {refund_rate:.1%} exceeds {REFUND_SPIKE_THRESHOLD:.1%}. Authority problem, not marketing.",
            diagnostics=diagnostics,
        )

    # ── 8. High trust + high CVR → scale spend ───────────────────────────────
    if (
        signal.confidence_score >= CONFIDENCE_FLOOR
        and cvr >= CONVERSION_SCALE_THRESHOLD
        and refund_rate < REFUND_SPIKE_THRESHOLD
        and not signal.authority_drift_detected
    ):
        return RouterDecision(
            city_id=signal.city_id,
            action_class=ActionClass.STRATEGY_ACTION,
            actions=[
                "increase_reddit_budget",
                "ship_city_live",
            ],
            priority="low",
            reason=(
                f"High trust ({signal.confidence_score:.2f}) + strong CVR ({cvr:.1%}). "
                "Scale acquisition spend."
            ),
            diagnostics=diagnostics,
        )

    # ── 9. High trust + low CVR → marketing problem ──────────────────────────
    if (
        signal.confidence_score >= CONFIDENCE_FLOOR
        and signal.clicks_7d > 50
        and cvr < 0.01
    ):
        return RouterDecision(
            city_id=signal.city_id,
            action_class=ActionClass.STRATEGY_ACTION,
            actions=[
                "flag_creative_review",
                "hold_budget_increase",
            ],
            priority="medium",
            reason=(
                f"High trust ({signal.confidence_score:.2f}) but very low CVR ({cvr:.1%}) with "
                f"{signal.clicks_7d} clicks. Marketing problem, not trust."
            ),
            diagnostics=diagnostics,
        )

    # ── 10. All clear → AUTO_PROCEED ─────────────────────────────────────────
    return RouterDecision(
        city_id=signal.city_id,
        action_class=ActionClass.AUTO_PROCEED,
        actions=["ship_city_live"],
        priority="low",
        reason=f"All signals nominal. Confidence {signal.confidence_score:.2f}, CVR {cvr:.1%}.",
        diagnostics=diagnostics,
    )


# ---------------------------------------------------------------------------
# Batch routing
# ---------------------------------------------------------------------------

def route_all(signals: list[CitySignal]) -> list[RouterDecision]:
    """Route a batch of city signals. Returns sorted by priority."""
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    decisions = [route(s) for s in signals]
    return sorted(decisions, key=lambda d: priority_order.get(d.priority, 99))


# ---------------------------------------------------------------------------
# Weekly executive summary generator
# ---------------------------------------------------------------------------

def generate_weekly_summary(decisions: list[RouterDecision]) -> dict:
    """
    Not dashboards. Decisions.
    Produces operator-facing summary: what changed, what acted, what needs judgment.
    """
    summary: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_cities_evaluated": len(decisions),
        "by_class": {},
        "critical_actions": [],
        "auto_repaired": [],
        "human_required": [],
        "scaled_cities": [],
        "paused_cities": [],
    }

    class_counts: dict[str, int] = {}
    for d in decisions:
        cls = d.action_class.value
        class_counts[cls] = class_counts.get(cls, 0) + 1

        if d.priority == "critical":
            summary["critical_actions"].append({
                "city": d.city_id, "reason": d.reason, "actions": d.actions
            })
        if d.action_class == ActionClass.AUTO_REPAIR:
            summary["auto_repaired"].append(d.city_id)
        if d.action_class == ActionClass.HUMAN_REVIEW:
            summary["human_required"].append({"city": d.city_id, "reason": d.reason})
        if "increase_reddit_budget" in d.actions or "ship_city_live" in d.actions:
            summary["scaled_cities"].append(d.city_id)
        if "pause_reddit_ads" in d.actions or "throttle_acquisition" in d.actions:
            summary["paused_cities"].append(d.city_id)

    summary["by_class"] = class_counts
    return summary
