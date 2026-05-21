---
story_id: "3.2"
story_key: "3-2-dependency-ordering-with-buffer-and-cycle-detection"
epic: "Epic 3: Deterministic Scheduling Engine & Airport Operations"
title: "Dependency Ordering with Buffer & Cycle Detection"
status: "ready-for-dev"
created: "2026-05-21"
dependencies: ["3.1"]
---

# Story 3.2: Dependency Ordering with Buffer & Cycle Detection

## User Story

**As the** scheduling engine,
**I want** to honour explicit flight dependencies with a buffer floor and detect cycles,
**So that** dependent flights never start before their dependencies complete and the algorithm never loops or non-terminates.

## Business Context

Story 3.1 implemented the basic greedy placement algorithm with runway separation, gate turnaround, runway-requirement matching, and horizon enforcement — but hardcoded `topo_depth=0` for all flights (no dependency ordering). This story replaces that stub with real topological depth computation, dependency buffer floor enforcement, and cycle detection.

Once complete, the scheduler correctly handles connecting-flight scenarios (VS-3), prevents circular dependency hangs, and cascades unschedulability from cancelled/unschedulable dependencies to their dependents.

**⚠️ PREREQUISITE: Story 3.1 must be fully implemented before working on this story.** Specifically, `scheduler/algorithm.py` must expose `schedule(flights: tuple[Flight, ...], config: Config) -> Schedule` with working single-flight constraint logic (separation, turnaround, runway match, horizon).

## Acceptance Criteria

**AC-1 — Topological sort key**
**Given** `scheduler/algorithm.schedule()` from Story 3.1
**When** I call it with flights that have a dependency DAG
**Then** the sort key is the true `(topo_depth, priority_rank, flight_number)` where `topo_depth` is computed from `dependencies` (leaves depth=0; depth = `1 + max(topo[d] for d in deps)`)

**AC-2 — Dependency buffer floor**
**Given** flight `F` depends on flight `F_dep` and both are scheduled
**Then** `F.start_sec ≥ F_dep.end_sec + ATC_DEPENDENCY_BUFFER_SEC`
**And** the dependency buffer floor coexists with separation/turnaround (whichever is later wins — `t_start = max(dep_floor, sep_floor, turnaround_floor)`)

**AC-3 — Cycle detection (direct and indirect)**
**When** the dependency graph contains a cycle (2-cycle, 3-cycle, or self-cycle)
**Then** every flight participating in the cycle is marked `unschedulable` with `unscheduled_reason` exactly:
`"dependency cycle: <flight_numbers sorted lex, comma-space separated>"`
e.g. for a 2-cycle between F1 and F2: `"dependency cycle: F1, F2"`
**And** non-cycle flights are scheduled normally

**AC-4 — Cascade from unschedulable/cancelled dependency**
**When** a flight's dependency `D` is either `unschedulable` or `cancelled`
**Then** the dependent flight is marked `unschedulable` with `unscheduled_reason` exactly:
`"dependency <D.flight_number> is not scheduled"`

**AC-5 — Test coverage**
`tests/test_scheduler_dependencies.py` covers:
- Linear chain of 3 with dep buffer enforced at each link
- Diamond DAG (A→B→D, A→C→D) — correct topo_depths and placement
- 2-cycle (F1↔F2): both unschedulable with exact reason string
- 3-cycle (F1→F2→F3→F1): all three unschedulable with exact reason string
- Self-cycle F1→F1 (defence-in-depth; `submit_flight` normally prevents this)
- Dep on cancelled flight → dependent unschedulable with exact reason
- Dep on unschedulable flight → dependent unschedulable with exact reason

## Technical Requirements

### Architecture Compliance

**Module dependency rules (MUST NOT violate):**
```
scheduler/algorithm.py  ← imports domain.models, config (Config), scheduler/constraints only
scheduler/constraints.py ← imports domain.models, config only
```
Neither may import `mcp`, `os`, `time`, `datetime`, or `random`.
Enforced by `tests/test_imports.py`.

