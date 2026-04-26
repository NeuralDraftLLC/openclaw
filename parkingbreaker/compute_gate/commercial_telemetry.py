"""
commercial_telemetry.py — Per-city revenue signal collector

Connects Stripe + Reddit Ads API data to CitySignal objects
so the decision router has commercial context alongside trust scores.

Every metric must answer: "What happens because of this?"
If the answer is only 'we observe it' — it's incomplete.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CommercialSnapshot:
    city_id: str
    window_days: int = 7

    # Funnel
    clicks: int = 0
    checkout_starts: int = 0
    paid_conversions: int = 0
    revenue_usd: float = 0.0

    # Quality
    refunds: int = 0
    chargebacks: int = 0
    support_complaints: int = 0
    successful_appeal_outcomes: int = 0

    # Infrastructure health
    stripe_webhook_failures_24h: int = 0
    checkout_start_delta_pct: float = 0.0
    last_successful_payment_at: str | None = None

    # Ad ops
    reddit_campaign_active: bool = False
    current_daily_budget_usd: float = 0.0
    reddit_impressions_7d: int = 0
    reddit_spend_7d: float = 0.0


class CommercialTelemetryCollector:
    """
    Pulls per-city commercial data from Stripe + Reddit Ads.
    Returns CommercialSnapshot objects for injection into CitySignal.

    Usage:
        collector = CommercialTelemetryCollector()
        snap = collector.collect("los-angeles")
    """

    def __init__(self) -> None:
        self.stripe_key = os.environ.get("STRIPE_SECRET_KEY")
        self.reddit_client_id = os.environ.get("REDDIT_CLIENT_ID")
        self.reddit_client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
        self.reddit_access_token = os.environ.get("REDDIT_ACCESS_TOKEN")

    def collect(self, city_id: str, window_days: int = 7) -> CommercialSnapshot:
        snap = CommercialSnapshot(city_id=city_id, window_days=window_days)
        try:
            self._enrich_stripe(snap)
        except Exception as exc:
            logger.warning("Stripe collection failed for %s: %s", city_id, exc)
        try:
            self._enrich_reddit(snap)
        except Exception as exc:
            logger.warning("Reddit collection failed for %s: %s", city_id, exc)
        return snap

    def collect_batch(self, city_ids: list[str]) -> dict[str, CommercialSnapshot]:
        return {cid: self.collect(cid) for cid in city_ids}

    # ── Stripe ───────────────────────────────────────────────────────────────

    def _enrich_stripe(
        self, snap: CommercialSnapshot, window_days: int = 7
    ) -> None:
        """
        Pulls charges, refunds, disputes from Stripe for this city.
        City scoping: Stripe metadata field `city_id` on PaymentIntent.
        """
        if not self.stripe_key:
            logger.debug("STRIPE_SECRET_KEY not set, skipping Stripe enrichment")
            return

        import stripe  # type: ignore
        stripe.api_key = self.stripe_key

        since_ts = int(
            (datetime.now(timezone.utc) - timedelta(days=window_days)).timestamp()
        )

        # Charges for this city
        charges = stripe.Charge.list(
            created={"gte": since_ts},
            limit=100,
        )
        city_charges = [
            c for c in charges.auto_paging_iter()
            if c.get("metadata", {}).get("city_id") == snap.city_id
        ]

        snap.paid_conversions = sum(1 for c in city_charges if c["status"] == "succeeded")
        snap.revenue_usd = sum(
            c["amount"] / 100 for c in city_charges if c["status"] == "succeeded"
        )
        snap.refunds = sum(1 for c in city_charges if c.get("refunded"))

        # Disputes
        disputes = stripe.Dispute.list(created={"gte": since_ts}, limit=100)
        snap.chargebacks = sum(
            1 for d in disputes.auto_paging_iter()
            if d.get("metadata", {}).get("city_id") == snap.city_id
        )

        # Webhook failure count from last 24h (EventDestination health)
        # Approximated via failed event delivery attempts
        recent_events = stripe.Event.list(
            type="charge.failed",
            created={"gte": int((datetime.now(timezone.utc) - timedelta(hours=24)).timestamp())},
            limit=100,
        )
        snap.stripe_webhook_failures_24h = sum(
            1 for e in recent_events.auto_paging_iter()
            if e.get("data", {}).get("object", {}).get("metadata", {}).get("city_id") == snap.city_id
        )

        # Last successful payment
        succeeded = [
            c for c in city_charges if c["status"] == "succeeded"
        ]
        if succeeded:
            snap.last_successful_payment_at = datetime.fromtimestamp(
                succeeded[0]["created"], tz=timezone.utc
            ).isoformat()

    # ── Reddit Ads ───────────────────────────────────────────────────────────

    def _enrich_reddit(
        self, snap: CommercialSnapshot, window_days: int = 7
    ) -> None:
        """
        Pulls Reddit Ads performance for this city's campaign.
        Requires city-campaign-map.json to map city_id → campaign_id.
        """
        import requests

        city_campaign_map = self._load_city_campaign_map()
        campaign_id = city_campaign_map.get(snap.city_id)
        if not campaign_id:
            logger.debug("No Reddit campaign mapped for city %s", snap.city_id)
            return

        snap.reddit_campaign_active = True

        headers = {"Authorization": f"Bearer {self.reddit_access_token}"}
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (
            datetime.now(timezone.utc) - timedelta(days=window_days)
        ).strftime("%Y-%m-%d")

        resp = requests.get(
            f"https://ads-api.reddit.com/api/v2.1/campaigns/{campaign_id}/reports",
            headers=headers,
            params={
                "startDate": start_date,
                "endDate": end_date,
                "metrics": "impressions,clicks,spend,ctr",
            },
            timeout=10,
        )

        if resp.status_code != 200:
            logger.warning(
                "Reddit Ads API returned %s for city %s", resp.status_code, snap.city_id
            )
            return

        data = resp.json()
        rows = data.get("data", {}).get("rows", [])
        snap.reddit_impressions_7d = sum(r.get("impressions", 0) for r in rows)
        snap.clicks = sum(r.get("clicks", 0) for r in rows)
        snap.reddit_spend_7d = sum(r.get("spend", 0.0) for r in rows)

        # Budget from campaign details
        budget_resp = requests.get(
            f"https://ads-api.reddit.com/api/v2.1/campaigns/{campaign_id}",
            headers=headers,
            timeout=10,
        )
        if budget_resp.status_code == 200:
            campaign_data = budget_resp.json().get("data", {})
            snap.current_daily_budget_usd = campaign_data.get("dailyBudget", 0.0)

    @staticmethod
    def _load_city_campaign_map() -> dict[str, str]:
        import json
        import pathlib
        map_path = pathlib.Path(__file__).parent.parent / "data" / "city-campaign-map.json"
        if not map_path.exists():
            return {}
        with open(map_path) as f:
            return json.load(f)
