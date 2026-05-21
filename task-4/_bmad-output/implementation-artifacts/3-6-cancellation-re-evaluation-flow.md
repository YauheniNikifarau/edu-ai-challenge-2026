---
story_id: "3.6"
story_key: "3-6-cancellation-re-evaluation-flow"
epic: "Epic 3: Deterministic Scheduling Engine & Airport Operations"
title: "Cancellation Re-Evaluation Flow with `dependents_reevaluated`"
status: "ready-for-dev"
created: "2026-05-21"
dependencies: ["2.2", "3.1", "3.2", "3.3", "3.4", "3.5"]
---

# Story 3.6: Cancellation Re-Evaluation Flow with `dependents_reevaluated`

Status: ready-for-dev

## Story

As an AI client,
I want cancelling a flight to re-evaluate its dependents and report the cascade,
So that I always know which downstream operations changed state as a result of my action (FR-SCH-7).

## Acceptance Criteria

1. **AC-1 — Cancel triggers re-schedule.** Given a scheduled flight `F` with downstream dependents `D1, D2`, when I call `cancel_flight({flight_number: "F"})`, then `F.state` is set to `FlightState.cancelled` (Story 2.2 behavior preserved), `generate_schedule` is invoked internally, and `AppState.latest_schedule` is replaced with the new schedule.

2. **AC-2 — `dependents_reevaluated` populated.** The response payload's `dependents_reevaluated` is a list of `{flight_number, previous_state, new_state, reason}` for **every flight whose state changed** as a result of the cancellation. The list is sorted by `flight_number` lex ascending.

3. **AC-3 — `reason` field.** `reason` equals the new `unscheduled_reason` string when `new_state == "unschedulable"`, and `null` for all other state transitions.

4. **AC-4 — No-dependent case.** When the cancelled flight has no dependents, `dependents_reevaluated` is `[]` and the re-schedule still occurs; `AppState.latest_schedule` is updated to reflect the removal.

5. **AC-5 — Re-cancellation preserved.** The Story 2.2 re-cancellation error `"flight F is already cancelled"` is unchanged; the cascade does NOT run when an already-cancelled flight is targeted.

6. **AC-6 — Architecture-pinned response shape.**
   ```json
   {
     "cancelled": "AA123",
     "dependents_reevaluated": [
       {
         "flight_number": "AA456",
         "previous_state": "scheduled",
         "new_state": "unschedulable",
         "reason": "dependency AA123 is not scheduled"
       }
     ]
   }
   ```

7. **AC-7 — Test coverage.** `tests/test_cancel_reevaluation.py` covers all four scenarios listed in the epics:
   - Cancel root of a chain → all dependents become `unschedulable` with correct reason
   - Cancel leaf → `dependents_reevaluated: []`
   - Cancel middle of a diamond → only true dependents reported
   - Cancel a scheduled flight that frees crew/runway → previously-unschedulable flight becomes `scheduled` (state change reported)

## Tasks / Subtasks

- [ ] **Task 1 — Extend `cancel_flight` in `tools.py`** (AC: 1, 2, 3, 4, 5, 6)
  - [ ] Capture `prev_states: dict[str, FlightState]` = `{fn: f.state for fn, f in state.flights.items()}` **before** any mutation.
  - [ ] Perform Story 2.2 mutation: `state.flights[fn] = flight.model_copy(update={"state": FlightState.cancelled, "unscheduled_reason": None})`.
  - [ ] Call the shared internal scheduling function established in Story 3.4 (e.g., `_run_schedule(config)` or equivalent) to update `AppState.latest_schedule` and mutate all flight states.
  - [ ] Compute `dependents_reevaluated`: iterate `state.flights.items()`, collect entries where `state.flights[fn].state != prev_states[fn]` and `fn != data.flight_number`, build `{flight_number, previous_state, new_state, reason}` dicts.
  - [ ] Set `reason = state.flights[fn].unscheduled_reason` when `new_state == FlightState.unschedulable`, else `None`.
  - [ ] Sort `dependents_reevaluated` by `flight_number` lex (`sorted(..., key=lambda x: x["flight_number"])`).
  - [ ] Return `{"cancelled": data.flight_number, "dependents_reevaluated": dependents_reevaluated}`.

