---
story_id: "3.3"
story_key: "3-3-ground-crew-capacity-invariant"
epic: "Epic 3: Deterministic Scheduling Engine & Airport Operations"
title: "Ground-Crew Capacity Invariant"
status: "ready-for-dev"
created: "2026-05-21"
dependencies: ["3.1", "3.2"]
---

# Story 3.3: Ground-Crew Capacity Invariant

## User Story

**As the** scheduling engine,
**I want** to enforce that concurrent scheduled operations never exceed `ATC_GROUND_CREW_COUNT`,
**So that** the schedule reflects the realistic ground-side resource ceiling (DD-10).

## Business Context

Ground crew is the third shared resource after runways and gates. Unlike runways (one op at a time per runway) and gates (one op at a time per gate), ground crew is a **global capacity counter** — `K` crew units serve the entire airport simultaneously. This story adds the crew constraint as the final piece of the single-flight constraint system before Stories 3.4–3.6 wire it into the full MCP surface.

The crew constraint is a **delay constraint, never a drop constraint**: if crew is temporarily at capacity, the flight is postponed until a slot opens. Only if the delay pushes beyond the scheduling horizon is the flight marked unschedulable (with the same reason string as story 3.1's horizon overflow).

## Acceptance Criteria

**Given** the algorithm from Stories 3.1 + 3.2

**When** I call `schedule()` with a config where `ground_crew_count = K`

**Then** for every instant `t` covered by any placement, the count of placements `p` with `p.start_sec ≤ t < p.end_sec` is `≤ K`

**And** when ground crew is the binding constraint, candidate flights are delayed (not dropped) until a crew slot opens within the horizon

**And** if the horizon is exceeded due to crew contention, the flight is marked `unschedulable` with `unscheduled_reason` exactly `"would exceed scheduling horizon"` (consistent with Story 3.1)

**And** `tests/test_scheduler_ground_crew.py` covers:
- `K=1` serializes everything (all flights placed sequentially, no two overlap at any instant)
- `K=2` allows 2 concurrent ops on different runways
- crew-delayed flight is placed once crew frees up (delay visible in `start_sec`)
- crew-induced horizon overflow → `unschedulable` with exact reason `"would exceed scheduling horizon"`

## Tasks / Subtasks

- [ ] Add crew-capacity helper to `scheduler/constraints.py` (AC: all)
  - [ ] Implement `earliest_crew_feasible_start(candidate_start, duration, committed_intervals, capacity) -> int`
  - [ ] Helper finds earliest t >= candidate_start where [t, t+duration) has peak occupancy < capacity at all points
  - [ ] Deterministic: uses sorted `committed_intervals` list, no set/dict iteration drives output

- [ ] Integrate crew constraint into `scheduler/algorithm.py` placement loop (AC: all)
  - [ ] Track `committed_crew: list[tuple[int, int]]` (start_sec, end_sec) built up as flights are placed
  - [ ] In per-(runway, gate) candidate loop: after computing runway/gate/dep floor `t`, apply crew check in advance-until-stable loop
  - [ ] On commit: append `(t_final, t_final + duration)` to `committed_crew`
  - [ ] After crew advances t, re-check horizon: if `t + duration > scheduling_horizon_sec` → mark unschedulable

- [ ] Create `tests/test_scheduler_ground_crew.py` (AC: all)
  - [ ] `K=1` serialization test
  - [ ] `K=2` concurrency test
  - [ ] Delayed-by-crew placement test
  - [ ] Crew-induced horizon overflow test

## Dev Notes

### Architecture Decision Reference (DD-10)

> Ground crew = shared capacity counter equal to `ATC_GROUND_CREW_COUNT`; each scheduled operation occupies one crew unit for `[start_sec, end_sec)`. Invariant: at any `t`, concurrent operations ≤ capacity. Scheduler advances start_sec until candidate window does not violate capacity.

Source: `_bmad-output/planning-artifacts/architecture.md` §Ground Crew Scheduling Semantics

### Algorithm Integration — The "Advance-Until-Stable" Pattern

The crew constraint is the **last check** within the per-`(runway, gate)` placement loop, applied after runway-sep/overlap, gate-turnaround, and dep-buffer floor. Because advancing for crew can re-expose runway/gate conflicts at the new `t`, use an **advance-until-stable** inner loop:

```python
t = floor_start
while True:
    t_prev = t
    t = runway_earliest(R, t, duration, op_type, config)   # from story 3.1
    t = gate_earliest(G, t, duration, config)              # from story 3.1
    t = crew_earliest(t, duration, committed_crew, config.ground_crew_count)  # NEW in 3.3
    if t == t_prev:
        break  # all constraints stable — this is the final placement time
# horizon check after the loop
if t + duration > config.scheduling_horizon_sec:
    mark unschedulable
    continue
# commit placement and record crew interval
committed_crew.append((t, t + duration))
```

This loop converges because `t` is strictly non-decreasing in each iteration and bounded by the horizon.

### `earliest_crew_feasible_start` — Implementation Hint

```python
def earliest_crew_feasible_start(
    candidate: int,
    duration: int,
    committed: list[tuple[int, int]],
    capacity: int,
) -> int:
    """Return earliest t >= candidate where [t, t+duration) has peak crew < capacity."""
    t = candidate
    while True:
        # Count overlapping intervals at any point in [t, t+duration)
        conflicting = [
            (s, e) for (s, e) in committed
            if s < t + duration and e > t
        ]
        if len(conflicting) < capacity:
            return t  # feasible: peak at most len(conflicting) which < capacity
        # Advance t to the earliest end_sec among conflicting intervals
        t = min(e for (_, e) in conflicting)
```

**Why this is correct:** when `len(conflicting) >= capacity`, at least one interval endpoint is the soonest time the occupancy drops. Setting `t = min(end_sec)` is the smallest advance that can relieve the constraint. The outer while loop retries until stable.

**Why this is deterministic:** `committed` is a list built from placements in fixed sort order (topo_depth, priority_rank, flight_number). The min() is over numeric values — no set/dict iteration. Output is fully determined by input.

### Tracking `committed_crew`

- Initialize as empty `list[tuple[int, int]]` before the main placement loop.
- Append `(t_final, t_final + duration)` **only when a flight is successfully placed** (not when it's marked unschedulable).
- Do NOT sort or deduplicate. Insertion order from placement sort is sufficient; `earliest_crew_feasible_start` operates on all intervals regardless of order.

### Files to Modify/Create

| File | Action | What Changes |
|---|---|---|
| `src/atc_mcp/scheduler/constraints.py` | **UPDATE** | Add `earliest_crew_feasible_start()` helper |
| `src/atc_mcp/scheduler/algorithm.py` | **UPDATE** | Add `committed_crew` tracking + crew constraint in placement loop |
| `tests/test_scheduler_ground_crew.py` | **CREATE** | 4 targeted test cases per AC |

### Current State of Files Being Modified

**`src/atc_mcp/scheduler/algorithm.py`** (as of Story 3.2):
- Exports `schedule(flights: tuple[Flight, ...], config: Config) -> Schedule`
- Implements placement loop with runway-sep/overlap, gate-turnaround, dep-buffer floor, cycle detection
- `committed_crew` tracking is absent — add it in this story

**`src/atc_mcp/scheduler/constraints.py`** (as of Story 3.2):
- Contains runway overlap/separation helpers and gate-turnaround helpers
- No crew helper yet — add `earliest_crew_feasible_start` here

### What Must Be Preserved (Regression Guard)

- **Do not change** the sort key `(topo_depth, priority_rank, flight_number)` — established in Story 3.1.
- **Do not change** the `(runway_id, gate_id)` lex tie-break for choosing the best (R, G) pair — established in Story 3.1.
- **Do not change** the unschedulable reason strings from Stories 3.1/3.2 — exact strings are contract.
- The `earliest_crew_feasible_start` helper must live in `constraints.py`, not inline in `algorithm.py`, to respect module boundaries.
- All tests from Stories 3.1 and 3.2 (`test_scheduler_placement.py`, `test_scheduler_dependencies.py`) must continue to pass. The crew constraint is additive: with `ground_crew_count` set to the number of flights (or higher), the crew constraint never binds and prior placement results are unchanged.

### Module Dependency Rules

```
scheduler/constraints.py  ← imports domain.models only (no mcp, no os, no time, no random)
scheduler/algorithm.py    ← imports domain.models, scheduler.constraints only
```

The crew helper must stay in `constraints.py`. `algorithm.py` calls it but does not define it. Verified by `tests/test_imports.py`.

### Test Fixture Notes

Use the `valid_env` fixture from `tests/conftest.py` which sets:
```
ATC_GROUND_CREW_COUNT=3
ATC_DURATION_ARRIVAL_SEC=1200
ATC_DURATION_DEPARTURE_SEC=1200
ATC_SCHEDULING_HORIZON_SEC=86400
ATC_RUNWAY_SEP_TAKEOFF_SEC=120
ATC_RUNWAY_SEP_LANDING_SEC=180
ATC_RUNWAY_SEP_MIXED_SEC=240
ATC_GATE_TURNAROUND_SEC=300
ATC_DEPENDENCY_BUFFER_SEC=600
ATC_RUNWAYS=[{"id":"R1","length_m":3500},{"id":"R2","length_m":3000}]
ATC_GATE_COUNT=4
```

For `K=1` and `K=2` tests, **override** `ATC_GROUND_CREW_COUNT` with `monkeypatch.setenv` inside the test, then call `load_config()` to get a fresh `Config`. Do not mutate the shared `valid_env` fixture.

**K=1 test design:**
- Submit 3 arrivals. With K=1, only one can run at a time.
- After schedule: placements should be sequential — each `start_sec` equals previous `end_sec` + sep buffer (no two intervals overlap at any t).
- Assert: for every pair of placements (i, j), NOT (`p_i.start_sec < p_j.end_sec AND p_j.start_sec < p_i.end_sec`).

**K=2 concurrency test:**
- 3 arrivals, 2 different runways, K=2.
- First two (higher priority) placed concurrently at t=0 on R1 and R2. Third is delayed by crew.
- Assert: first two share an overlapping window; third starts no earlier than one of them ends.

**Crew-delayed test (explicit delay visibility):**
- 2 arrivals, K=1, horizon >> durations.
- Flight A1 (high) placed at t=0, end=1200.
- Flight A2 (medium) crew-delayed: assert `A2.start_sec >= 1200` (crew frees at A1.end_sec + runway-sep).

**Horizon overflow test:**
- K=1, `ATC_SCHEDULING_HORIZON_SEC` set to just large enough for 1 flight.
- Submit 2 flights. First placed OK. Second's crew delay pushes it past horizon.
- Assert: second flight is `unschedulable` with reason `"would exceed scheduling horizon"`.

### Determinism Note

The crew constraint helper is pure and deterministic:
- Input `committed` is a list in insertion order (determined by the fixed sort key, which is itself deterministic).
- `min()` on a list of integers is deterministic.
- No `set`, `dict`, `random`, or wall-clock anywhere in the helper.
- `tests/test_imports.py` already enforces: `scheduler/` must not import `time`, `datetime`, `random`, `os`, `mcp`.

### Unschedulable Reason String (exact)

When crew delay causes horizon overflow, the flight must be marked:
```python
flight.model_copy(update={
    "state": FlightState.unschedulable,
    "unscheduled_reason": "would exceed scheduling horizon",
})
```

This is the **same string** as Story 3.1's horizon overflow. No parenthetical detail about t/duration/horizon is required for crew-induced overflow (the epics AC says "consistent with Story 3.1" — the exact string from story 3.1 is `"would exceed scheduling horizon"`).

Source: `_bmad-output/planning-artifacts/epics.md` §Story 3.3 AC + §Story 3.1 AC

### Previous Story Patterns (From 3.1 + 3.2)

- `Flight` is a frozen Pydantic v2 model; use `.model_copy(update={...})` for mutations.
- Unschedulable flights are added to `Schedule.unscheduled: tuple[Flight, ...]` with updated state/reason.
- `Schedule.placements: tuple[Placement, ...]` contains only successfully placed flights.
- `schedule()` signature: `def schedule(flights: tuple[Flight, ...], config: Config) -> Schedule`
- Import `Config` from `atc_mcp.config`, `Flight`/`Placement`/`Schedule`/`FlightState`/`OperationType` from `atc_mcp.domain.models`.

### Common Pitfalls to Avoid

❌ **Don't** apply crew check before the dep-floor or runway/gate checks — it must be the final check in the advance-until-stable loop, applied jointly.

❌ **Don't** append to `committed_crew` when a flight is marked unschedulable — only committed placements consume crew units.

❌ **Don't** define `earliest_crew_feasible_start` inside `algorithm.py` — it belongs in `constraints.py` per module boundaries.

❌ **Don't** use a different unschedulable reason string for crew-induced horizon overflow — it must be `"would exceed scheduling horizon"` (same as runway/dep floor overflow).

❌ **Don't** break the existing `K=3` behavior from the VS-1 walkthrough: 4 flights with durations 1200 each, at most 2 concurrent at any instant, peak=2 < 3=K → no crew delay. Tests from stories 3.1/3.2 must pass unchanged.

## Definition of Done

- [ ] `earliest_crew_feasible_start()` in `constraints.py` passes all edge cases (empty committed list, K=1, K=N with N flights)
- [ ] Algorithm placement loop integrates crew constraint via advance-until-stable inner loop
- [ ] `committed_crew` is populated only from successful placements, in placement order
- [ ] Crew-induced horizon overflow produces `"would exceed scheduling horizon"` (exact string)
- [ ] `tests/test_scheduler_ground_crew.py` created with 4 test cases; all pass
- [ ] All prior tests (test_scheduler_placement.py, test_scheduler_dependencies.py, test_imports.py, etc.) continue to pass — no regressions
- [ ] No forbidden imports in `constraints.py` or `algorithm.py` (`mcp`, `os`, `time`, `datetime`, `random`)
- [ ] Code follows PEP 8 naming conventions

## Related Documentation

- Architecture: `_bmad-output/planning-artifacts/architecture.md` §Ground Crew Scheduling Semantics (DD-10), §Scheduling Algorithm Step 2.3
- Epics: `_bmad-output/planning-artifacts/epics.md` Epic 3, Story 3.3
- Config: `src/atc_mcp/config.py` — `Config.ground_crew_count`
- Domain models: `src/atc_mcp/domain/models.py`
- Constraints: `src/atc_mcp/scheduler/constraints.py`
- Algorithm: `src/atc_mcp/scheduler/algorithm.py`
- Test fixtures: `tests/conftest.py`

---

## Dev Agent Record

### Agent Model Used

cascade

### Debug Log References

### Completion Notes List

### File List

- `src/atc_mcp/scheduler/constraints.py` — modified: add `earliest_crew_feasible_start()`
- `src/atc_mcp/scheduler/algorithm.py` — modified: add `committed_crew` tracking + crew constraint in placement loop
- `tests/test_scheduler_ground_crew.py` — created: 4 test cases

## Change Log

- 2026-05-21: Story created — ground-crew capacity invariant (DD-10) added to placement algorithm

---

**Story Status:** ready-for-dev
**Last Updated:** 2026-05-21
**Context Engine:** Ultimate BMad Method story context completed
