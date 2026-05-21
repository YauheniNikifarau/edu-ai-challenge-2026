# Story 2.2: `cancel_flight` Tool (State Mutation Only)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an AI client,
I want to cancel a queued or scheduled flight,
So that I can remove it from operations; the full dependent re-evaluation cascade is handled by Epic 3 (this story only mutates the cancelled flight's own state).

## Acceptance Criteria

1. **AC-1 — Cancel queued flight.** Given a flight `F` exists in `AppState.flights` with `state = FlightState.queued`, when I call `cancel_flight({flight_number: "F"})`, then `F.state` is set to `FlightState.cancelled`, its `placement` (if any) is cleared to `None`, and `F.unscheduled_reason` is set to `None`.

2. **AC-2 — Cancel scheduled flight.** Given a flight `F` exists with `state = FlightState.scheduled`, when I call `cancel_flight({flight_number: "F"})`, then `F.state` is set to `FlightState.cancelled`, its prior placement is cleared, and `F.unscheduled_reason` is set to `None`.

3. **AC-3 — Response payload shape.** The tool returns the canonical cancellation payload in the architecture-pinned shape:
   ```json
   {
     "cancelled": "F",
     "dependents_reevaluated": []
   }
   ```
   The `dependents_reevaluated` field is an empty list in this story (the cascade is wired in Epic 3 — leave it as an empty list here, do NOT silently swallow the field).

4. **AC-4 — Re-cancel error.** Given a flight `F` with `state == FlightState.cancelled`, when I call `cancel_flight({flight_number: "F"})`, then the tool returns an MCP error with message exactly equal to `"flight F is already cancelled"` and `AppState` is unchanged.

5. **AC-5 — Unknown flight error.** When the flight does not exist in `AppState.flights`, the tool returns an MCP error with message `"flight <flight_number> does not exist"`.

6. **AC-6 — Test coverage.** `tests/test_cancel_flight.py` covers:
   - Cancel queued flight (happy path)
   - Cancel scheduled-stub flight (manually set state to `scheduled` before calling cancel)
   - Re-cancel error message string-exact match
   - Unknown-flight error
   - Payload shape conformance (includes `dependents_reevaluated: []`)

## Tasks / Subtasks

- [x] **Task 1 — Implement `cancel_flight` handler in `tools.py`** (AC: 1, 2, 3, 4, 5)
  - [x] Import `McpError` from `mcp.types` at the top of `tools.py`.
  - [x] Import `state` from `atc_mcp.domain.state`.
  - [x] Import `Flight`, `FlightState` from `atc_mcp.domain.models`.
  - [x] Replace the `raise NotImplementedError("not yet implemented")` in `cancel_flight(data: CancelFlightInput) -> dict` with the implementation.
  - [x] **Step 1 — Validate flight exists:** Call `state.get_flight(data.flight_number)`. If `None`, raise `McpError(INVALID_PARAMS, f"flight {data.flight_number} does not exist")`.
  - [x] **Step 2 — Check if already cancelled:** If `flight.state == FlightState.cancelled`, raise `McpError(INVALID_PARAMS, f"flight {data.flight_number} is already cancelled")`.
  - [x] **Step 3 — Mutate flight state:** Use `flight.model_copy(update={...})` to create a new `Flight` instance with `state=FlightState.cancelled` and `unscheduled_reason=None`. (Note: `Flight` is frozen, so you cannot mutate in place — use `model_copy()`.)
  - [x] **Step 4 — Update state:** Call `state.flights[data.flight_number] = cancelled_flight` to replace the flight in the dict.
  - [x] **Step 5 — Return payload:** Return `{"cancelled": data.flight_number, "dependents_reevaluated": []}`.

- [x] **Task 2 — Create `tests/test_cancel_flight.py`** (AC: 6)
  - [x] Import `pytest`, `state` from `atc_mcp.domain.state`, `Flight`, `FlightState` from `atc_mcp.domain.models`, `cancel_flight`, `CancelFlightInput` from `atc_mcp.tools`, `McpError` from `mcp.types`.
  - [x] Add a `setup_function(function)` that calls `state.reset()` before each test to ensure clean state.
  - [x] **Test 1 — `test_cancel_queued_flight`:** Create a queued flight, add to state, call `cancel_flight`, assert state is `cancelled`, `unscheduled_reason` is `None`, and response payload matches `{"cancelled": "...", "dependents_reevaluated": []}`.
  - [x] **Test 2 — `test_cancel_scheduled_flight`:** Create a flight with `state=FlightState.scheduled`, add to state, call `cancel_flight`, assert state is `cancelled` and payload is correct.
  - [x] **Test 3 — `test_cancel_already_cancelled_raises_error`:** Create a cancelled flight, add to state, call `cancel_flight` and assert it raises `McpError` with message exactly `"flight F is already cancelled"` (use `pytest.raises(McpError) as exc_info` and assert `str(exc_info.value.error.message) == "flight F is already cancelled"`).
  - [x] **Test 4 — `test_cancel_unknown_flight_raises_error`:** Call `cancel_flight` with a flight number that does not exist, assert it raises `McpError` with message `"flight XYZ does not exist"`.
  - [x] **Test 5 — `test_cancel_payload_shape`:** Verify the response dict has exactly two keys: `"cancelled"` and `"dependents_reevaluated"`, and `dependents_reevaluated` is an empty list.

- [x] **Task 3 — Smoke verify**
  - [x] Run `pytest -q tests/test_cancel_flight.py` and confirm all tests pass.
  - [x] Run `pytest -q` from `task-4/` and confirm no regressions in existing tests.

## Dev Notes

### What This Story Does NOT Do (Deferred to Epic 3)

**This story only mutates the cancelled flight's own state.** The full dependent re-evaluation cascade (FR-SCH-7) is handled in Epic 3 when the scheduling engine is wired. At that point, `cancel_flight` will internally call `generate_schedule()` and populate `dependents_reevaluated` with the list of flights whose state changed as a result of the cancellation.

**For this story:** `dependents_reevaluated` is always an empty list `[]`. Do NOT silently omit the field — it must be present in the response payload to match the architecture contract. Epic 3 will replace the empty list with the actual cascade results.

### Architecture Contract — Cancellation Response Shape

From `architecture.md §Cancellation Re-evaluation Flow`:

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

**For this story:** `dependents_reevaluated` is always `[]` because we do not yet call `generate_schedule()`. The field must be present in the response.

### Error Handling — MCP Error Format

From `architecture.md §Format Patterns`:

> Domain-level errors are raised as `McpError` from the SDK with code `INVALID_PARAMS` and a message of the form `"<noun>: <reason>"` — e.g., `"flight_number AA123 already exists"`.

**For this story:**
- Unknown flight: `McpError(INVALID_PARAMS, f"flight {flight_number} does not exist")`
- Already cancelled: `McpError(INVALID_PARAMS, f"flight {flight_number} is already cancelled")`

**Import:** `from mcp.types import McpError, ErrorCode` and use `ErrorCode.INVALID_PARAMS` as the first argument to `McpError`.

### Pydantic Frozen Models — Use `model_copy(update={...})`

From Story 1.3, all domain models use `ConfigDict(frozen=True)`. You cannot mutate a `Flight` instance in place. Instead, use Pydantic's `model_copy()` method:

```python
cancelled_flight = flight.model_copy(update={
    "state": FlightState.cancelled,
    "unscheduled_reason": None
})
```

This creates a new `Flight` instance with the specified fields updated and all other fields copied from the original.

### State Mutation Pattern

From `domain/state.py`, the `AppState` class exposes:
- `get_flight(flight_number: str) -> Flight | None` — retrieve a flight
- `flights: dict[str, Flight]` — the insertion-ordered dict of all flights

**To update a flight:** `state.flights[flight_number] = new_flight_instance`

**Do NOT** use `state.add_flight()` for updates — that method is for appending new flights only (used by `submit_flight` in story 2.1).

### Test Pattern — Clean State Before Each Test

From Story 1.4, `tests/conftest.py` provides a `valid_env` fixture for environment variables. For this story, you need to reset `AppState` before each test to avoid cross-test contamination.

**Pattern:**
```python
def setup_function(function):
    """Reset state before each test."""
    state.reset()
```

This is a pytest convention — `setup_function` runs before each test function in the module.

### Error Message String-Exact Matching

AC-4 requires the error message to be **exactly** `"flight F is already cancelled"` (where `F` is the flight number). Do not add extra punctuation, capitalization, or wording changes.

**Test pattern:**
```python
with pytest.raises(McpError) as exc_info:
    cancel_flight(CancelFlightInput(flight_number="F"))

assert str(exc_info.value.error.message) == "flight F is already cancelled"
```

### Reference — Existing Code State

**From Story 1.3:** `domain/models.py` defines:
- `FlightState(StrEnum)` with values `queued`, `scheduled`, `unschedulable`, `cancelled`
- `Flight(BaseModel)` with fields: `flight_number`, `operation_type`, `priority`, `dependencies`, `runway_requirements`, `state`, `unscheduled_reason`
- All models use `ConfigDict(frozen=True, extra="forbid")`

**From Story 1.3:** `domain/state.py` defines:
- `AppState` class with `flights: dict[str, Flight]` and `latest_schedule: Schedule | None`
- Methods: `add_flight()`, `get_flight()`, `replace_flights_after_schedule()`, `set_latest_schedule()`, `reset()`
- Module-level singleton: `state = AppState()`

**From Story 1.4:** `tools.py` defines:
- `CancelFlightInput(BaseModel)` with `flight_number: str` and `ConfigDict(extra="forbid")`
- `cancel_flight(data: CancelFlightInput) -> dict` stub that raises `NotImplementedError`

**This story replaces the stub with the real implementation.**

### Import Discipline Reminder

From `architecture.md §Structure Patterns`:
- `tools.py` may import `mcp`, `domain/`, and `pydantic`.
- `tools.py` must NOT import `os` or read `os.environ` — that is `config.py`'s job.
- `domain/` must NOT import `mcp` — it is MCP-agnostic.

**For this story:** `tools.py` will import:
- `from mcp.types import McpError, ErrorCode`
- `from atc_mcp.domain.state import state`
- `from atc_mcp.domain.models import Flight, FlightState`

These imports are all allowed per the architecture.

### Why No `placement` Field on `Flight`?

The `Flight` model from Story 1.3 does NOT have a `placement` field. Placement information lives in the `Schedule` object (see `domain/models.py` — `Schedule` has `placements: tuple[Placement, ...]`).

**AC-1 and AC-2 say "its prior placement (if any) is cleared"** — this is a conceptual statement about the scheduling state, not a field mutation. In practice:
- When a flight is cancelled, its `state` is set to `FlightState.cancelled`.
- The next `generate_schedule()` call (in Epic 3) will not place the cancelled flight, so it will not appear in `Schedule.placements`.

**For this story:** You only need to mutate `state` and `unscheduled_reason`. There is no `placement` field to clear on the `Flight` object itself.

### Testing Without a Running MCP Server

All tests in this story are **synchronous unit tests** that call the tool handler function directly. You do NOT need to boot an MCP server or use `asyncio.run()`.

**Pattern:**
```python
from atc_mcp.tools import cancel_flight, CancelFlightInput

result = cancel_flight(CancelFlightInput(flight_number="F"))
assert result["cancelled"] == "F"
```

This is the same pattern used in Story 1.4's `test_server_bootstrap.py` — direct function calls, no MCP transport layer.

## Technical Requirements

### Language & Framework
- Python 3.11+
- Pydantic v2 (already in use)
- `mcp` SDK (already in use)
- `pytest` for tests

### Code Structure
- Modify: `src/atc_mcp/tools.py` (replace `cancel_flight` stub)
- Create: `tests/test_cancel_flight.py` (new test file)

### Testing Standards
- All tests must pass: `pytest -q tests/test_cancel_flight.py`
- No regressions: `pytest -q` (all existing tests still pass)
- Test coverage: 5 test cases covering happy paths, error cases, and payload shape

### Architecture Compliance
- Follow import discipline: `tools.py` may import `mcp`, `domain/`, `pydantic`
- Use frozen Pydantic models: `model_copy(update={...})` for mutations
- MCP error format: `McpError(ErrorCode.INVALID_PARAMS, "<message>")`
- Response payload: must include `dependents_reevaluated: []` field

### File Structure Requirements
- `tools.py` — add imports, replace stub implementation
- `tests/test_cancel_flight.py` — new file with 5 test cases and `setup_function`

## Project Context Reference

This story is part of Epic 2 (Flight Queue Management) in the Air Traffic Control MCP Server project. The project structure, module boundaries, and import discipline were established in Epic 1 (stories 1.1–1.4).

**Key architectural decisions:**
- All domain models are frozen Pydantic v2 models (`ConfigDict(frozen=True)`)
- `AppState` is the single in-memory state seam (no persistence)
- `tools.py` is the only MCP-facing layer for tool handlers
- Error messages follow the format `"<noun>: <reason>"` and use `McpError`

**Previous stories completed:**
- 1.1 — Project skeleton and module boundaries
- 1.2 — Configuration loading and startup validation
- 1.3 — Domain models, time model, and in-memory state seam
- 1.4 — MCP server bootstrap with tool and resource stubs

**Next story:** 2.3 will implement the `atc://flights` resource to expose the flight queue including cancelled flights.

## Dev Agent Record

### Implementation Plan

Implemented `cancel_flight` in `tools.py` using `mcp.shared.exceptions.McpError` (actual SDK location) and `mcp.types.ErrorData`/`INVALID_PARAMS`. Used `model_copy(update={...})` on the frozen `Flight` Pydantic model to produce a cancelled copy, then replaced the entry in `state.flights`. Tests use `setup_function` for state isolation without `valid_env` dependency (cancel_flight has no config dependency).

### Completion Notes

- Replaced `cancel_flight` stub in `tools.py` with full implementation (AC 1–5).
- Added `from mcp.shared.exceptions import McpError` and `from mcp.types import INVALID_PARAMS, ErrorData` imports.
- Created `tests/test_cancel_flight.py` with 5 tests covering all AC-6 scenarios.
- All 5 new tests pass; full suite 76/76 pass with no regressions.
- `dependents_reevaluated: []` field always present per AC-3 and architecture contract.
- Error messages string-exact per AC-4 (`"flight F is already cancelled"`) and AC-5 (`"flight XYZ does not exist"`).

## File List

- `src/atc_mcp/tools.py` — modified (imports added, `cancel_flight` stub replaced)
- `tests/test_cancel_flight.py` — created (5 test cases)

## Change Log

- Implemented `cancel_flight` tool handler with state mutation, error handling, and canonical response payload (Date: 2026-05-21)

## Story Completion Checklist

- [x] `cancel_flight` implementation in `tools.py` replaces the stub
- [x] All imports added to `tools.py` (McpError, state, Flight, FlightState)
- [x] `tests/test_cancel_flight.py` created with 5 test cases
- [x] All tests pass: `pytest -q tests/test_cancel_flight.py`
- [x] No regressions: `pytest -q` (all tests pass)
- [x] Error messages are string-exact per AC-4 and AC-5
- [x] Response payload includes `dependents_reevaluated: []` field per AC-3
- [x] Code follows import discipline and architecture patterns

---

**Ultimate context engine analysis completed — comprehensive developer guide created.**
