# Story 1.3: Domain Models, Time Model & In-Memory State Seam

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the scheduling engine,
I want frozen value types for `Flight`, `Schedule`, `Placement`, the `FlightState` enum, and integer-second time aliases, plus a single-seam in-memory store,
so that later stories have a stable, immutable data model and a clear mutation boundary.

## Acceptance Criteria

1. **AC-1 — Pydantic v2 frozen value types.** Importing from `domain.models` provides: `Flight`, `Schedule`, `Placement`, `Runway`, `BottleneckResult` — all Pydantic v2 `BaseModel` subclasses with `model_config = ConfigDict(frozen=True, extra="forbid")`. Unknown fields passed to any of these constructors raise a `ValidationError`.
2. **AC-2 — FlightState StrEnum pinned.** `FlightState` is a `StrEnum` (Python 3.11+ stdlib `enum.StrEnum`) with **exactly** the four values: `queued`, `scheduled`, `unschedulable`, `cancelled`. No other values exist. This is the readiness-report hardening recommendation R-A.
3. **AC-3 — Flight.unscheduled_reason is a first-class field.** `Flight` has `unscheduled_reason: str | None = None` defined as a Pydantic field — **not** computed, **not** log-only. It propagates to `atc://flights`, `get_airport_status`, and `generate_schedule` output in later stories.
4. **AC-4 — time_model.py exports Seconds alias.** `time_model.py` exports `Seconds = int` and contains a module-level docstring documenting: (a) all time values are non-negative integers, (b) `t=0` is the "schedule-generation moment", (c) `time.time()`, `datetime.now()`, `datetime.utcnow()`, and `random` are banned in `domain/` and `scheduler/`.
5. **AC-5 — AppState singleton with named mutator methods.** `domain/state.py` exposes a module-level `state: AppState` instance. `AppState` has: `flights: dict[str, Flight]` (insertion-ordered, keyed by `flight_number`), `latest_schedule: Schedule | None`, and helper methods `add_flight(flight: Flight) -> None`, `get_flight(flight_number: str) -> Flight | None`, `replace_flights_after_schedule(updated_flights: dict[str, Flight]) -> None`, `set_latest_schedule(schedule: Schedule) -> None`, `reset() -> None`. No other module may directly assign to `state.flights` or `state.latest_schedule`.
6. **AC-6 — test_imports.py extended.** The existing `tests/test_imports.py` (created in Story 1.1) is extended to assert that no file under `src/atc_mcp/domain/` or `src/atc_mcp/scheduler/` imports any of: `time`, `datetime`, `random`. The extension uses the same AST-based approach already in place. `pytest -q tests/test_imports.py` passes.
7. **AC-7 — Unit tests for model pinning.** A new `tests/test_domain_models.py` (or equivalent) verifies: (a) `FlightState` has exactly the four expected literal values; (b) constructing `Flight(...)` with an unknown field raises `ValidationError`; (c) a valid `Flight` can be constructed and its frozen fields cannot be reassigned; (d) `AppState.reset()` clears both `flights` and `latest_schedule`.

## Tasks / Subtasks

- [x] **Task 1 — Populate `src/atc_mcp/time_model.py`** (AC: 4)
  - [x] Add module-level docstring as the invariant contract (see Dev Notes §time_model.py spec below).
  - [x] Add `Seconds = int` type alias.
  - [x] Add no other imports (especially NOT `time`, `datetime`, `os`). The file must stay clean of any stdlib time imports so later `test_imports.py` assertions pass.

- [x] **Task 2 — Populate `src/atc_mcp/domain/models.py`** (AC: 1, 2, 3)
  - [x] Define supporting enums first (they have no dependencies): `FlightState(StrEnum)`, `OperationType(StrEnum)`, `Priority(StrEnum)`.
  - [x] Define `RunwayRequirements` model (`min_length_m: int = Field(gt=0)`).
  - [x] Define `Runway` model (`id: str`, `length_m: int = Field(gt=0)`). **See note below about `config.py` import.**
  - [x] Define `Flight` model with all fields per spec (see Dev Notes §Flight model spec).
  - [x] Define `Placement` model with all fields per spec.
  - [x] Define `Schedule` model (`placements: tuple[Placement, ...]`, `unscheduled: tuple[Flight, ...]`, `completion_time_seconds: int | None = None`).
  - [x] Define `BottleneckResult` model with all fields per spec.
  - [x] Apply `model_config = ConfigDict(frozen=True, extra="forbid")` to every `BaseModel`. **Do NOT apply `extra="forbid"` to enums — only to Pydantic `BaseModel` subclasses.**
  - [x] No imports of `mcp`, `os`, `time`, `datetime`, `random` — the import-discipline tests will catch violations.

