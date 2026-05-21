---
story_id: "3.4"
story_key: "3-4-wire-algorithm-to-generate-schedule-tool-timeline-runways-resources"
epic: "Epic 3: Deterministic Scheduling Engine & Airport Operations"
title: "Wire Algorithm to `generate_schedule` Tool + `atc://timeline` + `atc://runways` Resources"
status: "ready-for-dev"
created: "2026-05-21"
dependencies: ["3.1", "3.2", "3.3"]
---

# Story 3.4: Wire Algorithm to `generate_schedule` Tool + `atc://timeline` + `atc://runways` Resources

## User Story

**As an** AI client,
**I want** to invoke `generate_schedule` and read the resulting timeline and runway-usage resources,
**So that** I can produce and inspect a deterministic schedule through the MCP surface.

## Business Context

Stories 3.1–3.3 produce a working `scheduler.algorithm.schedule()` pure function. This story wires that function to the MCP layer: the `generate_schedule` tool becomes functional (replacing its `NotImplementedError` stub), and the `atc://timeline` and `atc://runways` resources are implemented to project the stored schedule. This is the story that makes the scheduling engine visible to AI clients.

## Acceptance Criteria

1. **Given** Stories 3.1–3.3 have produced a working `scheduler.algorithm.schedule()`
   **When** I invoke the `generate_schedule` MCP tool (no input args)
   **Then** the tool reads `AppState.flights` and `Config`, calls `schedule()`, stores the result in `AppState.latest_schedule`, mutates each flight's `state` and `unscheduled_reason` to reflect the new outcome, and returns the architecture-pinned tool payload.

2. **And** `atc://timeline` returns `{"events": [<operation>, ...]}` sorted by `(start_sec, runway_id, flight_number)`, each containing `flight_number`, `operation_type`, `runway_id`, `gate_id`, `start_sec`, `end_sec`, `depends_on`.

3. **And** `atc://runways` returns `{"runways": [{"id", "length_m", "scheduled_operations": [...], "busy_intervals_sec": [...], "next_free_sec": int}, ...]}` sorted by `id` lex, with per-runway `scheduled_operations` sorted by `start_sec`.

4. **And When** no schedule has yet been generated, `atc://timeline` returns `{"events": []}` and `atc://runways` returns `{"runways": [<runway with empty operations>, ...]}` (capacity exposed, usage empty, `next_free_sec: 0`).

5. **And** generating a schedule twice in a row with identical state produces byte-identical tool payload and resource payloads.

6. **And** `tests/test_generate_schedule_tool.py` and `tests/test_timeline_runways_resources.py` cover the full contract.

## Tasks / Subtasks