**Determinism rules:**
- Cycle member set → produce reason string with **`sorted(cycle_members)`** for lex order
- Any iteration over `set` objects used internally during cycle detection must be sorted before driving output
- Sort key `(topo_depth, priority_rank, flight_number)` is a total order — flight_number is unique

### Exact Reason Strings (copy-paste verbatim — tests will assert exact equality)

| Situation | `unscheduled_reason` value |
|---|---|
| Flight in a dependency cycle | `"dependency cycle: F1, F2"` (members sorted lex, comma-space joined) |
| Dependency is unschedulable or cancelled | `"dependency <flight_number> is not scheduled"` |
| (from Story 3.1) Runway req unmet | `"no runway meets minimum length <N>m (available runways: <id> <len>m, ...)"` |
| (from Story 3.1) Exceeds horizon | `"would exceed scheduling horizon"` |

**Note:** lowercase, no trailing period — matches `architecture.md §Format Patterns`.

### Algorithm Design — Step 1 Extension (Build Sort Order)

Story 3.1 hardcoded `topo_depth=0`. Replace with this two-phase computation:

**Phase A — Cycle detection via DFS coloring:**
```
color: dict[str, int]  # 0=unvisited, 1=in-stack (GRAY), 2=done (BLACK)
cycles: list[frozenset[str]]  # each cycle is the set of flight_numbers in it

def _dfs_cycles(fn: str, stack: list[str], ...):
    color[fn] = 1  # GRAY
    stack.append(fn)
    for dep_fn in flights[fn].dependencies:
        if dep_fn not in flight_map:
            continue  # dep was deleted / doesn't exist
        if color[dep_fn] == 1:  # back-edge → cycle
            # Collect cycle members: everything from stack[index(dep_fn):]
            cycle_start = stack.index(dep_fn)
            cycle_members = frozenset(stack[cycle_start:])
            cycles.append(cycle_members)
        elif color[dep_fn] == 0:
            _dfs_cycles(dep_fn, stack, ...)
    stack.pop()
    color[fn] = 2  # BLACK
```

- Call `_dfs_cycles` for every flight with `color[fn] == 0`
- Collect all unique cycled flight_numbers by flattening cycles
- These flights are immediately marked unschedulable; reason = `"dependency cycle: " + ", ".join(sorted(cycle_members))`

**Phase B — Topological depth via DFS memoization (non-cycled flights only):**
```
depth: dict[str, int] = {}

def _topo_depth(fn: str) -> int:
    if fn in depth:
        return depth[fn]
    flight = flight_map[fn]
    if not flight.dependencies:
        depth[fn] = 0
        return 0
    max_dep_depth = max(
        _topo_depth(d) for d in flight.dependencies
        if d in flight_map and d not in cycled_set
    )
    depth[fn] = max_dep_depth + 1
    return depth[fn]
```

### Algorithm Design — Step 2 Extension (Floor Start Time from Dependencies)

After sorting, for each flight `f` being placed:

1. For each `dep_fn` in `f.dependencies`:
   - Look up current state of `dep_fn` in the mutated flights dict (flights are updated as algorithm runs)
   - If `dep_fn` state is `unschedulable` or `cancelled`: mark `f` unschedulable with `"dependency <dep_fn> is not scheduled"`, skip to next flight
   - Else: `floor_start = max(floor_start, placements[dep_fn].end_sec + config.dependency_buffer_sec)`

2. Pass `floor_start` into the placement search from Story 3.1. The earliest feasible start respects `floor_start` in addition to runway separation and gate turnaround — `t = max(floor_start, sep_floor, turnaround_floor)`.

**Critical:** Process deps in a deterministic order — sort `f.dependencies` before iterating (they were submitted insertion-ordered, which is deterministic, but explicit sort is safer). Actually, since submission order is deterministic and the result of taking `max(...)` is commutative, the iteration order doesn't affect the floor value — but do check all deps before deciding to mark unschedulable to catch any unschedulable dep.

