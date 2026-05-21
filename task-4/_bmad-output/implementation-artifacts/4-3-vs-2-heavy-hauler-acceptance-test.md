# Story 4.3: VS-2 Heavy Hauler Acceptance Test

Status: ready-for-dev

## Story

As a product stakeholder,
I want the Heavy Hauler scenario from `spec.md §9` to pass automatically,
so that I have machine-checkable evidence the system reports runway-requirement failures without breaking other flights.

## Acceptance Criteria

1. **Config fixture**: test uses runways `[{"id":"R1","length_m":3500},{"id":"R2","length_m":3000}]` — matches `conftest.py` `VALID_ENV` exactly; no custom env setup needed.
2. **Heavy hauler submission**: one high-priority departure with `runway_requirements: {min_length_m: 4500}` is submitted (no runway in the config meets 4500m).
3. **Valid flights**: ≥ 3 other flights (mix of arrivals/departures, any priorities) that CAN be scheduled on R1 or R2 are submitted alongside the heavy hauler.
4. **After `generate_schedule` runs**: the heavy flight's `state == FlightState.unschedulable` and `unscheduled_reason` is exactly `"no runway meets minimum length 4500m (available runways: R1 3500m, R2 3000m)"` (lowercase, no trailing period, runways in lex id order).
5. **No collateral damage**: all other valid flights reach `state == FlightState.scheduled` after `generate_schedule`.
6. **`get_airport_status` unscheduled list**: contains the heavy flight and only the heavy flight.
7. **Determinism**: running the full submit→schedule→assert sequence 5 times in a loop produces identical `generate_schedule` output each time (compared via `json.dumps(..., sort_keys=True, separators=(",", ":"))`).

## Tasks / Subtasks

- [ ] Task 1: Create `tests/test_vs2_heavy_hauler.py` (AC: 1–7)
  - [ ] Subtask 1.1: Write `_submit_scenario()` helper that submits the heavy hauler + 3 valid flights using `SubmitFlightInput` / `submit_flight` from `atc_mcp.tools`
  - [ ] Subtask 1.2: Write `test_heavy_hauler_unschedulable` — asserts heavy flight state and exact reason string
  - [ ] Subtask 1.3: Write `test_valid_flights_all_scheduled` — asserts each valid flight reaches `FlightState.scheduled`
  - [ ] Subtask 1.4: Write `test_airport_status_unscheduled_contains_only_heavy` — asserts `get_airport_status` unscheduled list length == 1 and entry matches heavy flight number
  - [ ] Subtask 1.5: Write `test_determinism` — 5-run loop with `state.reset()` + re-submit each iteration, assert `len(set(json_results)) == 1`
  - [ ] Subtask 1.6: Add `autouse=True` fixture using `valid_env` + `state.reset()`

## Dev Notes

### Prerequisites — this story cannot pass until these are implemented

All of the following must be complete before this test can be run (they are currently `raise NotImplementedError`):

- **Story 3.1–3.3**: `scheduler/algorithm.py` + `scheduler/constraints.py` — the placement engine this test exercises.
- **Story 3.4**: `generate_schedule` tool wired in `tools.py` — calls `scheduler.algorithm.schedule()`, stores result in `AppState.latest_schedule`, updates `Flight.state` / `Flight.unscheduled_reason`.
- **Story 3.5**: `get_airport_status` tool wired in `tools.py` — returns the five-piece status payload including the unscheduled list.
- **Stories 4.1 and 4.2** are suggested predecessors (ordering in the epic) but NOT hard dependencies for this test's assertions.

### Test Pattern — Match Existing Codebase

All existing tests call tool functions **directly as Python functions** (not via MCP harness). Replicate this pattern:

```python
from atc_mcp.domain.state import state
from atc_mcp.tools import SubmitFlightInput, submit_flight, generate_schedule, get_airport_status
```

State lifecycle — use `autouse=True` fixture identical to `test_submit_flight.py`:

```python
@pytest.fixture(autouse=True)
def reset_state(valid_env):
    state.reset()
    yield
    state.reset()
```

`valid_env` is defined in `conftest.py` and uses `monkeypatch` to set `ATC_*` env vars — it is function-scoped (one fresh monkeypatch per test, including each iteration in the determinism loop).

### Config Reuse — No Custom Env Needed

`conftest.py` `VALID_ENV` already sets:
```
ATC_RUNWAYS = '[{"id":"R1","length_m":3500},{"id":"R2","length_m":3000}]'
```
This is exactly the Heavy Hauler fixture config from the epic. The test does NOT need a separate config fixture.

### Exact Reason String — Architecture-Pinned (Critical)

The reason string stored in `Flight.unscheduled_reason` and returned in `generate_schedule.unscheduled[].reason` MUST be exactly:

```
"no runway meets minimum length 4500m (available runways: R1 3500m, R2 3000m)"
```