- [x] **Task 3 — Populate `src/atc_mcp/domain/state.py`** (AC: 5)
  - [x] Define `AppState` class with fields `flights: dict[str, Flight]` and `latest_schedule: Schedule | None`.
  - [x] Implement all five methods: `add_flight`, `get_flight`, `replace_flights_after_schedule`, `set_latest_schedule`, `reset` (see Dev Notes §AppState spec).
  - [x] Create module-level singleton: `state = AppState()`.
  - [x] No imports of `mcp`, `os`, `time`, `datetime`, `random`.

- [x] **Task 4 — Extend `tests/test_imports.py`** (AC: 6)
  - [x] Add a new test (or parametrize the existing `domain/`+`scheduler/` assertion) that checks no `.py` file in `domain/` or `scheduler/` imports `time`, `datetime`, or `random` (by top-level imported name via AST, same approach as existing test).
  - [x] Verify `pytest -q tests/test_imports.py` still passes.
  - [x] **Do NOT** change the existing `mcp`/`os` assertions — extend only.

- [x] **Task 5 — Create `tests/test_domain_models.py`** (AC: 7)
  - [x] Test `FlightState` values: assert `set(FlightState) == {"queued", "scheduled", "unschedulable", "cancelled"}`.
  - [x] Test `Flight` rejects unknown fields: `Flight(flight_number="F1", operation_type="arrival", priority="high", _extra_field="x")` raises `ValidationError`.
  - [x] Test `Flight` is frozen: constructing a valid `Flight` then attempting `flight.state = "scheduled"` raises `ValidationError` (Pydantic frozen model exception).
  - [x] Test `AppState.reset()`: add a flight + set a schedule, call `reset()`, assert `state.flights == {}` and `state.latest_schedule is None`.
  - [x] Test `AppState.add_flight` / `get_flight` round-trip.
  - [x] Test `AppState.replace_flights_after_schedule` replaces the entire dict.
  - [x] Run `pytest -q tests/test_domain_models.py` and confirm it passes.

- [x] **Task 6 — Smoke-test full import chain** (AC: 1–6)
  - [x] Run `pytest -q` from `task-4/` and confirm all tests pass (at minimum `test_imports.py` and `test_domain_models.py`).
  - [x] Verify `python -c "from atc_mcp.domain.models import Flight, FlightState, Schedule, Placement, Runway, BottleneckResult; from atc_mcp.domain.state import state; from atc_mcp.time_model import Seconds; print('OK')"` prints `OK` without errors.

## Dev Notes

### time_model.py — Exact Spec

```python
"""
Time model for the ATC MCP server.

Epoch: t=0 is the moment a schedule is generated. The scheduler never reads wall-clock time.
Granularity: integer seconds. All durations, buffers, and placements are non-negative integers
expressed as (start_sec, end_sec) pairs.

Invariant: every time value in domain/ and scheduler/ must be a non-negative int.
Banned in domain/ and scheduler/: time.time(), datetime.now(), datetime.utcnow(), random.
"""

Seconds = int
```

**Why no further helpers here:** `time_model.py` is intentionally minimal at this stage. Later stories (scheduler) will import `Seconds` as a type annotation. The docstring is the contract; it is not optional.

---

### domain/models.py — Exact Model Specs

#### Enums (use `enum.StrEnum` from Python 3.11+ stdlib)

```python
from enum import StrEnum

class FlightState(StrEnum):
    queued       = "queued"
    scheduled    = "scheduled"
    unschedulable = "unschedulable"
    cancelled    = "cancelled"

class OperationType(StrEnum):
    arrival   = "arrival"
    departure = "departure"

class Priority(StrEnum):
    high   = "high"
    medium = "medium"
    low    = "low"
```

