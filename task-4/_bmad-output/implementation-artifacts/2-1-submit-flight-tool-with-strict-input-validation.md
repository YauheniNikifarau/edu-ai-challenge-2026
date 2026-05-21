# Story 2.1: `submit_flight` Tool with Strict Input Validation

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an AI client,
I want to submit a new flight (arrival or departure) with priority, dependencies, and optional runway requirements,
So that the airport queue grows in a controlled, well-validated way and downstream scheduling has clean inputs.

## Acceptance Criteria

1. **AC-1 — Happy-path submission.** Given the server is running with valid config, when I call the `submit_flight` tool with a Pydantic-validated payload `{flight_number: str, operation_type: "arrival"|"departure", priority: "high"|"medium"|"low", dependencies: list[str] = [], runway_requirements: {min_length_m: int} | null = null}`, then the input schema is `ConfigDict(extra="forbid")` and rejects unknown fields with a clear error, and the flight is appended to `AppState.flights` (insertion-ordered) with `state = FlightState.queued`, `placement = null`, `unscheduled_reason = null`, and the tool returns the canonical `Flight` JSON payload in the exact shape pinned in architecture (`snake_case` field names; `null` vs `[]` per convention).

2. **AC-2 — Duplicate flight rejection.** When the submitted `flight_number` already exists in `AppState.flights`, then the tool returns an error `"flight <flight_number> already exists"` and `AppState` is unchanged.

3. **AC-3 — Unknown dependency rejection.** When `dependencies` references a `flight_number` that does not exist, then the tool returns an error `"unknown dependency: <missing_flight_number>"` and `AppState` is unchanged.

4. **AC-4 — Self-dependency rejection.** When `dependencies` contains the submitting flight's own `flight_number`, then the tool returns an error `"flight cannot depend on itself"` and `AppState` is unchanged.

5. **AC-5 — Test coverage.** `tests/test_submit_flight.py` covers: happy path arrival; happy path departure with deps; duplicate rejection; unknown-dep rejection; self-dep rejection; extra-field rejection; missing required-field rejection; invalid enum literal rejection.

## Tasks / Subtasks

- [ ] **Task 1 — Implement `submit_flight` tool handler in `tools.py`** (AC: 1, 2, 3, 4)
  - [ ] Import `Flight`, `FlightState`, `OperationType`, `Priority`, `RunwayRequirements` from `atc_mcp.domain.models`.
  - [ ] Import `state` from `atc_mcp.domain.state`.
  - [ ] Replace the `NotImplementedError` stub with real implementation.
  - [ ] Validate duplicate: if `state.get_flight(data.flight_number)` is not `None`, return error dict `{"error": f"flight {data.flight_number} already exists"}`.
  - [ ] Validate dependencies: for each `dep` in `data.dependencies`, if `state.get_flight(dep)` is `None`, return error dict `{"error": f"unknown dependency: {dep}"}`.
  - [ ] Validate self-dependency: if `data.flight_number in data.dependencies`, return error dict `{"error": "flight cannot depend on itself"}`.
  - [ ] Convert `RunwayRequirementsInput` to `RunwayRequirements` domain type if present: `runway_requirements = RunwayRequirements(min_length_m=data.runway_requirements.min_length_m) if data.runway_requirements else None`.
  - [ ] Construct `Flight` instance: `flight = Flight(flight_number=data.flight_number, operation_type=OperationType(data.operation_type), priority=Priority(data.priority), dependencies=data.dependencies, runway_requirements=runway_requirements, state=FlightState.queued, unscheduled_reason=None)`.
  - [ ] Add to state: `state.add_flight(flight)`.
  - [ ] Return canonical JSON: `{"flight": flight.model_dump(mode="json")}`. Use `mode="json"` to serialize enums as strings.

