---
story_id: "3.1"
story_key: "3-1-scheduling-algorithm-core"
epic: "Epic 3: Deterministic Scheduling Engine & Airport Operations"
title: "Scheduling Algorithm Core — Placement, Separation, Gate Turnaround, Runway Match, Horizon"
status: "ready-for-dev"
created: "2026-05-21"
dependencies: ["1.2", "1.3", "2.1"]
---

# Story 3.1: Scheduling Algorithm Core — Placement, Separation, Gate Turnaround, Runway Match, Horizon

## User Story

**As the** scheduling engine,
**I want** a pure-function deterministic greedy placement algorithm that handles single-flight resource constraints,
**So that** I have a unit-testable foundation for layering dependency, ground-crew, and priority logic in later stories.

## Acceptance Criteria

**Given** `scheduler/algorithm.py` exposes `schedule(flights: tuple[Flight, ...], config: Config) -> Schedule`
**When** I call it with a tuple of flights (no dependencies, no ground-crew constraints — that comes in 3.2/3.3)
**Then** flights are sorted ascending by `(topo_depth=0, priority_rank, flight_number)` where `priority_rank` is `high=0, medium=1, low=2`
**And** for each flight, the earliest feasible `(runway, gate)` is selected, tie-broken by `(runway_id, gate_id)` lex
**And** separation buffer is applied between same-runway consecutive operations, using `ATC_RUNWAY_SEP_TAKEOFF_SEC` / `_LANDING_SEC` / `_MIXED_SEC` based on the op-type pair
**And** gate turnaround (`ATC_GATE_TURNAROUND_SEC`) is enforced on same-gate consecutive operations
**And** runway capability is matched against `runway_requirements.min_length_m` when present; flights with no matching runway are marked `unschedulable` with `unscheduled_reason` exactly `"no runway meets minimum length <N>m (available runways: <id> <len>m, ...)"`
**And** flights for which `t + duration > scheduling_horizon_sec` are marked `unschedulable` with `unscheduled_reason` exactly `"would exceed scheduling horizon"`
**And** the returned `Schedule` exposes `placements: tuple[Placement, ...]`, `unscheduled: tuple[Flight, ...]`, `completion_time_seconds: int | None`
**And** `scheduler/` does not import `mcp`, `os`, `time`, `datetime`, or `random` (verified by `tests/test_imports.py`)
**And** `tests/test_scheduler_placement.py` covers: single arrival placed at `t=0`; two same-runway arrivals respect separation; two same-gate departures respect turnaround; mixed op-type pair uses mixed separation; runway-requirement matching (one matches, one doesn't); horizon overflow → unschedulable with exact reason string; priority ordering (high before medium with one runway)

## Tasks / Subtasks

- [ ] Task 1: Implement `scheduler/constraints.py` helpers (AC: separation, turnaround, runway match)
  - [ ] `get_separation(prev_op: OperationType, new_op: OperationType, config: Config) -> int` — returns correct `_SEC` value
  - [ ] `earliest_runway_start(placements: list[Placement], new_op: OperationType, floor: int, config: Config) -> int` — max over all prev placements on that runway
  - [ ] `earliest_gate_start(placements: list[Placement], floor: int, config: Config) -> int` — max over all prev placements on that gate
  - [ ] `feasible_runways(runways: tuple[Runway, ...], req: RunwayRequirements | None) -> list[Runway]` — filter + lex sort
  - [ ] `runway_unschedulable_reason(n: int, runways: tuple[Runway, ...]) -> str` — exact reason string
- [ ] Task 2: Implement `scheduler/algorithm.py` pure `schedule()` function (AC: all)
  - [ ] Sort flights by `(0, priority_rank, flight_number)`, skip cancelled
  - [ ] For each flight: filter runways, find earliest `(runway, gate)` pair, commit or mark unschedulable
  - [ ] Horizon check after best_t computed
  - [ ] Build and return `Schedule(placements, unscheduled, completion_time_seconds)`
- [ ] Task 3: Create `tests/test_scheduler_placement.py` with all 7 required cases (AC: test cases)

## Dev Notes

### Scope Boundary — CRITICAL

**Story 3.1 covers ONLY single-flight resource constraints. Do NOT implement:**
- Dependency / topological ordering (Story 3.2) — `topo_depth` is hard-coded `0` for all flights here
- Ground-crew capacity invariant (Story 3.3) — no crew counter in this story
- MCP tool wiring (`generate_schedule` tool) — that is Story 3.4

The `schedule()` function is a **pure function** — it takes its inputs and returns a `Schedule`. It does NOT read from or write to `AppState` directly. The tool layer (Story 3.4) handles state mutation.

### Function Signatures

```python
# scheduler/algorithm.py
from atc_mcp.config import Config
from atc_mcp.domain.models import Flight, Schedule

def schedule(flights: tuple[Flight, ...], config: Config) -> Schedule:
    ...
```

```python
# scheduler/constraints.py
from atc_mcp.config import Config
from atc_mcp.domain.models import OperationType, Placement, RunwayRequirements
from atc_mcp.config import Runway  # config.Runway, NOT domain.models.Runway

def get_separation(prev_op: OperationType, new_op: OperationType, config: Config) -> int:
    ...
```

### Critical Import Note

`config.py` defines its own `Runway` model (separate from `domain/models.Runway`). **Use `atc_mcp.config.Runway`** (not `domain.models.Runway`) for runway-capability matching, since `Config.runways` is `tuple[atc_mcp.config.Runway, ...]`.

Both have `id: str` and `length_m: int`, but they are different Pydantic models.

### Gate ID Generation

`Config` has `gate_count: int` but no list of gate objects. Generate gate IDs inline:

```python
gates: list[str] = [f"G{i}" for i in range(1, config.gate_count + 1)]
```

Gates are already in lex-ascending order from `G1` to `G{n}` (works for lex tie-breaking).

### Algorithm Flow (Greedy Placement)

```
For each flight in sort_order(flights):
  1. duration = config.duration_arrival_sec  (if arrival)
              OR config.duration_departure_sec (if departure)
  2. feasible = [r for r in sorted(config.runways, key=lambda r: r.id)
                 if not flight.runway_requirements or r.length_m >= flight.runway_requirements.min_length_m]
  3. If feasible is empty → unschedulable with exact reason string → continue
  4. best_t, best_runway_id, best_gate_id = None
  5. For runway in feasible (sorted lex by id):
       For gate in gates (G1..Gn, already lex order):
         t = max(floor_start=0,
                 earliest_runway_start(runway_ops[runway.id], flight.operation_type, 0, config),
                 earliest_gate_start(gate_ops[gate], 0, config))
         if best_t is None or t < best_t:
           best_t, best_runway_id, best_gate_id = t, runway.id, gate
  6. If best_t + duration > config.scheduling_horizon_sec → unschedulable, reason="would exceed scheduling horizon" → continue
  7. Commit placement; update runway_ops[best_runway_id] and gate_ops[best_gate_id]
```

`floor_start` is `0` for all flights in Story 3.1 (no dependency buffer — that is Story 3.2).

### Separation Logic (op-type pair)

| prev op → new op | buffer to use |
|---|---|
| departure → departure | `config.runway_sep_takeoff_sec` |
| arrival → arrival | `config.runway_sep_landing_sec` |
| arrival → departure | `config.runway_sep_mixed_sec` |
| departure → arrival | `config.runway_sep_mixed_sec` |

The constraint is: `t_new >= prev.end_sec + sep`

For a runway with multiple previous placements, iterate all and take the max:
```python
floor = max((p.end_sec + get_separation(p.operation_type, new_op, config) for p in runway_ops[r_id]), default=0)
```

### Gate Turnaround Logic

```python
floor = max((p.end_sec + config.gate_turnaround_sec for p in gate_ops[gate_id]), default=0)
```

This is the gate occupancy constraint: new op must start at least `turnaround_sec` after any previous op on the same gate ends.

### Exact Reason Strings (copy verbatim)

**Runway requirement failure:**
```python
available = ", ".join(
    f"{r.id} {r.length_m}m"
    for r in sorted(config.runways, key=lambda r: r.id)
)
reason = f"no runway meets minimum length {flight.runway_requirements.min_length_m}m (available runways: {available})"
```
Example: `"no runway meets minimum length 4500m (available runways: R1 3500m, R2 3000m)"`

**Horizon overflow:**
```python
reason = "would exceed scheduling horizon"
```
(Exact string, no additional detail — this is what the Story 3.1 and 3.3 ACs specify.)

### Unschedulable Flight Handling

When a flight is unschedulable, produce a NEW `Flight` instance (frozen model, use `model_copy`):
```python
unschedulable_flight = flight.model_copy(update={
    "state": FlightState.unschedulable,
    "unscheduled_reason": reason,
})
unscheduled.append(unschedulable_flight)
```
Do NOT append the original `flight` object — the state must be updated.

The algorithm does NOT mutate `AppState` — it returns updated flight states inside `Schedule.unscheduled`. The state mutation responsibility belongs to the `generate_schedule` tool handler (Story 3.4).

### Sort Key

```python
PRIORITY_RANK = {Priority.high: 0, Priority.medium: 1, Priority.low: 2}

sorted_flights = sorted(
    [f for f in flights if f.state != FlightState.cancelled],
    key=lambda f: (0, PRIORITY_RANK[f.priority], f.flight_number),
)
```

In Story 3.2, the `0` (topo_depth) becomes a computed value. Structure the code so replacing it is trivial.

### Schedule Return Value

```python
completion = max((p.end_sec for p in placements), default=None)
return Schedule(
    placements=tuple(placements),
    unscheduled=tuple(unscheduled),
    completion_time_seconds=completion,
)
```

`completion_time_seconds` is `None` when `placements` is empty (no scheduled flights).

### Files to Modify / Create

| File | Action | Notes |
|---|---|---|
| `src/atc_mcp/scheduler/algorithm.py` | UPDATE | Currently a stub with only a docstring |
| `src/atc_mcp/scheduler/constraints.py` | UPDATE | Currently a stub with only a docstring |
| `tests/test_scheduler_placement.py` | CREATE | Does not exist yet |

No other files need modification. `tools.py` still has `generate_schedule` raising `NotImplementedError` — leave it unchanged.

### Architecture Compliance

- **Import direction:** `scheduler/` may import from `atc_mcp.config` and `atc_mcp.domain.models`. Must NOT import `mcp`, `os`, `time`, `datetime`, `random`. `test_imports.py` enforces this via AST scan.
- **Determinism:** Use `sorted()` with explicit key; never iterate `set` for output; all time math is integer arithmetic.
- **Pydantic models:** `Flight` and `Placement` are `frozen=True`. Use `.model_copy(update={...})` to produce updated instances.
- **Time model:** All times are non-negative `int` seconds; no float arithmetic. `t=0` is relative epoch.

### Reference Config (from `tests/conftest.py` `VALID_ENV`)

```
ATC_RUNWAYS=[{"id":"R1","length_m":3500},{"id":"R2","length_m":3000}]
ATC_GATE_COUNT=4  (gates: G1, G2, G3, G4)
ATC_GROUND_CREW_COUNT=3  (not used in 3.1)
ATC_RUNWAY_SEP_TAKEOFF_SEC=120
ATC_RUNWAY_SEP_LANDING_SEC=180
ATC_RUNWAY_SEP_MIXED_SEC=240
ATC_GATE_TURNAROUND_SEC=300
ATC_DEPENDENCY_BUFFER_SEC=600  (not used in 3.1)
ATC_SCHEDULING_HORIZON_SEC=86400
ATC_DURATION_ARRIVAL_SEC=1200
ATC_DURATION_DEPARTURE_SEC=1200
```

### VS-1 Placement Trace (Expected Results with Reference Config)

Flights submitted in order: AA001 (arrival/high), AA002 (departure/medium), AA003 (arrival/low), AA004 (departure/low).
All topo_depth=0 → sort: AA001(0,0), AA002(1,0), AA003(2,0), AA004(2,0) — AA003 and AA004 tied on rank so sorted by flight_number.

| Flight | Op | Runway | Gate | start_sec | end_sec |
|---|---|---|---|---|---|
| AA001 | arrival | R1 | G1 | 0 | 1200 |
| AA002 | departure | R2 | G2 | 0 | 1200 |
| AA004 | departure | R2 | G4 | 1320 | 2520 |
| AA003 | arrival | R1 | G3 | 1380 | 2580 |

Key derivations:
- AA004 on R2: R2 last was departure → departure sep=120 → `1200+120=1320`; G4 is free; `t=1320`.
- AA003 on R1: R1 last was arrival → arrival sep=180 → `1200+180=1380`; G1 turnaround `1200+300=1500 > 1380`, G2 turnaround `1200+300=1500 > 1380`, G3 is free at 0 → `t=1380`. Lex tie-break: R1 < R2 and G3 < G4.

These exact results are the architecture's VS-1 walkthrough — confirm your implementation matches.

### Testing Patterns (from existing test files)

All test files use the same pattern:

```python
import pytest
from atc_mcp.config import load_config
from atc_mcp.domain.models import Flight, FlightState, OperationType, Priority, Placement
from atc_mcp.scheduler.algorithm import schedule

@pytest.fixture(autouse=True)
def reset_state(valid_env):
    state.reset()
    yield
    state.reset()
```

The `valid_env` fixture (from `conftest.py`) sets all `ATC_*` env vars via `monkeypatch.setenv`.

For scheduler tests, get a config via:
```python
from atc_mcp.config import load_config
config = load_config()  # within valid_env fixture scope
```

### Test Cases Required by AC

1. **Single arrival at t=0:** One arrival flight → placed at `(R1, G1, 0, 1200)`.
2. **Same-runway arrivals respect separation:** Two arrivals on same runway → second starts at `first.end_sec + runway_sep_landing_sec`.
3. **Same-gate departures respect turnaround:** Two departures sharing a gate → second starts at `first.end_sec + gate_turnaround_sec`.
4. **Mixed op-type uses mixed separation:** Arrival then departure on same runway → sep = `runway_sep_mixed_sec`.
5. **Runway-requirement matching:** One flight needs 4500m min, runways are 3500m/3000m → unschedulable with exact reason; other flight (no req) → scheduled normally.
6. **Horizon overflow:** Set `ATC_SCHEDULING_HORIZON_SEC` small enough that `t + duration > horizon` → `unscheduled_reason == "would exceed scheduling horizon"`.
7. **Priority ordering:** High-priority flight submitted AFTER low-priority flight; single runway → high gets earlier slot.

Hint for horizon test: use `monkeypatch.setenv("ATC_SCHEDULING_HORIZON_SEC", "100")` with `duration_arrival_sec=1200` so the first flight overflows.

### Learnings from Previous Stories

- **Pydantic `.model_copy(update={...})`** is the established pattern for producing updated frozen model instances (used in `tools.py` Story 2.2 for `cancel_flight`).
- **`model_dump()` vs `model_dump(mode="json")`**: use `mode="json"` when producing JSON-serializable dicts (converts enums to strings); use plain `.model_dump()` when working internally with Python objects.
- **`state.reset()` in autouse fixture**: the pattern used in all test files — both before yield AND after yield for clean isolation.
- **`test_imports.py` does an AST walk**: adding a `from atc_mcp.config import Config` import in `scheduler/algorithm.py` is fine — AST sees `atc_mcp` as the top-level, not `os`. This passes all import discipline tests.
- **All 86+ tests must continue to pass** — `tests/test_imports.py` will automatically scan the new scheduler files.
- **`ruff check`** is used in this project — follow PEP 8 naming; private helpers use `_leading_underscore`.

### Project Structure Notes

- `src/atc_mcp/scheduler/__init__.py` exists (empty, created in Story 1.1) — no changes needed
- Test file goes at `tests/test_scheduler_placement.py` — this path is implied by the story AC; it does not conflict with any existing file
- Do not create a `tests/test_scheduler_algorithm.py` — use the AC-specified name `test_scheduler_placement.py`

### References

- Architecture: `_bmad-output/planning-artifacts/architecture.md` §Scheduling Algorithm (resolves DD-4)
- Architecture: `_bmad-output/planning-artifacts/architecture.md` §Scenario Walkthroughs (VS-1, VS-2, VS-3)
- Architecture: `_bmad-output/planning-artifacts/architecture.md` §Format Patterns (reason strings)
- Architecture: `_bmad-output/planning-artifacts/architecture.md` §Ordering Patterns (determinism rules)
- Epics: `_bmad-output/planning-artifacts/epics.md` Epic 3, Story 3.1
- Domain models: `src/atc_mcp/domain/models.py` (Flight, FlightState, Placement, Schedule, OperationType, Priority)
- Config: `src/atc_mcp/config.py` (Config, Runway — note: separate Runway from domain.models.Runway)
- Time model: `src/atc_mcp/time_model.py` (Seconds = int, t=0 epoch)
- Existing tests: `tests/conftest.py` (VALID_ENV, valid_env fixture)
- Previous story: `_bmad-output/implementation-artifacts/2-3-atc-flights-resource.md` (patterns)

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

- `src/atc_mcp/scheduler/algorithm.py` — updated: implement `schedule()` pure function
- `src/atc_mcp/scheduler/constraints.py` — updated: implement constraint helper functions
- `tests/test_scheduler_placement.py` — created: 7+ test cases for placement logic

---

**Story Status:** ready-for-dev
**Last Updated:** 2026-05-21
**Context Engine:** Ultimate BMad Method story context completed