**`StrEnum` vs `str + Enum`:** Python 3.11 introduces `enum.StrEnum` directly. Do NOT use `class FlightState(str, Enum)` (the old pattern) — use `StrEnum`. Values are usable directly as strings (e.g., `FlightState.queued == "queued"` is `True`), which is required for Pydantic JSON serialization.

#### RunwayRequirements

```python
class RunwayRequirements(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    min_length_m: int = Field(gt=0)
```

#### Runway

```python
class Runway(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    length_m: int = Field(gt=0)
```

**Config.py dependency note:** Story 1.2 (`config.py`) will define `Config.runways: tuple[Runway, ...]` and must import `Runway` from `atc_mcp.domain.models`. This is the only place `config.py` imports from `domain/`. The architecture diagram says `config.py ← imports stdlib only`, but this means "no MCP imports, no env-var reads from domain/" — NOT that it can't import domain value types. The `test_imports.py` rules (no `mcp`, no `os` in `domain/`) do not prevent `config.py` from importing `Runway`. If Story 1.2 is developed before Story 1.3, the Story 1.2 developer should stub `Runway` inline in `config.py` and then migrate it here once Story 1.3 is merged.

#### Flight

```python
class Flight(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    flight_number:       str
    operation_type:      OperationType
    priority:            Priority
    dependencies:        list[str] = Field(default_factory=list)
    runway_requirements: RunwayRequirements | None = None
    state:               FlightState = FlightState.queued
    unscheduled_reason:  str | None = None
```

**Critical: `unscheduled_reason` is a first-class field.** It is NOT a computed property, NOT a log message, NOT a separate dict. It lives on the `Flight` object and travels through every surface: `atc://flights` resource, `get_airport_status` unscheduled list, and `generate_schedule` tool output. Later stories (3.x) will set it by constructing a new `Flight` via `model_copy(update={"state": ..., "unscheduled_reason": ...})`.

**Mutation pattern for frozen models:** Since `Flight` is frozen (`ConfigDict(frozen=True)`), fields cannot be reassigned in place. To "update" a flight's state after scheduling, callers must create a new instance:
```python
updated = flight.model_copy(update={"state": FlightState.scheduled, "unscheduled_reason": None})
```
This pattern will be used throughout Stories 3.x. Do NOT attempt `flight.state = ...` — it will raise `ValidationError`.

#### Placement (Schedule Entry)

```python
class Placement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    flight_number:  str
    operation_type: OperationType
    runway_id:      str
    gate_id:        str
    start_sec:      int = Field(ge=0)
    end_sec:        int = Field(ge=0)
```

**Naming note:** The architecture uses both "ScheduleEntry" and "Placement". The epics (authoritative for story implementation) use `Placement`. Use `Placement` in code.

**Gate IDs:** Gates are string identifiers (e.g., `"G1"`, `"G2"`) derived from config's `gate_count`. There is no `Gate` model — gates are just string labels. The scheduler generates gate IDs as `f"G{n}"` for `n in range(1, config.gate_count + 1)`.

#### Schedule

```python
class Schedule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    placements:               tuple[Placement, ...]
    unscheduled:              tuple[Flight, ...]
    completion_time_seconds:  int | None = None
```

**`tuple` vs `list`:** `placements` and `unscheduled` use `tuple[..., ...]` for immutability (consistent with the frozen model pattern). Pydantic v2 serializes `tuple` fields as JSON arrays.

#### BottleneckResult

```python
class BottleneckResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    chain:                   list[str]
    total_duration_seconds:  int | None
    operation_durations:     list[int]
    dependency_buffers:      list[int]
```

**Empty case contract (DD-9):** when no active scheduled dependency chain exists, the tool returns:
```json
{"chain": [], "total_duration_seconds": null, "operation_durations": [], "dependency_buffers": []}
```
This maps to `BottleneckResult(chain=[], total_duration_seconds=None, operation_durations=[], dependency_buffers=[])`.

---

### domain/state.py — AppState Spec