- [ ] **Task 2 — Create `tests/test_submit_flight.py`** (AC: 5)
  - [ ] Use `valid_env` fixture from `conftest.py` to set env vars.
  - [ ] Import `state` from `atc_mcp.domain.state` and call `state.reset()` in a `setup` fixture or at the start of each test.
  - [ ] Import `submit_flight` from `atc_mcp.tools` and `SubmitFlightInput` for constructing inputs.
  - [ ] **Test: `test_submit_arrival_happy_path`** — submit a simple arrival with no deps, no runway requirements; assert returned flight has `state="queued"`, `unscheduled_reason=None`, `dependencies=[]`; assert `state.get_flight(flight_number)` returns the flight.
  - [ ] **Test: `test_submit_departure_with_dependencies`** — submit flight F1 (no deps), then submit F2 with `dependencies=["F1"]`; assert F2 returned correctly; assert `state.get_flight("F2").dependencies == ["F1"]`.
  - [ ] **Test: `test_submit_with_runway_requirements`** — submit flight with `runway_requirements={"min_length_m": 3500}`; assert returned flight has `runway_requirements.min_length_m == 3500`.
  - [ ] **Test: `test_duplicate_flight_rejected`** — submit F1, then submit F1 again; assert second call returns `{"error": "flight F1 already exists"}`; assert `len(state.flights) == 1`.
  - [ ] **Test: `test_unknown_dependency_rejected`** — submit F2 with `dependencies=["F999"]` (F999 does not exist); assert returns `{"error": "unknown dependency: F999"}`; assert `state.get_flight("F2") is None`.
  - [ ] **Test: `test_self_dependency_rejected`** — submit F1 with `dependencies=["F1"]`; assert returns `{"error": "flight cannot depend on itself"}`; assert `state.get_flight("F1") is None`.
  - [ ] **Test: `test_extra_field_rejected`** — construct `SubmitFlightInput` with an extra field (e.g., `_unknown="x"`); assert Pydantic raises `ValidationError` with "extra fields not permitted".
  - [ ] **Test: `test_missing_required_field`** — construct `SubmitFlightInput` without `flight_number`; assert Pydantic raises `ValidationError`.
  - [ ] **Test: `test_invalid_enum_literal`** — construct `SubmitFlightInput` with `operation_type="takeoff"` (invalid); assert Pydantic raises `ValidationError`.
  - [ ] Run `pytest -q tests/test_submit_flight.py` and confirm all tests pass.

- [ ] **Task 3 — Verify integration with existing tests** (AC: 1–5)
  - [ ] Run `pytest -q` from `task-4/` and confirm all tests pass (including `test_imports.py`, `test_config.py`, `test_domain_models.py`, `test_server_bootstrap.py`).
  - [ ] Verify `tools.py` still does not import `mcp` directly (only `pydantic` and `domain/` imports).

## Dev Notes

### Relevant Architecture Patterns & Constraints

- **MCP tool error format (architecture.md §"Format Patterns"):** Tool-level errors (duplicate flight, unknown dependency, self-dependency) return a dict with an `"error"` key containing a lowercase sentence with no trailing period. Do NOT raise `McpError` in this story — that lands in Story 2.2+ when `mcp.types` is imported. For now, return `{"error": "..."}` as a plain dict; FastMCP will wrap it in a JSON-RPC error response automatically.
- **JSON output convention (architecture.md §"JSON Convention"):** Use `snake_case` field names, `_sec` suffix for integer-second fields, `null` for "not yet computed", `[]` for empty lists. Pydantic's `model_dump(mode="json")` handles enum serialization (converts `FlightState.queued` → `"queued"`).
- **Insertion-ordered flights dict (architecture.md §"State Persistence"):** `AppState.flights` is a Python 3.11+ `dict` (insertion-ordered by default). Flights are appended in submission order; this order is preserved for deterministic resource/status output in later stories.
- **Frozen domain models (architecture.md §"Pydantic Model Conventions"):** `Flight` is frozen (`ConfigDict(frozen=True)`). Once constructed, it cannot be mutated. Later stories use `flight.model_copy(update={...})` to produce updated instances.
- **Input schema vs domain model separation (architecture.md §"Structure Patterns"):** `SubmitFlightInput` (in `tools.py`) is the MCP input schema with `extra="forbid"` and `Literal` enums. `Flight` (in `domain/models.py`) is the domain value type with `StrEnum` enums and frozen semantics. The tool handler converts between them.

### Source Tree Components to Touch

```
task-4/
└── src/
│   └── atc_mcp/
│       └── tools.py             # UPDATE — replace submit_flight stub with real implementation
└── tests/
    └── test_submit_flight.py    # NEW — all test cases for AC-5
```

**Do NOT touch:**
- `src/atc_mcp/domain/models.py` — already complete from Story 1.3
- `src/atc_mcp/domain/state.py` — already complete from Story 1.3
- `src/atc_mcp/server.py` — already wired from Story 1.4
- `src/atc_mcp/resources.py` — stub remains until Story 2.3
- `tests/conftest.py` — already has `valid_env` fixture from Story 1.4

### Input Schema Already Defined (Story 1.4)

`tools.py` already has `SubmitFlightInput` defined from Story 1.4:

```python
class SubmitFlightInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    flight_number: str
    operation_type: Literal["arrival", "departure"]
    priority: Literal["high", "medium", "low"]
    dependencies: list[str] = []
    runway_requirements: RunwayRequirementsInput | None = None
```

