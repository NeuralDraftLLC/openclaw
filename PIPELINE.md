# PIPELINE.md — Triple-Layer City Research Overseer Guide

> Load this file whenever you are running, reviewing, or debugging city research.
> It is the complete operating manual for the triple-layer pipeline.

---

## What you are overseeing

ParkingBreaker needs verified, machine-readable city data for each jurisdiction we serve: where to mail an appeal, how long the user has, whether there is an online option, and what the issuing agency is.

The **triple-layer pipeline** is how we research and validate that data. Every city in `backend/cities/` must pass through it before it can serve real customers.

The canonical roster of active cities is `data/city_research/triple_layer_roster.json`.

---

## The four layers at a glance

| Layer                                    | Artifact                                                                  | What it is                                                                                                                                                                                                                                                                                                                                                                      |
| ---------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- | ----------- |
| **1 — Operational**                      | `backend/cities/<city_id>.json`                                           | The product record. Schema 4.3.0. This is what the checkout gate, letter generator, and registry all read.                                                                                                                                                                                                                                                                      |
| **2 — Provenance**                       | `research_provenance` key inside the city JSON                            | Per-field source notes. Every value explains where it came from (`official_city_gov`, `web_search_unverified`, `inferred`, …). `_internal.po_box_drift` is a pipeline-written signal.                                                                                                                                                                                           |
| **2b — Provenance companion (optional)** | `backend/cities/<city_id>.provenance.json` (same for `cities_generated/`) | **Sidecar file** with the same nested shape as the operational JSON; each leaf is a FieldProvenance record (`tier`, `sources`, notes). For OpenClaw / humans who want a clean file boundary. **Not read by checkout or the letter generator** unless you add an explicit merge. See `backend/CITY_PROVENANCE_COMPANION.md` and `scripts/scaffold_city_provenance_companion.py`. |
| **3 — QA Digest**                        | `research_qa_review` key inside the city JSON                             | Human-readable compilation of Layer 2. Not a second opinion — a sorted mirror for quick skimming.                                                                                                                                                                                                                                                                               |
| **3.5 — Compute Gate**                   | `backend/cities_generated/<city_id>.triple_layer_compute.json`            | Deterministic code-only check. Finds P.O. Box conflicts, mail completeness gaps, drift flags. Decides if Layer 3.75 is needed. **Never calls MiniMax.**                                                                                                                                                                                                                         |
| **3.75 — Drift Resolution**              | `backend/cities_generated/<city_id>.triple_layer_drift_resolution.json`   | Optional MiniMax web-search call. Only fires when compute gate sets `eligible_for_minimax_drift_resolution: true`. Returns `action: patch                                                                                                                                                                                                                                       | replace | no_change`. |
| **4 — Meta-Analysis**                    | `backend/cities_generated/<city_id>.triple_layer_analysis.json`           | Agent-facing report: heuristic findings + rubric excerpt + empty slots for your review notes. Read this first when auditing a city.                                                                                                                                                                                                                                             |

---

## City rosters — know which list you're working from

| Roster                   | File                                            | Size       | Use when                                         |
| ------------------------ | ----------------------------------------------- | ---------- | ------------------------------------------------ |
| **Triple-layer active**  | `data/city_research/triple_layer_roster.json`   | 12 cities  | Auditing / agent loop on fully-researched cities |
| **Master (Census 2020)** | `data/cities/master.json`                       | 341 cities | Expanding coverage — every US city ≥ 100k pop    |
| **Legacy embedded**      | `_RAW_CITY_LINES` in `batch_research_cities.py` | ~96 cities | Fallback only; master.json supersedes it         |

`batch_research_cities.py` uses `--source auto` by default: if `master.json` exists it reads all 341 cities, otherwise falls back to the embedded 96. Since `master.json` is committed, **you always get 341 cities by default**.

---

## The research commands

All commands run from `backend/`. The `PYTHONPATH=src` prefix is required.

### Research a single city (full 5-step MiniMax pipeline)

```bash
cd backend
PYTHONPATH=src python src/services/this.py "Dallas, TX" \
  --city-id us-tx-dallas \
  -o cities_generated/us-tx-dallas.json
```

### Research + compute gate + drift resolution in one shot

