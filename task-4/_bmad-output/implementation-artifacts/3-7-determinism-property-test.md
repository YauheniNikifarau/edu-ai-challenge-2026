---
story_id: "3.7"
story_key: "3-7-determinism-property-test"
epic: "Epic 3: Deterministic Scheduling Engine & Airport Operations"
title: "Determinism Property Test (100-Run Byte-Identical)"
status: "ready-for-dev"
created: "2026-05-21"
dependencies: ["3.1", "3.2", "3.3", "3.4"]
---

# Story 3.7: Determinism Property Test (100-Run Byte-Identical)

## User Story

**As a** maintainer,
**I want** a property test that asserts the scheduling pipeline produces byte-identical output across many runs with identical input,
**So that** determinism (NFR-3, FR-SCH-6) is enforced automatically and any future regression is caught immediately.

## Business Context

Determinism is a first-class non-functional requirement (NFR-3, FR-SCH-6). The architecture makes an explicit determinism argument covering sort key total-ordering, lex tie-breaks at every choice point, integer-only arithmetic, banned wall-clock/RNG reads, and sorted iteration at every output boundary. This property test is the machine-checkable enforcement of that argument — it will catch any future slip (an unsorted set iteration, a newly introduced `random` call, a `dict` ordering assumption) instantly, before it reaches production.

This story is the capstone of Epic 3. It only creates one test file but is a mandatory deliverable alongside the scheduler implementation.

## Acceptance Criteria

**Given** `generate_schedule` is fully wired (Stories 3.1–3.4 complete)
**When** I run `tests/test_determinism.py`
**Then** the test builds a non-trivial fixture (≥10 flights, mixed priorities, at least one dependency chain, at least one runway-requirement-binding flight) configured to produce both scheduled **and** unschedulable outcomes
**And** it calls `scheduler.algorithm.schedule()` (the pure function) 100 times with the same `tuple[Flight, ...]` and `Config`, serialising the full output to canonical JSON via `json.dumps(..., sort_keys=True, separators=(",", ":"))`
**And** all 100 serialised strings are byte-identical — asserted via `assert len({results}) == 1`
**And** the test also asserts byte-identical output for `atc://flights`, `atc://timeline`, `atc://runways` resource payloads across 100 reads from the same fixed state
**And** the test runs in under 5 seconds
**And** any introduction of `time.time()`, `datetime.now()`, `random`, or unsorted `set` iteration into `scheduler/` or `domain/` causes either `tests/test_imports.py` or this test to fail

## Technical Requirements

### Architecture Compliance

**From architecture.md §Ordering Patterns (Determinism Enforcement):**

> These are not stylistic — they are correctness rules tied to FR-SCH-6.

- Every list returned to MCP is sorted before emission; sort keys documented per list in architecture.
- `set` iteration **never** drives output; `sorted(my_set)` or explicitly ordered structures only.
- Property test in `tests/test_determinism.py` asserts byte-identical `(schedule, unscheduled, completion_time_seconds)` across 100 runs.

**From architecture.md §Scheduling Algorithm (resolves DD-4):**

Determinism argument is explicit:
1. Inputs sorted by total order `(topo_depth, priority_rank, flight_number)` — `flight_number` is unique.
2. Runway/gate iteration is lex-sorted `(runway_id, gate_id)` — no hash/set iteration drives output.
3. Time math is pure integer arithmetic — no floats, no rounding.
4. Tie-breaks at every choice point are lex on stable string IDs.
5. No `random`, no time-seeded RNG, no wall-clock reads.
6. Cycle detection uses sorted DFS — unschedulable list order is deterministic.
7. `dict` and `list` iteration are insertion-ordered (Python 3.7+); `set` **never** iterated for output.

**From epics.md Story 3.7 AC:**

> The test also asserts byte-identical output for `atc://flights`, `atc://timeline`, `atc://runways` payloads across the same 100 iterations.

