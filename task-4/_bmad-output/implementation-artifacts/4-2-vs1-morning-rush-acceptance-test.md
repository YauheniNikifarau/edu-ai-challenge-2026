---
story_id: "4.2"
story_key: "4-2-vs1-morning-rush-acceptance-test"
epic: "Epic 4: Bottleneck Analysis, Validation & Project Delivery"
title: "VS-1 Morning Rush Acceptance Test"
status: "ready-for-dev"
created: "2026-05-21"
dependencies: ["3.1", "3.2", "3.3", "3.4", "3.5"]
---

# Story 4.2: VS-1 Morning Rush Acceptance Test

## User Story

**As a** product stakeholder,
**I want** the end-to-end Morning Rush scenario from `spec.md §9` to pass automatically,
**So that** I have machine-checkable evidence the system handles mixed-priority arrivals/departures on a clean state.

## Business Context

VS-1 is one of three mandatory acceptance scenarios in `spec.md §9`. It validates the core scheduling capability: submitting a mixed set of flights across all priority levels onto a clean airport state, generating a schedule, and verifying that every schedulable flight is placed, no resources are double-booked, and priority ordering is respected under contention.

This is a **pure test story** — no production code is written here. The scheduler (Epic 3, stories 3.1–3.5) must be complete before this test can pass. Story 4.1 (`analyze_bottleneck`) is **not** a prerequisite for VS-1.

## Acceptance Criteria

**Given** `tests/test_vs1_morning_rush.py` uses the reference fixture config (recorded in the test docstring)
**When** the test submits ≥ 6 flights with a mix of `arrival` and `departure` across `high`, `medium`, `low` priorities, no dependencies, exercising at least one resource-contention point
**And** invokes `generate_schedule`
**Then** every flight that can be scheduled IS scheduled (no false `unschedulable` outcomes)
**And** no two placements overlap on the same runway or same gate (asserted programmatically)
**And** under contention, higher-priority flights have earlier `start_sec` than lower-priority same-runway peers (asserted)
**And** any unscheduled flights are reported in `get_airport_status` unscheduled list with non-null reason strings
**And** the test runs deterministically (re-run 5 times in CI → identical assertions)

## Technical Requirements

### Prerequisites — Epic 3 Must Be Complete

This story's test calls tools that **currently raise `NotImplementedError`** in `tools.py`:
- `generate_schedule()` — stub at line 71–72 of `src/atc_mcp/tools.py`
- `get_airport_status()` — stub at line 75–77 of `src/atc_mcp/tools.py`

Additionally `timeline_resource()` in `resources.py` currently returns `{"events": []}`.

**DO NOT implement these tools or the scheduler here.** They are implemented in Stories 3.1–3.5. This story only creates the test file. The test will fail with `NotImplementedError` until Epic 3 is done — that is expected and correct.

### Architecture Compliance

**Reference config** (from `architecture.md §Scenario Walkthroughs` — identical to `conftest.py VALID_ENV`):
```
ATC_RUNWAYS=[{"id":"R1","length_m":3500},{"id":"R2","length_m":3000}]
ATC_GATE_COUNT=4
ATC_GROUND_CREW_COUNT=3
ATC_RUNWAY_SEP_TAKEOFF_SEC=120
ATC_RUNWAY_SEP_LANDING_SEC=180
ATC_RUNWAY_SEP_MIXED_SEC=240
ATC_GATE_TURNAROUND_SEC=300
ATC_DEPENDENCY_BUFFER_SEC=600
ATC_SCHEDULING_HORIZON_SEC=86400
ATC_DURATION_ARRIVAL_SEC=1200
ATC_DURATION_DEPARTURE_SEC=1200
```

This is the same config as `conftest.py VALID_ENV`. Use the `valid_env` pytest fixture from `conftest.py` — do not redeclare it.

### Tool & Resource Signatures (from `src/atc_mcp/tools.py` and `resources.py`)

```python
from atc_mcp.tools import (
    SubmitFlightInput, RunwayRequirementsInput,
    CancelFlightInput, submit_flight,
    generate_schedule, get_airport_status,
)
from atc_mcp.resources import timeline_resource
```