- [ ] Task 1: Expose Config to tool/resource handlers via AppState (AC: #1, #3, #4)
  - [ ] 1.1 Add `config: Config | None = None` attribute and `set_config(config: Config) -> None` method to `AppState` in `domain/state.py`
  - [ ] 1.2 Import `Config` from `atc_mcp.config` in `domain/state.py` (safe: AST check sees `atc_mcp`, not `os` or `mcp`)
  - [ ] 1.3 Call `state.set_config(config)` in `server.py::create_app()` before returning the `FastMCP` instance

- [ ] Task 2: Implement `generate_schedule` tool handler (AC: #1, #5)
  - [ ] 2.1 Import `schedule` from `atc_mcp.scheduler.algorithm` in `tools.py`
  - [ ] 2.2 Replace `NotImplementedError` stub with a real implementation that:
    - Asserts `state.config is not None`
    - Calls `schedule(tuple(state.flights.values()), state.config)` → `Schedule`
    - Calls `state.set_latest_schedule(result)`
    - Builds an updated flights dict reflecting new states (see Flight State Mutation below)
    - Calls `state.replace_flights_after_schedule(updated_flights)`
    - Returns the architecture-pinned JSON payload (see Payload Shapes below)

- [ ] Task 3: Implement `atc://timeline` resource (AC: #2, #4, #5)
  - [ ] 3.1 Replace the stub in `resources.py::timeline_resource()` with a real implementation
  - [ ] 3.2 Return `{"events": []}` when `state.latest_schedule is None`
  - [ ] 3.3 Map each `Placement` to an event dict and sort by `(start_sec, runway_id, flight_number)`
  - [ ] 3.4 Include `depends_on` field per event (read from `state.flights[fn].dependencies`)

- [ ] Task 4: Implement `atc://runways` resource (AC: #3, #4, #5)
  - [ ] 4.1 Replace the stub in `resources.py::runways_resource()` with a real implementation
  - [ ] 4.2 Return all configured runways (from `state.config.runways`) sorted by `id` lex
  - [ ] 4.3 For each runway compute `scheduled_operations`, `busy_intervals_sec`, `next_free_sec` from `state.latest_schedule`
  - [ ] 4.4 Return empty lists / `next_free_sec: 0` when no schedule

- [ ] Task 5: Tests (AC: #6)
  - [ ] 5.1 Create `tests/test_generate_schedule_tool.py`
  - [ ] 5.2 Create `tests/test_timeline_runways_resources.py`

## Dev Notes

### ⚠️ Critical Design: Config Access Pattern

**Problem:** `generate_schedule()` and `runways_resource()` need `Config`, but the current code passes config only to `create_app(config)` in `server.py` — it is not accessible from `tools.py` or `resources.py`.

**Solution (chosen):** Extend `AppState` in `domain/state.py` to hold config.

```python
# domain/state.py — additions
from atc_mcp.config import Config   # safe: AST check sees "atc_mcp", not "os"/"mcp"

class AppState:
    def __init__(self) -> None:
        self.flights: dict[str, Flight] = {}
        self.latest_schedule: Schedule | None = None
        self.config: Config | None = None          # NEW

    def set_config(self, config: Config) -> None:  # NEW
        self.config = config
```

```python
# server.py — in create_app(), before return mcp
from atc_mcp.domain.state import state
state.set_config(config)
```

**Why this approach:**
- `state` singleton is already imported by both `tools.py` and `resources.py` — no new dependency graph edges.
- `test_domain_no_mcp_no_os` only checks for `"mcp"` and `"os"` in direct imports; `"atc_mcp"` is not forbidden.
- Mirrors the existing `state.latest_schedule` pattern for stored server-level data.
- Single seam for future expansion (matches architecture §State Persistence).

**⚠️ Do NOT:** create a separate module-level `_config` in `tools.py` and another in `resources.py` — this duplicates state and can desync.

**⚠️ Do NOT:** call `load_config()` inside tool handlers — `config.py` reads `os.environ` and config must be loaded only once at startup.

### ⚠️ Payload Shape Discrepancy: Epics Text vs Architecture

The epics story 3.4 AC text uses informal field names that **differ from the architecture-pinned shapes**. **Architecture always wins.** Below are the authoritative shapes.

#### `generate_schedule` output (architecture §MCP Tool Catalog)

```json
{
  "schedule": [
    {
      "flight_number": "AA123",
      "operation_type": "arrival",
      "runway_id": "R1",
      "gate_id": "G3",
      "start_sec": 0,
      "end_sec": 1200
    }
  ],
  "unscheduled": [
    {"flight_number": "AA999", "reason": "No runway meets minimum length 4500m"}
  ],
  "completion_time_seconds": 1200,
  "summary": {
    "scheduled_count": 1,
    "unscheduled_count": 1,
    "cancelled_count": 0
  }
}
```

- Root key is `"schedule"` (not `"placements"`) — maps to `Schedule.placements`
- Includes a `"summary"` sub-object
- `"unscheduled"` items have `flight_number` + `reason` (not the full `Flight` shape)

#### `atc://timeline` payload (architecture §MCP Resource Catalog)

```json
{
  "events": [
    {
      "start_sec": 0,
      "end_sec": 1200,
      "flight_number": "AA123",
      "operation_type": "arrival",
      "runway_id": "R1",
      "gate_id": "G3",
      "depends_on": []
    }
  ]
}
```

- Root key is **`"events"`** (epics 3.4 AC text incorrectly says `"timeline"` — ignore that)
- Existing stub already returns `{"events": []}` — keep this key
- Sort order: `(start_sec, runway_id, flight_number)` — **3-tuple** (epics text says 2-tuple, architecture wins)
- Each event includes `"depends_on"`: list of dependency flight numbers — read from `state.flights[flight_number].dependencies`

#### `atc://runways` payload (architecture §MCP Resource Catalog)

```json
{
  "runways": [
    {
      "id": "R1",
      "length_m": 3500,
      "scheduled_operations": [
        {
          "flight_number": "AA123",
          "operation_type": "arrival",
          "start_sec": 0,
          "end_sec": 1200
        }
      ],
      "busy_intervals_sec": [[0, 1200]],
      "next_free_sec": 1200
    }
  ]
}
```

- Per-runway key is **`"id"`** (not `"runway_id"` — epics text is wrong)
- Operations sub-key is **`"scheduled_operations"`** (not `"placements"`)
- Includes `"busy_intervals_sec"` (list of `[start, end]` pairs) and `"next_free_sec"`
- Sort runways by `id` lex
- Sort `scheduled_operations` per runway by `start_sec`
- `next_free_sec`: `max(op.end_sec for ops)` or `0` when empty

### Flight State Mutation After `schedule()`

The `generate_schedule` handler must update `state.flights` to reflect the new schedule outcome. Use the `replace_flights_after_schedule` helper that already exists on `AppState`:

```python
from atc_mcp.domain.models import FlightState

result = schedule(tuple(state.flights.values()), state.config)
state.set_latest_schedule(result)

# Build updated flights preserving insertion order
scheduled_numbers = {p.flight_number for p in result.placements}
unscheduled_map = {f.flight_number: f for f in result.unscheduled}

updated: dict[str, Flight] = {}
for fn, flight in state.flights.items():
    if flight.state == FlightState.cancelled:
        updated[fn] = flight  # preserve cancelled flights untouched
    elif fn in scheduled_numbers:
        updated[fn] = flight.model_copy(update={
            "state": FlightState.scheduled,
            "unscheduled_reason": None,
        })
    elif fn in unscheduled_map:
        unscheduled_flight = unscheduled_map[fn]
        updated[fn] = flight.model_copy(update={
            "state": FlightState.unschedulable,
            "unscheduled_reason": unscheduled_flight.unscheduled_reason,
        })
    else:
        # Should not occur: scheduler processes all non-cancelled flights
        updated[fn] = flight

state.replace_flights_after_schedule(updated)
```

**Key:** `Flight` is `frozen=True` — mutations must use `model_copy(update={...})` not direct field assignment.

### `generate_schedule` Return Payload Construction

```python
scheduled_placements = [
    {
        "flight_number": p.flight_number,
        "operation_type": p.operation_type,
        "runway_id": p.runway_id,
        "gate_id": p.gate_id,
        "start_sec": p.start_sec,
        "end_sec": p.end_sec,
    }
    for p in result.placements
]

unscheduled_list = [
    {"flight_number": f.flight_number, "reason": f.unscheduled_reason or ""}
    for f in result.unscheduled
]

cancelled_count = sum(
    1 for f in state.flights.values() if f.state == FlightState.cancelled
)

return {
    "schedule": scheduled_placements,
    "unscheduled": unscheduled_list,
    "completion_time_seconds": result.completion_time_seconds,
    "summary": {
        "scheduled_count": len(result.placements),
        "unscheduled_count": len(result.unscheduled),
        "cancelled_count": cancelled_count,
    },
}
```

Note: `"schedule"` is built from `result.placements`, not by serialising the `Schedule` model directly (because the JSON key differs from the Pydantic field name `placements`).

### `runways_resource` Implementation Pattern

```python
def runways_resource() -> str:
    if state.config is None:
        return json.dumps({"runways": []})

    # Group placements by runway
    placements_by_runway: dict[str, list] = {r.id: [] for r in state.config.runways}
    if state.latest_schedule is not None:
        for p in state.latest_schedule.placements:
            placements_by_runway[p.runway_id].append(p)

    runways_data = []
    for runway in sorted(state.config.runways, key=lambda r: r.id):
        ops = sorted(placements_by_runway[runway.id], key=lambda p: p.start_sec)
        scheduled_ops = [
            {
                "flight_number": p.flight_number,
                "operation_type": p.operation_type,
                "start_sec": p.start_sec,
                "end_sec": p.end_sec,
            }
            for p in ops
        ]
        busy = [[p.start_sec, p.end_sec] for p in ops]
        next_free = max((p.end_sec for p in ops), default=0)
        runways_data.append({
            "id": runway.id,
            "length_m": runway.length_m,
            "scheduled_operations": scheduled_ops,
            "busy_intervals_sec": busy,
            "next_free_sec": next_free,
        })

    return json.dumps({"runways": runways_data})
```

### `timeline_resource` Implementation Pattern

```python
def timeline_resource() -> str:
    if state.latest_schedule is None:
        return json.dumps({"events": []})

    events = sorted(
        state.latest_schedule.placements,
        key=lambda p: (p.start_sec, p.runway_id, p.flight_number),
    )
    events_data = [
        {
            "start_sec": p.start_sec,
            "end_sec": p.end_sec,
            "flight_number": p.flight_number,
            "operation_type": p.operation_type,
            "runway_id": p.runway_id,
            "gate_id": p.gate_id,
            "depends_on": state.flights[p.flight_number].dependencies
            if p.flight_number in state.flights else [],
        }
        for p in events
    ]
    return json.dumps({"events": events_data})
```

**Note:** `depends_on` reads from `state.flights` (not from the `Placement` model, which doesn't store dependencies). Since cancelled flights are excluded from placements, all `p.flight_number` keys should be present in `state.flights`.

### Two `Runway` Classes — Don't Mix Them

There are **two separate `Runway` Pydantic models** in the codebase:
- `atc_mcp.config.Runway` — used inside `Config.runways`; fields: `id: str`, `length_m: int`
- `atc_mcp.domain.models.Runway` — domain model; fields: `id: str`, `length_m: int`

They are structurally identical but live in different modules. `Config.runways` contains `config.Runway` instances. When `resources.py` iterates `state.config.runways`, it receives `config.Runway` objects — do not try to import or cast to `domain.models.Runway`.

### Module Dependency and Import Discipline

Permitted imports added by this story:
- `domain/state.py` adds `from atc_mcp.config import Config` → **safe** (`atc_mcp` ∉ `{"mcp", "os"}`)
- `tools.py` adds `from atc_mcp.scheduler.algorithm import schedule` → already allowed (`tools.py` can import scheduler)
- `resources.py` reads `state.config.runways` → already allowed via `state` import

No new violations introduced:
- `domain/state.py` still imports nothing from `mcp`, `os`, `time`, `datetime`, `random`
- `resources.py` still does not import `os` or `mcp` directly

### Files to Modify

| File | Change type | What changes |
|------|-------------|--------------|
| `src/atc_mcp/domain/state.py` | UPDATE | Add `config` attribute + `set_config()` method; add `from atc_mcp.config import Config` import |
| `src/atc_mcp/server.py` | UPDATE | Add `state.set_config(config)` call in `create_app()` |
| `src/atc_mcp/tools.py` | UPDATE | Replace `generate_schedule()` stub with real implementation; add `schedule` import |
| `src/atc_mcp/resources.py` | UPDATE | Replace `runways_resource()` and `timeline_resource()` stubs |

### Files to Create

| File | Purpose |
|------|---------|
| `tests/test_generate_schedule_tool.py` | Contract tests for the `generate_schedule` tool |
| `tests/test_timeline_runways_resources.py` | Contract tests for `atc://timeline` and `atc://runways` |

### Project Structure Notes

- All new code lives in files already registered with the MCP server — **no registration changes needed** in `server.py` beyond the `set_config` call.
- `scheduler.algorithm.schedule()` is a pure function with signature `schedule(flights: tuple[Flight, ...], config: Config) -> Schedule` — assumed delivered by Stories 3.1–3.3. Do not inline scheduling logic here.
- Gate IDs in `Placement` (e.g. `"G1"`, `"G2"`) are assigned by the scheduler — `resources.py` reads them as opaque strings from placements.
- `AppState.reset()` already clears `flights` and `latest_schedule`. The new `config` attribute should **not** be cleared by `reset()` since config is server-lifetime state (set once at startup, not per-request).

### Testing Requirements

#### `tests/test_generate_schedule_tool.py`

1. **Happy path — scheduled flights**: Submit 2 flights, call `generate_schedule`, assert return payload has `"schedule"`, `"unscheduled"`, `"completion_time_seconds"`, `"summary"` keys; `summary.scheduled_count == 2`; `state.latest_schedule` is set.
2. **Unschedulable flight**: Submit a flight with `min_length_m` that no runway meets; after `generate_schedule`, payload `unscheduled` list contains the flight with a non-empty `reason`; `state.flights[fn].state == "unschedulable"`.
3. **Flight state mutation**: Before `generate_schedule` all flights are `queued`; after, scheduled ones are `scheduled`, unschedulable are `unschedulable`.
4. **Empty queue**: Call `generate_schedule` with no flights; returns `{schedule: [], unscheduled: [], completion_time_seconds: null, summary: {scheduled_count: 0, unscheduled_count: 0, cancelled_count: 0}}`.
5. **Cancelled flights preserved**: Submit 2 flights, cancel one, call `generate_schedule`; cancelled flight is not in `schedule` list and remains `cancelled` in `state.flights`; `summary.cancelled_count == 1`.
6. **Determinism**: Call `generate_schedule` twice with identical state; both calls return byte-identical payloads (assert `json.dumps(r1) == json.dumps(r2)`).

#### `tests/test_timeline_runways_resources.py`

1. **Timeline — no schedule yet**: `timeline_resource()` returns `{"events": []}`.
2. **Runways — no schedule yet**: `runways_resource()` returns `{"runways": [...]}` with one entry per configured runway, all `scheduled_operations: []`, `busy_intervals_sec: []`, `next_free_sec: 0`.
3. **Timeline — after schedule**: After `generate_schedule`, `timeline_resource()` returns events with all required fields; sorted by `(start_sec, runway_id, flight_number)`.
4. **Timeline — `depends_on` field**: Event for a dependent flight shows its parent flight number in `depends_on`; event for an independent flight shows `depends_on: []`.
5. **Runways — after schedule**: `scheduled_operations` lists only the flights on that runway; `busy_intervals_sec` matches the operation windows; `next_free_sec` equals the latest `end_sec` on that runway.
6. **Runways — sorted by id lex**: If config has runways `R2`, `R1`, the output lists `R1` first.
7. **Determinism**: After a fixed schedule, calling `timeline_resource()` and `runways_resource()` 10 times each produces byte-identical outputs.

### Conftest Fixture Usage

Use the existing `conftest.py` `valid_env` fixture to get a `Config`. Create a local helper to call `load_config()` with the fixture, then call `state.set_config(cfg)` and `state.reset()` appropriately in fixtures:

```python
@pytest.fixture(autouse=True)
def clean_state():
    state.reset()
    yield
    state.reset()

@pytest.fixture
def cfg(valid_env):
    from atc_mcp.config import load_config
    c = load_config()
    state.set_config(c)
    return c
```

**Important:** `state.reset()` clears `flights` and `latest_schedule` but NOT `config`. Ensure `set_config` is called in the fixture before the test body runs. Calling `state.reset()` in `clean_state` is safe since tests don't need config to survive `reset()`.

### Preserving Existing Behaviour

- `flights_resource()` in `resources.py` is **not touched** — its implementation from Story 2.3 is correct and must not regress.
- `cancel_flight()` in `tools.py` is **not touched** — the `dependents_reevaluated: []` placeholder from Story 2.2 is intentional; Epic 3.6 wires the cascade.
- `submit_flight()` in `tools.py` is **not touched**.
- All 86 previously passing tests must continue to pass.

### References

- Architecture `generate_schedule` tool shape: `_bmad-output/planning-artifacts/architecture.md` §MCP Tool Catalog
- Architecture `atc://timeline` shape: `_bmad-output/planning-artifacts/architecture.md` §MCP Resource Catalog
- Architecture `atc://runways` shape: `_bmad-output/planning-artifacts/architecture.md` §MCP Resource Catalog
- Architecture §Scheduling Algorithm: deterministic greedy placement
- Architecture §Cancellation Re-evaluation Flow: `cancel_flight` calls `generate_schedule` internally (Story 3.6 will wire this)
- Architecture §Ordering Patterns: MUST sort before emitting
- Epics Story 3.4: `_bmad-output/planning-artifacts/epics.md` §Story 3.4 (use for AC intent; use architecture for payload shapes)
- Existing `AppState` API: `src/atc_mcp/domain/state.py`
- Existing `generate_schedule` stub: `src/atc_mcp/tools.py:70`
- Existing `runways_resource` / `timeline_resource` stubs: `src/atc_mcp/resources.py:23-30`
- Previous story pattern: `_bmad-output/implementation-artifacts/2-3-atc-flights-resource.md`

## Definition of Done

- [ ] `domain/state.py` has `config: Config | None` and `set_config()` method
- [ ] `server.py` calls `state.set_config(config)` before returning the `FastMCP` instance
- [ ] `generate_schedule()` in `tools.py` no longer raises `NotImplementedError`
- [ ] `generate_schedule()` calls `scheduler.algorithm.schedule()`, stores result, mutates flight states, returns architecture-pinned payload
- [ ] `timeline_resource()` returns `{"events": [...]}` sorted by `(start_sec, runway_id, flight_number)` with `depends_on`
- [ ] `runways_resource()` returns `{"runways": [...]}` with `id`, `length_m`, `scheduled_operations`, `busy_intervals_sec`, `next_free_sec` per runway
- [ ] No-schedule state returns empty lists (not errors)
- [ ] `tests/test_generate_schedule_tool.py` created with all 6 test cases
- [ ] `tests/test_timeline_runways_resources.py` created with all 7 test cases
- [ ] All new and pre-existing tests pass (no regressions)
- [ ] `test_imports.py` still passes (no forbidden imports added)
- [ ] Determinism property assertions pass
- [ ] No use of `time`, `datetime`, `random`, `os` in `domain/` or `scheduler/`
- [ ] All JSON fields use `snake_case`; time fields end in `_sec`

## Dev Agent Record

### Agent Model Used

_to be filled by dev agent_

### Debug Log References

### Completion Notes List

### File List

- `src/atc_mcp/domain/state.py` — updated: `config` attribute, `set_config()` method, `Config` import
- `src/atc_mcp/server.py` — updated: `state.set_config(config)` call in `create_app()`
- `src/atc_mcp/tools.py` — updated: `generate_schedule()` implemented
- `src/atc_mcp/resources.py` — updated: `runways_resource()` and `timeline_resource()` implemented
- `tests/test_generate_schedule_tool.py` — created
- `tests/test_timeline_runways_resources.py` — created

---

**Story Status:** ready-for-dev
**Last Updated:** 2026-05-21
**Context Engine:** Ultimate BMad Method story context completed