- [ ] **Task 2 — Create `tests/test_cancel_reevaluation.py`** (AC: 7)
  - [ ] Add `setup_function(function)` that calls `state.reset()`.
  - [ ] Add a local helper that loads config via `valid_env` fixture or manually sets env vars + calls `load_config()`.
  - [ ] **Test 1 — `test_cancel_root_of_chain`:** Submit `A → B → C` (B depends on A, C depends on B). Schedule. Cancel A. Assert B and C are `unschedulable`, reason `"dependency <X> is not scheduled"`. Assert `dependents_reevaluated` contains entries for both B and C sorted by `flight_number`.
  - [ ] **Test 2 — `test_cancel_leaf`:** Submit standalone flight (no other flight depends on it). Schedule. Cancel it. Assert `dependents_reevaluated == []`. Assert `AppState.latest_schedule` is updated.
  - [ ] **Test 3 — `test_cancel_middle_of_diamond`:** Submit `A → B`, `A → C`, `D` depends on both `B` and `C`. Schedule. Cancel `B`. Assert only `D` appears in `dependents_reevaluated` (not `A`, not `C`, not `B` itself).
  - [ ] **Test 4 — `test_cancel_frees_resource`:** Configure server tightly (1 runway, 1 gate, 1 ground crew, horizon just enough for 2 flights). Submit `F1` (high priority) and `F2` (unschedulable due to crew contention). Schedule — `F2` becomes `unschedulable`. Cancel `F1`. Assert `F2` is now `scheduled` and `dependents_reevaluated` contains `F2` with `previous_state="unschedulable"`, `new_state="scheduled"`, `reason=null`.

- [ ] **Task 3 — Smoke verify**
  - [ ] `pytest -q tests/test_cancel_reevaluation.py` — all new tests pass.
  - [ ] `pytest -q` — zero regressions (full suite passes).

## Dev Notes

### Critical: How `cancel_flight` Calls the Scheduler

Story 3.4 wires `generate_schedule` as a tool handler. To avoid duplicating algorithm invocation logic, Story 3.4 **must** expose a private internal function (e.g., `_run_schedule(config: Config) -> dict`) that:
1. Calls `scheduler.algorithm.schedule(tuple(state.flights.values()), config)`
2. Calls `state.replace_flights_after_schedule(updated_flights)` to update flight states
3. Calls `state.set_latest_schedule(schedule)` to persist the new schedule
4. Returns the schedule payload dict

Both `generate_schedule()` and `cancel_flight()` call `_run_schedule(config)`. **Do NOT** copy-paste the scheduling logic into `cancel_flight` — that is the primary wheel-reinvention risk for this story.

If Story 3.4 did not extract `_run_schedule`, refactor it here before adding the cascade logic.

### `config` Availability in `cancel_flight`

By Story 3.4, `config` is loaded at server startup and accessible in `tools.py`. Confirm the mechanism Story 3.4 used (e.g., module-level `_config: Config` variable set by `server.py`, or passed as a closure). Use exactly the same pattern — do not call `load_config()` inside the tool handler.

### Exact `dependents_reevaluated` Computation

```python
prev_states = {fn: f.state for fn, f in state.flights.items()}

# … cancel the flight, run _run_schedule(config) …

dependents_reevaluated = []
for fn, flight in state.flights.items():
    if fn == data.flight_number:
        continue  # skip the cancelled flight itself
    if flight.state != prev_states[fn]:
        dependents_reevaluated.append({
            "flight_number": fn,
            "previous_state": str(prev_states[fn]),
            "new_state": str(flight.state),
            "reason": flight.unscheduled_reason if flight.state == FlightState.unschedulable else None,
        })
dependents_reevaluated.sort(key=lambda x: x["flight_number"])
```

**Important:** capture `prev_states` before mutating `state.flights`. `state.replace_flights_after_schedule()` replaces the entire dict, so any reference captured after that call reflects the new state.

### Architecture-Pinned Response Shape

From `architecture.md §Cancellation Re-evaluation Flow`:

```json
{
  "cancelled": "AA123",
  "dependents_reevaluated": [
    {"flight_number": "AA456", "previous_state": "scheduled",
     "new_state": "unschedulable",
     "reason": "dependency AA123 is not scheduled"}
  ]
}
```

**Note:** The epics story 3.6 AC also says "the response also includes the updated full schedule snapshot (architecture-pinned shape)." However, the architecture's pinned cancel response shape shows only `cancelled` and `dependents_reevaluated`. **Follow the architecture-pinned shape** — it is the authoritative contract. AI clients that want the new schedule can call `generate_schedule` or read `atc://timeline`.

### `dependents_reevaluated` Items — `reason` Field

| `new_state`      | `reason` value                                      |
|-----------------|-----------------------------------------------------|
| `unschedulable` | `flight.unscheduled_reason` (from scheduler output) |
| `scheduled`     | `null`                                              |
| `queued`        | `null` (flights reset to queued on re-schedule)     |
| `cancelled`     | Never appears — only the target is cancelled here   |

### Story 2.2 Error Behavior Must Be Preserved

The following two `McpError` raises in `cancel_flight` must remain untouched:
```python
if flight is None:
    raise McpError(ErrorData(code=INVALID_PARAMS, message=f"flight {data.flight_number} does not exist"))
if flight.state == FlightState.cancelled:
    raise McpError(ErrorData(code=INVALID_PARAMS, message=f"flight {data.flight_number} is already cancelled"))
```
The cascade logic runs **only** on the happy path after both guards pass.

### State Mutation — Frozen Models

