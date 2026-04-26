"""
ad_ops_executor.py — Executes ad ops decisions from the decision router

Translates RouterDecision.actions into actual Reddit Ads API calls.
This is where data drives dollars — automatically.

Actions handled:
  - pause_reddit_ads
  - increase_reddit_budget
  - reduce_reddit_budget_50pct
  - throttle_acquisition
  - lock_expansion_spend
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

REDDIT_ADS_BASE = "https://ads-api.reddit.com/api/v2.1"
BUDGET_SCALE_UP_FACTOR = 1.18     # 18% increase on scale signal
BUDGET_THROTTLE_FACTOR = 0.50     # 50% cut on refund spike
MIN_DAILY_BUDGET_USD = 5.0        # never drop below $5/day


class AdOpsExecutor:
    def __init__(self) -> None:
        self.access_token = os.environ.get("REDDIT_ACCESS_TOKEN")
        self._campaign_map: dict[str, str] | None = None

    def execute(self, city_id: str, actions: list[str]) -> list[dict]:
        """Execute all ad ops actions for a city. Returns list of execution results."""
        results = []
        for action in actions:
            try:
                result = self._dispatch(city_id, action)
                results.append({"action": action, "status": "ok", "detail": result})
            except Exception as exc:
                logger.error("Ad ops action %s failed for %s: %s", action, city_id, exc)
                results.append({"action": action, "status": "error", "error": str(exc)})
        return results

    def _dispatch(self, city_id: str, action: str) -> Any:
        if action == "pause_reddit_ads":
            return self._set_campaign_status(city_id, "paused")
        elif action == "increase_reddit_budget":
            return self._scale_budget(city_id, BUDGET_SCALE_UP_FACTOR)
        elif action == "reduce_reddit_budget_50pct":
            return self._scale_budget(city_id, BUDGET_THROTTLE_FACTOR)
        elif action == "throttle_acquisition":
            return self._scale_budget(city_id, BUDGET_THROTTLE_FACTOR)
        elif action == "lock_expansion_spend":
            # Freeze budget at current level, pause new campaigns
            return self._set_campaign_status(city_id, "paused")
        else:
            logger.debug("Action %s has no ad ops handler — passed through", action)
            return {"skipped": True}

    def _get_campaign_id(self, city_id: str) -> str | None:
        if self._campaign_map is None:
            self._campaign_map = self._load_campaign_map()
        return self._campaign_map.get(city_id)

    def _set_campaign_status(self, city_id: str, status: str) -> dict:
        campaign_id = self._get_campaign_id(city_id)
        if not campaign_id:
            logger.warning("No campaign mapped for city %s — cannot %s", city_id, status)
            return {"skipped": True, "reason": "no_campaign_mapped"}

        resp = requests.patch(
            f"{REDDIT_ADS_BASE}/campaigns/{campaign_id}",
            headers=self._headers(),
            json={"status": status},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Campaign %s for %s set to %s", campaign_id, city_id, status)
        return {"campaign_id": campaign_id, "new_status": status}

    def _scale_budget(self, city_id: str, factor: float) -> dict:
        campaign_id = self._get_campaign_id(city_id)
        if not campaign_id:
            return {"skipped": True, "reason": "no_campaign_mapped"}

        # Fetch current budget
        resp = requests.get(
            f"{REDDIT_ADS_BASE}/campaigns/{campaign_id}",
            headers=self._headers(),
            timeout=10,
        )
        resp.raise_for_status()
        current_budget = resp.json().get("data", {}).get("dailyBudget", 0.0)
        new_budget = max(MIN_DAILY_BUDGET_USD, round(current_budget * factor, 2))

        patch_resp = requests.patch(
            f"{REDDIT_ADS_BASE}/campaigns/{campaign_id}",
            headers=self._headers(),
            json={"dailyBudget": new_budget},
            timeout=10,
        )
        patch_resp.raise_for_status()
        logger.info(
            "Budget for %s adjusted %.2f → %.2f (×%.2f)",
            city_id, current_budget, new_budget, factor,
        )
        return {
            "campaign_id": campaign_id,
            "prev_budget": current_budget,
            "new_budget": new_budget,
            "factor": factor,
        }

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    @staticmethod
    def _load_campaign_map() -> dict[str, str]:
        import json, pathlib
        map_path = pathlib.Path(__file__).parent.parent / "data" / "city-campaign-map.json"
        if not map_path.exists():
            return {}
        with open(map_path) as f:
            return json.load(f)