### Data Structures

The algorithm needs to track, for each placed flight, its committed placement (for dep floor calculation). Suggested:

```python
placements: dict[str, Placement] = {}   # flight_number -> Placement (committed)
```

This dict is built up as flights are placed in topological order, so by the time we process flight `F`, all its deps have already been processed (placed or marked unschedulable).

### Files

| File | Action | Notes |
|---|---|---|
| `src/atc_mcp/scheduler/algorithm.py` | **UPDATE** | Replace `topo_depth=0` stub; add cycle detection + dep buffer logic |
| `src/atc_mcp/scheduler/constraints.py` | **UPDATE (optional)** | Add `compute_dep_floor()` helper if decomposition helps clarity |
| `tests/test_scheduler_dependencies.py` | **CREATE** | 7+ test cases per AC-5 |

**Do NOT modify:** `domain/models.py`, `domain/state.py`, `config.py`, `tools.py`, `resources.py`, `tests/test_scheduler_placement.py` (Story 3.1 tests must continue passing).

## Implementation Guidance

### What Story 3.1 Provides (Do Not Re-implement)

Story 3.1's `algorithm.py` delivers these capabilities that this story builds on:
- `schedule(flights: tuple[Flight, ...], config: Config) -> Schedule` function signature
- Runway separation (takeoff/landing/mixed), gate turnaround enforcement
- Runway-requirement matching with exact unschedulable reason format
- Horizon overflow detection with exact unschedulable reason format
- Earliest feasible `(runway, gate)` search with `(runway_id, gate_id)` lex tie-break
- `PRIORITY_RANK = {Priority.high: 0, Priority.medium: 1, Priority.low: 2}` constant

### Implementation Steps

**Step 1:** Add a private helper (in `algorithm.py` or `constraints.py`) that takes `flight_map: dict[str, Flight]` and returns `(topo_depths: dict[str, int], cycled: set[str])`.

**Step 2:** In `schedule()`, call the helper on non-cancelled flights. Immediately mark all flights in `cycled` as unschedulable with the cycle reason string.

**Step 3:** Replace the `topo_depth=0` stub in the sort key with the computed `topo_depths.get(fn, 0)`.

**Step 4:** In the per-flight placement loop, compute `dep_floor` before calling the existing placement search. If any dep is unschedulable/cancelled, mark `f` unschedulable and `continue`.

**Step 5:** After placing a flight, add its `Placement` to the `placements` dict so downstream deps can compute their floor.

### Code Skeleton