This story only needs to replace the `submit_flight(data: SubmitFlightInput) -> dict` stub body.

### Domain Models Available (Story 1.3)

From `domain/models.py`:
- `Flight(BaseModel)` — frozen, with fields: `flight_number`, `operation_type: OperationType`, `priority: Priority`, `dependencies: list[str]`, `runway_requirements: RunwayRequirements | None`, `state: FlightState`, `unscheduled_reason: str | None`
- `FlightState(StrEnum)` — `queued | scheduled | unschedulable | cancelled`
- `OperationType(StrEnum)` — `arrival | departure`
- `Priority(StrEnum)` — `high | medium | low`
- `RunwayRequirements(BaseModel)` — frozen, with field `min_length_m: int`

From `domain/state.py`:
- `state: AppState` — module-level singleton with `flights: dict[str, Flight]` and methods `add_flight(flight)`, `get_flight(flight_number)`, `reset()`

### Validation Order (Critical for Error Message Determinism)

Validate in this exact order to match the architecture's error-priority contract:
1. **Duplicate check first** — if the flight already exists, reject immediately before checking dependencies.
2. **Unknown dependency check second** — iterate `data.dependencies` in order; return error on the first unknown dependency found.
3. **Self-dependency check third** — after confirming all deps exist, check if any dep is the flight itself.

This order ensures deterministic error messages when multiple validation failures could occur.

### Conversion Between Input Schema and Domain Model

`SubmitFlightInput` uses `Literal["arrival", "departure"]` for `operation_type`. `Flight` uses `OperationType(StrEnum)`. Convert with:
```python
operation_type = OperationType(data.operation_type)  # "arrival" → OperationType.arrival
```

Same for `priority`:
```python
priority = Priority(data.priority)  # "high" → Priority.high
```

`RunwayRequirementsInput` (MCP input schema) → `RunwayRequirements` (domain model):
```python
runway_requirements = (
    RunwayRequirements(min_length_m=data.runway_requirements.min_length_m)
    if data.runway_requirements
    else None
)
```

### Return Value Format

**Success case:**
```json
{
  "flight": {
    "flight_number": "AA123",
    "operation_type": "arrival",
    "priority": "high",
    "dependencies": [],
    "runway_requirements": {"min_length_m": 3500},
    "state": "queued",
    "unscheduled_reason": null
  }
}
```

Use `flight.model_dump(mode="json")` to serialize. `mode="json"` ensures enums are serialized as strings (not enum objects).

**Error case:**
```json
{"error": "flight AA123 already exists"}
```

Do NOT raise exceptions for validation errors in this story. Return error dicts. FastMCP will convert them to MCP error responses.

### Testing Standards Summary

- **Framework:** `pytest` only. No `pytest-asyncio`, no subprocess tests.
- **State management:** Call `state.reset()` at the start of each test (or in a fixture) to ensure clean state.
- **Pydantic validation tests:** Use `pytest.raises(ValidationError)` to assert that invalid inputs raise at construction time (before the tool handler is even called).
- **Error message assertions:** Assert exact error strings (e.g., `result["error"] == "flight F1 already exists"`). The architecture pins these formats.
- **Run command:** `pytest -q tests/test_submit_flight.py` from `task-4/`.

### Previous Story Intelligence (Stories 1.1–1.4)

**Story 1.1** created the project skeleton. `tools.py` was an empty stub.

**Story 1.2** wired `config.py` completely. No impact on this story.

**Story 1.3** populated `domain/models.py` and `domain/state.py` with all the types this story needs:
- `Flight`, `FlightState`, `OperationType`, `Priority`, `RunwayRequirements` — all frozen Pydantic v2 models
- `AppState` with `flights: dict[str, Flight]` and methods `add_flight`, `get_flight`, `reset`

**Story 1.4** wired the MCP server and created tool/resource stubs. It defined `SubmitFlightInput` and the stub `submit_flight(data: SubmitFlightInput) -> dict` that raises `NotImplementedError`. This story replaces that stub with real logic.

**Key learnings from Story 1.4:**
- `tools.py` does NOT import `mcp` yet. It only imports `pydantic` and `domain/` modules. `McpError` is not used until Story 2.2+.
- Tool handlers return plain dicts. FastMCP wraps them in JSON-RPC responses.
- The `valid_env` fixture in `conftest.py` sets all 11 `ATC_*` env vars for tests.

### Library / Framework Requirements

| Concern | Choice | Notes |
|---|---|---|
| Domain models | `atc_mcp.domain.models` | `Flight`, `FlightState`, `OperationType`, `Priority`, `RunwayRequirements` |
| State management | `atc_mcp.domain.state` | `state: AppState` singleton |
| Input validation | `pydantic>=2` | `SubmitFlightInput` already defined in `tools.py` |
| Testing | `pytest>=8` | No plugins needed |

