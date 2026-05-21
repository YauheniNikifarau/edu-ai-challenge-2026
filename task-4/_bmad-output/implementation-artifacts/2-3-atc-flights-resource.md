---
story_id: "2.3"
story_key: "2-3-atc-flights-resource"
epic: "Epic 2: Flight Queue Management"
title: "`atc://flights` Resource"
status: "review"
created: "2026-05-21"
dependencies: ["1.3", "1.4", "2.1"]
---

# Story 2.3: `atc://flights` Resource

## User Story

**As an** AI client,
**I want** to inspect the full flight queue including unscheduled and cancelled flights with their reason strings,
**So that** I always have ground truth for what the airport is tracking, regardless of scheduling state.

## Business Context

This resource provides the complete visibility into the flight queue that AI clients need to understand the current state of all flights. It surfaces flights in all states (queued, scheduled, unschedulable, cancelled) with their reason strings, making it the primary inspection surface for understanding why certain flights cannot be scheduled.

This is a read-only resource that projects the current `AppState.flights` dictionary into a sorted, deterministic JSON payload. It's critical for debugging, monitoring, and AI decision-making.

## Acceptance Criteria

**Given** `AppState.flights` contains a mix of `queued`, `scheduled`, `unschedulable`, and `cancelled` flights
**When** I read the `atc://flights` resource
**Then** the payload is the architecture-pinned JSON: `{"flights": [<Flight>, ...]}` with `snake_case` fields, `_sec` suffix on integer-second fields, `null` for "not yet computed" placement, `[]` for empty dependency lists
**And** the `flights` list is sorted by the documented sort order from architecture (`(state_rank, flight_number)` lex, with `state_rank` per the architecture spec)
**And** each entry's `unscheduled_reason` field is present (value `null` when not applicable, lowercase sentence with no trailing period when set)
**And** the resource never reads `os.environ`, never imports `mcp` directly from `domain/` (it lives in `resources.py` which does), and produces byte-identical output across N reads for identical state
**And** `tests/test_flights_resource.py` covers: empty state returns `{"flights": []}`; mixed-state ordering; reason-string format; determinism across 100 reads

## Technical Requirements

### Architecture Compliance

**From architecture.md §MCP Resource Catalog:**

Resource URI: `atc://flights`

**Payload shape (JSON):**
```json
{
  "flights": [
    {
      "flight_number": "AA123",
      "operation_type": "arrival",
      "priority": "high",
      "dependencies": [],
      "runway_requirements": {"min_length_m": 3500},
      "state": "scheduled",
      "unscheduled_reason": null
    }
  ]
}
```

**Ordering:** by `(state_rank, flight_number)` where `state_rank` is:
- `scheduled=0`
- `queued=1`
- `unschedulable=2`
- `cancelled=3`

This ensures scheduled flights appear first, followed by queued, then unschedulable, then cancelled. Within each state group, flights are sorted alphabetically by flight_number for determinism.

### Data Model

**From domain/models.py:**
- `Flight` model with all fields: `flight_number`, `operation_type`, `priority`, `dependencies`, `runway_requirements`, `state`, `unscheduled_reason`
- `FlightState` enum: `queued`, `scheduled`, `unschedulable`, `cancelled`
- `OperationType` enum: `arrival`, `departure`
- `Priority` enum: `high`, `medium`, `low`

**From domain/state.py:**
- `AppState.flights: dict[str, Flight]` — insertion-ordered dictionary
- Access via `state.flights` singleton

### JSON Conventions

**From architecture.md §Format Patterns:**

