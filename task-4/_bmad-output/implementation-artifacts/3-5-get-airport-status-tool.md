---
story_id: "3.5"
story_key: "3-5-get-airport-status-tool"
epic: "Epic 3: Deterministic Scheduling Engine & Airport Operations"
title: "`get_airport_status` Tool"
status: "completed"
created: "2026-05-21"
completed: "2026-05-21"
dependencies: ["3.1", "3.2", "3.3", "3.4"]
---

# Story 3.5: `get_airport_status` Tool

## User Story

**As an** AI client,
**I want** a single tool call that returns a structured operational snapshot,
**So that** I can answer "what's the state of the airport right now?" in one round-trip.

## Business Context

This tool is the primary observability surface for AI clients. In one MCP call it delivers: flight counts by state and operation type; per-runway capacity and usage; gate and ground-crew utilisation; resource constraint indicators; unschedulable flights with reasons; and the schedule completion time.

The payload is a **pure projection** of current in-memory state — it never triggers a new schedule run. The work splits cleanly: `status.py` owns the domain-level computation (no MCP imports), `tools.py` wires it to the MCP surface.

## Acceptance Criteria (FR-TOOL-3)

**Given** Story 3.4 has wired `generate_schedule` and `AppState.latest_schedule` may be `null` or populated
**When** I invoke `get_airport_status` (no input args)
**Then** the response matches the architecture-pinned JSON shape:
```json
{
  "flight_counts": {
    "by_state": {"queued": 1, "scheduled": 4, "unschedulable": 1, "cancelled": 0},
    "by_operation_type": {"arrival": 3, "departure": 3}
  },
  "runways": [
    {"id": "R1", "length_m": 3500, "capacity_sec": 86400, "usage_sec": 2400, "usage_pct": 2.78}
  ],
  "gates": {"capacity": 4, "in_use_peak": 2, "in_use_at_completion": 0},
  "ground_crew": {"capacity": 3, "in_use_peak": 2, "in_use_at_completion": 0},
  "resource_constraints": [],
  "unscheduled": [
    {"flight_number": "AA999", "reason": "no runway meets minimum length 4500m (available runways: R1 3500m, R2 3000m)"}
  ],
  "completion_time_seconds": 1200
}
```
**And** `ground_crew.in_use_peak = 0` and `ground_crew.in_use_at_completion = 0` when no schedule exists
**And** `completion_time_seconds = null` when `AppState.latest_schedule is None`
**And** `unscheduled` is sorted by `flight_number` lex
**And** `runways` is sorted by `id` lex
**And** repeated calls with identical state return byte-identical payloads
**And** `tests/test_airport_status.py` covers: empty state; queue-only (no schedule); fully-scheduled; mixed with unschedulables; ground-crew peak math

## Tasks / Subtasks

- [ ] Implement `build_status(state: AppState, config: Config) -> dict` in `src/atc_mcp/status.py` (AC: full payload)
  - [ ] Count flights by state (`queued`, `scheduled`, `unschedulable`, `cancelled`)
  - [ ] Count flights by operation type (`arrival`, `departure`)
  - [ ] Build `runways` list from `config.runways` + placements; sort by `id` lex
  - [ ] Compute `gates` peak and at-completion from placements
  - [ ] Compute `ground_crew` peak and at-completion from placements using DD-10 interval model
  - [ ] Build `resource_constraints` strings for any resource at capacity
  - [ ] Build `unscheduled` list from flights with `state == unschedulable`; sort by `flight_number` lex
  - [ ] Set `completion_time_seconds` from `latest_schedule` (or `null`)
- [ ] Wire `get_airport_status()` in `src/atc_mcp/tools.py` to call `build_status(state, config)` (AC: tool returns payload)
  - [ ] Use whatever config-access pattern story 3.4 established (module-level `_config` or closure capture)
- [ ] Create `tests/test_airport_status.py` with all required test cases (AC: 5+ scenarios)

## Dev Notes

### Module dependency direction — enforced by `tests/test_imports.py`

```
status.py  ← imports domain only (NO mcp, NO os, NO time, NO datetime, NO random)
tools.py   ← imports domain, status
```

`status.py` receives `AppState` and `Config` as function parameters. It never reads `os.environ` and never imports `mcp`.

### Payload field computation

**`flight_counts`**
```python
by_state = {s.value: 0 for s in FlightState}
for f in state.flights.values():
    by_state[f.state.value] += 1

by_op = {"arrival": 0, "departure": 0}
for f in state.flights.values():
    by_op[f.operation_type.value] += 1
```

**`runways`** — built from `config.runways` (a `tuple[Runway, ...]` where each `Runway` has `.id: str` and `.length_m: int`):
- `capacity_sec` = `config.scheduling_horizon_sec`
- `usage_sec` = sum of `(p.end_sec - p.start_sec)` for all placements `p` where `p.runway_id == runway.id`
- `usage_pct` = `round(usage_sec / capacity_sec * 100, 2)` — use `0.0` when `capacity_sec == 0` or no schedule
- Sort output list by `runway.id` lex — determinism requirement from architecture §Ordering Patterns