```python
class AppState:
    def __init__(self) -> None:
        self.flights: dict[str, Flight] = {}          # insertion-ordered, keyed by flight_number
        self.latest_schedule: Schedule | None = None

    def add_flight(self, flight: Flight) -> None:
        """Append flight to the queue. Caller is responsible for duplicate checks."""
        self.flights[flight.flight_number] = flight

    def get_flight(self, flight_number: str) -> Flight | None:
        """Return the flight or None if not found."""
        return self.flights.get(flight_number)

    def replace_flights_after_schedule(self, updated_flights: dict[str, Flight]) -> None:
        """Replace the entire flights dict atomically after a schedule run.

        Preserves insertion order of the incoming dict. The caller (generate_schedule
        tool handler in Story 3.x) builds updated_flights by iterating self.flights
        in order and constructing new Flight instances via model_copy().
        """
        self.flights = updated_flights

    def set_latest_schedule(self, schedule: Schedule) -> None:
        """Store the result of the latest generate_schedule call."""
        self.latest_schedule = schedule

    def reset(self) -> None:
        """Clear all state (used by tests and future restart scenarios)."""
        self.flights = {}
        self.latest_schedule = None

state = AppState()
```

**Singleton pattern:** `state = AppState()` is module-level. All tool handlers import it via `from atc_mcp.domain.state import state`. Tests call `state.reset()` in their setup/teardown. Never re-import `AppState` and instantiate a second copy in production code.

**Why no setter for individual flight state updates:** `replace_flights_after_schedule` performs an atomic bulk update rather than per-flight mutations. This is the architecture's "single mutation boundary" principle — after scheduling, all flight states are updated in one operation, preventing partial-update races and making the state transition testable as a unit.

---

### Relevant Architecture Patterns & Constraints

- **Module import direction (architecture.md §Structure Patterns):** `domain/` and `scheduler/` must not import `mcp` or read `os.environ`. `config.py` is the only env reader. `tools.py` and `resources.py` are the only MCP-facing layers. This story's `domain/models.py` and `domain/state.py` must honor this — their only imports should be stdlib, `pydantic`, and peer `domain/` modules.
- **Determinism guard-rails (architecture.md §Ordering Patterns):** `time.time()`, `datetime.now()`, `datetime.utcnow()`, and `random` are banned in `domain/` and `scheduler/`. This story adds that ban to `test_imports.py`. Do NOT add any of these imports anywhere in `domain/` or `scheduler/` — not even in comments that accidentally get parsed, not in `# type: ignore` stubs.
- **Pydantic v2 conventions (architecture.md §Pydantic Model Conventions):** use `ConfigDict`, `Field`, `field_validator` (v2 style). Do NOT use `@validator` (v1 legacy). Use `model_config = ConfigDict(...)` as a class attribute, NOT `class Config: ...` (v1 pattern).
- **`StrEnum` (Python 3.11+):** available directly as `from enum import StrEnum`. No backport needed since `requires-python = ">=3.11"` in `pyproject.toml`.
- **No `time`, `datetime`, `random` in domain or scheduler:** enforced by `test_imports.py` after this story's extension. The current `test_imports.py` only checks `mcp` and `os`; this story adds the time-related bans per Story 1.1 dev notes ("Story 1.3 extends test_imports.py…").

---

### Files to Touch

```
task-4/
├── src/
│   └── atc_mcp/
│       ├── time_model.py                  # UPDATE — add docstring + Seconds alias
│       └── domain/
│           ├── models.py                  # UPDATE — add all models and enums
│           └── state.py                   # UPDATE — add AppState class + singleton
└── tests/
    ├── test_imports.py                    # UPDATE — extend with time/datetime/random ban
    └── test_domain_models.py              # NEW — model pinning + AppState unit tests
```

No other files in the tree are modified by this story. `config.py`, `server.py`, `tools.py`, `resources.py`, `scheduler/`, `bottleneck.py`, `status.py` are **untouched** — they remain as empty or placeholder stubs from Story 1.1.

---

### Source Tree Context from Story 1.1

Story 1.1 created empty placeholder stubs for all source files. The files this story modifies currently contain either nothing or a one-line docstring. There is no existing logic to preserve or break. The only file with real content is `tests/test_imports.py` — read it before extending it to understand the existing AST-based approach and avoid duplicating test logic.