1. **Field naming:** `snake_case` for all JSON fields
2. **Time fields:** Integer seconds with `_sec` suffix (though Flight model doesn't have time fields directly)
3. **Null handling:** 
   - `null` for "not yet computed" or "not applicable" (e.g., `unscheduled_reason: null` for scheduled flights)
   - `[]` for "computed and empty" (e.g., `dependencies: []`)
4. **Enum representation:** String literals (`"arrival"`, `"high"`, `"queued"`, etc.)
5. **Reason string format:** Lowercase sentence, no trailing period, names the offending value where applicable

### Determinism Requirements

**From architecture.md §Ordering Patterns (Determinism Enforcement):**

> These are not stylistic — they are correctness rules tied to `FR-SCH-6`.

**MUST sort before emitting:**
- The flights list MUST be sorted by `(state_rank, flight_number)` before returning
- Never iterate `set` to produce output
- Use stable sort keys to ensure byte-identical output across multiple reads

**Property test requirement:**
- `tests/test_flights_resource.py` must include a test that calls the resource 100 times with identical state and asserts byte-identical JSON output

### Module Dependency Rules

**From architecture.md §Structure Patterns:**

```
domain/        ← no MCP imports, no env var reads
resources.py   ← imports domain
```

- The resource handler lives in `resources.py`
- It imports from `domain.models` and `domain.state`
- It does NOT import `os`, `time`, `datetime`, or `random`
- The `domain/` modules remain MCP-agnostic

## Implementation Guidance

### File to Modify

**UPDATE:** `src/atc_mcp/resources.py`

Current state (from Story 1.4):
```python
def flights_resource() -> str:
    """Current flight queue including unscheduled and cancelled."""
    return json.dumps({"flights": []})
```

### Implementation Steps

1. **Import required modules:**
   ```python
   from atc_mcp.domain.state import state
   from atc_mcp.domain.models import FlightState
   ```

2. **Define state_rank mapping:**
   Create a helper function or dict to map `FlightState` to integer rank:
   - `scheduled` → 0
   - `queued` → 1
   - `unschedulable` → 2
   - `cancelled` → 3

3. **Implement sorting logic:**
   - Extract all flights from `state.flights.values()`
   - Sort by `(state_rank(flight.state), flight.flight_number)`
   - Use `sorted()` with a key function for determinism

4. **Convert to JSON:**
   - Convert each `Flight` Pydantic model to dict using `.model_dump()`
   - Ensure `dependencies` is `[]` not `null` when empty (Pydantic default_factory handles this)
   - Ensure `runway_requirements` is `null` when not set
   - Ensure `unscheduled_reason` is `null` when not set
   - Wrap in `{"flights": [...]}`
   - Use `json.dumps()` with consistent formatting

5. **Handle empty state:**
   - When `state.flights` is empty, return `{"flights": []}`

### Code Pattern Example

```python
def flights_resource() -> str:
    """Current flight queue including unscheduled and cancelled."""
    from atc_mcp.domain.state import state
    from atc_mcp.domain.models import FlightState
    
    # State rank mapping for deterministic ordering
    STATE_RANK = {
        FlightState.scheduled: 0,
        FlightState.queued: 1,
        FlightState.unschedulable: 2,
        FlightState.cancelled: 3,
    }
    
    # Sort flights by (state_rank, flight_number)
    sorted_flights = sorted(
        state.flights.values(),
        key=lambda f: (STATE_RANK[f.state], f.flight_number)
    )
    
    # Convert to JSON-serializable dicts
    flights_data = [f.model_dump() for f in sorted_flights]
    
    return json.dumps({"flights": flights_data})
```

### Testing Requirements

**CREATE:** `tests/test_flights_resource.py`

Test cases to cover:

1. **Empty state:**
   - Given: `state.flights` is empty
   - When: Read `atc://flights`
   - Then: Returns `{"flights": []}`

2. **Single flight:**
   - Given: One queued flight in state
   - When: Read resource
   - Then: Returns flight with all fields correctly serialized

3. **Mixed state ordering:**
   - Given: Flights in all four states (scheduled, queued, unschedulable, cancelled)
   - When: Read resource
   - Then: Flights appear in correct order (scheduled first, then queued, then unschedulable, then cancelled)
   - And: Within each state group, flights are alphabetically sorted by flight_number

4. **Reason string format:**
   - Given: An unschedulable flight with `unscheduled_reason` set
   - When: Read resource
   - Then: Reason appears as lowercase sentence with no trailing period
   - And: Scheduled/queued flights have `unscheduled_reason: null`

5. **Dependencies serialization:**
   - Given: Flight with empty dependencies list
   - When: Read resource
   - Then: `dependencies: []` (not `null`)
   - Given: Flight with dependencies
   - Then: `dependencies: ["AA001", "AA002"]`

6. **Runway requirements serialization:**
   - Given: Flight with no runway requirements
   - When: Read resource
   - Then: `runway_requirements: null`
   - Given: Flight with runway requirements
   - Then: `runway_requirements: {"min_length_m": 3500}`

7. **Determinism property test:**
   - Given: A fixed set of flights in state
   - When: Read resource 100 times
   - Then: All 100 outputs are byte-identical

### Integration Points

**Upstream dependencies:**
- Story 1.3: Domain models (`Flight`, `FlightState`, etc.) and `AppState`
- Story 1.4: MCP server registration (resource already registered, just needs implementation)
- Story 2.1: `submit_flight` tool populates `AppState.flights` (though not strictly required for this story's tests)

**Downstream consumers:**
- AI clients reading the resource via MCP
- Future stories that need to verify flight state visibility

**State mutations:**
- This resource is read-only
- It projects current state; does not mutate anything

## Definition of Done

- [x] `flights_resource()` in `resources.py` implemented per specification
- [x] Reads from `state.flights` singleton
- [x] Sorts by `(state_rank, flight_number)` deterministically
- [x] Returns architecture-pinned JSON shape
- [x] Handles empty state correctly
- [x] All JSON conventions followed (snake_case, null vs [], enum strings)
- [x] `tests/test_flights_resource.py` created with all 7 test cases
- [x] All tests pass
- [x] Determinism property test (100 reads) passes
- [x] No imports of `os`, `time`, `datetime`, `random` in resource handler
- [x] Code follows PEP 8 naming conventions
- [x] No regression in existing tests

## Notes for Developer

### Critical Implementation Details

1. **State rank mapping is mandatory:** The sort order is specified in the architecture and must be exactly as documented. Don't use alphabetical state names or enum value order.

2. **Pydantic serialization:** Use `.model_dump()` not `.dict()` (Pydantic v2 convention). This automatically handles:
   - Enum conversion to string literals
   - `None` → `null` in JSON
   - Default factories for empty lists

3. **Determinism is non-negotiable:** The 100-read property test is not optional. This resource must produce byte-identical output for identical state.

4. **Empty vs null:** Be precise about when to use `[]` vs `null`:
   - `dependencies`: Always a list, `[]` when empty (handled by Pydantic default_factory)
   - `runway_requirements`: `null` when not set, object when set
   - `unscheduled_reason`: `null` when not applicable, string when set

5. **No premature optimization:** Don't cache the JSON output. The resource is read-only and state can change between reads. Always read fresh from `state.flights`.

### Common Pitfalls to Avoid

❌ **Don't** iterate over `state.flights.keys()` or use set operations — always work with `.values()` and sort explicitly

❌ **Don't** use `json.dumps(sort_keys=True)` — this sorts dictionary keys, not the flights list. You must sort the flights list explicitly before serialization.

❌ **Don't** forget to handle the empty state case — `state.flights` can be empty at server startup

❌ **Don't** add extra fields not in the architecture spec — stick to the exact `Flight` model fields

❌ **Don't** import from `mcp` SDK in this module — `resources.py` is the boundary, not the domain

### Why This Matters

This resource is the primary visibility surface for AI clients to understand what flights exist and why some cannot be scheduled. The reason strings are first-class data (not logs) and must propagate correctly. The deterministic ordering ensures AI clients can rely on consistent output for decision-making.

The architecture explicitly calls out that unschedulable flights "must remain visible with a clear reason" (FR-SCH-4). This resource is how that requirement is fulfilled.

## Related Documentation

- Architecture: `_bmad-output/planning-artifacts/architecture.md` §MCP Resource Catalog
- Epics: `_bmad-output/planning-artifacts/epics.md` Epic 2, Story 2.3
- Domain models: `src/atc_mcp/domain/models.py`
- State management: `src/atc_mcp/domain/state.py`

---

## Dev Agent Record

### Implementation Plan

Implemented `flights_resource()` in `resources.py` by:
1. Adding top-level imports: `FlightState` from `domain.models`, `state` from `domain.state`
2. Defining `_STATE_RANK` dict inside the function mapping each `FlightState` to its sort rank (scheduled=0, queued=1, unschedulable=2, cancelled=3)
3. Sorting `state.flights.values()` with `sorted()` and a stable `(rank, flight_number)` key for byte-identical determinism
4. Serialising via `f.model_dump()` — Pydantic v2 handles StrEnum→string, None→null, default-factory list→[]

Created `tests/test_flights_resource.py` with 10 test functions (exceeds the 7-case requirement) covering: empty state, single-flight serialisation, cross-state ordering, within-state alphabetical ordering, reason string format, empty/non-empty dependencies, null/object runway requirements, and 100-read determinism property test.

### Completion Notes

- All 86 tests pass (76 pre-existing + 10 new), zero regressions
- `ruff check` passes cleanly on both changed files
- No forbidden imports (`os`, `time`, `datetime`, `random`) added
- `_STATE_RANK` dict is local to the function to keep it scope-appropriate; the lookup is O(1) and allocation cost is negligible for a read-only resource

## File List

- `src/atc_mcp/resources.py` — modified: implemented `flights_resource()`, added domain imports
- `tests/test_flights_resource.py` — created: 10 test cases

## Change Log

- 2026-05-21: Implemented `flights_resource()` with deterministic state-rank sorting and Pydantic v2 serialisation; created `tests/test_flights_resource.py` (10 tests)

---

**Story Status:** review
**Last Updated:** 2026-05-21
**Context Engine:** Ultimate BMad Method story context completed
