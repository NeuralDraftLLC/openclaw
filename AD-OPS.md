# AD-OPS.md — Growth / Reddit budget rules (always load)

This file is **binding** for agent **`main`** (heartbeat specialist) and any session that touches ParkingBreaker telemetry or Reddit spend. Read **after** `SOUL.md` and `USER.md`, **before** acting on funnel or budget data. There is no separate SiteOps / finance / ad-optimizer agent.

## Data source

- **Read telemetry:** `GET {PARKINGBREAKER_API_BASE}/telemetry/stats/{city_id}` (30-day window).
- **OpenClaw bundle (descriptive + diagnostic + predictive):** `GET {PARKINGBREAKER_API_BASE}/telemetry/openclaw/export` — same auth; poll for agent summaries / Telegram (see `INTEGRATIONS.md`).
- **Auth:** `Authorization: Bearer {PB_INTERNAL_TOKEN}` when backend has token set.
- **Canonical city IDs:** 63 cities — `backend/cities/*.json` basenames; **no** `us-co-denver`.

## API fields you may cite (do not invent names)

| Field                        | Meaning                                                                                 |
| ---------------------------- | --------------------------------------------------------------------------------------- |
| `summary.citation_validated` | Count of `citation_validated` events (organic + paid mixed — weak proxy for “traffic”). |
| `summary.checkout_initiated` | Checkout starts (`checkout_initiated`).                                                 |
| `summary.payment_confirmed`  | Paid (`payment_confirmed`).                                                             |
| `checkout_to_paid_rate`      | `payment_confirmed / checkout_initiated` (0 if denominator 0).                          |
| `appeal_success_rate`        | Same as outcomes dismissal rate when present.                                           |
| `events.events_by_type`      | Per-type counts including `ad_click` when frontend UTM ingest is live.                  |

## Data trust ladder (traffic proxy for PAUSE / WATCH)

Use the **best available** signal for “paid-ish traffic volume” in decision narratives:

1. **`ad_click`** — from `events.events_by_type.ad_click` when the key is present (Reddit `?utm_source=reddit` landings).
2. Else **`citation_validated`** — `summary.citation_validated` (mixed organic + paid; **never** treat as pure ad traffic once `ad_click` exists for that city/period).

The bundled observer script labels table traffic as `N:ad` vs `N:org` to show which proxy was used.

## Classifier thresholds (match observer + this file)

| Recommendation        | Condition                                                         |
| --------------------- | ----------------------------------------------------------------- |
| **INCREASE_BUDGET**   | `checkout_initiated >= 20` **and** `checkout_to_paid_rate > 0.05` |
| **PAUSE_SPEND**       | `traffic_proxy >= 50` **and** `checkout_to_paid_rate < 0.01`      |
| **INSUFFICIENT_DATA** | `checkout_initiated < 5`                                          |
| **WATCH**             | Otherwise                                                         |
| **ERROR**             | HTTP / parse failure                                              |

**Confidence** (narrative only): `checkout_initiated >= 50` → high; `>= 20` → medium; else low.

**Scripts are the source of truth.** The observer implements classification (`classify_city`, `confidence_label`, `traffic_proxy_from_stats` in `parkingbreaker_observer.py`). The agent **narrates or escalates**; it does **not** re-derive thresholds from raw API payloads during heartbeat.

## Output contract (scripts emit, agent consumes)

The following fields are **machine-authored**. The model must not invent or recompute them; it reads them from `telemetry_*.json` snapshots and `memory/ad-ops/latest.delta.json`.

### Per-city row (in `snapshot[]` and in `actions_pending[]`)