Rules (from architecture §Format Patterns + Story 3.1 AC):
- **Lowercase** sentence (conflict: architecture §Runway Capability Schema shows uppercase "No" — the Format Patterns section and Stories 3.1/4.3 both specify lowercase; follow the format pattern rule).
- **No trailing period**.
- Runways listed in **lex ascending order by `id`** (`R1` before `R2`).
- Format: `"no runway meets minimum length <N>m (available runways: <id> <len>m, ...)"`.

### `generate_schedule` Return Shape

Per architecture §MCP Tool Catalog, `generate_schedule` returns:

```json
{
  "schedule": [<Placement>],
  "unscheduled": [{"flight_number": "HH1", "reason": "no runway meets..."}],
  "completion_time_seconds": 1200,
  "summary": {"scheduled_count": 3, "unscheduled_count": 1, "cancelled_count": 0}
}
```

Assert `result["unscheduled"]` — this is the key in `generate_schedule` output (NOT `unscheduled_flights`).

### `get_airport_status` Field Name Conflict — Needs Attention

**Architecture §get_airport_status output** uses key `"unscheduled"`.  
**Epic Story 3.5 AC** and **Story 4.3 AC** use `"unscheduled_flights"`.

The test must match whatever key name Story 3.5 actually establishes. When writing the assertion, inspect the return dict from `get_airport_status()` and use the correct key. Preferred: follow the architecture JSON shape (`"unscheduled"`) since it is the pinned source of truth for exact payload shapes.

### Flight State After `generate_schedule`

`generate_schedule` is responsible for mutating `AppState.flights` — updating each `Flight.state` and `Flight.unscheduled_reason` to reflect the scheduling outcome (per Story 3.4 AC). The test can read `state.get_flight(fn).state` directly after calling `generate_schedule()`.

### Scenario Helper Design

Submit exactly 4 flights so the assertions are simple and unambiguous:

| Flight | Type | Priority | `runway_requirements` | Expected outcome |
|---|---|---|---|---|
| `"HH1"` | departure | high | `{min_length_m: 4500}` | unschedulable |
| `"F1"` | arrival | medium | none | scheduled |
| `"F2"` | departure | low | none | scheduled |
| `"F3"` | arrival | high | none | scheduled |

`HH1` is named to convey "Heavy Hauler 1" for readability. The high priority on `HH1` is intentional — VS-2 requires that high priority alone does NOT override an impossible runway constraint.

### Determinism Test Mechanics

The `test_determinism` test must call `state.reset()` and re-submit before each `generate_schedule` call. Because `valid_env` is function-scoped via monkeypatch, env vars stay set for the entire test function duration. The loop is safe:

```python
def test_determinism():
    import json
    results = []
    for _ in range(5):
        state.reset()
        _submit_scenario()
        result = generate_schedule()
        results.append(json.dumps(result, sort_keys=True, separators=(",", ":")))
    assert len(set(results)) == 1
```

### Import Discipline — Must Not Violate

`tests/test_vs2_heavy_hauler.py` may import from:
- `atc_mcp.tools` — tool functions and input models
- `atc_mcp.domain.state` — for direct state inspection
- `atc_mcp.domain.models` — for `FlightState`, `OperationType`, etc.
- stdlib (`json`, `pytest`)
- `mcp.shared.exceptions.McpError` — only if testing error paths (none in this story)

Must NOT import from `atc_mcp.scheduler.*` or `atc_mcp.config` directly in this test.

### Project Structure Notes

- **New file**: `tests/test_vs2_heavy_hauler.py` — only deliverable for this story.
- No modifications to existing source files.
- Follows the established test layout: `tests/test_<scenario>.py` naming per architecture §Test Layout.
- No new pytest plugins or conftest additions needed; reuses `valid_env` from existing `conftest.py`.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` §Story 4.3] — acceptance criteria
- [Source: `_bmad-output/planning-artifacts/architecture.md` §Runway Capability Schema] — VS-2 behavior + reason string
- [Source: `_bmad-output/planning-artifacts/architecture.md` §Format Patterns] — lowercase reason rule
- [Source: `_bmad-output/planning-artifacts/architecture.md` §MCP Tool Catalog — `generate_schedule`] — return shape
- [Source: `_bmad-output/planning-artifacts/architecture.md` §MCP Tool Catalog — `get_airport_status`] — unscheduled field shape
- [Source: `tests/conftest.py`] — `VALID_ENV` fixture with matching runway config
- [Source: `tests/test_submit_flight.py`] — test pattern (direct function calls, `autouse=True` state reset)
- [Source: `src/atc_mcp/tools.py`] — tool function signatures (`generate_schedule()`, `get_airport_status()` take no args)
- [Source: `src/atc_mcp/domain/state.py`] — `state.reset()`, `state.get_flight()`
- [Source: `src/atc_mcp/domain/models.py`] — `FlightState` enum values

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-5

### Debug Log References

### Completion Notes List

### File List

- `tests/test_vs2_heavy_hauler.py` (NEW)