```bash
PYTHONPATH=src python src/services/this.py "Dallas, TX" \
  --city-id us-tx-dallas \
  -o cities_generated/us-tx-dallas.json \
  --drift-resolve
```

### Batch — full triple-layer QA across all 341 cities (two-phase workflow)

**Phase 1 — research + compute gate + drift resolution:**

```bash
# Recommended: full triple-layer per city, skip already-researched ones
python scripts/batch_research_cities.py --drift-resolve --skip-existing --job-delay 2

# Specific slice (e.g. cities 1–50):
python scripts/batch_research_cities.py --drift-resolve --start 0 --limit 50

# Dry-run to preview commands:
python scripts/batch_research_cities.py --drift-resolve --dry-run --limit 5
```

**Phase 2 — build analysis JSONs for all cities in `cities_generated/`:**

```bash
# Uses the triple_layer_roster (12 cities) by default — extend --count for more
PYTHONPATH=src python scripts/agent_triple_layer_loop.py --skip-research --count 12
```

> Note: `agent_triple_layer_loop.py` reads from `triple_layer_roster.json`. To run analysis
> on all 341 batch-researched cities, either expand the roster or run analysis directly
> against all files in `cities_generated/`.

### Run the agent loop (random sample, research + analysis JSONs)

```bash
# Dry-run first to see what would be picked
PYTHONPATH=src python scripts/agent_triple_layer_loop.py --count 3 --seed 42 --dry-run

# Live run with drift resolution
PYTHONPATH=src python scripts/agent_triple_layer_loop.py --count 3 --seed 42 --drift-resolve

# Analysis only — skip research, rebuild analysis JSONs from existing city files
PYTHONPATH=src python scripts/agent_triple_layer_loop.py --count 12 --skip-research
```

### Deterministic repairs only (cities_generated batch)

```bash
# Normalize jurisdiction, mail.city/ZIP/country, local_rules sentinels, timezone — no LLM
PYTHONPATH=src python scripts/apply_repairs_cities_generated.py
```

### Targeted drift patch (no re-research)

```bash
# Use when city JSON already exists and you only want to run compute gate + drift step
PYTHONPATH=src python scripts/_patch_drift.py us-ca-san_jose us-pa-philadelphia
```

### Normalize / validate existing JSON (schema check only)

```bash
PYTHONPATH=src python src/services/this.py --check          # checks all cities/ JSONs
PYTHONPATH=src python src/services/this.py -i cities/us-tx-dallas.json -o /tmp/out.json  # normalize one
```

---

## Serviceability (terminal gating — agent stop/go)

Every **`*.triple_layer_compute.json`** includes a deterministic **`serviceability`** block (no LLM). Only three verdicts:

| Verdict                 | Meaning                                                                                                                                                                                                                                                                                                      |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`ready_to_service`**  | Terminal **green**: at least one viable path (complete mail **or** `https` online appeal URL), and no remaining blocking issues after compute rules (including pay+contest / PO drift codes). Safe to treat as “done for this snapshot”; no need to re-research unless sources change.                       |
| **`cannot_service`**    | Terminal **no**: `research_pipeline_failure` present, **or** neither mail nor online URL — conclusive “we don’t have a path from this artifact.”                                                                                                                                                             |
| **`needs_system_work`** | **Not shippable** — blocking issues, narrative/structured conflicts, or warnings the gate treats as promotion stoppers. **Do not** bulk-re-run cities that already show `ready_to_service` or `cannot_service`; instead **extend code, prompts, or drift rules** until new cities land in a terminal bucket. |

After research, `this.py` **always** writes a fresh compute sidecar (and **rebuilds** it after `--drift-resolve` so it matches the final city JSON). Optional: `--require-serviceability-ready` exits with code **2** unless the verdict is `ready_to_service` (useful for CI or strict batch gates).

### Export gate (promotion — stricter than serviceability alone)

The same compute JSON includes **`export_gate`**, driven only by code:

- **`export_allowed: true`** only if `serviceability.verdict` is `ready_to_service`, narrative **does not** hit pay+contest / multi-stage mail risk, and **`research_model_confidence`** on the **city** JSON meets floors (default **0.85** for `overall_0_1`; **`mail_address_0_1`** required only when there is a complete mail path — online-only skips mail score).
- Otherwise **`export_allowed: false`** with **`blocked_reasons`** and a plain‑English **`summary`**.