**Banned imports in `scheduler/` and `domain/` (enforced by `tests/test_imports.py`):**
- `time`, `datetime`, `random` — already tested by `test_scheduler_no_time_datetime_random()` and `test_domain_no_time_datetime_random()`

### Test Structure

The test file has two logical phases:

**Phase 1 — Pure-function schedule() determinism (100 runs):**
- Call `scheduler.algorithm.schedule(flights_tuple, config)` directly — it is a pure function.
- No state mutation involved; same inputs must produce byte-identical output.
- Serialize each `Schedule` result to canonical JSON.
- Assert `len(set(serialised_results)) == 1`.

**Phase 2 — Resource function determinism (100 reads from fixed state):**
- Set up `state` with the scheduled/unschedulable flight states (using the result from Phase 1).
- Call `flights_resource()`, `timeline_resource()`, `runways_resource()` 100 times each on **unchanged** state.
- Assert byte-identical outputs for all three.

### Fixture Design Requirements

The fixture **MUST** satisfy all of the following — the test is useless if it does not exercise every determinism path:

| Requirement | Why |
|---|---|
| ≥ 10 flights | Tests sort stability under volume |
| Mixed `high`, `medium`, `low` priority | Exercises `priority_rank` sort key |
| At least one 3-flight dependency chain (A → B → C) | Exercises `topo_depth` sort key + dep-buffer floor |
| At least one 2-flight dependency chain | Tests chain-length variety |
| At least one flight with `runway_requirements.min_length_m` that restricts to one runway | Exercises runway-filter path + lex `(runway_id, gate_id)` tie-break |
| At least one flight with `runway_requirements.min_length_m` exceeding ALL runways | Exercises unschedulable path with reason string |
| Both scheduled **and** unschedulable outcomes in the same run | Tests that `unscheduled` list ordering is also deterministic |

**Reference config** (matches `conftest.VALID_ENV`):
```
runways: R1(3500m), R2(3000m)
gate_count=4, ground_crew_count=3
runway_sep_takeoff_sec=120, runway_sep_landing_sec=180, runway_sep_mixed_sec=240
gate_turnaround_sec=300, dependency_buffer_sec=600, scheduling_horizon_sec=86400
duration_arrival_sec=1200, duration_departure_sec=1200
```

**Suggested 12-flight fixture** (use this exact fixture for reproducibility across dev/CI):

| Flight | Op | Priority | Dependencies | `min_length_m` | Expected outcome |
|---|---|---|---|---|---|
| DET01 | arrival | high | — | — | scheduled |
| DET02 | departure | high | — | — | scheduled |
| DET03 | arrival | medium | — | — | scheduled |
| DET04 | departure | medium | `[DET01]` | — | scheduled (chain: DET01→DET04) |
| DET05 | arrival | low | — | — | scheduled |
| DET06 | departure | low | `[DET04]` | — | scheduled (chain: DET01→DET04→DET06) |
| DET07 | arrival | medium | `[DET03]` | — | scheduled (chain: DET03→DET07) |
| DET08 | departure | high | — | 3200 | scheduled on R1 only (R1=3500≥3200, R2=3000<3200) |
| DET09 | departure | high | — | 4000 | **unschedulable** (no runway ≥ 4000) |
| DET10 | arrival | low | — | — | scheduled |
| DET11 | departure | medium | — | — | scheduled |
| DET12 | arrival | high | — | — | scheduled |

This fixture produces: scheduled flights on both runways across all 4 gates, 3-flight chain (DET01→DET04→DET06), 2-flight chain (DET03→DET07), runway-bound placement (DET08 forced to R1), and 1 unschedulable flight (DET09) with exact reason string.

### Serialisation Format

Canonical serialisation for phase 1 comparison:

```python
import json

def canonical(schedule) -> str:
    return json.dumps(
        {
            "placements": [p.model_dump() for p in schedule.placements],
            "unscheduled": [
                {"flight_number": f.flight_number, "reason": f.unscheduled_reason}
                for f in schedule.unscheduled
            ],
            "completion_time_seconds": schedule.completion_time_seconds,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
```

