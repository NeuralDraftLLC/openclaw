# ARTOS — Autonomous Revenue + Trust Operating System

**ParkingBreaker v2 Architecture**

---

## The Shift

Cron is no longer "jobs that run."
It is a **closed-loop operating system for the business.**

Full automation is not: more scripts

It is:
```
telemetry → decision → action → verification → escalation
```
with minimal human intervention only at **true trust boundaries.**

---

## The System Continuously Answers

- Which cities are safe to sell today
- Which cities are degrading
- Where revenue is leaking
- Where ads should be increased or paused
- Where pricing should be defended or changed
- Where operator review is actually required

**Every data signal must have an action path. Not just a report.**

---

## The 4 Action Classes

| Class | Trigger | Action | Human? |
|-------|---------|--------|--------|
| **A. AUTO_PROCEED** | `verdict = ready_to_service`, trust stable | Ship city live | ❌ |
| **B. AUTO_REPAIR** | `status = REPAIR`, confidence < 0.50 | Trigger MiniMax re-source loop | ❌ |
| **C. HUMAN_REVIEW** | FAIL + no override, payment anomaly, authority drift, checkout collapse | Queue manual approval | ✅ Rare |
| **D. STRATEGY_ACTION** | High demand + high trust → scale; high refunds → pause; low CVR → creative | Change Reddit spend / pricing | ❌ |

> Humans are **rare and expensive.** Only true trust boundaries require them.

---

## Architecture: The Decision Router

```
               ┌─────────────────────────────────┐
               │        CITY SIGNALS             │
               │  confidence · authority drift   │
               │  Stripe CVR · refunds           │
               │  Reddit clicks · spend          │
               │  checkout starts · chargebacks  │
               └──────────────┬──────────────────┘
                              │
                   decision_router.py
                              │
          ┌───────────────────┼────────────────────┐
          │                   │                    │
   AUTO_PROCEED         AUTO_REPAIR         STRATEGY_ACTION
   ship_city_live   trigger_research_loop   pause/scale ads
                                                   │
                                         ad_ops_executor.py
                                                   │
                                        Reddit Ads API calls
```

---

## File Map

| File | Role |
|------|------|
| `decision_router.py` | **The brain.** Waterfall priority → 4 action classes |
| `commercial_telemetry.py` | Stripe + Reddit data → CommercialSnapshot per city |
| `ad_ops_executor.py` | Executes ad budget changes automatically |
| `export_gate.py` | Every export request cleared through the router |
| `scoring_policy.py` | Trust scoring (existing) — feeds into router |
| `tests/test_decision_router.py` | Full unit coverage of all routing branches |

---

## Decision Priority Waterfall

```
1. Revenue boundary watchdog (Stripe failures / checkout collapse) → CRITICAL
2. Payment anomaly (chargebacks > 3%)                             → CRITICAL
3. Hard trust FAIL + no override                                   → HIGH
4. Authority drift or override hotspot                             → HIGH
5. Confidence < 0.50                                              → AUTO_REPAIR
6. Confidence < 0.75 (below ad floor)                             → pause ads
7. Refund rate > 8%                                               → throttle
8. High trust + CVR > 4%                                          → scale spend
9. High trust + clicks > 50 + CVR < 1%                            → flag creative
10. All clear                                                      → AUTO_PROCEED
```

---

## Revenue Telemetry Per City

Track per city:
- `clicks_7d`
- `checkout_starts_7d`
- `paid_conversions_7d`
- `refunds_7d`
- `chargebacks_7d`
- `support_complaints_7d`
- `successful_appeal_outcomes_7d`

### Diagnostic Matrix

| Signal Pattern | Meaning | Action |
|----------------|---------|--------|
| High trust + low CVR | Marketing problem | Flag creative review |
| Low trust + high refunds | Authority problem | Pause ads + repair |
| High trust + high CVR | Scale signal | Increase Reddit budget |
| Checkout drop > 30% | Infrastructure broken | Pause all paid traffic |
| Chargebacks > 3% | Payment risk | Human review + pause |

---

## The Golden Rule

> **Every metric must answer: "What happens because of this?"**
>
> If the answer is: *"we observe it"* → incomplete
>
> If the answer is: *"the system acts"* → you're building correctly.

---

## Weekly Executive Summary Output

Not dashboards. **Decisions.**

```json
{
  "generated_at": "2026-04-27T...",
  "total_cities_evaluated": 54,
  "critical_actions": [
    {"city": "los-angeles", "reason": "Checkout drop 38%", "actions": ["pause_reddit_ads", "alert_operator_p0"]}
  ],
  "auto_repaired": ["phoenix", "tucson"],
  "human_required": [
    {"city": "denver", "reason": "Refund spike 11%"}
  ],
  "scaled_cities": ["chicago", "miami"],
  "paused_cities": ["los-angeles", "seattle"]
}
```

---

## TODO: Wire-In Points

- [ ] `export_gate.py._trigger_repair()` → call `research_worker.enqueue(city_id, fields)`
- [ ] `commercial_telemetry.py` → wire `checkout_starts_7d` from Stripe checkout session events
- [ ] `commercial_telemetry.py` → wire `support_complaints_7d` from Zendesk/email
- [ ] Cron: call `route_all(signals)` every 6 hours, push decisions to `heartbeat-state.json`
- [ ] Weekly cron: call `generate_weekly_summary()` → send via SendGrid to Amir
- [ ] `city-campaign-map.json` → populate 54 campaign IDs from Reddit Ads Manager