```python
def schedule(flights: tuple[Flight, ...], config: Config) -> Schedule:
    PRIORITY_RANK = {Priority.high: 0, Priority.medium: 1, Priority.low: 2}
    
    # Split cancelled out — they are never placed
    active = [f for f in flights if f.state != FlightState.cancelled]
    flight_map = {f.flight_number: f for f in active}
    
    # Phase 1: Cycle detection + topo depth
    topo_depths, cycled = _compute_topo_and_cycles(flight_map)
    
    # Mark cycled flights immediately (build updated flight objects)
    result_flights: dict[str, Flight] = {}
    for f in flights:
        if f.flight_number in cycled:
            members = sorted(
                fn for fn in cycled
                # Only report members of THIS cycle (if flights can be in separate cycles,
                # you need to track which cycle each member belongs to)
            )
            result_flights[f.flight_number] = f.model_copy(update={
                "state": FlightState.unschedulable,
                "unscheduled_reason": "dependency cycle: " + ", ".join(members),
            })
        else:
            result_flights[f.flight_number] = f
    
    # Sort non-cycled active flights
    schedulable = [
        result_flights[f.flight_number]
        for f in flights
        if f.flight_number not in cycled and f.state != FlightState.cancelled
    ]
    sorted_flights = sorted(
        schedulable,
        key=lambda f: (topo_depths.get(f.flight_number, 0), PRIORITY_RANK[f.priority], f.flight_number),
    )
    
    # Phase 2: Placement with dep floor
    placements: dict[str, Placement] = {}
    runway_intervals: dict[str, list[tuple[int, int, OperationType]]] = {...}  # from Story 3.1
    gate_intervals: dict[str, list[tuple[int, int]]] = {...}  # from Story 3.1
    
    for f in sorted_flights:
        # Compute dep floor
        dep_floor = 0
        dep_blocked = False
        for dep_fn in f.dependencies:
            dep_state = result_flights[dep_fn].state
            if dep_state in (FlightState.unschedulable, FlightState.cancelled):
                result_flights[f.flight_number] = result_flights[f.flight_number].model_copy(update={
                    "state": FlightState.unschedulable,
                    "unscheduled_reason": f"dependency {dep_fn} is not scheduled",
                })
                dep_blocked = True
                break
            if dep_fn in placements:
                dep_floor = max(dep_floor, placements[dep_fn].end_sec + config.dependency_buffer_sec)
        
        if dep_blocked:
            continue
        
        # Existing Story 3.1 placement logic with dep_floor as additional constraint
        placement = _find_earliest_placement(f, config, runway_intervals, gate_intervals, floor_start=dep_floor)
        if placement is None:
            result_flights[f.flight_number] = result_flights[f.flight_number].model_copy(update={
                "state": FlightState.unschedulable,
                "unscheduled_reason": "would exceed scheduling horizon",
            })
            continue
        
        placements[f.flight_number] = placement
        result_flights[f.flight_number] = result_flights[f.flight_number].model_copy(update={
            "state": FlightState.scheduled,
        })
        # Update runway_intervals and gate_intervals with the new placement
        ...
    
    # Build Schedule
    placed = tuple(placements[fn] for fn in sorted(placements, key=lambda fn: (placements[fn].start_sec, fn)))
    unscheduled = tuple(f for f in result_flights.values() if f.state == FlightState.unschedulable)
    completion = max((p.end_sec for p in placed), default=None)
    return Schedule(placements=placed, unscheduled=unscheduled, completion_time_seconds=completion)
```

**Note:** Adapt to the actual internal structure Story 3.1 established. The skeleton above is illustrative — `_find_earliest_placement` and the interval tracking structures come from Story 3.1.

### Cycle Detection — Handling Multiple Separate Cycles

If the flight graph has two independent cycles (e.g., {F1, F2} and {F3, F4}), each cycle's member set must produce its own reason string. The DFS naturally discovers separate cycles as separate back-edge events.

Track `which_cycle: dict[str, frozenset[str]]` — mapping `flight_number → cycle_members_set`. When marking unschedulable: `"dependency cycle: " + ", ".join(sorted(which_cycle[fn]))`.

### Testing Requirements

**CREATE:** `tests/test_scheduler_dependencies.py`

Use `conftest.py`'s `VALID_ENV` and `valid_env` fixture. Call `load_config()` within each test (or fixture) to get a `Config`.

Reference config from `conftest.py`:
- `ATC_DEPENDENCY_BUFFER_SEC = 600`
- `ATC_DURATION_ARRIVAL_SEC = 1200`, `ATC_DURATION_DEPARTURE_SEC = 1200`
- `ATC_RUNWAY_SEP_TAKEOFF_SEC = 120`, `ATC_RUNWAY_SEP_LANDING_SEC = 180`, `ATC_RUNWAY_SEP_MIXED_SEC = 240`

**Test 1 — Linear chain dep buffer:**
```
A (arrival, high) → B (departure, medium) → C (arrival, low)
```
- A placed at [0, 1200)
- B.start_sec ≥ 1200 + 600 = 1800; B placed at 1800
- C.start_sec ≥ (B.end_sec) + 600; assert C.start_sec ≥ B.end_sec + 600
- All three state = scheduled

**Test 2 — Diamond DAG:**
```
A → B → D
A → C → D
```
- topo_depths: A=0, B=1, C=1, D=2
- D.start_sec ≥ max(B.end_sec, C.end_sec) + dep_buffer
- Assert all 4 scheduled; D.start_sec satisfies constraint for both B and C