The `sort_keys=True` is belt-and-suspenders for nested dicts; the real determinism guarantee must come from the algorithm itself, not from JSON key sorting.

### Config Construction

Build `Config` directly — **do not** use `load_config()` in the property test body, as env-var access belongs only in `config.py`. Use the `valid_env` fixture from `conftest.py` + `load_config()`, OR construct the `Config` Pydantic model directly from `atc_mcp.config`:

```python
from atc_mcp.config import Config, Runway as ConfigRunway

_CONFIG = Config(
    runways=(ConfigRunway(id="R1", length_m=3500), ConfigRunway(id="R2", length_m=3000)),
    gate_count=4,
    ground_crew_count=3,
    runway_sep_takeoff_sec=120,
    runway_sep_landing_sec=180,
    runway_sep_mixed_sec=240,
    gate_turnaround_sec=300,
    dependency_buffer_sec=600,
    scheduling_horizon_sec=86400,
    duration_arrival_sec=1200,
    duration_departure_sec=1200,
)
```

`Config` is a frozen Pydantic model; constructing it directly bypasses env-var reads and keeps the test hermetic. This is the preferred approach for a pure-function property test.

### Module Dependency Rules

`tests/test_determinism.py` imports:
- `from atc_mcp.scheduler.algorithm import schedule` — pure function under test
- `from atc_mcp.config import Config, Runway as ConfigRunway` — config value type
- `from atc_mcp.domain.models import Flight, FlightState, OperationType, Priority, RunwayRequirements`
- `from atc_mcp.domain.state import state` — for Phase 2 resource testing
- `from atc_mcp.resources import flights_resource, runways_resource, timeline_resource` — Phase 2

These imports are **all legal**: tests are not `domain/` or `scheduler/` modules, so they may import anything.

## Implementation Guidance

### File to Create

**CREATE:** `tests/test_determinism.py`

### Implementation Steps

1. **Build the fixture** as a module-level constant or pytest fixture:
   - Construct the 12 `Flight` objects using the table above.
   - Pack them into a `tuple[Flight, ...]` in submission order (DET01..DET12).
   - Construct `_CONFIG` directly (see Config Construction above).

2. **Phase 1 — Pure function, 100 runs:**
   ```python
   def test_schedule_output_is_byte_identical_100_runs():
       results = [canonical(schedule(_FLIGHTS, _CONFIG)) for _ in range(100)]
       assert len(set(results)) == 1, "schedule() output is not deterministic"
   ```

3. **Phase 2 — Resource functions, 100 reads:**
   - Call `schedule(_FLIGHTS, _CONFIG)` once to obtain a `Schedule`.
   - Update `state` to reflect the result: use `state.reset()`, add all flights via `state.add_flight()`, call `state.replace_flights_after_schedule()` with updated `Flight` objects (states set to `scheduled` / `unschedulable` from the schedule result), call `state.set_latest_schedule(sched)`.
   - Call each resource function 100 times on the unchanged state.

   ```python
   def test_resources_are_byte_identical_100_reads(det_state):
       flights_outputs = {flights_resource() for _ in range(100)}
       assert len(flights_outputs) == 1, "atc://flights not deterministic"

       timeline_outputs = {timeline_resource() for _ in range(100)}
       assert len(timeline_outputs) == 1, "atc://timeline not deterministic"

       runways_outputs = {runways_resource() for _ in range(100)}
       assert len(runways_outputs) == 1, "atc://runways not deterministic"
   ```

4. **State setup helper** (pytest fixture `det_state`):
   ```python
   @pytest.fixture
   def det_state():
       state.reset()
       for f in _FLIGHTS:
           state.add_flight(f)
       sched = schedule(_FLIGHTS, _CONFIG)
       # build updated_flights: merge placement results back into Flight objects
       placed = {p.flight_number for p in sched.placements}
       unscheduled_map = {f.flight_number: f for f in sched.unscheduled}
       updated = {}
       for fn, flight in state.flights.items():
           if fn in placed:
               updated[fn] = flight.model_copy(update={"state": FlightState.scheduled})
           elif fn in unscheduled_map:
               updated[fn] = unscheduled_map[fn]
           else:
               updated[fn] = flight
       state.replace_flights_after_schedule(updated)
       state.set_latest_schedule(sched)
       yield
       state.reset()
   ```

