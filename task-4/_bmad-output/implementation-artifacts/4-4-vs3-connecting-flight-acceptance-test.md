---
story_id: "4.4"
story_key: "4-4-vs3-connecting-flight-acceptance-test"
epic: "Epic 4: Bottleneck Analysis, Validation & Project Delivery"
title: "VS-3 Connecting Flight Acceptance Test"
status: "ready-for-dev"
created: "2026-05-21"
dependencies: ["3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "4.1"]
---

# Story 4.4: VS-3 Connecting Flight Acceptance Test

## User Story

**As a** product stakeholder,
**I want** the Connecting Flight scenario from `spec.md §9` to pass automatically,
**so that** I have machine-checkable evidence the system correctly orders dependent operations.

## Acceptance Criteria

**Given** `tests/test_vs3_connecting_flight.py` submits an inbound arrival `IN001` and a dependent
outbound departure `OUT002` with `dependencies: ["IN001"]`

**When** `generate_schedule` runs

**Then** both flights are scheduled (`unscheduled = []`)

**And** `OUT002.start_sec >= IN001.end_sec + ATC_DEPENDENCY_BUFFER_SEC`

**And** `atc://timeline` lists `IN001` before `OUT002` (sort by `start_sec`)

**And** `analyze_bottleneck` returns a chain containing `["IN001", "OUT002"]` with:
- `operation_durations == [ATC_DURATION_ARRIVAL_SEC, ATC_DURATION_DEPARTURE_SEC]` (i.e., `[1200, 1200]`)
- `dependency_buffers == [ATC_DEPENDENCY_BUFFER_SEC]` (i.e., `[600]`)

**And** the test is deterministic (identical assertions on repeated runs)

## Tasks / Subtasks

- [ ] Task 1: Create `tests/test_vs3_connecting_flight.py` (AC: all)
  - [ ] 1.1: Submit IN001 (arrival, medium) and OUT002 (departure, medium, deps=["IN001"]) using reference config fixture
  - [ ] 1.2: Call `generate_schedule()` and assert both flights scheduled with no unscheduled entries
  - [ ] 1.3: Assert `OUT002.start_sec >= IN001.end_sec + 600` (dep buffer enforced)
  - [ ] 1.4: Assert `OUT002.start_sec - IN001.end_sec == 600` exactly (buffer is the binding constraint)
  - [ ] 1.5: Read `atc://timeline` JSON; assert IN001 event appears before OUT002 event
  - [ ] 1.6: Call `analyze_bottleneck()` and assert the exact chain/duration/buffers
  - [ ] 1.7: Run the full scenario 5 times and assert all results are byte-identical (determinism)

## Dev Notes

### Pre-Conditions — This Story Requires Epic 3 + Story 4.1 Done

This story creates the **acceptance test only**; the underlying implementations that the test exercises
must be complete before this story's tests can pass:

| Dependency | File | Status at story creation |
|---|---|---|
| Story 3.1–3.3 | `scheduler/algorithm.py`, `scheduler/constraints.py` | stub (empty) |
| Story 3.4 | `tools.generate_schedule`, `resources.timeline_resource`, `resources.runways_resource` | raises `NotImplementedError` / returns `{"events": []}` |
| Story 3.5 | `tools.get_airport_status` | raises `NotImplementedError` |
| Story 3.6 | cancellation cascade in `cancel_flight` | returns `dependents_reevaluated: []` (placeholder) |
| Story 3.7 | `tests/test_determinism.py` | does not exist |
| Story 4.1 | `bottleneck.py`, `tools.analyze_bottleneck` | stub / raises `NotImplementedError` |

**The test file may be written now; it will fail until stories 3.x and 4.1 are complete.**

### Reference Config (VS-3)

Use the shared `valid_env` fixture from `tests/conftest.py` — it already sets the reference config:

```python
VALID_ENV = {
    "ATC_RUNWAYS": '[{"id":"R1","length_m":3500},{"id":"R2","length_m":3000}]',
    "ATC_GATE_COUNT": "4",
    "ATC_GROUND_CREW_COUNT": "3",
    "ATC_RUNWAY_SEP_TAKEOFF_SEC": "120",
    "ATC_RUNWAY_SEP_LANDING_SEC": "180",
    "ATC_RUNWAY_SEP_MIXED_SEC": "240",
    "ATC_GATE_TURNAROUND_SEC": "300",
    "ATC_DEPENDENCY_BUFFER_SEC": "600",
    "ATC_SCHEDULING_HORIZON_SEC": "86400",
    "ATC_DURATION_ARRIVAL_SEC": "1200",
    "ATC_DURATION_DEPARTURE_SEC": "1200",
}
```

Constants to use in assertions: `DEP_BUFFER=600`, `ARRIVAL_DUR=1200`, `DEPARTURE_DUR=1200`.

### Exact Expected Placement (Architecture Walkthrough)

From `_bmad-output/planning-artifacts/architecture.md §VS-3 — Connecting Flight`:

**Inputs (submission order):**

| # | Flight | Op type | Priority | Deps |
|---|---|---|---|---|
| 1 | IN001 | arrival | medium | — |
| 2 | OUT002 | departure | medium | `["IN001"]` |

**Expected placement:**

| Flight | Op | Runway | Gate | start_sec | end_sec |
|---|---|---|---|---|---|
| IN001 | arrival | R1 | G1 | 0 | 1200 |
| OUT002 | departure | R1 | G1 | 1800 | 3000 |

**Placement derivation:**
1. IN001 — topo_depth=0, no deps, floor=0. First candidate `(R1,G1)` free at t=0. Place `[0,1200)`.
2. OUT002 — topo_depth=1, dep_buffer floor = 1200+600=1800. All four candidates `(R1/G1, R1/G2, R2/G1, R2/G2)` yield t=1800 after checking runway sep (mixed=240→1440), gate turnaround (1500), and floor (1800). Tie-break lex → `(R1,G1)`. Place `[1800,3000)`.

> The exact values are asserted in the test, not just inequalities: this locks regression-detectable
> behavior to the algorithm spec.

### Tool and Resource Call Signatures (as of Story 3.4)

```python
# tools.py — all tool handlers receive a Pydantic input model or no args
from atc_mcp.tools import submit_flight, SubmitFlightInput, generate_schedule, analyze_bottleneck
from atc_mcp.resources import timeline_resource
from atc_mcp.config import load_config
from atc_mcp.domain.state import state
import json

# Load config (requires valid_env fixture to set ATC_* env vars)
config = load_config()

# Submit flights
submit_flight(SubmitFlightInput(
    flight_number="IN001", operation_type="arrival", priority="medium"
))
submit_flight(SubmitFlightInput(
    flight_number="OUT002", operation_type="departure", priority="medium",
    dependencies=["IN001"]
))

# Generate schedule — Story 3.4 signature: generate_schedule(config) -> dict
sched = generate_schedule(config)

# Read timeline resource — Story 3.4: timeline_resource(state, config) -> str (JSON)
timeline_json = json.loads(timeline_resource())

# Analyze bottleneck — Story 4.1: analyze_bottleneck(config) -> dict
bottleneck = analyze_bottleneck(config)
```

> **IMPORTANT:** The exact function signatures for `generate_schedule`, `analyze_bottleneck`, and
> `timeline_resource` will be defined by Stories 3.4 and 4.1. When implementing this test, verify
> the actual signatures in `tools.py` and `resources.py` before calling them. Adjust the test
> to match the real signatures — do NOT invent parameters.

### Test Structure Pattern

Follow the pattern established in `tests/test_cancel_flight.py` and `tests/test_submit_flight.py`:

```python
import json
import pytest

from atc_mcp.config import load_config
from atc_mcp.domain.state import state
from atc_mcp.tools import SubmitFlightInput, submit_flight, generate_schedule, analyze_bottleneck
from atc_mcp.resources import timeline_resource


def setup_function(function):
    """Reset in-memory state before each test."""
    state.reset()


def test_vs3_both_flights_scheduled(valid_env):
    ...

def test_vs3_dependency_buffer_enforced(valid_env):
    ...

def test_vs3_timeline_order(valid_env):
    ...

def test_vs3_bottleneck_chain(valid_env):
    ...

def test_vs3_determinism(valid_env):
    ...
```

- Use `valid_env` fixture (from `conftest.py`) — sets all `ATC_*` env vars via `monkeypatch.setenv`
- Call `state.reset()` in `setup_function` to guarantee clean state per test
- Do NOT share state between tests (each test re-submits flights)

### Assertions Checklist

**Scheduling assertions:**
- `sched["unscheduled"] == []` — both flights must be scheduled
- `IN001_start_sec == 0`, `IN001_end_sec == 1200`
- `OUT002_start_sec == 1800`, `OUT002_end_sec == 3000`
- `OUT002_start_sec - IN001_end_sec == 600` (dep buffer exactly)
- `OUT002_start_sec >= IN001_end_sec + 600` (inequality form per AC)

**Timeline assertions (from `atc://timeline`):**
- Resource returns events sorted by `(start_sec, runway_id, flight_number)` — IN001 event first (start_sec=0), OUT002 event second (start_sec=1800)
- Each event shape (from architecture `atc://timeline` catalog):
  ```json
  {"start_sec": 0, "end_sec": 1200, "flight_number": "IN001",
   "operation_type": "arrival", "runway_id": "R1", "gate_id": "G1", "depends_on": []}
  {"start_sec": 1800, "end_sec": 3000, "flight_number": "OUT002",
   "operation_type": "departure", "runway_id": "R1", "gate_id": "G1", "depends_on": ["IN001"]}
  ```
- Assert `events[0]["flight_number"] == "IN001"` and `events[1]["flight_number"] == "OUT002"`
- Assert `events[1]["depends_on"] == ["IN001"]` (dependency visible in timeline)

**Bottleneck assertions (from `analyze_bottleneck`):**
- `result["chain"] == ["IN001", "OUT002"]`
- `result["total_duration_seconds"] == 3000` (= OUT002.end_sec - IN001.start_sec = 3000 - 0)
- `result["operation_durations"] == [1200, 1200]`
- `result["dependency_buffers"] == [600]`
- `len(result["operation_durations"]) == len(result["chain"])` (2 == 2)
- `len(result["dependency_buffers"]) == len(result["chain"]) - 1` (1 == 1)

**Determinism assertion:**
```python
def test_vs3_determinism(valid_env):
    import json
    results = []
    for _ in range(5):
        state.reset()
        config = load_config()
        submit_flight(SubmitFlightInput(...))
        submit_flight(SubmitFlightInput(...))
        sched = generate_schedule(config)
        serialised = json.dumps(sched, sort_keys=True, separators=(",", ":"))
        results.append(serialised)
    assert len(set(results)) == 1, "generate_schedule is not deterministic across runs"
```

### Architecture Compliance Rules

From `architecture.md §Ordering Patterns` and `§Format Patterns`:

- `atc://timeline` payload key is `"events"` (not `"timeline"`) — see architecture Resource Catalog and Story 3.4 AC which uses `{"timeline": [...]}`. **Verify the actual key used in `timeline_resource()` before asserting.** Architecture catalog uses `"events"` but Story 3.4 AC text says `"timeline"`. Use whichever the implementation chooses; assert consistently.
- Timeline sort order: `(start_sec, runway_id, flight_number)` — per architecture §Resource Catalog
- All time field names end in `_sec`
- Enum values are lowercase string literals: `"arrival"`, `"departure"`, `"medium"`
- `dependency_buffers` length must equal `len(chain) - 1`; `operation_durations` length must equal `len(chain)`

### Module Dependency Rules

From `architecture.md §Structure Patterns`:

```
tests/          ← imports atc_mcp.tools, atc_mcp.resources, atc_mcp.config, atc_mcp.domain
tools.py        ← MCP boundary; DO NOT import in domain/ or scheduler/
resources.py    ← MCP boundary; DO NOT import in domain/ or scheduler/
```

The test file imports from `tools`, `resources`, `config`, and `domain` only.
Do NOT import `mcp` SDK directly in the test file.

### Files to Create

| Action | File | Notes |
|---|---|---|
| CREATE | `tests/test_vs3_connecting_flight.py` | New test file, ~80 lines |

### Files NOT to Modify

- `tools.py` — behavior comes from Epic 3 / Story 4.1; this story is test-only
- `resources.py` — behavior comes from Story 3.4; this story is test-only
- `bottleneck.py` — behavior comes from Story 4.1; this story is test-only
- `conftest.py` — do NOT modify; use `valid_env` fixture as-is

### Regression Safety

- Running `pytest -q tests/test_vs3_connecting_flight.py` must not affect other test files
- All existing tests (currently 86 passing as of story 2.3) must continue to pass: `pytest -q`
- Because Epic 3 and Story 4.1 are not yet done, this test file will initially show failures on every test function — this is expected and correct

### Project Structure Notes

- Test file location: `tests/test_vs3_connecting_flight.py` — flat `tests/` directory, no subdirectories
- No test fixtures-as-files; all fixtures are Python factories in `conftest.py`
- File naming: `test_vs3_connecting_flight.py` matches the architecture's test plan convention

### References

- Architecture walkthrough VS-3: `_bmad-output/planning-artifacts/architecture.md §VS-3 — Connecting Flight`
- Architecture resource catalog: `_bmad-output/planning-artifacts/architecture.md §MCP Resource Catalog`
- Architecture tool catalog: `_bmad-output/planning-artifacts/architecture.md §MCP Tool Catalog`
- Active chain definition: `_bmad-output/planning-artifacts/architecture.md §"Active Scheduled Dependency Chain" Definition (DD-9)`
- Story 4.1 AC (bottleneck output shape): `_bmad-output/planning-artifacts/epics.md §Story 4.1`
- Story 3.4 AC (timeline format): `_bmad-output/planning-artifacts/epics.md §Story 3.4`
- Test pattern reference: `tests/test_cancel_flight.py`, `tests/conftest.py`
- VS-3 scenario spec: `_bmad-output/planning-artifacts/epics.md §Story 4.4`

## Definition of Done

- [ ] `tests/test_vs3_connecting_flight.py` created
- [ ] Test imports `valid_env` fixture and calls `state.reset()` in `setup_function`
- [ ] `test_vs3_both_flights_scheduled` passes (both IN001 and OUT002 in `scheduled` state, `unscheduled == []`)
- [ ] `test_vs3_dependency_buffer_enforced` passes (exact timing: OUT002.start=1800, IN001.end=1200, diff=600)
- [ ] `test_vs3_timeline_order` passes (IN001 before OUT002, `depends_on: ["IN001"]` on OUT002 event)
- [ ] `test_vs3_bottleneck_chain` passes (chain=["IN001","OUT002"], total=3000, durations=[1200,1200], buffers=[600])
- [ ] `test_vs3_determinism` passes (5 identical serialized schedule outputs)
- [ ] All pre-existing tests continue to pass (`pytest -q`)
- [ ] No imports of `os`, `time`, `datetime`, `random`, or `mcp` SDK in the test file

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

- `tests/test_vs3_connecting_flight.py` — created: VS-3 acceptance test

### Change Log

- 2026-05-21: Story created

---

**Story Status:** ready-for-dev
**Last Updated:** 2026-05-21
**Context Engine:** Ultimate BMad Method story context completed
