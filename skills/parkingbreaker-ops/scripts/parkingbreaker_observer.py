"""
ParkingBreaker Telemetry Observer — OpenClaw Skill

Required env:
  PARKINGBREAKER_API_BASE   e.g. https://fightcitytickets-production.up.railway.app
  PB_INTERNAL_TOKEN         when backend enforces auth

Usage:
  python3 parkingbreaker_observer.py                    # all cities
  python3 parkingbreaker_observer.py us-ca-san_francisco
"""

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

API_BASE = os.environ.get("PARKINGBREAKER_API_BASE", "").rstrip("/")
TOKEN = os.environ.get("PB_INTERNAL_TOKEN", "")

ALL_CITY_IDS = [
    "us-ak-anchorage",
    "us-ar-little_rock",
    "us-az-chandler",
    "us-az-gilbert",
    "us-az-glendale",
    "us-az-mesa",
    "us-az-phoenix",
    "us-ca-los_angeles",
    "us-ca-san_diego",
    "us-ca-san_francisco",
    "us-ca-santa_clarita",
    "us-co-boulder",
    "us-co-colorado_springs",
    "us-co-fort_collins",
    "us-dc-washington",
    "us-fl-jacksonville",
    "us-fl-miami",
    "us-fl-orlando",
    "us-fl-tampa",
    "us-ga-atlanta",
    "us-id-boise",
    "us-il-chicago",
    "us-in-indianapolis",
    "us-ks-wichita",
    "us-ky-louisville",
    "us-la-new_orleans",
    "us-ma-boston",
    "us-md-baltimore",
    "us-mi-detroit",
    "us-mn-minneapolis",
    "us-mo-kansas_city",
    "us-mo-st_louis",
    "us-nc-charlotte",
    "us-nc-fayetteville",
    "us-nc-raleigh",
    "us-nd-bismarck",
    "us-ne-lincoln",
    "us-ne-omaha",
    "us-nm-albuquerque",
    "us-nv-las_vegas",
    "us-nv-reno",
    "us-ny-buffalo",
    "us-ny-new_york",
    "us-oh-columbus",
    "us-ok-tulsa",
    "us-or-eugene",
    "us-or-portland",
    "us-or-salem",
    "us-pa-philadelphia",
    "us-pa-pittsburgh",
    "us-tn-memphis",
    "us-tn-nashville",
    "us-tx-austin",
    "us-tx-corpus_christi",
    "us-tx-dallas",
    "us-tx-fort_worth",
    "us-tx-houston",
    "us-tx-lubbock",
    "us-tx-plano",
    "us-tx-san_antonio",
    "us-va-virginia_beach",
    "us-wa-seattle",
    "us-wa-spokane",
    "us-wi-madison",
]


def get_city_performance(city_id: str) -> dict[str, Any]:
    if not API_BASE:
        return {"error": "PARKINGBREAKER_API_BASE not set"}

    url = f"{API_BASE}/telemetry/stats/{city_id}"
    headers = {"Accept": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "city_id": city_id}
    except Exception as e:
        return {"error": str(e), "city_id": city_id}


def traffic_proxy_from_stats(stats: dict) -> tuple[int, str]:
    """
    Paid-traffic proxy for classifier + display.
    Prefer events.events_by_type.ad_click when the key is present (even if 0);
    otherwise fall back to summary.citation_validated.
    Returns (value, source_label).
    """
    events_block = stats.get("events") or {}
    by_type = events_block.get("events_by_type") or {}
    if not isinstance(by_type, dict):
        by_type = {}
    if "ad_click" in by_type:
        return int(by_type.get("ad_click") or 0), "ad_click"
    summary = stats.get("summary") or {}
    return int(summary.get("citation_validated", 0) or 0), "citation_validated"


def classify_city(stats: dict) -> str:
    if "error" in stats:
        return "ERROR"

    summary = stats.get("summary", {})
    checkout_n = int(summary.get("checkout_initiated", 0) or 0)
    traffic_proxy, _src = traffic_proxy_from_stats(stats)
    c2p_rate = float(stats.get("checkout_to_paid_rate", 0) or 0)

    if checkout_n >= 20 and c2p_rate > 0.05:
        return "INCREASE_BUDGET"
    if traffic_proxy >= 50 and c2p_rate < 0.01:
        return "PAUSE_SPEND"
    if checkout_n < 5:
        return "INSUFFICIENT_DATA"
    return "WATCH"