- `submit_flight(SubmitFlightInput(...))` → `{"flight": {...}}` or `{"error": "..."}`
- `generate_schedule()` → `{"schedule": [...], "unscheduled": [...], "completion_time_seconds": int|null, "summary": {...}}`
- `get_airport_status()` → `{"flight_counts": {...}, "runways": [...], "gates": {...}, "ground_crew": {...}, "resource_constraints": [...], "unscheduled": [...], "completion_time_seconds": int|null}`
- `timeline_resource()` → `str` (JSON): `{"events": [{"start_sec", "end_sec", "flight_number", "operation_type", "runway_id", "gate_id", "depends_on"}, ...]}`

**⚠️ Field name discrepancy to be aware of:**  
`epics.md §Story 3.5` uses `"unscheduled_flights"` but `architecture.md §MCP Tool Catalog` pins the field name as `"unscheduled"` in the `get_airport_status` response. **Architecture is the source of truth** — use `result["unscheduled"]`.

### Test Invocation Pattern

Follow the established pattern from `tests/test_cancel_flight.py`:
- Use `setup_function()` to call `state.reset()` before each test (not `@pytest.fixture` teardown)
- Call tool functions **directly** (not via MCP client harness — the project tests at the Python-function level)
- `load_config()` within the test using `monkeypatch` or the `valid_env` fixture

```python
from atc_mcp.config import load_config
from atc_mcp.domain.state import state
```

`load_config()` must be called after env vars are set (i.e., inside the test body or fixture after `valid_env` fixture runs). The `config` object returned is used only if a tool needs it injected — check Story 3.4 implementation to confirm whether `generate_schedule()` reads from global state or accepts a config argument.

### Flight Fixture Design (≥ 6 flights, no deps, exercises contention)

Use exactly 6 flights submitted in this order. The fixture creates two interleaved resource-contention streams (arrivals on R1, departures on R2), with priorities forcing ordering:

| # | Flight | Op type | Priority | Deps |
|---|--------|---------|----------|------|
| 1 | AA001 | arrival | high | — |
| 2 | AA002 | departure | high | — |
| 3 | AA003 | arrival | medium | — |
| 4 | AA004 | departure | medium | — |
| 5 | AA005 | arrival | low | — |
| 6 | AA006 | departure | low | — |

With 2 runways and 6 flights of differing priorities, arrivals and departures contend for runways from flight 3 onward (resource contention point ✓). All 6 are schedulable within the 86400-sec horizon (duration 1200 × 3 serial + buffers << 86400 ✓).

**Expected sort order** (per `architecture.md §Scheduling Algorithm` sort key `(topo_depth=0, priority_rank, flight_number)`):
`priority_rank = high:0, medium:1, low:2`

Sort: AA001(0,0,"AA001") → AA002(0,0,"AA002") → AA003(0,1,"AA003") → AA004(0,1,"AA004") → AA005(0,2,"AA005") → AA006(0,2,"AA006")

**Expected assignment streams** (each runway serves one operation-type stream in the greedy placer):
- R1 receives: AA001 (high arrival), then AA003 (medium arrival), then AA005 (low arrival)
- R2 receives: AA002 (high departure), then AA004 (medium departure), then AA006 (low departure)

This guarantees the priority-ordering assertion is testable on each runway.

### Assertions to Implement

#### AC-1: All 6 flights are scheduled

```python
result = generate_schedule()
assert result["unscheduled"] == []
assert len(result["schedule"]) == 6
```

#### AC-2: No runway overlap

Group placements by `runway_id`, sort by `start_sec`. For consecutive pair `(p_i, p_{i+1})` on the same runway: `p_i["end_sec"] <= p_{i+1}["start_sec"]`.

```python
from collections import defaultdict

by_runway = defaultdict(list)
for p in result["schedule"]:
    by_runway[p["runway_id"]].append(p)

for runway_id, placements in by_runway.items():
    placements.sort(key=lambda p: p["start_sec"])
    for i in range(len(placements) - 1):
        assert placements[i]["end_sec"] <= placements[i + 1]["start_sec"], (
            f"Runway {runway_id} overlap: {placements[i]} vs {placements[i+1]}"
        )
```

#### AC-3: No gate overlap

Same approach keyed by `gate_id`. Gate turnaround means the gap is `>= gate_turnaround_sec` (300s), but for VS-1 the minimum assertion is just no overlap (`p_i["end_sec"] <= p_{i+1}["start_sec"]`):

```python
by_gate = defaultdict(list)
for p in result["schedule"]:
    by_gate[p["gate_id"]].append(p)

for gate_id, placements in by_gate.items():
    placements.sort(key=lambda p: p["start_sec"])
    for i in range(len(placements) - 1):
        assert placements[i]["end_sec"] <= placements[i + 1]["start_sec"], (
            f"Gate {gate_id} overlap: {placements[i]} vs {placements[i+1]}"
        )
```