**Do NOT add:** `mcp.types.McpError` (not needed until Story 2.2+), `typing.cast`, `dataclasses`, `attrs`, or any other validation library beyond Pydantic.

### Disaster-Prevention Notes

- **Do NOT mutate `Flight` instances.** They are frozen. Construct new instances only.
- **Do NOT import `mcp` in `tools.py` in this story.** `McpError` lands in Story 2.2. For now, return error dicts.
- **Do NOT use `state.flights[flight_number] = flight` directly.** Use `state.add_flight(flight)` — it's the named mutation boundary.
- **Do NOT forget `state.reset()` in tests.** Without it, tests will interfere with each other (flights from one test leak into the next).
- **Do NOT return `flight.model_dump()` without `mode="json"`.** Without `mode="json"`, enums serialize as enum objects (e.g., `OperationType.arrival` instead of `"arrival"`), which breaks JSON-RPC.
- **Do NOT validate dependencies by checking `data.dependencies` against `state.flights.keys()` with a set operation.** Iterate in order and return the first missing dependency to ensure deterministic error messages.
- **Do NOT raise `ValidationError` from the tool handler.** Pydantic raises `ValidationError` at input construction time (before the handler is called). The handler only returns error dicts for domain-level validation (duplicate, unknown dep, self-dep).

### Expected Test Output Pattern

After implementing this story, `pytest -q tests/test_submit_flight.py` should show approximately 9 tests passing:
- 1 happy-path arrival
- 1 happy-path departure with dependencies
- 1 happy-path with runway requirements
- 1 duplicate rejection
- 1 unknown dependency rejection
- 1 self-dependency rejection
- 1 extra-field rejection (Pydantic)
- 1 missing required-field rejection (Pydantic)
- 1 invalid enum literal rejection (Pydantic)

### Project Structure Notes

After this story, `submit_flight` is the first fully-implemented MCP tool. The pattern established here (input validation → domain model construction → state mutation → JSON response) will be reused in Story 2.2 (`cancel_flight`) and Story 3.x (scheduling tools).

The file tree remains unchanged except for:
- `src/atc_mcp/tools.py` — `submit_flight` stub replaced with real implementation
- `tests/test_submit_flight.py` — new test file

### References

- [Source: _bmad-output/planning-artifacts/epics.md §"Story 2.1: `submit_flight` Tool with Strict Input Validation"] — AC source, validation order, test coverage requirements
- [Source: _bmad-output/planning-artifacts/architecture.md §"MCP Tool Catalog: submit_flight"] — input/output JSON shapes, validation rules, error messages
- [Source: _bmad-output/planning-artifacts/architecture.md §"Format Patterns"] — error dict format, snake_case convention, null vs [] convention
- [Source: _bmad-output/planning-artifacts/architecture.md §"Pydantic Model Conventions"] — `extra="forbid"`, `frozen=True`, `model_dump(mode="json")`
- [Source: _bmad-output/planning-artifacts/architecture.md §"State Persistence (resolves DD-5)"] — `AppState.flights` is insertion-ordered dict
- [Source: _bmad-output/implementation-artifacts/1-3-domain-models-time-model-and-in-memory-state-seam.md] — domain models available, `AppState` methods
- [Source: _bmad-output/implementation-artifacts/1-4-mcp-server-bootstrap-with-tool-and-resource-stubs.md] — `SubmitFlightInput` schema, tool registration pattern, FastMCP error handling

### Latest Technical Information

- **Pydantic v2 `model_dump(mode="json")`:** Serializes enums as strings, handles `None` → `null`, and applies all field aliases. Always use `mode="json"` when returning Pydantic models as JSON-RPC responses.
- **Python 3.11+ dict insertion order:** Guaranteed by language spec. `AppState.flights` preserves submission order without needing `OrderedDict`.
- **`StrEnum` string equality:** `OperationType.arrival == "arrival"` is `True`. You can construct from string: `OperationType("arrival")` returns `OperationType.arrival`.
- **Pydantic `ValidationError` structure:** When constructing `SubmitFlightInput` with invalid data, Pydantic raises `ValidationError` with a `.errors()` method returning a list of error dicts. Tests should use `pytest.raises(ValidationError)` and optionally inspect `exc_info.value.errors()` for specific field errors.

### Project Context Reference

No `project-context.md` was discovered under `task-4/` at the time this story was created. All implementation rules come from `architecture.md` and `epics.md`.

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List

### Change Log
