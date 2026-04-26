"""
test_decision_router.py — Unit tests for the decision router

Tests every branch of the waterfall priority logic.
No mocking of external APIs — pure unit tests on CitySignal → RouterDecision.
"""

import pytest
from ..decision_router import (
    ActionClass,
    CitySignal,
    RouterDecision,
    route,
    route_all,
    generate_weekly_summary,
    CONFIDENCE_FLOOR,
    CONFIDENCE_REPAIR_FLOOR,
    REFUND_SPIKE_THRESHOLD,
    CHARGEBACK_THRESHOLD,
    STRIPE_FAILURE_THRESHOLD,
    CHECKOUT_DROP_THRESHOLD,
)


def make_healthy_signal(city_id="los-angeles") -> CitySignal:
    """A city that should AUTO_PROCEED."""
    return CitySignal(
        city_id=city_id,
        confidence_score=0.91,
        scoring_verdict="ready_to_service",
        clicks_7d=200,
        checkout_starts_7d=40,
        paid_conversions_7d=8,
        refunds_7d=0,
        chargebacks_7d=0,
        stripe_webhook_failures_24h=0,
        checkout_start_delta_pct=0.02,
        reddit_campaign_active=True,
        current_daily_budget_usd=20.0,
    )


class TestAutoProceed:
    def test_healthy_city_proceeds(self):
        d = route(make_healthy_signal())
        assert d.action_class == ActionClass.AUTO_PROCEED
        assert "ship_city_live" in d.actions
        assert d.priority == "low"


class TestRevenueBoundaryWatchdog:
    def test_stripe_failures_trigger_critical(self):
        s = make_healthy_signal()
        s.stripe_webhook_failures_24h = STRIPE_FAILURE_THRESHOLD
        d = route(s)
        assert d.action_class == ActionClass.HUMAN_REVIEW
        assert d.priority == "critical"
        assert "pause_reddit_ads" in d.actions
        assert "alert_operator_p0" in d.actions

    def test_checkout_collapse_triggers_critical(self):
        s = make_healthy_signal()
        s.checkout_start_delta_pct = -(CHECKOUT_DROP_THRESHOLD + 0.01)
        d = route(s)
        assert d.action_class == ActionClass.HUMAN_REVIEW
        assert d.priority == "critical"


class TestPaymentAnomaly:
    def test_chargeback_spike_triggers_human_review(self):
        s = make_healthy_signal()
        s.paid_conversions_7d = 10
        s.chargebacks_7d = 1  # 10% > 3% threshold
        d = route(s)
        assert d.action_class == ActionClass.HUMAN_REVIEW
        assert "queue_chargeback_review" in d.actions


class TestHardTrustFailure:
    def test_fail_verdict_no_override_triggers_human(self):
        s = make_healthy_signal()
        s.confidence_score = 0.3
        s.scoring_verdict = "FAIL"
        s.override_active = False
        d = route(s)
        assert d.action_class == ActionClass.HUMAN_REVIEW
        assert "queue_trust_failure_review" in d.actions

    def test_fail_verdict_with_override_does_not_block(self):
        s = make_healthy_signal()
        s.confidence_score = 0.3
        s.scoring_verdict = "FAIL"
        s.override_active = True  # human already approved override
        d = route(s)
        # Falls through to confidence-based routing
        assert d.action_class in (ActionClass.AUTO_REPAIR, ActionClass.STRATEGY_ACTION)


class TestAuthorityDrift:
    def test_drift_detected_queues_manual(self):
        s = make_healthy_signal()
        s.authority_drift_detected = True
        d = route(s)
        assert d.action_class == ActionClass.HUMAN_REVIEW
        assert "queue_manual_approval" in d.actions

    def test_active_override_queues_manual(self):
        s = make_healthy_signal()
        s.override_active = True
        s.scoring_verdict = "ready_to_service"  # not a FAIL
        d = route(s)
        assert d.action_class == ActionClass.HUMAN_REVIEW


class TestAutoRepair:
    def test_below_repair_floor_triggers_repair(self):
        s = make_healthy_signal()
        s.confidence_score = CONFIDENCE_REPAIR_FLOOR - 0.05
        s.scoring_verdict = "REPAIR"
        s.override_active = False
        d = route(s)
        assert d.action_class == ActionClass.AUTO_REPAIR
        assert "trigger_research_loop" in d.actions
        assert "hold_export" in d.actions

    def test_repair_also_pauses_active_campaign(self):
        s = make_healthy_signal()
        s.confidence_score = 0.40
        s.scoring_verdict = "REPAIR"
        s.reddit_campaign_active = True
        d = route(s)
        assert "pause_reddit_ads" in d.actions


class TestStrategyAction:
    def test_below_ad_floor_pauses_ads(self):
        s = make_healthy_signal()
        s.confidence_score = CONFIDENCE_FLOOR - 0.05
        s.scoring_verdict = "ready_to_service"
        d = route(s)
        assert d.action_class == ActionClass.STRATEGY_ACTION
        assert "pause_reddit_ads" in d.actions or "hold_export" in d.actions

    def test_refund_spike_throttles(self):
        s = make_healthy_signal()
        s.paid_conversions_7d = 10
        s.refunds_7d = 1  # 10% > 8% threshold
        d = route(s)
        assert d.action_class == ActionClass.STRATEGY_ACTION
        assert "throttle_acquisition" in d.actions

    def test_high_cvr_scales_budget(self):
        s = make_healthy_signal()
        s.confidence_score = 0.92
        s.checkout_starts_7d = 100
        s.paid_conversions_7d = 8  # 8% CVR > 4% threshold
        s.refunds_7d = 0
        d = route(s)
        assert d.action_class == ActionClass.STRATEGY_ACTION
        assert "increase_reddit_budget" in d.actions

    def test_high_trust_low_cvr_flags_creative(self):
        s = make_healthy_signal()
        s.confidence_score = 0.90
        s.clicks_7d = 200
        s.checkout_starts_7d = 200
        s.paid_conversions_7d = 0  # 0% CVR
        d = route(s)
        assert d.action_class == ActionClass.STRATEGY_ACTION
        assert "flag_creative_review" in d.actions


class TestBatchRouting:
    def test_sorted_by_priority(self):
        signals = [
            make_healthy_signal("chicago"),       # should be LOW
            make_healthy_signal("denver"),
        ]
        signals[1].stripe_webhook_failures_24h = 5  # critical
        decisions = route_all(signals)
        assert decisions[0].priority == "critical"
        assert decisions[-1].priority == "low"


class TestWeeklySummary:
    def test_summary_structure(self):
        s1 = make_healthy_signal("chicago")
        s2 = make_healthy_signal("denver")
        s2.stripe_webhook_failures_24h = 5
        decisions = route_all([s1, s2])
        summary = generate_weekly_summary(decisions)
        assert "total_cities_evaluated" in summary
        assert summary["total_cities_evaluated"] == 2
        assert len(summary["critical_actions"]) >= 1
        assert "AUTO_PROCEED" in summary["by_class"] or "HUMAN_REVIEW" in summary["by_class"]