#### AC-4: Priority ordering on each runway

For each runway, flights sorted by `start_sec` must be in non-decreasing priority rank order (high=0 before medium=1 before low=2):

```python
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}

flight_priority = {
    f["flight_number"]: f["priority"]
    for f in [submit_result["flight"] for submit_result in submissions]
}

for runway_id, placements in by_runway.items():
    placements.sort(key=lambda p: p["start_sec"])
    ranks = [PRIORITY_RANK[flight_priority[p["flight_number"]]] for p in placements]
    assert ranks == sorted(ranks), (
        f"Runway {runway_id}: priority order violated, got {ranks}"
    )
```

Note: `flight_priority` can be built while submitting flights (capture each `submit_flight` result).

#### AC-5: Unscheduled flights in `get_airport_status` have non-null reasons

Since all 6 flights are schedulable:

```python
status = get_airport_status()
assert status["unscheduled"] == []
```

If the test is extended to include an unschedulable flight, assert `f["reason"] is not None` for each entry. See VS-2 (Story 4.3) for that case.

#### AC-6: Determinism (5 identical runs)

```python
import json

outputs = []
for _ in range(5):
    state.reset()
    # re-submit all flights + regenerate
    _submit_all_flights()
    run = generate_schedule()
    outputs.append(
        json.dumps(run, sort_keys=True, separators=(",", ":"))
    )
assert len(set(outputs)) == 1, "Schedule output is not deterministic across 5 runs"
```

Extract the submission + schedule logic into a helper `_submit_all_flights()` so the determinism test can call it cleanly.

### Timeline Resource Cross-Check (optional but recommended)

After `generate_schedule()`, call `timeline_resource()` and verify the returned events are consistent with `result["schedule"]`:

```python
import json as _json
timeline_data = _json.loads(timeline_resource())
events = timeline_data["events"]
# Events sorted by (start_sec, runway_id, flight_number)
assert len(events) == 6
# Each event should be present in result["schedule"]
sched_keys = {(p["flight_number"], p["runway_id"]) for p in result["schedule"]}
for ev in events:
    assert (ev["flight_number"], ev["runway_id"]) in sched_keys
```

## Implementation Guidance

### File to Create

**CREATE:** `tests/test_vs1_morning_rush.py`

No production code changes. No other files touched.

### Recommended Test Structure