5. **Performance guard**: The test should be marked with a comment that it targets < 5 s. With 300 resource calls + 100 pure-function calls against a 12-flight fixture, this is trivially fast.

### Testing Requirements

**CREATE:** `tests/test_determinism.py`

Test functions to implement (minimum set):

| Test function | Asserts |
|---|---|
| `test_schedule_output_is_byte_identical_100_runs` | `schedule()` is byte-identical across 100 calls with same inputs |
| `test_resources_are_byte_identical_100_reads` | `flights_resource()`, `timeline_resource()`, `runways_resource()` each byte-identical across 100 reads |
| `test_unscheduled_flight_present_in_fixture` | DET09 is in `Schedule.unscheduled` with reason matching `"no runway meets minimum length 4000m"` (sanity check that fixture is non-trivial) |
| `test_scheduled_flight_count_matches_expected` | 11 flights scheduled, 1 unschedulable — verifies fixture produces the expected outcome |

### Integration Points

**Upstream dependencies (all must be done before running this test):**
- Story 3.1: `scheduler/algorithm.py` exposes `schedule(flights, config) -> Schedule` with placement, separation, gate turnaround, runway matching, horizon
- Story 3.2: Dependency ordering with buffer and cycle detection wired into `schedule()`
- Story 3.3: Ground-crew capacity invariant wired into `schedule()`
- Story 3.4: `generate_schedule` tool wired; `runways_resource()` and `timeline_resource()` fully implemented (not stubs)

**No source-code changes required by this story.** This story only creates `tests/test_determinism.py`. All production code changes happen in 3.1–3.4.

## Definition of Done

- [ ] `tests/test_determinism.py` created
- [ ] Fixture has ≥ 10 flights meeting all requirements from the table above (mixed priorities, dep chains, runway-binding, unschedulable)
- [ ] `test_schedule_output_is_byte_identical_100_runs` passes
- [ ] `test_resources_are_byte_identical_100_reads` passes (all three resources)
- [ ] `test_unscheduled_flight_present_in_fixture` sanity check passes
- [ ] `test_scheduled_flight_count_matches_expected` sanity check passes
- [ ] All existing tests still pass (zero regressions)
- [ ] Whole test suite completes in < 5 s (property test alone well under 1 s)
- [ ] No forbidden imports in test file: `os.environ`, `random`, `time`, `datetime` must not be used in the test body itself

## Notes for Developer

### Critical Implementation Details

1. **Call the pure function, not the tool handler.** `tools.generate_schedule()` mutates `AppState.latest_schedule` and likely loads config from a module-level reference. For the property test, call `scheduler.algorithm.schedule(flights_tuple, config)` directly. This is the correct level of abstraction — you are testing the algorithm, not the MCP adapter.

2. **The fixture order matters for determinism.** The sort key includes `flight_number` as the final tie-breaker. The fixture flight numbers are `DET01`..`DET12` — lex ordering is stable and predictable. Do not randomise submission order in the property test.

3. **`set` of serialised strings is the assertion mechanism.** `len({s1, s2, ..., s100}) == 1` is both concise and correct. If the algorithm is non-deterministic even once, the set size grows above 1 and the test fails immediately.

4. **State isolation.** The `det_state` fixture must call `state.reset()` in setup AND teardown (yield fixture). Otherwise a prior test that left `state.flights` populated will pollute the resource-function reads. Follow the pattern from existing tests (see `test_cancel_flight.py` and `test_flights_resource.py` which also mutate `state` and reset it).

