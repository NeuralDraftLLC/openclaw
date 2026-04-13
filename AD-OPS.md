# AD-OPS.md — Growth / Reddit budget rules (always load)

This file is **binding** for agent **`main`** (heartbeat specialist) and any session that touches ParkingBreaker telemetry or Reddit spend. Read **after** `SOUL.md` and `USER.md`, **before** acting on funnel or budget data. There is no separate SiteOps / finance / ad-optimizer agent.

## Data source

- **Read telemetry:** `GET {PARKINGBREAKER_API_BASE}/telemetry/stats/{city_id}` (30-day window).
- **OpenClaw bundle (descriptive + diagnostic + predictive):** `GET {PARKINGBREAKER_API_BASE}/telemetry/openclaw/export` — same auth; poll for agent summaries / Telegram (see `INTEGRATIONS.md`).
- **Auth:** `Authorization: Bearer {PB_INTERNAL_TOKEN}` when backend has token set.
- **Canonical city IDs:** 63 cities — `backend/cities/*.json` basenames; **no** `us-co-denver`.

## API fields you may cite (do not invent names)

| Field | Meaning |
|--------|--------|
| `summary.citation_validated` | Count of `citation_validated` events (organic + paid mixed — weak proxy for “traffic”). |
| `summary.checkout_initiated` | Checkout starts (`checkout_initiated`). |
| `summary.payment_confirmed` | Paid (`payment_confirmed`). |
| `checkout_to_paid_rate` | `payment_confirmed / checkout_initiated` (0 if denominator 0). |
| `appeal_success_rate` | Same as outcomes dismissal rate when present. |
| `events.events_by_type` | Per-type counts including `ad_click` when frontend UTM ingest is live. |

## Data trust ladder (traffic proxy for PAUSE / WATCH)

Use the **best available** signal for “paid-ish traffic volume” in decision narratives:

1. **`ad_click`** — from `events.events_by_type.ad_click` when the key is present (Reddit `?utm_source=reddit` landings).
2. Else **`citation_validated`** — `summary.citation_validated` (mixed organic + paid; **never** treat as pure ad traffic once `ad_click` exists for that city/period).

The bundled observer script labels table traffic as `N:ad` vs `N:org` to show which proxy was used.

## Classifier thresholds (match observer + this file)

| Recommendation | Condition |
|----------------|-----------|
| **INCREASE_BUDGET** | `checkout_initiated >= 20` **and** `checkout_to_paid_rate > 0.05` |
| **PAUSE_SPEND** | `traffic_proxy >= 50` **and** `checkout_to_paid_rate < 0.01` |
| **INSUFFICIENT_DATA** | `checkout_initiated < 5` |
| **WATCH** | Otherwise |
| **ERROR** | HTTP / parse failure |

**Confidence** (narrative only): `checkout_initiated >= 50` → high; `>= 20` → medium; else low.

## Hard safety rules

1. **No Reddit budget mutation** without:
   - A non-empty `city-campaign-map.json` entry for that `city_id`, and  
   - **Explicit human approval** in Telegram/WhatsApp (typed approve for that city + action).
2. **No** pause-all-cities or bulk “turn off everything.” One city, one decision per approval cycle.
3. **No** single-step budget change **greater than 50%** of current daily spend without explicit owner approval text (not just “ok”).
4. **Do not** act on `INCREASE_BUDGET` / `PAUSE_SPEND` when `checkout_initiated < 5` (should be INSUFFICIENT_DATA — double-check).
5. **Never** log or paste `PB_INTERNAL_TOKEN`, Stripe keys, Reddit `CLIENT_SECRET`, or `REFRESH_TOKEN`.
6. **Telemetry is read-only** until a human approves spend changes. **Reddit budget mutations** use the budget script (or equivalent) **only after** approval — never from telemetry alone.

## Approval flow (Level 2)

1. Summarize actionable rows: `city_id`, `traffic_proxy` + source (`ad`/`org`), `checkout_initiated`, `payment_confirmed`, `checkout_to_paid_rate`, `recommendation`, `confidence`.
2. For **INCREASE_BUDGET** or **PAUSE_SPEND**, send Telegram message: proposed dollar change, campaign id from `city-campaign-map.json`, and **one-line rationale**.
3. **Approval tokens:** owner must reply with clear approve, e.g. `APPROVE INCREASE us-ca-san_francisco $35` or `APPROVE PAUSE us-tx-dallas`.
4. **No reply within 30 minutes** of a pending action → treat as **NO**; do not execute.
5. **Deny patterns:** “no”, “hold”, “wait”, emoji-only → **do not execute**.

## Escalation (immediate ping, not only heartbeat)

If **any** city previously had `checkout_initiated >= 20` and `checkout_to_paid_rate >= 0.02` but **now** reports `checkout_to_paid_rate < 0.005` with `checkout_initiated >= 10`, send **immediate** alert (not batched) — possible tracking breakage or landing-page regression.

## Operator tooling (paths)

| Purpose | Path |
|--------|------|
| Telemetry observer (optional) | `~/.openclaw/skills/parkingbreaker-ops/scripts/parkingbreaker_observer.py` |
| Reddit budget (post-approval only) | `~/.openclaw/skills/reddit-budget/scripts/reddit_budget.py` |
| City → campaign map | `./city-campaign-map.json` (repo root) |

## Reddit execution notes

- Reddit has **no** campaign-id column in ParkingBreaker DB — mapping is **only** in `city-campaign-map.json`.
- `reddit_budget.py` enforces **MAX_DAILY_USD** (50) unless you change the file with owner sign-off.
- If Reddit API returns errors, **stop** — do not retry budget mutations more than once without human context.

---

_Keep this file accurate when thresholds or API shapes change._