Batch promoters should copy into canonical `cities/` **only** when `export_gate.export_allowed` is true — no need to re-research cities that already have a terminal **`cannot_service`** / blocked export snapshot. Optional: `--require-export-pass` exits **3** when export is blocked.

The Layer 4 file **`*.triple_layer_analysis.json`** mirrors **`export_gate`** so operators see “why cannot promote” next to heuristics.

---

## How to read a city's health status

After running `--skip-research`, the analysis JSON tells you everything. Load it:

```
backend/cities_generated/<city_id>.triple_layer_analysis.json
```

Key fields to check in `heuristic_findings`:

| Field                                                     | Healthy value                | Action if unhealthy                                                                                                                              |
| --------------------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `research_pipeline_failure`                               | `false`                      | Re-run research. Check `research_qa_review` for stage that failed.                                                                               |
| `internal_provenance_keys`                                | `[]` (empty)                 | Any `_internal.po_box_drift` entry = conflicting PO boxes. Run `_patch_drift.py`.                                                                |
| `mail_narrative_crosscheck.narrative_structured_mismatch` | `false`                      | Structured mail and narrative text disagree. Run drift resolution or manually verify the address.                                                |
| `mail_narrative_crosscheck.structured_po_boxes`           | One value, matching expected | Multiple values = real conflict.                                                                                                                 |
| `provenance_key_count`                                    | > 0                          | Zero means city JSON was not researched through triple-layer (manually curated). Acceptable if `verification_metadata.confidence_score >= 0.80`. |

---

## Quick health sweep (run this to grade all 12 cities at once)

```python
# Run from backend/
import json, pathlib
PYTHONPATH = "src"  # set before running

results = []
for f in sorted(pathlib.Path("cities_generated").glob("*.triple_layer_analysis.json")):
    a = json.loads(f.read_text())
    h = a.get("heuristic_findings", {})
    mc = h.get("mail_narrative_crosscheck", {})
    drift = bool(h.get("internal_provenance_keys"))
    mismatch = mc.get("narrative_structured_mismatch", False)
    ok = not h.get("research_pipeline_failure") and not mismatch and not drift
    print(
        f"{'OK  ' if ok else 'WARN'}  {a['city_id']:<30}  "
        f"drift={str(drift):<5}  mismatch={str(mismatch):<5}  "
        f"prov={h.get('provenance_key_count', 0):>3}"
    )
```

Expected output for a fully clean roster: all `OK`.

---

## Decision rules for WARN cities

### `drift=True` (P.O. Box conflict in provenance)

1. Run `_patch_drift.py <city_id>`.
2. Read the resulting `.triple_layer_drift_resolution.json`:
   - `action: patch` → conflict resolved, city JSON has been updated. Re-run health sweep.
   - `action: no_change` → MiniMax couldn't resolve. **Escalate to human**: paste both P.O. Box numbers in Telegram with a link to the official city parking page and ask which is the dispute intake address.
3. After patching, rebuild analysis JSON: `agent_triple_layer_loop.py --skip-research --count 12`.

### `mismatch=True` without `drift=True`

- The structured mail address is clean but narrative text in `evidence_summary` or `notes` references a different address.
- Manually verify the structured address at the official city URL.
- If correct, you can clear the flag by updating `research_provenance["_internal.po_box_drift"]` to `null` and recompiling the QA digest.

### `research_pipeline_failure=True`

- The 5-step MiniMax pipeline hit an unrecoverable error at one of the stages.
- Check `research_qa_review.report` for the failing stage name.
- Re-run the full research: `this.py "<Research Label>" --city-id <city_id> -o cities_generated/<city_id>.json`.
- If it fails twice, drop the city from the roster until investigated.

### Confidence score below 0.70

- `verification_metadata.confidence_score` or `research_model_confidence.overall_0_1` below 0.70.
- Re-run research. The pipeline allows 3 implicit retries via MiniMax. If still below 0.70 after a fresh run, the city lacks authoritative online sources — mark `status: beta` in the city JSON until a human manually verifies.

---

## Promoting a city from cities_generated/ to cities/

After a successful research run and a clean health sweep, promote the city to the canonical registry:

```bash
# Copy (overwrites if exists)
python3 -c "import shutil; shutil.copy('backend/cities_generated/us-tx-dallas.json', 'backend/cities/us-tx-dallas.json'); print('done')"
```

