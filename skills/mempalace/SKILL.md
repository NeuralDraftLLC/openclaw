---
name: mempalace
description: "Default long-term memory: MemPalace MCP (ChromaDB + palace at ~/.mempalace/palace). Use mempalace__* for recall, filing, and KG — before relying on workspace MEMORY.md or embedding search alone."
version: "1.1.0"
triggers:
  - "what did we talk about"
  - "what did we decide"
  - "last week"
  - "last month"
  - "remember that"
  - "have we discussed"
  - "recall"
  - "search memory"
  - "long-term memory"
user-invocable: true
metadata:
  openclaw:
    emoji: "🧠"
    requires:
      bins: ["python3"]
---

# MemPalace — Default long-term memory

## Memory model (read this first)

| Layer                             | Role                                                                                                                                                                                 |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **MemPalace (this skill)**        | **Canonical** cross-channel, durable memory: verbatim snippets, drawers, knowledge graph, diary. Use MCP tools first for “what did we say / decide / file?”                          |
| Workspace `MEMORY.md` + `memory/` | Working notes and daily logs; pre-compaction hook **mines** `memory/` into the palace automatically.                                                                                 |
| OpenClaw `memorySearch` (Ollama)  | **Optional fuzzy** recall over indexed workspace/session text — helpful for same-repo grep-like semantic hits; it does **not** replace MemPalace for authoritative long-term recall. |

**Default behavior:** For anything that sounds like history, decisions, or “do we already know this?”, call **`mempalace__mempalace_status`** (light) and/or **`mempalace__mempalace_search`** before answering from guesswork.

OpenClaw exposes MCP tools as `mempalace__<toolName>` (server key `mempalace` in `openclaw.json`).

---

## Core tools (default workflow)

### `mempalace__mempalace_status`

**When:** After reading `SOUL.md` / `USER.md` / `MEMORY.md` in workspace, or at session start when recall might matter.

Confirms the palace exists and shows drawer/wing/room overview.

### `mempalace__mempalace_search`

**When:** User asks about past decisions, history, or exact phrasing across time or channels.

**Arguments:** `query` (required), `limit` (optional, default 5), `wing`, `room` (optional filters).

### `mempalace__mempalace_add_drawer`

**When:** A durable decision, policy, or quote should persist for months and be findable later.

**Arguments:** `wing`, `room`, `content` (required), `source_file`, `added_by` (optional).

---

## Taxonomy and graph

- `mempalace__mempalace_list_wings` / `mempalace__mempalace_list_rooms` / `mempalace__mempalace_get_taxonomy`
- **KG:** `mempalace__mempalace_kg_query`, `mempalace__mempalace_kg_add`, `mempalace__mempalace_kg_invalidate`, `mempalace__mempalace_kg_timeline`, `mempalace__mempalace_kg_stats`
- **Graph navigation:** `mempalace__mempalace_traverse`, `mempalace__mempalace_find_tunnels`, `mempalace__mempalace_graph_stats`

## Utilities

- `mempalace__mempalace_check_duplicate` — before filing near-duplicates
- `mempalace__mempalace_delete_drawer` — irreversible delete by `drawer_id`
- `mempalace__mempalace_get_aaak_spec` — AAAK format
- `mempalace__mempalace_diary_write` / `mempalace__mempalace_diary_read` — agent diary (AAAK)

## When NOT to use MemPalace

- Ephemeral chit-chat in the **current** turn that will not matter tomorrow.
- Channel or API operations — use the correct channel/MCP tool instead.

## Filing hygiene

Prefer `wing` ≈ project (`parkingbreaker`, `omega`, …) and `room` ≈ topic (`stripe`, `reddit-ads`, `ops`). File sparingly: decisions, policies, and quotes worth recalling months later.