| Field                     | Type           | Notes                                                                           |
| ------------------------- | -------------- | ------------------------------------------------------------------------------- |
| `city_id`                 | string         | Canonical ID                                                                    |
| `recommendation`          | enum           | `INCREASE_BUDGET` \| `PAUSE_SPEND` \| `WATCH` \| `INSUFFICIENT_DATA` \| `ERROR` |
| `confidence`              | enum           | `high` \| `medium` \| `low`                                                     |
| `traffic_proxy`           | int            | Numeric proxy value                                                             |
| `traffic_source`          | enum           | `ad_click` \| `citation_validated`                                              |
| `checkout_initiated`      | int            |                                                                                 |
| `payment_confirmed`       | int            |                                                                                 |
| `checkout_to_paid_rate`   | float          |                                                                                 |
| `campaign_map_present`    | bool           | `false` ⇒ hard block on mutations                                               |
| `approval_required`       | bool           |                                                                                 |
| `blocked_reason`          | string \| null | e.g. `missing_campaign_id`, `c_i_lt_5`, `exceeds_50pct_change`                  |
| `notify_priority`         | enum           | `P0` (escalation, e.g. c2p crash) \| `P1` (new action) \| `P2` (informational)  |
| `why_one_line`            | string         | Max ~120 characters                                                             |
| `telegram_message`        | string         | Prebuilt body; send verbatim when approved                                      |
| `approval_token_template` | string         | e.g. `APPROVE INCREASE us-ca-san_francisco $35`                                 |

### Delta file: `memory/ad-ops/latest.delta.json`

| Field                 | Type            | Notes                                                                       |
| --------------------- | --------------- | --------------------------------------------------------------------------- |
| `generated_at`        | string          | ISO-8601 UTC                                                                |
| `snapshot_hash`       | string          | SHA-256 of full snapshot body (for dedupe with `adOps.lastSnapshotHash`)    |
| `actions_pending`     | array           | Rows matching per-city schema above                                         |
| `resolved`            | array of string | `city_id`s whose prior action no longer applies                             |
| `needs_investigation` | bool            | `true` if P0 fired, schema validation failed, or scripts require human eyes |

### Consume model (what the heartbeat does with this contract)

- Only treat spend-related rows as executable when `blocked_reason == null` and `approval_required == true`.
- Surface `telegram_message` **verbatim**; do not paraphrase policy in place of script text.
- Honour `notify_priority`: `P0` bypasses per-city cooldown (`escalationP0` in `memory/heartbeat-state.json`); `P1` / `P2` respect `cooldownsSeconds.perCityAction`.

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

1. Use contract fields on each row: `city_id`, traffic + funnel metrics, `recommendation`, `confidence`, `approval_token_template`, `telegram_message`.
2. For **INCREASE_BUDGET** or **PAUSE_SPEND**, send the script’s `telegram_message` (includes rationale and token shape when populated).
3. **Approval tokens:** owner must reply with clear approve matching `approval_token_template`, e.g. `APPROVE INCREASE us-ca-san_francisco $35` or `APPROVE PAUSE us-tx-dallas`.
4. **No reply within 30 minutes** of a pending action → treat as **NO**; do not execute.
5. **Deny patterns:** “no”, “hold”, “wait”, emoji-only → **do not execute**.

## Escalation (immediate ping, not only heartbeat)

If **any** city previously had `checkout_initiated >= 20` and `checkout_to_paid_rate >= 0.02` but **now** reports `checkout_to_paid_rate < 0.005` with `checkout_initiated >= 10`, send **immediate** alert (not batched) — possible tracking breakage or landing-page regression. Scripts should emit `notify_priority: "P0"` and `needs_investigation: true` on this pattern.

## Operator tooling (paths)

| Purpose                            | Path                                                                       |
| ---------------------------------- | -------------------------------------------------------------------------- |
| Telemetry observer (optional)      | `~/.openclaw/skills/parkingbreaker-ops/scripts/parkingbreaker_observer.py` |
| Reddit budget (post-approval only) | `~/.openclaw/skills/reddit-budget/scripts/reddit_budget.py`                |
| City → campaign map                | `./city-campaign-map.json` (repo root)                                     |

## Reddit execution notes

- Reddit has **no** campaign-id column in ParkingBreaker DB — mapping is **only** in `city-campaign-map.json`.
- `reddit_budget.py` enforces **MAX_DAILY_USD** (50) unless you change the file with owner sign-off.
- If Reddit API returns errors, **stop** — do not retry budget mutations more than once without human context.

---

_Keep this file accurate when thresholds or API shapes change._