def confidence_label(stats: dict) -> str:
    checkout_n = int(stats.get("summary", {}).get("checkout_initiated", 0) or 0)
    if checkout_n >= 50:
        return "high"
    if checkout_n >= 20:
        return "medium"
    return "low"


def print_report(city_ids: list[str]) -> None:
    import datetime
    
    col = "{:<30} {:>14} {:>21} {:>19} {:>22} {:>20} {:>12}"
    header = col.format(
        "city_id",
        "traffic_proxy",
        "checkout_initiated",
        "payment_confirmed",
        "checkout_to_paid_rate",
        "recommendation",
        "confidence",
    )
    print(header)
    print("-" * len(header))

    action_rows = []
    all_cities_snapshot = []
    for city_id in city_ids:
        stats = get_city_performance(city_id)
        if "error" in stats:
            print(col.format(city_id, "ERROR", "-", "-", "-", stats["error"][:20], "-"))
            continue

        traffic_proxy, src = traffic_proxy_from_stats(stats)
        summary = stats.get("summary", {})
        checkout_n = int(summary.get("checkout_initiated", 0) or 0)
        paid_n = int(summary.get("payment_confirmed", 0) or 0)
        c2p_rate = float(stats.get("checkout_to_paid_rate", 0) or 0)
        rec = classify_city(stats)
        conf = confidence_label(stats)
        proxy_tag = "ad" if src == "ad_click" else "org"
        display_traffic = f"{traffic_proxy}:{proxy_tag}"

        print(
            col.format(
                city_id,
                display_traffic,
                checkout_n,
                paid_n,
                f"{c2p_rate:.4f}",
                rec,
                conf,
            )
        )

        if rec in ("INCREASE_BUDGET", "PAUSE_SPEND") or True:
            # We append all processed cities for OpenClaw to store
            all_cities_snapshot.append(
                {
                    "city_id": city_id,
                    "traffic_proxy": traffic_proxy,
                    "traffic_source": src,
                    "checkout_initiated": checkout_n,
                    "payment_confirmed": paid_n,
                    "checkout_to_paid_rate": c2p_rate,
                    "recommendation": rec,
                    "confidence": conf,
                }
            )

        if rec in ("INCREASE_BUDGET", "PAUSE_SPEND"):
            action_rows.append(
                {
                    "city_id": city_id,
                    "recommendation": rec,
                    "checkout_to_paid_rate": c2p_rate,
                    "confidence": conf,
                    "awaiting_approval": True,
                }
            )

    if action_rows:
        print("\n⚠  ACTIONS PENDING HUMAN APPROVAL:")
        for row in action_rows:
            print(
                f"  {row['recommendation']:20s}  {row['city_id']}  "
                f"(c2p={row['checkout_to_paid_rate']:.4f}, "
                f"confidence={row['confidence']})"
            )
        print("\nDo NOT execute budget changes without approval in Telegram/WhatsApp.")
    else:
        print("\nNo budget actions recommended this cycle.")

    # Write rolling historic log for OpenClaw Engine
    log_dir = os.path.expanduser("~/h/code/FIGHTCITYTICKETS-1/memory/ad-ops")
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"telemetry_{timestamp}.json")
    with open(log_path, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "actions_pending": action_rows,
            "snapshot": all_cities_snapshot
        }, f, indent=2)
    print(f"\n[Engine] Telemetry snapshot saved to {log_path} for OpenClaw consumption.")


if __name__ == "__main__":
    if not API_BASE:
        print("ERROR: set PARKINGBREAKER_API_BASE in env or OpenClaw vault.")
        sys.exit(1)

    targets = sys.argv[1:] if len(sys.argv) > 1 else ALL_CITY_IDS
    unknown = [c for c in targets if c not in ALL_CITY_IDS]
    if unknown:
        print(f"WARNING: unknown city IDs (will attempt anyway): {unknown}")

    print(f"ParkingBreaker Telemetry Observer — {len(targets)} city/cities\n")
    print_report(targets)