`Flight` is `ConfigDict(frozen=True)`. The scheduler updates flight states by building a new `dict[str, Flight]` and calling `state.replace_flights_after_schedule(updated_flights)`. The `state.flights[data.flight_number]` direct assignment from Story 2.2 still handles the cancellation mutation before the re-schedule run; the scheduler then picks up the cancelled state and resolves dependents correctly.

### Existing `cancel_flight` Code (Story 2.2)

Current implementation in `src/atc_mcp/tools.py:58-67`:
```python
def cancel_flight(data: CancelFlightInput) -> dict:
    """Cancel a flight and re-evaluate dependents."""
    flight = state.get_flight(data.flight_number)
    if flight is None:
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"flight {data.flight_number} does not exist"))
    if flight.state == FlightState.cancelled:
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"flight {data.flight_number} is already cancelled"))
    cancelled_flight = flight.model_copy(update={"state": FlightState.cancelled, "unscheduled_reason": None})
    state.flights[data.flight_number] = cancelled_flight
    return {"cancelled": data.flight_number, "dependents_reevaluated": []}
```

This story **replaces only the last `return` line** (and adds the prev_states capture before mutation + the `_run_schedule` call). The guards and mutation logic above remain identical.

### Test Setup Pattern

Follow the established pattern from `tests/test_cancel_flight.py`:
- `setup_function(function)` calls `state.reset()` for isolation.
- Tests call tool handler functions directly (no MCP transport needed).
- Load config via `monkeypatch` + `conftest.VALID_ENV` or `valid_env` fixture.

The `conftest.py` `VALID_ENV` fixture provides:
```python
ATC_RUNWAYS='[{"id":"R1","length_m":3500},{"id":"R2","length_m":3000}]'
ATC_GATE_COUNT=4, ATC_GROUND_CREW_COUNT=3
ATC_RUNWAY_SEP_TAKEOFF_SEC=120, ATC_RUNWAY_SEP_LANDING_SEC=180, ATC_RUNWAY_SEP_MIXED_SEC=240
ATC_GATE_TURNAROUND_SEC=300, ATC_DEPENDENCY_BUFFER_SEC=600
ATC_SCHEDULING_HORIZON_SEC=86400
ATC_DURATION_ARRIVAL_SEC=1200, ATC_DURATION_DEPARTURE_SEC=1200
```

For Test 4 (frees resource), override with tighter constraints directly via `monkeypatch`.

### Import Discipline

`tools.py` already imports:
- `from mcp.shared.exceptions import McpError`
- `from mcp.types import INVALID_PARAMS, ErrorData`
- `from atc_mcp.domain.models import Flight, FlightState, OperationType, Priority, RunwayRequirements`
- `from atc_mcp.domain.state import state`

For this story, add `FlightState` to the comparison (already imported). Ensure `config` access follows the Story 3.4 pattern (no new imports of `os` or `config.py` inside `cancel_flight`).

### Anti-Patterns to Avoid

- **Do NOT** call `generate_schedule()` (the tool handler) from `cancel_flight` — that returns the tool's JSON response dict and re-enters error handling. Call the internal shared function `_run_schedule(config)` instead.
- **Do NOT** capture `prev_states` after `state.replace_flights_after_schedule()` — it will reflect the new state, making all diffs empty.
- **Do NOT** include the cancelled flight itself in `dependents_reevaluated` — skip it with `if fn == data.flight_number: continue`.
- **Do NOT** use `set` iteration over flight keys — `state.flights` is insertion-ordered `dict`, iterate `.items()` directly.
- **Do NOT** add new fields to the cancel response beyond the architecture-pinned shape (`cancelled`, `dependents_reevaluated`).

### Project Structure Notes

- **File to modify:** `src/atc_mcp/tools.py` (only `cancel_flight` function)
- **File to create:** `tests/test_cancel_reevaluation.py` (new, 4 test functions)
- **Do NOT** modify `domain/models.py`, `domain/state.py`, or `scheduler/algorithm.py` for this story — those are owned by earlier stories.
- `tests/test_cancel_flight.py` (Story 2.2) must continue to pass unchanged.

### References

- Architecture: `_bmad-output/planning-artifacts/architecture.md` §Cancellation Re-evaluation Flow
- Architecture: `_bmad-output/planning-artifacts/architecture.md` §MCP Tool Catalog: `cancel_flight`
- Epics: `_bmad-output/planning-artifacts/epics.md` Epic 3, Story 3.6
- Prior story: `_bmad-output/implementation-artifacts/2-2-cancel-flight-tool.md` §Dev Agent Record
- Current implementation: `src/atc_mcp/tools.py:58-67`
- State seam: `src/atc_mcp/domain/state.py`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-5-20260521

### Debug Log References

### Completion Notes List

### File List

- `src/atc_mcp/tools.py` — modified: extend `cancel_flight` with prev_state capture, `_run_schedule` call, `dependents_reevaluated` computation
- `tests/test_cancel_reevaluation.py` — created: 4 test cases covering the cascade scenarios