**Test 3 — 2-cycle:**
```
F1.dependencies = ["F2"], F2.dependencies = ["F1"]
```
- Both unschedulable
- `F1.unscheduled_reason == "dependency cycle: F1, F2"`
- `F2.unscheduled_reason == "dependency cycle: F1, F2"`

**Test 4 — 3-cycle:**
```
F1 → F2 → F3 → F1
```
- All three unschedulable
- Each reason = `"dependency cycle: F1, F2, F3"`

**Test 5 — Self-cycle (defence-in-depth):**
```
F1.dependencies = ["F1"]
```
- `F1.unscheduled_reason == "dependency cycle: F1"`

**Test 6 — Dep on cancelled:**
```
A (arrival, high), B (departure, medium, deps=["A"])
Manually set A.state = FlightState.cancelled before calling schedule()
```
- B.unscheduled_reason == `"dependency A is not scheduled"`

**Test 7 — Dep on unschedulable:**
```
A (departure, high, runway_requirements=min_length_m=9999 — no runway matches)
B (arrival, medium, deps=["A"])
```
- A.state = unschedulable (runway req unmet — from Story 3.1 logic)
- B.unscheduled_reason == `"dependency A is not scheduled"`

**Test 8 — Non-cycle flights unaffected by cycle:**
```
F1 ↔ F2 (cycle), F3 (no deps, arrival, high)
```
- F1 and F2 unschedulable with cycle reason
- F3 scheduled normally

**Test 9 — Dep buffer beats separation/turnaround (buffer dominates):**
- Use `ATC_DEPENDENCY_BUFFER_SEC = 600` and small separation values
- B's dep floor from A = 1200 + 600 = 1800
- Even if runway sep would allow placement earlier, B.start_sec = 1800

**Test 10 — Separation beats dep buffer (separation dominates):**
- Construct a scenario where runway separation or gate turnaround forces B later than 1800
- B.start_sec = max(dep_floor, sep_floor) — assert whichever is larger wins

### Integration with Existing Tests

After implementation, ALL of these must still pass:
- `tests/test_scheduler_placement.py` (Story 3.1) — no regressions
- `tests/test_cancel_flight.py`, `tests/test_submit_flight.py`, `tests/test_flights_resource.py` (Epic 2)
- `tests/test_imports.py` — `scheduler/` must not import forbidden modules

Run: `pytest -q` from project root to verify.

## Definition of Done

- [ ] `_compute_topo_and_cycles()` helper implemented (in `algorithm.py` or `constraints.py`)
- [ ] `schedule()` uses computed `topo_depths` in sort key (replaces hardcoded `0`)
- [ ] `schedule()` marks all cycled flights `unschedulable` with exact reason string (sorted lex members)
- [ ] `schedule()` marks dependents of unschedulable/cancelled flights with exact reason string
- [ ] `schedule()` enforces dep buffer floor (`dep.end_sec + dep_buffer_sec`) on placement
- [ ] Dep buffer floor coexists with separation/turnaround (max of all constraints)
- [ ] `tests/test_scheduler_dependencies.py` created with ≥ 7 test cases (all AC-5 cases)
- [ ] All tests pass (no regressions in prior stories)
- [ ] No forbidden imports (`mcp`, `os`, `time`, `datetime`, `random`) in `scheduler/`
- [ ] `ruff check` clean

## Notes for Developer

### Critical Implementation Details

1. **Cycle member collection per cycle:** If the graph has two independent cycles, each flight should report its own cycle's members (not all cycled flights globally). Track `which_cycle[fn] = frozenset(cycle_members)` mapping per flight.

2. **Cancelled flights are excluded from topo/cycle computation:** Only process `active = [f for f in flights if f.state != FlightState.cancelled]`. Cancelled flights skip placement entirely; their deps' `dep_floor` is computed only for non-cancelled, non-cycled deps.