5. **`model_dump()` is the right serialiser.** It converts `StrEnum` → string literal, `None` → JSON `null`, and `list` → JSON array, matching the MCP surface convention. Do not use `dict()` (Pydantic v1 legacy) or custom serialisers.

6. **`Placement.model_dump()` order.** Because `Placement` is a Pydantic frozen model, `model_dump()` always returns fields in declaration order. With `sort_keys=True` in `json.dumps`, any key ordering is also normalised. This double-coverage is intentional.

7. **Resource functions after Story 3.4 need config.** `runways_resource()` requires knowledge of the runway list (from `Config`) to report all runways, including ones with no placements. Check how Story 3.4 wires this (module-level config variable in `resources.py`, or config stored in `AppState`, or a closure). The test fixture setup must match — for example, if `resources.py` exposes a `set_config(cfg)` call, invoke it with `_CONFIG` before Phase 2.

8. **Reason string case.** Architecture mandates lowercase reason strings (`"no runway meets minimum length…"` not `"No runway…"`). The sanity-check test `test_unscheduled_flight_present_in_fixture` must check for the lowercase form. The exact architecture-pinned format (from `epics.md Story 3.1 AC`) is:
   ```
   "no runway meets minimum length <N>m (available runways: <id> <len>m, ...)"
   ```
   So for DET09 with `min_length_m=4000` and config runways R1(3500m) R2(3000m):
   ```
   "no runway meets minimum length 4000m (available runways: R1 3500m, R2 3000m)"
   ```

### Common Pitfalls to Avoid

❌ **Don't** call `tools.generate_schedule()` 100 times — it mutates state and may have config-wiring assumptions. Test the pure `schedule()` function instead.

❌ **Don't** use `==` comparison on `Schedule` objects directly — Pydantic frozen model equality compares field-by-field which is correct, but the canonical JSON approach is more robust and matches the spec's "byte-identical" language.

❌ **Don't** assert on a single run first and then run 100 times — the property test must run 100 times unconditionally so CI cannot be tricked by a lucky single run.

❌ **Don't** skip the resource test phase — the spec explicitly requires `atc://flights`, `atc://timeline`, `atc://runways` to be covered.

❌ **Don't** forget `state.reset()` in teardown — state pollution is the most common source of spurious test failures across Epic 3 stories.

❌ **Don't** import `os` or `random` in the test file — even though it would not violate the `test_imports.py` rules (which only cover `src/atc_mcp/`), it would be bad practice and could confuse future reviewers about the determinism intent.

### Why This Test Catches Real Bugs

The canonical failure modes that this test will catch:

| Bug | How detected |
|---|---|
| `for flight in set(state.flights.values())` in scheduler | Set hash randomisation → inconsistent sort order → different schedule |
| `datetime.now()` used as tiebreak | Wall-clock changes between runs → different placement |
| `random.shuffle` applied to candidates | Direct RNG usage → different placements |
| Missing `sorted()` call on resource output list | Dict insertion order can shift across Python minor versions |
| Float arithmetic in time calculations | Floating-point rounding non-determinism between invocations |

## Related Documentation

- Architecture: `_bmad-output/planning-artifacts/architecture.md` §Ordering Patterns, §Scheduling Algorithm (DD-4), §Enforcement Guidelines
- Epics: `_bmad-output/planning-artifacts/epics.md` Epic 3, Story 3.7
- Scheduling pure function: `src/atc_mcp/scheduler/algorithm.py` (implemented in Stories 3.1–3.3)
- Resource functions: `src/atc_mcp/resources.py` (fully implemented in Stories 2.3 + 3.4)
- State seam: `src/atc_mcp/domain/state.py`
- Domain models: `src/atc_mcp/domain/models.py`
- Existing import-discipline test: `tests/test_imports.py`
- Conftest fixtures: `tests/conftest.py` (VALID_ENV values match `_CONFIG` above)

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

- `tests/test_determinism.py` — created

### Change Log

---

**Story Status:** ready-for-dev
**Last Updated:** 2026-05-21
**Context Engine:** Ultimate BMad Method story context completed