Then verify it passes the serviceability gate:

```bash
cd backend
PYTHONPATH=src python -c "
from services.city_registry import CityRegistry, compute_city_serviceability
import pathlib
reg = CityRegistry(pathlib.Path('cities'))
reg.load_cities()
cfg = reg.get_city_config('us-tx-dallas')
rep = compute_city_serviceability(cfg)
print('ok:', rep.ok, 'errors:', rep.errors, 'warns:', rep.warnings)
"
```

If `ok: True` → run tests (`python -m pytest -q`) → commit.

---

## Adding a new city to the roster

1. Find the city in `data/cities/master.json` (Census 2020, pop ≥ 100k) to get exact `cityId` and name.
2. Research it with full triple-layer QA:
   ```bash
   cd backend
   PYTHONPATH=src python src/services/this.py "Columbus, OH" \
     --city-id us-oh-columbus \
     -o cities_generated/us-oh-columbus.json \
     --drift-resolve
   ```
3. Build its analysis JSON:
   ```bash
   # Temporarily add it to the roster, then:
   PYTHONPATH=src python scripts/agent_triple_layer_loop.py --skip-research --count 13
   ```
4. Run health sweep (see "Quick health sweep" above). Address any WARN before promoting.
5. Promote to `cities/`:
   ```bash
   python3 -c "import shutil; shutil.copy('backend/cities_generated/us-oh-columbus.json', 'backend/cities/us-oh-columbus.json')"
   ```
6. Verify serviceability gate passes (see "Promoting a city" section).
7. Add the city to `data/city_research/triple_layer_roster.json`.
8. Run `python -m pytest -q` from `backend/`. All tests must pass.
9. Commit.

---

## What sidecars live where

| File                                           | Location                                               | In git?                         |
| ---------------------------------------------- | ------------------------------------------------------ | ------------------------------- |
| `<city_id>.json` (canonical)                   | `backend/cities/`                                      | ✅ Yes                          |
| `<city_id>.json` (working copy)                | `backend/cities_generated/`                            | ❌ No (gitignored via .gitkeep) |
| `<city_id>.triple_layer_analysis.json`         | `backend/cities_generated/`                            | ❌ No                           |
| `<city_id>.triple_layer_compute.json`          | `backend/cities_generated/`                            | ❌ No                           |
| `<city_id>.triple_layer_drift_resolution.json` | `backend/cities_generated/`                            | ❌ No                           |
| Roster                                         | `data/city_research/triple_layer_roster.json`          | ✅ Yes                          |
| Rubric                                         | `data/city_research/triple_layer_analysis_rubric.json` | ✅ Yes                          |

**Never write sidecar files into `backend/cities/`.** That directory is the production registry source — the CityRegistry loads every `*.json` in it.

---

## Known open items (as of last audit)

| City                 | Issue                                                                 | Status                                                      |
| -------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------- |
| `us-ca-san_jose`     | Two P.O. Box numbers (7019 and 730209) — MiniMax returned `no_change` | Needs human verification of which box is the dispute intake |
| `us-tx-dallas`       | `appeal_deadline_days: 31` (above 30-day comfort threshold)           | Soft warning only; within 7–45 allowed range                |
| `us-tx-fort_worth`   | Same 31-day deadline warning                                          | Same                                                        |
| All SF adapter tests | Skipped — SF removed from roster                                      | Re-enable after SF goes through triple-layer pipeline       |

---

## File map (quick reference)

```
backend/
  cities/                         ← canonical registry (git-tracked)
  cities_generated/               ← pipeline output, sidecars (not tracked)
  scripts/
    agent_triple_layer_loop.py    ← the main agent loop
    _patch_drift.py               ← targeted drift-only fix
    batch_research_cities.py      ← bulk research runner
  src/services/
    this.py                       ← CLI entrypoint (research + normalize)
    city_research_minimax.py      ← MiniMax 5-step research + drift_resolution step
    city_research_compute_gate.py ← deterministic Layer 3.5
    city_research_analysis.py     ← Layer 4 meta-analysis builder
    city_registry.py              ← production registry + serviceability gate

data/city_research/
  triple_layer_roster.json        ← canonical 12-city list
  triple_layer_analysis_rubric.json ← agent review instructions per layer
```