**`gates`** — interval-overlap approach using all placements (each placement occupies one gate):
- `capacity` = `config.gate_count`
- `in_use_peak` = maximum number of placements `p` with overlapping `[p.start_sec, p.end_sec)` at any instant
- `in_use_at_completion` = count of placements `p` where `p.start_sec < completion_time_seconds <= p.end_sec`
  - When `completion_time_seconds is None` → `0`
- When no schedule → `{"capacity": config.gate_count, "in_use_peak": 0, "in_use_at_completion": 0}`

**`ground_crew`** — same interval-overlap approach (DD-10: one crew unit per operation):
- `capacity` = `config.ground_crew_count`
- `in_use_peak` and `in_use_at_completion` computed identically to `gates`
- When no schedule → `{"capacity": config.ground_crew_count, "in_use_peak": 0, "in_use_at_completion": 0}`

**Peak overlap algorithm** (O(n log n), deterministic):
```python
def _peak_concurrent(placements: Iterable[Placement]) -> int:
    events: list[tuple[int, int]] = []
    for p in placements:
        events.append((p.start_sec, +1))
        events.append((p.end_sec, -1))
    events.sort()          # stable; deterministic
    peak = current = 0
    for _, delta in events:
        current += delta
        if current > peak:
            peak = current
    return peak
```

**`resource_constraints`** — list of human-readable strings when a resource is at capacity at any point. No format is strictly pinned by the architecture; keep simple (e.g. `"ground_crew_at_capacity"`, `"gates_at_capacity"`). Return `[]` when no constraints are binding.

**`unscheduled`** — flights whose `state == FlightState.unschedulable`:
```python
unscheduled = sorted(
    [{"flight_number": f.flight_number, "reason": f.unscheduled_reason}
     for f in state.flights.values()
     if f.state == FlightState.unschedulable],
    key=lambda x: x["flight_number"],
)
```
`unscheduled_reason` is always a non-null string when state is `unschedulable` (see `domain/models.py` and reason-string format in architecture §Format Patterns: lowercase, no trailing period).

**`completion_time_seconds`**: `state.latest_schedule.completion_time_seconds if state.latest_schedule else None`

### Config access in `tools.py`

`get_airport_status()` needs `Config`. Story 3.4 establishes the config-access pattern for tools that require it. Use whichever pattern it establishes:

- **Pattern A (module-level setter, preferred):** `tools.py` holds `_config: Config | None = None`; `server.py` calls `tools.set_config(config)` after `load_config()` in `main()`.
- **Pattern B (closure):** `create_app(config)` in `server.py` wraps the tool as a closure capturing `config`.

If story 3.4 has not yet set the pattern, implement Pattern A:
```python
# tools.py
_config: Config | None = None

def set_config(c: "Config") -> None:
    global _config
    _config = c
```
```python
# server.py — in main(), before create_app():
tools.set_config(config)
```

### Critical constraints

- **Do NOT call `generate_schedule` inside `build_status`** — status is a read-only projection of existing state.
- **No `set` iteration for any output list** — use `sorted()` with explicit keys.
- **No time/random/datetime imports** in `status.py` — enforced by `tests/test_imports.py`.
- **`usage_pct` rounding**: use `round(..., 2)` to produce a float; the architecture example shows `2.78`.
- **Field name canonical authority is the architecture JSON** — the epics text uses `unscheduled_flights` and `current_schedule_completion_seconds` but the architecture pinned JSON uses `unscheduled` and `completion_time_seconds`. Use the architecture names.

### Current file states

**`src/atc_mcp/status.py`** — currently just:
```python
"""Airport and flight status query helpers (Story 2+)."""
```
Add `build_status(state: AppState, config: Config) -> dict` with required imports at the top.

**`src/atc_mcp/tools.py`** — `get_airport_status()` currently:
```python
def get_airport_status() -> dict:
    """Return structured airport operational status."""
    raise NotImplementedError("not yet implemented")
```
Replace with a call to `status.build_status(state, _config)`.

**Imports to add in `status.py`:**
```python
from atc_mcp.config import Config
from atc_mcp.domain.models import FlightState, Placement
from atc_mcp.domain.state import AppState
from atc_mcp.time_model import Seconds  # for type annotations if used
```

### Testing requirements

**File:** `tests/test_airport_status.py`
Test `build_status(state, config)` directly — no MCP bootstrap needed. Use `state.reset()` in teardown to prevent state pollution.

Load config via `load_config()` with `monkeypatch` + `VALID_ENV` from `conftest.py`:
```
R1: length_m=3500, R2: length_m=3000
gate_count=4, ground_crew_count=3
scheduling_horizon_sec=86400
duration_arrival_sec=1200, duration_departure_sec=1200
```

