"""
export_gate.py — City export gating via decision router

Every city export request is checked through the router first.
Never allow a city to go live if the router says HOLD.

Replaces the old scoring_policy.py verdict-only check with
a full action-aware gate that can trigger repairs automatically.
"""

from __future__ import annotations

import logging
from typing import Any

from .decision_router import (
    ActionClass,
    CitySignal,
    RouterDecision,
    route,
)
from .commercial_telemetry import CommercialTelemetryCollector
from .ad_ops_executor import AdOpsExecutor

logger = logging.getLogger(__name__)


class ExportGate:
    """
    Single entry point for any city export request.

    Usage:
        gate = ExportGate()
        result = gate.check(city_id, trust_data)
        if result["allowed"]:
            proceed_with_export(city_id)
    """

    def __init__(self) -> None:
        self.telemetry = CommercialTelemetryCollector()
        self.ad_ops = AdOpsExecutor()

    def check(
        self,
        city_id: str,
        trust_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Evaluate city for export readiness.
        Automatically executes non-human actions.
        Returns decision dict.
        """
        # Build signal from trust + commercial data
        commercial = self.telemetry.collect(city_id)
        signal = self._build_signal(city_id, trust_data, commercial)

        # Route
        decision = route(signal)

        # Execute any immediate ad ops actions
        ad_results = []
        ad_actions = [
            a for a in decision.actions
            if a in {
                "pause_reddit_ads",
                "increase_reddit_budget",
                "reduce_reddit_budget_50pct",
                "throttle_acquisition",
                "lock_expansion_spend",
            }
        ]
        if ad_actions:
            ad_results = self.ad_ops.execute(city_id, ad_actions)

        # Trigger repair loop if needed
        if "trigger_research_loop" in decision.actions:
            self._trigger_repair(city_id, trust_data.get("repair_fields", []))

        allowed = decision.action_class in (ActionClass.AUTO_PROCEED, ActionClass.STRATEGY_ACTION)
        # STRATEGY_ACTION cities can still export unless hold_export is in actions
        if "hold_export" in decision.actions:
            allowed = False

        return {
            "allowed": allowed,
            "decision": decision.to_dict(),
            "ad_ops_executed": ad_results,
        }

    @staticmethod
    def _build_signal(
        city_id: str,
        trust_data: dict[str, Any],
        commercial: Any,
    ) -> CitySignal:
        from .decision_router import CitySignal
        return CitySignal(
            city_id=city_id,
            confidence_score=trust_data.get("confidence_score", 0.0),
            scoring_verdict=trust_data.get("verdict", "unknown"),
            repair_fields=trust_data.get("repair_fields", []),
            repair_tier=trust_data.get("repair_tier", "none"),
            override_active=trust_data.get("override_active", False),
            authority_drift_detected=trust_data.get("authority_drift", False),
            clicks_7d=commercial.clicks,
            checkout_starts_7d=commercial.checkout_starts,
            paid_conversions_7d=commercial.paid_conversions,
            refunds_7d=commercial.refunds,
            chargebacks_7d=commercial.chargebacks,
            support_complaints_7d=commercial.support_complaints,
            successful_appeal_outcomes_7d=commercial.successful_appeal_outcomes,
            stripe_webhook_failures_24h=commercial.stripe_webhook_failures_24h,
            checkout_start_delta_pct=commercial.checkout_start_delta_pct,
            last_successful_payment_at=commercial.last_successful_payment_at,
            reddit_campaign_active=commercial.reddit_campaign_active,
            current_daily_budget_usd=commercial.current_daily_budget_usd,
        )

    @staticmethod
    def _trigger_repair(city_id: str, repair_fields: list[str]) -> None:
        """
        Kicks off the MiniMax re-source loop for stale city fields.
        No human needed — AUTO_REPAIR handles itself.
        """
        logger.info(
            "AUTO_REPAIR triggered for %s — fields: %s",
            city_id, repair_fields
        )
        # TODO: import and call research_worker.enqueue(city_id, repair_fields)
        # Placeholder until research_worker.py is wired in