**Expected current test_imports.py structure (from Story 1.1):**
- Iterates `.py` files under `src/atc_mcp/`
- Collects `Import`/`ImportFrom` nodes via `ast.parse`
- Asserts `domain/` and `scheduler/` don't import `mcp` or `os`
- Asserts only `config.py` may import `os`
- Asserts only `tools.py` and `resources.py` may import `mcp`

**Extension to add:** assert that files under `domain/` and `scheduler/` do not import `time`, `datetime`, or `random` (top-level names, same AST check).

---

### Testing Standards Summary

- **Framework:** `pytest` only. No plugins, no `pytest-asyncio` (not needed here — all code is synchronous pure Python).
- **Approach:** unit tests, no subprocess invocations, no MCP server needed.
- **Static AST test extension:** the `test_imports.py` extension must parse with `ast` (not `importlib`) to stay consistent with Story 1.1's approach and survive modules that are not yet fully wired.
- **Frozen model mutation test:** use `pytest.raises(ValidationError)` around `flight.state = "scheduled"` to verify the frozen constraint.
- **Run command:** `pytest -q` from `task-4/`.

---

### Disaster Prevention Notes

- **Do NOT** define `RunwayRequirements` as a nested class inside `Flight`. Define it as a top-level class in `domain/models.py` so it can be imported independently by `tools.py` (Story 2.x uses it for the `submit_flight` input schema).
- **Do NOT** add a `placement: Placement | None` field to `Flight`. The architecture stores placements in `Schedule.placements` (keyed by flight number implicitly via `Placement.flight_number`), not on the flight itself. Keeping placement state on the flight would duplicate data and violate the "single source of truth" for schedule state.
- **Do NOT** use `list[Placement]` for `Schedule.placements` — use `tuple[Placement, ...]` so the frozen model is deeply immutable in spirit.
- **Do NOT** create a `tests/conftest.py` — Story 1.1 dev notes explicitly say not to. Shared fixtures land later.
- **Do NOT** use `class FlightState(str, Enum)` — use `StrEnum` directly (Python 3.11+).
- **Do NOT** use `Optional[X]` — use `X | None` (Python 3.10+ union syntax; consistent with rest of codebase).
- **StrEnum value casing:** the literal values must be **lowercase** (`"queued"`, not `"QUEUED"` or `"Queued"`) to match the JSON convention throughout the architecture and all tool/resource payloads.
- **Story 1.2 coordination:** Story 1.2 (`config.py`) needs `Runway` from `domain.models`. If Story 1.3 is implemented after Story 1.2, update `config.py` to `from atc_mcp.domain.models import Runway` instead of any inline definition. If before, Story 1.2 will pick up `Runway` naturally.

---

### Project Structure Notes

- **Alignment:** `domain/models.py` and `domain/state.py` are exactly the files listed in `architecture.md §Complete Project Directory Structure`. No new files are added to the source tree.
- **Detected variance — class naming:** The architecture diagram (`architecture.md §Component Decomposition`) calls the store class `AirportState` but `epics.md §Story 1.3 AC` calls it `AppState`. **Use `AppState`** — the epics are the implementation spec. This is not a conflict; `AirportState` was the architect's working name, overridden by the stories.
- **`Placement` vs `ScheduleEntry`:** same situation — epics use `Placement`; use `Placement` in code.

---

### References

