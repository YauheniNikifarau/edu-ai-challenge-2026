# ATC MCP Server

## What this is

An MCP (Model Context Protocol) server that provides air-traffic control scheduling assistance through a stdio-based interface. It manages flight queues, generates deterministic schedules respecting runway separation rules and resource constraints, and exposes operational insights via structured tools and resources. The server maintains an in-memory state model and exits with code 1 on any configuration error.

## Install / build steps

Requires Python 3.11 or later. We recommend using a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .[dev]
```

This installs the server in editable mode along with development dependencies (`pytest`, `ruff`).

## Full environment variable reference

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

**Validation failure examples:**
- Missing: `CONFIG ERROR: ATC_GATE_COUNT is invalid: variable not set`
- Non-integer: `CONFIG ERROR: ATC_GATE_COUNT is invalid: expected integer, got "three"`
- Out of range: `CONFIG ERROR: ATC_GATE_COUNT is invalid: must be >= 1, got 0`
- Malformed JSON: `CONFIG ERROR: ATC_RUNWAYS is invalid: not valid JSON: <parser-message>`
- Empty array: `CONFIG ERROR: ATC_RUNWAYS is invalid: must contain at least one runway`
- Duplicate id: `CONFIG ERROR: ATC_RUNWAYS is invalid: duplicate runway id "R1"`

## Run instructions

```bash
python -m atc_mcp
```

The server uses stdio transport exclusively and writes only JSON-RPC frames to stdout. All startup errors go to stderr. On configuration failure, the process exits with code 1.

## How to connect an MCP-compatible client

The server uses **stdio transport** exclusively. MCP clients launch it as a subprocess.

### Claude Desktop

Place this block in `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the platform equivalent:

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

> Adjust `"command"` to the full path of your venv's Python if needed (e.g., `"/path/to/.venv/bin/python"`).

### MCP CLI (dev/inspect mode)

```bash
# Inspect tools and resources interactively (requires `mcp` CLI, installed via `pip install mcp[cli]`)
ATC_RUNWAYS='[{"id":"R1","length_m":3500}]' ATC_GATE_COUNT=4 ATC_GROUND_CREW_COUNT=3 ATC_RUNWAY_SEP_TAKEOFF_SEC=60 ATC_RUNWAY_SEP_LANDING_SEC=90 ATC_RUNWAY_SEP_MIXED_SEC=120 ATC_GATE_TURNAROUND_SEC=900 ATC_DEPENDENCY_BUFFER_SEC=600 ATC_SCHEDULING_HORIZON_SEC=86400 ATC_DURATION_ARRIVAL_SEC=1200 ATC_DURATION_DEPARTURE_SEC=1200 mcp dev python -m atc_mcp
```

## Full tool catalog

### `submit_flight`
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

### `cancel_flight`
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

### `generate_schedule`
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

### `get_airport_status`
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

### `analyze_bottleneck`
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

## Full resource catalog

### `atc://flights`
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

### `atc://runways`
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

### `atc://timeline`
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

## How to run the tests

From the project root (`task-4/`):

```bash
pytest -q
```

This runs the full test suite in quiet mode. For verbose output, omit the `-q` flag.

## What this server does NOT do

- No authentication, authorization, or multi-tenant isolation
- No persistence across restarts (full state reset on server exit)
- No audit logs, metrics dashboards, or monitoring
- No web UI, CLI client, or visualization
- No aircraft physics, weather modeling, or radar simulation
- No quantitative SLAs or performance guarantees
- No internationalization or accessibility (no human-facing UI)
- No external integrations beyond the MCP stdio interface
