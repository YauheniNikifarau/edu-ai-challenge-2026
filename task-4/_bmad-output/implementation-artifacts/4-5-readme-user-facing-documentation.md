---
story_id: "4.5"
story_key: "4-5-readme-user-facing-documentation"
epic: "Epic 4: Bottleneck Analysis, Validation & Project Delivery"
title: "`README.md` — User-Facing Documentation"
status: "review"
created: "2026-05-21"
dependencies: ["1.2", "1.4", "2.1", "2.2", "2.3", "3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "4.1", "4.2", "4.3", "4.4"]
---

# Story 4.5: `README.md` — User-Facing Documentation

## User Story

**As a** new user (or grader),
**I want** a single README that tells me everything I need to install, configure, run, connect to, and understand this server,
**So that** I can be productive in under five minutes.

## Business Context

This story delivers the public-facing documentation for the entire project. It is the first artifact a grader, contributor, or MCP client developer will read. Accuracy is critical: any drift between the README and the actual code (`config.py` for env vars, `server.py` for tool/resource registration) is a defect.

This is a pure content-creation story. **No source code changes are required.** The deliverable is `task-4/README.md` (the file does not yet exist).

## Acceptance Criteria

**Given** the project is feature-complete (Epics 1–3 done, Stories 4.1–4.4 done)
**When** I read `task-4/README.md`
**Then** it includes the following nine sections **in order**:

1. **What this is** — 1-paragraph overview of the ATC MCP server
2. **Install / build steps** — `pip install -e .[dev]`
3. **Full environment variable reference** — every `ATC_*` var with type, units, example value, and validation rules
4. **Run instructions** — `python -m atc_mcp`
5. **How to connect an MCP-compatible client** — concrete Claude Desktop or `mcp` CLI example
6. **Full tool catalog** — all 5 tools, each with one-line description, input schema summary, output shape summary
7. **Full resource catalog** — all 3 resources, each with one-line description and payload shape summary
8. **How to run the tests** — `pytest -q`
9. **Explicit non-features** — from `spec.md §11`

**And** every env var in §3 matches exactly what `config.py` reads (verify against source: `src/atc_mcp/config.py`)
**And** every tool in §6 matches exactly what `server.py` registers (verify: `mcp.add_tool(...)` calls in `src/atc_mcp/server.py`)
**And** every resource in §7 matches exactly what `server.py` registers (verify: `mcp.resource(...)` calls in `src/atc_mcp/server.py`)
**And** a quick manual cross-check confirms the README is sufficient to onboard without reading source code

## Tasks / Subtasks

- [x] Create `task-4/README.md` (AC: all)
  - [x] Write §1 — What this is (1 paragraph, no marketing fluff)
  - [x] Write §2 — Install / build (pip command, Python version requirement, venv recommendation)
  - [x] Write §3 — Full env var reference (all 11 `ATC_*` vars, sourced from `config.py`)
  - [x] Write §4 — Run instructions (`python -m atc_mcp`, stderr on config failure)
  - [x] Write §5 — MCP client connection (Claude Desktop JSON snippet with all env vars pre-filled)
  - [x] Write §6 — Tool catalog (all 5 tools; input + output shapes from architecture)
  - [x] Write §7 — Resource catalog (all 3 resources; URI + payload shape from architecture)
  - [x] Write §8 — Testing (`pytest -q` from `task-4/`)
  - [x] Write §9 — Non-features list (verbatim from `spec.md §11`)
- [x] Cross-check §3 against `src/atc_mcp/config.py` — no env var omitted or added (AC: drift)
- [x] Cross-check §6 against `src/atc_mcp/server.py` `mcp.add_tool(...)` calls (AC: drift)
- [x] Cross-check §7 against `src/atc_mcp/server.py` `mcp.resource(...)` calls (AC: drift)

## Dev Notes

### Critical: No Code Changes — Documentation Only

This story creates one file: `task-4/README.md`. Do **not** modify any `.py` file. If you discover drift between the README content below and the actual code, fix the README content to match the code, then note it here.

### File to Create

**CREATE:** `task-4/README.md` (i.e., at the project root, alongside `pyproject.toml`)

Verify it does not already exist before creating.

---

### §3 — Environment Variable Reference (exact, sourced from `src/atc_mcp/config.py`)

All 11 variables are **required**. There are no defaults. The server exits with code 1 on any misconfiguration, printing a single stderr line:

```
CONFIG ERROR: <ENV_VAR_NAME> is invalid: <reason>
```

| Variable | Type | Unit | Accepted Range | Example |
|---|---|---|---|---|
| `ATC_RUNWAYS` | JSON array | — | Non-empty; each entry `{"id": str, "length_m": int ≥ 1}`; ids must be unique | `[{"id":"R1","length_m":3500},{"id":"R2","length_m":3000}]` |
| `ATC_GATE_COUNT` | int | count | ≥ 1 | `4` |
| `ATC_GROUND_CREW_COUNT` | int | count | ≥ 1 | `3` |
| `ATC_RUNWAY_SEP_TAKEOFF_SEC` | int | seconds | ≥ 0 | `60` |
| `ATC_RUNWAY_SEP_LANDING_SEC` | int | seconds | ≥ 0 | `90` |
| `ATC_RUNWAY_SEP_MIXED_SEC` | int | seconds | ≥ 0 | `120` |
| `ATC_GATE_TURNAROUND_SEC` | int | seconds | ≥ 0 | `900` |
| `ATC_DEPENDENCY_BUFFER_SEC` | int | seconds | ≥ 0 | `600` |
| `ATC_SCHEDULING_HORIZON_SEC` | int | seconds | ≥ 1 | `86400` |
| `ATC_DURATION_ARRIVAL_SEC` | int | seconds | ≥ 1 | `1200` |
| `ATC_DURATION_DEPARTURE_SEC` | int | seconds | ≥ 1 | `1200` |

> **Runway count** is derived from `len(ATC_RUNWAYS)` — there is no separate runway-count variable.

**Validation failure shapes (representative — include in README):**
- Missing: `CONFIG ERROR: ATC_GATE_COUNT is invalid: variable not set`
- Non-integer: `CONFIG ERROR: ATC_GATE_COUNT is invalid: expected integer, got "three"`
- Out of range: `CONFIG ERROR: ATC_GATE_COUNT is invalid: must be >= 1, got 0`
- Malformed JSON: `CONFIG ERROR: ATC_RUNWAYS is invalid: not valid JSON: <parser-message>`
- Empty array: `CONFIG ERROR: ATC_RUNWAYS is invalid: must contain at least one runway`
- Duplicate id: `CONFIG ERROR: ATC_RUNWAYS is invalid: duplicate runway id "R1"`

---

### §5 — MCP Client Connection (Claude Desktop example)

The server uses **stdio transport** exclusively. MCP clients launch it as a subprocess. Provide this exact Claude Desktop snippet in the README:

```json
{
  "mcpServers": {
    "atc-mcp": {
      "command": "python",
      "args": ["-m", "atc_mcp"],
      "env": {
        "ATC_RUNWAYS": "[{\"id\":\"R1\",\"length_m\":3500},{\"id\":\"R2\",\"length_m\":3000}]",
        "ATC_GATE_COUNT": "4",
        "ATC_GROUND_CREW_COUNT": "3",
        "ATC_RUNWAY_SEP_TAKEOFF_SEC": "60",
        "ATC_RUNWAY_SEP_LANDING_SEC": "90",
        "ATC_RUNWAY_SEP_MIXED_SEC": "120",
        "ATC_GATE_TURNAROUND_SEC": "900",
        "ATC_DEPENDENCY_BUFFER_SEC": "600",
        "ATC_SCHEDULING_HORIZON_SEC": "86400",
        "ATC_DURATION_ARRIVAL_SEC": "1200",
        "ATC_DURATION_DEPARTURE_SEC": "1200"
      }
    }
  }
}
```

> Place this block in `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the platform equivalent. Adjust `"command"` to the full path of your venv's Python if needed (e.g., `"/path/to/.venv/bin/python"`).

Also mention the `mcp` SDK dev/inspect mode:

```bash
# Inspect tools and resources interactively (requires `mcp` CLI, installed via `pip install mcp[cli]`)
ATC_RUNWAYS='[{"id":"R1","length_m":3500}]' ATC_GATE_COUNT=4 ... mcp dev python -m atc_mcp
```

---

### §6 — Tool Catalog (sourced from `src/atc_mcp/server.py` + `src/atc_mcp/tools.py` + architecture)

Registered via `mcp.add_tool(...)` in `server.py`. Exactly 5 tools — verify count matches source.

#### `submit_flight`
- **Purpose:** Register a new flight (arrival or departure) in the queue.
- **Input schema:**
  ```json
  {
    "flight_number": "AA123",
    "operation_type": "arrival | departure",
    "priority": "high | medium | low",
    "dependencies": ["AA001"],
    "runway_requirements": {"min_length_m": 3500}
  }
  ```
  - `dependencies` defaults to `[]`; `runway_requirements` is optional.
  - Input is validated with `extra="forbid"` — unknown fields are rejected.
- **Output:** `{"flight": {<Flight object>}}` on success; `{"error": "..."}` on duplicate, unknown dependency, or self-dependency.

#### `cancel_flight`
- **Purpose:** Cancel a flight and re-evaluate any dependents.
- **Input schema:** `{"flight_number": "AA123"}`
- **Output:**
  ```json
  {
    "cancelled": "AA123",
    "dependents_reevaluated": [
      {"flight_number": "AA456", "previous_state": "scheduled", "new_state": "unschedulable", "reason": "dependency AA123 is not scheduled"}
    ]
  }
  ```
  Errors: `"flight AA123 is already cancelled"` / `"flight AA123 does not exist"`.

#### `generate_schedule`
- **Purpose:** Replace the current schedule with a freshly computed deterministic one.
- **Input schema:** `{}` (no parameters)
- **Output:**
  ```json
  {
    "schedule": [{"flight_number": "AA123", "operation_type": "arrival", "runway_id": "R1", "gate_id": "G1", "start_sec": 0, "end_sec": 1200}],
    "unscheduled": [{"flight_number": "AA999", "reason": "no runway meets minimum length 4500m (available runways: R1 3500m, R2 3000m)"}],
    "completion_time_seconds": 1200,
    "summary": {"scheduled_count": 1, "unscheduled_count": 1, "cancelled_count": 0}
  }
  ```

#### `get_airport_status`
- **Purpose:** Return a structured operational snapshot of the airport.
- **Input schema:** `{}` (no parameters)
- **Output:**
  ```json
  {
    "flight_counts": {"by_state": {"queued": 1, "scheduled": 4, "unschedulable": 1, "cancelled": 0}, "by_operation_type": {"arrival": 3, "departure": 3}},
    "runways": [{"id": "R1", "length_m": 3500, "capacity_sec": 86400, "usage_sec": 2400, "usage_pct": 2.78}],
    "gates": {"capacity": 4, "in_use_peak": 2, "in_use_at_completion": 0},
    "ground_crew": {"capacity": 3, "in_use_peak": 2, "in_use_at_completion": 0},
    "resource_constraints": [],
    "unscheduled": [{"flight_number": "AA999", "reason": "..."}],
    "completion_time_seconds": 1200
  }
  ```

#### `analyze_bottleneck`
- **Purpose:** Identify the longest active scheduled dependency chain (critical path).
- **Input schema:** `{}` (no parameters)
- **Output:**
  ```json
  {
    "chain": ["AA100", "AA200", "AA300"],
    "total_duration_seconds": 5400,
    "operation_durations": [1200, 1200, 1200],
    "dependency_buffers": [600, 600]
  }
  ```
  Empty case (no schedule or no dependency chains): `{"chain": [], "total_duration_seconds": null, "operation_durations": [], "dependency_buffers": []}`.

---

### §7 — Resource Catalog (sourced from `src/atc_mcp/server.py` + `src/atc_mcp/resources.py` + architecture)

Registered via `mcp.resource(...)` in `server.py`. Exactly 3 resources.

#### `atc://flights`
- **Purpose:** Full flight queue including queued, scheduled, unschedulable, and cancelled flights.
- **Payload:**
  ```json
  {
    "flights": [
      {"flight_number": "AA123", "operation_type": "arrival", "priority": "high", "dependencies": [], "runway_requirements": null, "state": "scheduled", "unscheduled_reason": null}
    ]
  }
  ```
  Sorted by `(state_rank, flight_number)` where `scheduled=0, queued=1, unschedulable=2, cancelled=3`.

#### `atc://runways`
- **Purpose:** Runway availability and usage for the latest schedule.
- **Payload:**
  ```json
  {
    "runways": [
      {"id": "R1", "length_m": 3500, "scheduled_operations": [{"flight_number": "AA123", "operation_type": "arrival", "start_sec": 0, "end_sec": 1200}], "busy_intervals_sec": [[0, 1200]], "next_free_sec": 1200}
    ]
  }
  ```
  Sorted by `id` lex.

#### `atc://timeline`
- **Purpose:** Chronological timeline of all scheduled operations.
- **Payload:**
  ```json
  {
    "events": [
      {"start_sec": 0, "end_sec": 1200, "flight_number": "AA123", "operation_type": "arrival", "runway_id": "R1", "gate_id": "G1", "depends_on": []}
    ]
  }
  ```
  Sorted by `(start_sec, runway_id, flight_number)`.

---

### §9 — Non-Features (verbatim from `spec.md §11`)

Include exactly this list in the README under a "What this server does NOT do" heading:

- No authentication, authorization, or multi-tenant isolation
- No persistence across restarts (full state reset on server exit)
- No audit logs, metrics dashboards, or monitoring
- No web UI, CLI client, or visualization
- No aircraft physics, weather modeling, or radar simulation
- No quantitative SLAs or performance guarantees
- No internationalization or accessibility (no human-facing UI)
- No external integrations beyond the MCP stdio interface

---

### Project Structure Notes

- **Output path:** `task-4/README.md` — at the same level as `pyproject.toml`. Do not put it inside `src/` or `docs/`.
- **Python requirement:** Python 3.11+ (from `pyproject.toml`: `requires-python = ">=3.11"`).
- **Install command:** `pip install -e .[dev]` (installs `mcp`, `pydantic>=2`, `pytest>=8`, `ruff`).
- **Entrypoint:** `python -m atc_mcp` (via `src/atc_mcp/__main__.py` → `atc_mcp.server.main()`). Also valid: `python -m atc_mcp.server`. No `[project.scripts]` entry is defined in `pyproject.toml`, so there is no short-form CLI alias.
- **Transport:** stdio only. The server writes **nothing** to stdout except JSON-RPC frames. All startup errors go to stderr.

### JSON Conventions (apply throughout README examples)

These are from architecture.md §Format Patterns — README code examples must follow them:
- Field names: `snake_case`
- Time values: integer seconds with `_sec` suffix
- `null` for "not yet computed" / "not applicable"; `[]` for "computed and empty"
- Enum literals: `"arrival"/"departure"`, `"high"/"medium"/"low"`, `"queued"/"scheduled"/"unschedulable"/"cancelled"`

### References

- Env vars: [Source: `src/atc_mcp/config.py`] — `load_config()` function and `Config` model
- Tool registration: [Source: `src/atc_mcp/server.py`] — `create_app()` function
- Tool input/output shapes: [Source: `_bmad-output/planning-artifacts/architecture.md` §MCP Tool Catalog]
- Resource shapes: [Source: `_bmad-output/planning-artifacts/architecture.md` §MCP Resource Catalog]
- Non-features: [Source: `_bmad-output/planning-artifacts/epics.md` §Explicit non-requirements]
- Run/install: [Source: `_bmad-output/planning-artifacts/architecture.md` §Initialization Steps]

## Dev Agent Record

### Agent Model Used

Claude 3.7 Sonnet (via Windsurf Cascade)

### Debug Log References

N/A - Documentation-only story, no code changes

### Completion Notes List

- ✅ Created comprehensive `README.md` with all 9 required sections
- ✅ Verified all 11 environment variables match `src/atc_mcp/config.py` exactly
- ✅ Verified all 5 tools match `src/atc_mcp/server.py` registrations
- ✅ Verified all 3 resources match `src/atc_mcp/server.py` registrations
- ✅ Included validation error examples from config.py implementation
- ✅ Provided Claude Desktop configuration snippet with all env vars
- ✅ Documented MCP CLI dev mode usage
- ✅ Listed all non-features from spec.md §11
- ✅ No code drift detected - README accurately reflects implementation

### File List

- `README.md` — created

## Change Log

- **2026-05-21**: Created comprehensive `README.md` with all 9 required sections (§1-§9). Verified accuracy against source files: all 11 env vars match `config.py`, all 5 tools match `server.py` registrations, all 3 resources match `server.py` registrations. No code drift detected.
