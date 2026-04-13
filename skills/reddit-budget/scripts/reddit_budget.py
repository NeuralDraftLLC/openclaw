#!/usr/bin/env python3
"""
Reddit Ads API helper — list campaigns and update daily budget.

Requires env (OpenClaw vault):
  REDDIT_CLIENT_ID
  REDDIT_CLIENT_SECRET
  REDDIT_REFRESH_TOKEN   # OAuth app with adsread + adsedit (or equivalent write scope)
  REDDIT_AD_ACCOUNT_ID   # ad account id (often t2_... or numeric per Reddit Business UI)
Optional:
  REDDIT_USER_AGENT      # defaults to ParkingBreakerOpenClaw/1.0

Safety:
  MAX_DAILY_USD = 50 — refuses --set above this cap (override only by editing this file).

Docs: https://ads-api.reddit.com/docs/

Usage:
  python3 reddit_budget.py list
  python3 reddit_budget.py set <campaign_id> <daily_budget_usd> [--dry-run]
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

MAX_DAILY_USD = 50.0

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
ADS_BASE = "https://ads-api.reddit.com"


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _ua() -> str:
    return _env(
        "REDDIT_USER_AGENT",
        "ParkingBreakerOpenClaw/1.0 by /u/(configure REDDIT_USER_AGENT)",
    )


def refresh_access_token() -> str:
    cid = _env("REDDIT_CLIENT_ID")
    secret = _env("REDDIT_CLIENT_SECRET")
    refresh = _env("REDDIT_REFRESH_TOKEN")
    if not cid or not secret or not refresh:
        raise SystemExit(
            "Missing REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_REFRESH_TOKEN"
        )

    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    body = urllib.parse.urlencode(
        {"grant_type": "refresh_token", "refresh_token": refresh}
    ).encode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Basic {auth}",
            "User-Agent": _ua(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    token = data.get("access_token")
    if not token:
        raise SystemExit(f"Token response missing access_token: {data}")
    return str(token)


def _ads_request(
    method: str,
    path: str,
    token: str,
    payload: dict | None = None,
) -> dict:
    url = f"{ADS_BASE}{path}" if path.startswith("/") else f"{ADS_BASE}/{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": _ua(),
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        raise SystemExit(f"HTTP {e.code} {e.reason}: {err_body[:500]}") from e


def list_campaigns(token: str) -> dict:
    ad_acct = _env("REDDIT_AD_ACCOUNT_ID")
    if not ad_acct:
        raise SystemExit("REDDIT_AD_ACCOUNT_ID not set")
    # Reddit v3: campaigns under ad account
    path = f"/api/v3/ad_accounts/{ad_acct}/campaigns"
    return _ads_request("GET", path, token)


def update_campaign_budget(
    token: str,
    campaign_id: str,
    daily_budget_usd: float,
    *,
    dry_run: bool = False,
) -> dict:
    if daily_budget_usd <= 0:
        raise SystemExit("daily_budget_usd must be positive")
    if daily_budget_usd > MAX_DAILY_USD:
        raise SystemExit(
            f"Refusing budget ${daily_budget_usd}: exceeds MAX_DAILY_USD={MAX_DAILY_USD}"
        )

    # Reddit typically expects budget in micro-currency or cents — verify in Ads UI docs.
    # Plan: cents (USD * 100).
    daily_budget_cents = int(round(daily_budget_usd * 100))
    body = {"data": {"daily_budget": daily_budget_cents}}

    path = f"/api/v3/campaigns/{campaign_id}"
    if dry_run:
        print(json.dumps({"dry_run": True, "method": "PATCH", "path": path, "body": body}, indent=2))
        return {}

    return _ads_request("PATCH", path, token, body)


def main() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        raise SystemExit(0)

    cmd = argv[0]
    token = refresh_access_token()

    if cmd == "list":
        out = list_campaigns(token)
        print(json.dumps(out, indent=2))
        return

    if cmd == "set":
        if len(argv) < 3:
            raise SystemExit("usage: reddit_budget.py set <campaign_id> <daily_budget_usd> [--dry-run]")
        campaign_id = argv[1]
        try:
            usd = float(argv[2])
        except ValueError as e:
            raise SystemExit(f"invalid dollar amount: {argv[2]}") from e
        dry = "--dry-run" in argv[3:]
        update_campaign_budget(token, campaign_id, usd, dry_run=dry)
        if not dry:
            print(f"OK: PATCH campaign {campaign_id} daily_budget_usd={usd}")
        return

    raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