```python
"""VS-1 Morning Rush acceptance test — spec.md §9 VS-1.

Fixture config (recorded per epics AC):
  ATC_RUNWAYS=[{"id":"R1","length_m":3500},{"id":"R2","length_m":3000}]
  ATC_GATE_COUNT=4, ATC_GROUND_CREW_COUNT=3
  ATC_RUNWAY_SEP_TAKEOFF_SEC=120, ATC_RUNWAY_SEP_LANDING_SEC=180, ATC_RUNWAY_SEP_MIXED_SEC=240
  ATC_GATE_TURNAROUND_SEC=300, ATC_DEPENDENCY_BUFFER_SEC=600
  ATC_SCHEDULING_HORIZON_SEC=86400
  ATC_DURATION_ARRIVAL_SEC=1200, ATC_DURATION_DEPARTURE_SEC=1200

Flights submitted (6, no deps, exercising runway contention from flight 3 onward):
  AA001 arrival  high
  AA002 departure high
  AA003 arrival  medium
  AA004 departure medium
  AA005 arrival  low
  AA006 departure low
"""
import json
from collections import defaultdict

import pytest

from atc_mcp.config import load_config
from atc_mcp.domain.state import state
from atc_mcp.resources import timeline_resource
from atc_mcp.tools import SubmitFlightInput, generate_schedule, get_airport_status, submit_flight

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}

FLIGHTS = [
    ("AA001", "arrival",   "high"),
    ("AA002", "departure", "high"),
    ("AA003", "arrival",   "medium"),
    ("AA004", "departure", "medium"),
    ("AA005", "arrival",   "low"),
    ("AA006", "departure", "low"),
]


def setup_function(function):
    state.reset()


def _submit_all():
    """Submit all FLIGHTS to clean state; return {flight_number: priority} map."""
    priority_map = {}
    for flight_number, op_type, priority in FLIGHTS:
        res = submit_flight(SubmitFlightInput(
            flight_number=flight_number,
            operation_type=op_type,
            priority=priority,
        ))
        assert "error" not in res, f"submit_flight failed: {res}"
        priority_map[flight_number] = priority
    return priority_map


def test_all_flights_scheduled(valid_env):
    load_config()  # triggers env-var validation
    priority_map = _submit_all()
    result = generate_schedule()
    assert result["unscheduled"] == [], f"Unexpected unscheduled: {result['unscheduled']}"
    assert len(result["schedule"]) == len(FLIGHTS)


def test_no_runway_overlap(valid_env):
    load_config()
    _submit_all()
    result = generate_schedule()
    by_runway = defaultdict(list)
    for p in result["schedule"]:
        by_runway[p["runway_id"]].append(p)
    for runway_id, placements in by_runway.items():
        placements.sort(key=lambda p: p["start_sec"])
        for i in range(len(placements) - 1):
            assert placements[i]["end_sec"] <= placements[i + 1]["start_sec"], (
                f"Runway {runway_id} overlap between {placements[i]} and {placements[i+1]}"
            )


def test_no_gate_overlap(valid_env):
    load_config()
    _submit_all()
    result = generate_schedule()
    by_gate = defaultdict(list)
    for p in result["schedule"]:
        by_gate[p["gate_id"]].append(p)
    for gate_id, placements in by_gate.items():
        placements.sort(key=lambda p: p["start_sec"])
        for i in range(len(placements) - 1):
            assert placements[i]["end_sec"] <= placements[i + 1]["start_sec"], (
                f"Gate {gate_id} overlap between {placements[i]} and {placements[i+1]}"
            )


def test_priority_ordering_per_runway(valid_env):
    load_config()
    priority_map = _submit_all()
    result = generate_schedule()
    by_runway = defaultdict(list)
    for p in result["schedule"]:
        by_runway[p["runway_id"]].append(p)
    for runway_id, placements in by_runway.items():
        placements.sort(key=lambda p: p["start_sec"])
        ranks = [PRIORITY_RANK[priority_map[p["flight_number"]]] for p in placements]
        assert ranks == sorted(ranks), (
            f"Runway {runway_id}: priority ordering violated. "
            f"Flights by start: {[p['flight_number'] for p in placements]}, ranks: {ranks}"
        )


def test_airport_status_no_unscheduled(valid_env):
    load_config()
    _submit_all()
    generate_schedule()
    status = get_airport_status()
    assert status["unscheduled"] == []


def test_determinism(valid_env):
    load_config()
    outputs = []
    for _ in range(5):
        state.reset()
        _submit_all()
        run = generate_schedule()
        outputs.append(json.dumps(run, sort_keys=True, separators=(",", ":")))
    assert len(set(outputs)) == 1, "generate_schedule is not deterministic across 5 runs"


def test_timeline_consistent_with_schedule(valid_env):
    load_config()
    _submit_all()
    result = generate_schedule()
    events = json.loads(timeline_resource())["events"]
    assert len(events) == len(FLIGHTS)
    sched_keys = {(p["flight_number"], p["runway_id"]) for p in result["schedule"]}
    for ev in events:
        assert (ev["flight_number"], ev["runway_id"]) in sched_keys
```

### How `load_config()` integrates with tools

Check the Story 3.x implementation of `generate_schedule()` and `get_airport_status()` once implemented:
- If they read config from a module-level singleton (similar to `state` in `domain/state.py`), `load_config()` must be called once to populate it before the first tool call. This is the expected pattern — call `load_config()` at the top of each test or in a module-level fixture.
- If the tools accept `config` as a parameter, pass the result of `load_config()` directly.

Do not assume — **read `tools.py` after Epic 3 lands** and adapt the call signature accordingly.

### State Reset Pattern

Each test calls `setup_function()` (function-scope auto-reset) which does `state.reset()`. The determinism test calls `state.reset()` explicitly between iterations because it loops. Do not rely on `setup_function` inside the loop body.

## Tasks / Subtasks

- [ ] Create `tests/test_vs1_morning_rush.py` with module docstring recording fixture config (AC: all)
  - [ ] Implement `_submit_all()` helper that submits 6 FLIGHTS and returns priority map
  - [ ] `test_all_flights_scheduled` — verifies `unscheduled == []` and schedule has 6 entries (AC-1)
  - [ ] `test_no_runway_overlap` — groups by runway, checks end_sec ≤ next start_sec (AC-2)
  - [ ] `test_no_gate_overlap` — groups by gate, checks end_sec ≤ next start_sec (AC-3)
  - [ ] `test_priority_ordering_per_runway` — asserts non-decreasing priority rank per runway (AC-4)
  - [ ] `test_airport_status_no_unscheduled` — calls get_airport_status, asserts unscheduled == [] (AC-5)
  - [ ] `test_determinism` — 5-run loop asserting byte-identical JSON output (AC-6)
  - [ ] `test_timeline_consistent_with_schedule` — cross-checks timeline_resource against schedule (bonus)