3. **`model_copy(update={...})` for mutations:** `Flight` is frozen Pydantic v2. To update state, use `flight.model_copy(update={"state": FlightState.unschedulable, "unscheduled_reason": "..."})`. Established pattern from Story 2.2 (`cancel_flight` in `tools.py`).

4. **`sorted()` on dep flight numbers in reason string:** The reason string `"dependency cycle: F1, F2"` requires `sorted(cycle_members)` — alphabetical (Python default string sort). This is mandatory for determinism.

5. **Dep floor check order matters for multi-dep flights:** Check ALL deps before deciding to place. If *any* dep is unschedulable/cancelled, immediately mark unschedulable (first such dep encountered alphabetically for determinism). Do NOT partially advance `dep_floor` and then fail — reset and mark.

6. **`placements` dict is keyed by `flight_number`:** The dict is built up in topological order. By design, when processing flight `F`, all deps of `F` are already in `placements` (or were marked unschedulable). This is guaranteed by the topological sort.

7. **Self-cycle handling:** A self-cycle (`F.dependencies = ["F"]`) is detected as a back-edge immediately when the DFS visits `F` (it is already GRAY). The cycle member set = `{F.flight_number}` and reason = `"dependency cycle: F"`.

### Common Pitfalls to Avoid

❌ **Don't** hardcode `topo_depth=0` in the sort key — that's the Story 3.1 stub; this story replaces it.

❌ **Don't** use `set` iteration to produce the cycle reason string — always `sorted(cycle_members)`.

❌ **Don't** skip computing the dep floor for flights that have some scheduled AND some unschedulable deps — once ANY dep is unschedulable/cancelled the whole flight is blocked, exit early.

❌ **Don't** modify the `Flight` Pydantic model fields — all necessary fields (`state`, `unscheduled_reason`) already exist in `domain/models.py` from Story 1.3.

❌ **Don't** re-run the full DFS for every flight — compute all depths and cycles in a single pass over the graph.

❌ **Don't** add the `placements` tracking dict to `AppState` — it is local to each `schedule()` call, not persistent state.

### VS-3 Validation Impact

This story is required for VS-3 (Connecting Flight) to pass. The scenario:
- `IN001` (arrival, medium, no deps) → placed at [0, 1200)
- `OUT002` (departure, medium, deps=["IN001"]) → `dep_floor = 1200 + 600 = 1800`, placed at [1800, 3000)

After this story, `scheduler.schedule()` with the VS-3 inputs should produce exactly this placement. `tests/test_vs3_connecting_flight.py` (Story 4.4) will validate the full end-to-end, but can be manually verified here.

## Related Documentation

- Architecture: `_bmad-output/planning-artifacts/architecture.md` §Scheduling Algorithm (resolves DD-4)
- Architecture: `_bmad-output/planning-artifacts/architecture.md` §Ordering Patterns (determinism enforcement)
- Epics: `_bmad-output/planning-artifacts/epics.md` Epic 3, Story 3.2
- Previous story: `_bmad-output/implementation-artifacts/2-3-atc-flights-resource.md` (model_copy pattern)
- Story 3.1: `_bmad-output/implementation-artifacts/3-1-*.md` (placement algorithm base — must exist before this story)
- Config: `src/atc_mcp/config.py` — `Config` fields, including `dependency_buffer_sec`
- Models: `src/atc_mcp/domain/models.py` — `Flight`, `FlightState`, `Schedule`, `Placement`
- State: `src/atc_mcp/domain/state.py` — `AppState`
- Test fixtures: `tests/conftest.py` — `valid_env`, `VALID_ENV`

---

## Dev Agent Record

### Agent Model Used

_to be filled by dev agent_

### Debug Log References

### Completion Notes List

### File List

### Change Log

- 2026-05-21: Story created by create-story workflow

---

**Story Status:** ready-for-dev
**Last Updated:** 2026-05-21
**Context Engine:** Ultimate BMad Method story context completed