Required test cases:

1. **empty state** — `state.flights == {}`, `state.latest_schedule is None`:
   - all `by_state` counts are 0, all `by_op_type` counts are 0
   - `runways` has R1 and R2 (from config) with `usage_sec=0`, `usage_pct=0.0`, `capacity_sec=86400`
   - `gates` and `ground_crew` peak both 0
   - `completion_time_seconds is None`
   - `unscheduled == []`

2. **queue-only state (no schedule)** — flights submitted but `latest_schedule is None`:
   - `by_state["queued"]` matches flight count
   - runway `usage_sec` = 0 (no placements)
   - `completion_time_seconds is None`

3. **fully-scheduled state** — all flights placed in schedule:
   - `by_state["scheduled"]` equals total flight count
   - `completion_time_seconds` equals the last `end_sec` in placements
   - `usage_sec` is non-zero for runways that had operations

4. **mixed state with unschedulables** — some scheduled, one unschedulable with a reason:
   - `unscheduled` list contains the unschedulable flight with its reason
   - `unscheduled` is sorted by `flight_number` lex
   - `flight_counts.by_state` reflects the mix correctly

5. **ground-crew peak math** — construct a `Schedule` with 2 overlapping placements (same gate and runway window):
   - `ground_crew.in_use_peak == 2` (the known overlap count)
   - `ground_crew.in_use_at_completion` matches the count at `completion_time_seconds`

6. **determinism property test** (mandatory per NFR-3):
   ```python
   import json
   results = {
       json.dumps(build_status(state, config), sort_keys=True, separators=(",", ":"))
       for _ in range(100)
   }
   assert len(results) == 1
   ```

### Project Structure Notes

Files to touch:
| Action | File | Change |
|--------|------|--------|
| UPDATE | `src/atc_mcp/status.py` | Add `build_status()` implementation |
| UPDATE | `src/atc_mcp/tools.py` | Replace `get_airport_status()` stub; add config access |
| UPDATE | `src/atc_mcp/server.py` | If Pattern A: add `tools.set_config(config)` in `main()` |
| CREATE | `tests/test_airport_status.py` | 6 test functions |

Architecture enforces `status.py` lives at `src/atc_mcp/status.py` (not inside `domain/` or `scheduler/`) — it is a projection layer, not a pure domain type.

### References

- [Source: `_bmad-output/planning-artifacts/architecture.md` §MCP Tool Catalog — `get_airport_status` JSON shape]
- [Source: `_bmad-output/planning-artifacts/architecture.md` §Ground Crew Scheduling Semantics (DD-10) — interval model]
- [Source: `_bmad-output/planning-artifacts/architecture.md` §Ordering Patterns — sort before emit, no set iteration]
- [Source: `_bmad-output/planning-artifacts/architecture.md` §Structure Patterns — module dependency direction]
- [Source: `_bmad-output/planning-artifacts/architecture.md` §Format Patterns — reason string format, null vs []]
- [Source: `_bmad-output/planning-artifacts/epics.md` Epic 3, Story 3.5]
- [Source: `src/atc_mcp/domain/models.py` — `FlightState`, `OperationType`, `Schedule`, `Placement`]
- [Source: `src/atc_mcp/domain/state.py` — `AppState` with `flights` and `latest_schedule`]
- [Source: `src/atc_mcp/config.py` — `Config` with `runways: tuple[Runway, ...]`, `gate_count`, `ground_crew_count`, `scheduling_horizon_sec`]
- [Source: `tests/conftest.py` — `VALID_ENV` fixture dict for test config]
- [Source: `_bmad-output/implementation-artifacts/2-3-atc-flights-resource.md` — use `.model_dump()` not `.dict()`; always sort before emitting; avoid set iteration]

## Dev Agent Record

### Agent Model Used

cascade

### Debug Log References

None

### Completion Notes List

- Implemented `build_status()` in `src/atc_mcp/status.py` with all required fields
- Peak concurrent resource calculation using event-based O(n log n) algorithm
- Count-at-time calculation for resources at completion
- Updated `get_airport_status()` in `src/atc_mcp/tools.py` to call `build_status()`
- Created comprehensive test suite in `tests/test_airport_status.py` with 7 test cases:
  1. Empty state
  2. Queue-only (no schedule)
  3. Fully-scheduled state
  4. Mixed state with unschedulables
  5. Ground crew peak math with overlapping placements
  6. Determinism property (100 iterations)
  7. Resource constraints at capacity
- All 130 tests pass including 7 new tests
- Module dependency constraints met: status.py imports only domain models, no mcp/os/time/datetime/random
- Deterministic output verified with sorted lists and stable algorithms

### File List

- `src/atc_mcp/status.py` - Implemented `build_status()` function
- `src/atc_mcp/tools.py` - Updated `get_airport_status()` tool
- `tests/test_airport_status.py` - Created comprehensive test suite