- [Source: _bmad-output/planning-artifacts/epics.md §"Story 1.3: Domain Models, Time Model & In-Memory State Seam"] — AC source, model names, AppState method list.
- [Source: _bmad-output/planning-artifacts/architecture.md §"State Persistence (resolves DD-5)"] — flights dict, latest_schedule field, restart semantics.
- [Source: _bmad-output/planning-artifacts/architecture.md §"MCP Tool Catalog: submit_flight"] — Flight JSON shape, RunwayRequirements schema.
- [Source: _bmad-output/planning-artifacts/architecture.md §"MCP Tool Catalog: generate_schedule"] — Schedule output shape, Placement fields.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Active Scheduled Dependency Chain (resolves DD-9)"] — BottleneckResult shape and empty-case contract.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Runway Capability Schema (resolves DD-8)"] — Runway model `{id, length_m}`.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Time Model (resolves DD-6)"] — Seconds = int, t=0 epoch, banned stdlib modules.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Pydantic Model Conventions"] — ConfigDict(frozen=True), extra="forbid", Field validators, v2 style.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Ordering Patterns"] — bans on time.time(), datetime.now(), random.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Structure Patterns" / "Module dependency direction"] — import graph enforced by test_imports.py.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Format Patterns"] — reason string format: lowercase, no trailing period, names offending value.
- [Source: _bmad-output/implementation-artifacts/1-1-project-skeleton-and-module-boundaries.md §"Disaster-Prevention Notes"] — do not create conftest.py; Story 1.3 owns the time/datetime/random import ban extension.
- [Source: _bmad-output/implementation-artifacts/1-1-project-skeleton-and-module-boundaries.md §"Dev Notes"] — "Story 1.3 extends test_imports.py to assert this. Don't add those bans here."
- [Source: _bmad-output/planning-artifacts/epics.md §"Story 1.4"] — Story 1.4 wires the MCP server and imports `domain.models` and `domain.state`; this story must produce clean importable modules by then.

---

### Latest Technical Information

- **Pydantic v2 `model_copy(update={})`:** the canonical way to produce a new frozen model instance with changed fields. Replaces v1's `.copy(update={})`. Signature: `flight.model_copy(update={"state": FlightState.scheduled})`. Returns a new `Flight`; does not mutate the original.
- **`StrEnum` availability:** `from enum import StrEnum` is available since Python 3.11 (stdlib). No PyPI package needed. Instances compare equal to their string values: `FlightState.queued == "queued"` → `True`. Pydantic v2 natively serializes `StrEnum` values as their string literals in JSON output.
- **Pydantic v2 `tuple[T, ...]` fields:** `Schedule.placements: tuple[Placement, ...]` uses the variable-length tuple syntax. Pydantic v2 serializes this as a JSON array. Validators accept both `list` and `tuple` as input and coerce to tuple. **Do not annotate as `Tuple[Placement, ...]`** from `typing` — use the native `tuple[Placement, ...]` (Python 3.9+ lowercase generics).
- **`Field(default_factory=list)` for `Flight.dependencies`:** use `Field(default_factory=list)` rather than `= []` as a default value (Pydantic v2 best practice to avoid shared mutable defaults, even though frozen models prevent mutation).

---

### Project Context Reference

No `project-context.md` was discovered under `task-4/` at the time this story was created. All implementation rules come from `architecture.md` and `epics.md`.

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (Windsurf / Cascade)

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Task 1: `time_model.py` populated with exact spec docstring and `Seconds = int` alias. Zero stdlib imports — import-discipline tests pass.
- Task 2: `domain/models.py` fully implemented — `FlightState`, `OperationType`, `Priority` StrEnums; `RunwayRequirements`, `Runway`, `Flight`, `Placement`, `Schedule`, `BottleneckResult` Pydantic v2 frozen models with `extra="forbid"`. No banned imports.
- Task 3: `domain/state.py` fully implemented — `AppState` class with all five methods (`add_flight`, `get_flight`, `replace_flights_after_schedule`, `set_latest_schedule`, `reset`) and module-level `state = AppState()` singleton.
- Task 4: `tests/test_imports.py` extended with `test_domain_no_time_datetime_random` and `test_scheduler_no_time_datetime_random` — existing assertions untouched.
- Task 5: `tests/test_domain_models.py` created — 9 unit tests covering FlightState pinning, Flight frozen/unknown-field validation, AppState all methods. All pass.
- Task 6: `pytest -q` from task-4/ — 55 tests pass, 0 failures. Smoke import chain prints `OK`.

### File List

- src/atc_mcp/time_model.py
- src/atc_mcp/domain/models.py
- src/atc_mcp/domain/state.py
- tests/test_imports.py
- tests/test_domain_models.py

### Change Log

- 2026-05-20: Story 1.3 implemented — time model alias, all domain models, AppState singleton, test_imports extension, domain model unit tests. 55/55 tests pass.
