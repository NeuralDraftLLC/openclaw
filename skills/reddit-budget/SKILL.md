---
name: reddit_ads_budget
description: List Reddit Ads campaigns and update daily budgets via Reddit Ads API v3 (OAuth refresh token). Enforces a hard per-campaign daily cap. Use only after human approval per AD-OPS.md.
version: "1.0.0"
author: "Amir Khodabakhsh"
triggers:
  - "update Reddit campaign budget"
  - "list Reddit ads campaigns"
  - "pause Reddit spend"
  - "reddit ads daily budget"
user-invocable: true
metadata: {"openclaw":{"emoji":"📣","requires":{"bins":["python3"],"env":["REDDIT_CLIENT_ID","REDDIT_CLIENT_SECRET","REDDIT_REFRESH_TOKEN","REDDIT_AD_ACCOUNT_ID"]}}}
---

# Reddit Ads — budget helper

## What it does

- Refreshes an OAuth access token (`grant_type=refresh_token`).
- `list` — `GET /api/v3/ad_accounts/{REDDIT_AD_ACCOUNT_ID}/campaigns`
- `set <campaign_id> <daily_budget_usd>` — `PATCH /api/v3/campaigns/{id}` with daily budget (see script for units).

## Rules (non-negotiable)

1. **Never** call `set` without explicit human approval (Telegram/WhatsApp), per repo root `AD-OPS.md`.
2. **Never** print client secret or refresh token.
3. **Never** bypass `MAX_DAILY_USD` in `scripts/reddit_budget.py` without owner sign-off.
4. Map `city_id` → campaign id via `city-campaign-map.json` in the ParkingBreaker repo before any change.

## Reddit app setup (summary)

1. Reddit Business / Developer app with redirect URI configured.
2. OAuth scopes: at minimum **adsread**; budget updates need a **write** scope (e.g. ads management — confirm current Reddit scope names in dashboard).
3. Obtain **refresh_token** with `duration=permanent`.

## Vault

```bash
openclaw vault set REDDIT_CLIENT_ID <id>
openclaw vault set REDDIT_CLIENT_SECRET <secret>
openclaw vault set REDDIT_REFRESH_TOKEN <token>
openclaw vault set REDDIT_AD_ACCOUNT_ID <ad_account_id>
# Recommended:
openclaw vault set REDDIT_USER_AGENT "ParkingBreakerBot/1.0 (contact: you@example.com)"
```

## Run

```bash
python3 /home/amir/.openclaw/skills/reddit-budget/scripts/reddit_budget.py list
python3 /home/amir/.openclaw/skills/reddit-budget/scripts/reddit_budget.py set <campaign_id> 25 --dry-run
python3 /home/amir/.openclaw/skills/reddit-budget/scripts/reddit_budget.py set <campaign_id> 25
```

## API drift

If `list` or `set` returns 404/410, check [Reddit Ads API v3 docs](https://ads-api.reddit.com/docs/) — paths and JSON bodies change. Update `reddit_budget.py` accordingly.