- [ ] Verify test fails with `NotImplementedError` before Epic 3 (confirms test is wired correctly)
- [ ] Verify all 7 tests pass after Epic 3 is complete with zero regressions

## Dev Notes

### Project Structure Notes

- **New file only:** `tests/test_vs1_morning_rush.py` — follows established test layout pattern
- **No changes to** `src/` — all production code is Epic 3's responsibility
- **Module imports** must follow import-discipline rules from `test_imports.py`: test files may import from `atc_mcp.tools`, `atc_mcp.resources`, `atc_mcp.domain.*`, `atc_mcp.config`
- **conftest.py** provides `valid_env` fixture (sets all `ATC_*` env vars via monkeypatch) — reuse it, do not redeclare `VALID_ENV`

### Architecture Traceability

| Assertion | Architecture Source |
|-----------|----------------------|
| All flights scheduled | `epics.md §VS-1`, `spec.md §9` |
| No runway overlap | `FR-SCH-1`, `architecture.md §Scheduling Algorithm` |
| No gate overlap | `FR-SCH-2`, `architecture.md §Ground Crew Scheduling Semantics` |
| Priority ordering | `FR-SCH-3`, `architecture.md §Scheduling Algorithm` sort key |
| Unscheduled in status | `FR-SCH-4`, `architecture.md §MCP Tool Catalog §get_airport_status` |
| Determinism | `FR-SCH-6 / NFR-3`, `architecture.md §Ordering Patterns` |

### Potential Pitfall: `generate_schedule()` output shape after Epic 3

The current stub at `tools.py:70–72` raises `NotImplementedError`. When Epic 3 lands, the return shape is pinned in `architecture.md §MCP Tool Catalog §generate_schedule`:
```json
{
  "schedule": [{"flight_number", "operation_type", "runway_id", "gate_id", "start_sec", "end_sec"}],
  "unscheduled": [{"flight_number", "reason"}],
  "completion_time_seconds": int | null,
  "summary": {"scheduled_count", "unscheduled_count", "cancelled_count"}
}
```
Use `result["schedule"]` and `result["unscheduled"]`. Do NOT use `result["placements"]` — the tool output uses `"schedule"`, the internal `Schedule` model uses `placements`.

### Potential Pitfall: `get_airport_status()` field name

Architecture pins the field as `"unscheduled"` (not `"unscheduled_flights"` as mentioned in epics story 3.5). Use `status["unscheduled"]`.

### VS-1 Architecture Walkthrough (4-flight reference)

`architecture.md §VS-1 Walkthrough` traces 4 flights (AA001–AA004). This story uses 6 flights — the 4-flight trace is informational only. The test must work dynamically (not hard-code specific `start_sec` values), because the scheduler is responsible for determining placements.

If you want to add a sanity-check test with the 4-flight walkthrough and assert exact placements (useful for debugging), that is acceptable as an additional test function, but the mandatory VS-1 test uses 6 flights.

### References

- `architecture.md §Scenario Walkthroughs §VS-1` — reference config and 4-flight trace
- `architecture.md §MCP Tool Catalog` — pinned tool response shapes
- `architecture.md §Scheduling Algorithm` — sort key, priority rank, tie-break policy
- `architecture.md §Ordering Patterns` — determinism enforcement rules
- `epics.md §Epic 4, Story 4.2` — acceptance criteria source
- `tests/conftest.py` — `valid_env` fixture and `VALID_ENV` dict
- `tests/test_cancel_flight.py` — established test pattern (`setup_function`, direct tool calls)
- `src/atc_mcp/tools.py` — current tool stubs (check signatures after Epic 3 implementation)
- `src/atc_mcp/resources.py` — `timeline_resource()` (check shape after Epic 3 implementation)

---

## Dev Agent Record

### Agent Model Used

_to be filled_

### Debug Log References

### Completion Notes List

### File List

- `tests/test_vs1_morning_rush.py` — created: VS-1 acceptance test (7 test functions)
