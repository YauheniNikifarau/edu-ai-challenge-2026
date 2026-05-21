---
story_id: "4.1"
story_key: "4-1-bottleneck-chain-algorithm-and-analyze-bottleneck-tool"
epic: "Epic 4: Bottleneck Analysis, Validation & Project Delivery"
title: "Bottleneck Chain Algorithm + `analyze_bottleneck` Tool"
status: "ready-for-dev"
created: "2026-05-21"
dependencies: ["3.1", "3.2", "3.3", "3.4"]
---

# Story 4.1: Bottleneck Chain Algorithm + `analyze_bottleneck` Tool

## User Story

**As an** AI client,
**I want** to identify the longest active scheduled dependency chain with its total duration and per-operation/per-buffer breakdown,
**So that** I can pinpoint the critical path constraining airport throughput.

## Business Context

The bottleneck tool exposes the single most scheduling-critical dependency chain in the current schedule. This lets an AI operator identify which sequence of dependent operations is holding up the most airport capacity — e.g., a long inbound-arrival → ground-service → outbound-departure chain that blocks runways and crew. The result is the canonical "critical path" answer for the current airport state, computed deterministically over the latest schedule snapshot.

## Acceptance Criteria

**Given** `bottleneck.py` exposes `longest_active_chain(state: AppState, config: Config) -> BottleneckResult`

**When** `AppState.latest_schedule` contains placements for flights whose `dependencies` form one or more chains
**Then** "active scheduled dependency chain" = ordered sequence of currently-`scheduled` (non-cancelled, non-unschedulable) flights where each consecutive pair `(f_i, f_{i+1})` satisfies `f_{i+1}.dependencies` contains `f_i.flight_number`
**And** chain duration = `f_n.end_sec - f_1.start_sec` ≡ `sum(operation_durations) + sum(dependency_buffers)` in steady-state
**And** "longest" tie-break selects the chain whose **starting flight has the lex-smallest `flight_number`**

**And** the `analyze_bottleneck` MCP tool returns:
```json
{
  "chain": ["AA100", "AA200", "AA300"],
  "total_duration_seconds": 3600,
  "operation_durations": [1200, 1200, 1200],
  "dependency_buffers": [600, 600]
}
```
where `len(operation_durations) == len(chain)` and `len(dependency_buffers) == len(chain) - 1`

**And When** there is no schedule, or no scheduled flights have dependencies on other scheduled flights
**Then** the tool returns `{"chain": [], "total_duration_seconds": null, "operation_durations": [], "dependency_buffers": []}`

**And** repeated calls with identical state return byte-identical payloads

**And** `tests/test_bottleneck.py` covers:
- empty state (no flights, no schedule)
- single scheduled flight with no deps (returns empty chain)
- 2-chain
- 3-chain
- two equal-length chains → lex tie-break on starting flight_number
- chain broken by a cancelled middle flight (only contiguous scheduled segments count)
- chain broken by an unschedulable middle flight
- diamond DAG (longest path through diamond wins)

## Tasks / Subtasks

- [ ] Task 1: Implement `longest_active_chain` in `bottleneck.py` (AC: chain definition, DP algorithm, tie-break)
  - [ ] 1.1: Build `scheduled_placements: dict[str, Placement]` from `state.latest_schedule` filtered to `FlightState.scheduled` flights only
  - [ ] 1.2: Build `scheduled_deps` map: for each scheduled flight, list only the deps that are themselves scheduled
  - [ ] 1.3: Check if any flight has ≥1 scheduled dep; if not, return empty `BottleneckResult`
  - [ ] 1.4: Topological sort of scheduled flights (Kahn's BFS on the scheduled-dep subgraph)
  - [ ] 1.5: DP in topo order: `dp[f] = duration(f) + max(dp[d] + dep_buffer_sec)` over scheduled deps d; `dp[f] = duration(f)` for leaf flights. Track `parent[f]` and `chain_start[f]` for tie-break.
  - [ ] 1.6: Find `best_tail` = flight with max `dp` value, breaking ties by lex-smallest `chain_start`
  - [ ] 1.7: Reconstruct chain from `best_tail` via parent pointers (reversed)
  - [ ] 1.8: Return `BottleneckResult` with `chain`, `total_duration_seconds`, `operation_durations`, `dependency_buffers`
- [ ] Task 2: Wire `analyze_bottleneck` in `tools.py` (AC: tool response shape, empty case)
  - [ ] 2.1: Replace `raise NotImplementedError` with call to `longest_active_chain(state, <config>)` and return `result.model_dump(mode="json")`
  - [ ] 2.2: Ensure config is accessible in `tools.py` (reuse pattern established by Epic 3 / `generate_schedule`)
- [ ] Task 3: Create `tests/test_bottleneck.py` with all 8 required scenarios

## Dev Notes

### Architecture Compliance

**Module dependency direction** (`architecture.md §Structure Patterns`):
```
bottleneck.py  ← imports domain only (+ config.py for Config type)
tools.py       ← imports domain, scheduler, bottleneck, status
```

`bottleneck.py` receives `Config` as a parameter — it does not call `load_config()`. Importing `Config` from `atc_mcp.config` for type annotation is safe: `test_imports.py` only forbids `mcp` and `os` imports in checked modules; `bottleneck.py` is not inside `domain/` or `scheduler/` so those checks do not apply.

**Banned imports in `bottleneck.py`:** `mcp`, `os`, `time`, `datetime`, `random` (would violate `test_only_tools_and_resources_import_mcp` and `test_only_config_imports_os`).

### Critical — Config Access in `tools.py`

`analyze_bottleneck()` in `tools.py` needs a live `Config` instance. There is no `config` parameter available to tool handler functions registered via `FastMCP.add_tool()`.

**This pattern must already be established by Epic 3 story that wires `generate_schedule`** (which also needs `config` for `scheduler.algorithm.schedule()`). When you arrive at this story, look at how `generate_schedule` accesses config and reuse exactly that pattern. **Do not invent a new pattern.**

If Epic 3 has not been implemented yet, the recommended approach is to extend `AppState` to hold config:
```python
# domain/state.py
class AppState:
    def __init__(self) -> None:
        self.flights: dict[str, Flight] = {}
        self.latest_schedule: Schedule | None = None
        self.config: object = None  # set by server.main() after load_config()
```
Then `server.main()` sets `state.config = config` before calling `create_app(config)`, and `tools.py` uses `state.config`.

### Data Model (already in place — do NOT recreate)

**`BottleneckResult`** is already defined in `src/atc_mcp/domain/models.py`:
```python
class BottleneckResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    chain: list[str]
    total_duration_seconds: int | None
    operation_durations: list[int]
    dependency_buffers: list[int]
```

**`Placement`** (from `domain/models.py`): `flight_number`, `operation_type`, `runway_id`, `gate_id`, `start_sec: int`, `end_sec: int`

**`Schedule`** (from `domain/models.py`): `placements: tuple[Placement, ...]`, `unscheduled: tuple[Flight, ...]`, `completion_time_seconds: int | None`

**`AppState`** (from `domain/state.py`):
- `state.flights: dict[str, Flight]` — keyed by flight_number, insertion-ordered
- `state.latest_schedule: Schedule | None` — last result of `generate_schedule`
- `state.flights[fn].state: FlightState` — the authoritative flight state post-scheduling

### Algorithm Detail

```
EMPTY = BottleneckResult(chain=[], total_duration_seconds=None,
                         operation_durations=[], dependency_buffers=[])

def longest_active_chain(state, config) -> BottleneckResult:
    if state.latest_schedule is None:
        return EMPTY

    # 1. Scheduled-flights map: flight_number → Placement
    scheduled_placements = {
        p.flight_number: p
        for p in state.latest_schedule.placements
        if state.flights.get(p.flight_number) is not None
           and state.flights[p.flight_number].state == FlightState.scheduled
    }

    # 2. Scheduled-dep adjacency: flight_number → [dep_fn that is also scheduled]
    scheduled_deps = {
        fn: [d for d in state.flights[fn].dependencies if d in scheduled_placements]
        for fn in scheduled_placements
    }

    # 3. Early exit: no flight has any scheduled dep
    if not any(scheduled_deps.values()):
        return EMPTY

    # 4. Kahn's topo sort over scheduled-dep subgraph
    in_degree = {fn: 0 for fn in scheduled_placements}
    dependents_of = {fn: [] for fn in scheduled_placements}
    for fn, deps in scheduled_deps.items():
        for d in deps:
            in_degree[fn] += 1
            dependents_of[d].append(fn)

    queue = [fn for fn, deg in in_degree.items() if deg == 0]
    topo_order = []
    while queue:
        queue.sort()               # deterministic: process lex order within same depth
        fn = queue.pop(0)
        topo_order.append(fn)
        for dependent in sorted(dependents_of[fn]):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    # 5. DP in topo order
    dur = lambda fn: scheduled_placements[fn].end_sec - scheduled_placements[fn].start_sec
    buf = config.dependency_buffer_sec
    dp: dict[str, int] = {}
    parent: dict[str, str | None] = {}
    chain_start: dict[str, str] = {}

    for fn in topo_order:
        deps = scheduled_deps[fn]
        if not deps:
            dp[fn] = dur(fn)
            parent[fn] = None
            chain_start[fn] = fn
        else:
            # Pick dep with max dp; tie-break by lex-smallest chain_start
            best = min(
                deps,
                key=lambda d: (-dp[d], chain_start[d])
            )
            dp[fn] = dp[best] + buf + dur(fn)
            parent[fn] = best
            chain_start[fn] = chain_start[best]

    # 6. Find best tail: max dp, tie-break by lex-smallest chain_start
    best_tail = min(
        scheduled_placements,
        key=lambda fn: (-dp[fn], chain_start[fn])
    )

    if parent[best_tail] is None and not scheduled_deps[best_tail]:
        # Leaf with no chain — single flight, not a chain of 2+
        return EMPTY

    # 7. Reconstruct chain
    chain = []
    fn = best_tail
    while fn is not None:
        chain.append(fn)
        fn = parent[fn]
    chain.reverse()

    # 8. Build result
    op_durs = [dur(fn) for fn in chain]
    dep_bufs = [buf] * (len(chain) - 1)
    total = sum(op_durs) + sum(dep_bufs)
    return BottleneckResult(
        chain=chain,
        total_duration_seconds=total,
        operation_durations=op_durs,
        dependency_buffers=dep_bufs,
    )
```

**⚠ Chain length ≥ 2 is required for a non-empty result.** A single scheduled flight with no scheduled deps is NOT a chain — return `EMPTY`.

### `tools.py` Change

The existing stub in `tools.py`:
```python
def analyze_bottleneck() -> dict:
    """Identify the longest active scheduled dependency chain."""
    raise NotImplementedError("not yet implemented")
```

Replace the body with:
```python
    from atc_mcp.bottleneck import longest_active_chain
    result = longest_active_chain(state, <config>)
    return result.model_dump(mode="json")
```

Where `<config>` is whatever the Epic 3 pattern established (e.g., `state.config`).

### JSON Shape Verification

The `BottleneckResult.model_dump(mode="json")` produces:
```json
{
  "chain": ["AA100", "AA200"],
  "total_duration_seconds": 3000,
  "operation_durations": [1200, 1200],
  "dependency_buffers": [600]
}
```
Empty case (from `EMPTY.model_dump(mode="json")`):
```json
{
  "chain": [],
  "total_duration_seconds": null,
  "operation_durations": [],
  "dependency_buffers": []
}
```
`total_duration_seconds: null` is the required JSON representation when `None` — Pydantic handles this automatically with `mode="json"`.

### Determinism

- `bottleneck.py` must not import `time`, `datetime`, `random` (would fail `test_only_config_imports_os` / `test_domain_no_mcp_no_os` if present in `domain/`)
- Topo sort tie-break uses `queue.sort()` (or `sorted()`) — no `set` iteration to drive order
- All list operations are deterministic; no hash randomization
- The existing `test_imports.py` does not check `bottleneck.py` directly, but the spirit must be upheld

### Project Structure Notes

- **MODIFY:** `src/atc_mcp/bottleneck.py` — currently a one-line stub; implement `longest_active_chain`
- **MODIFY:** `src/atc_mcp/tools.py` — wire `analyze_bottleneck()` to call `longest_active_chain`
- **CREATE:** `tests/test_bottleneck.py` — 8 required test scenarios
- **DO NOT** create a new `BottleneckResult` model — it already exists in `domain/models.py`
- **DO NOT** add `analyze_bottleneck` to `server.py` — it is already registered there

### Testing Notes

**Fixture config** for tests — reuse the `valid_env` fixture from `conftest.py`:
```python
VALID_ENV = {
    "ATC_RUNWAYS": '[{"id":"R1","length_m":3500},{"id":"R2","length_m":3000}]',
    "ATC_GATE_COUNT": "4",
    "ATC_GROUND_CREW_COUNT": "3",
    "ATC_RUNWAY_SEP_TAKEOFF_SEC": "120",
    "ATC_RUNWAY_SEP_LANDING_SEC": "180",
    "ATC_RUNWAY_SEP_MIXED_SEC": "240",
    "ATC_GATE_TURNAROUND_SEC": "300",
    "ATC_DEPENDENCY_BUFFER_SEC": "600",
    "ATC_SCHEDULING_HORIZON_SEC": "86400",
    "ATC_DURATION_ARRIVAL_SEC": "1200",
    "ATC_DURATION_DEPARTURE_SEC": "1200",
}
```

Since `longest_active_chain` is a pure function (takes `state` and `config`), you can test it **without booting the MCP server** — just build `AppState` instances directly, populate `flights` and `latest_schedule`, and pass a `Config` loaded via `load_config()` (with `valid_env` monkeypatched).

**Key test patterns:**

```python
# Test: empty state
def test_empty_state_returns_empty_chain(valid_env):
    from atc_mcp.config import load_config
    from atc_mcp.domain.state import AppState
    from atc_mcp.bottleneck import longest_active_chain
    s = AppState()
    cfg = load_config()
    result = longest_active_chain(s, cfg)
    assert result.chain == []
    assert result.total_duration_seconds is None

# Test: diamond DAG fixture
# F1 → F2 → F4 and F1 → F3 → F4
# All scheduled. Longest path: F1 → F2 → F4 or F1 → F3 → F4 — equal length
# Tie-break: F1 has lex-smallest starting flight — both chains start at F1,
# so need to pick based on chain starting flight lex order (same here, either valid)
```

**Cancelled / unschedulable middle flight test:**
```python
# Chain: A → B → C. B is cancelled.
# scheduled_placements should only include A and C
# scheduled_deps[C] will NOT include B (B is not in scheduled_placements)
# Result: no 2+ chains → return EMPTY
```

### References

- `_bmad-output/planning-artifacts/architecture.md` §"Active Scheduled Dependency Chain" Definition (resolves DD-9)
- `_bmad-output/planning-artifacts/architecture.md` §MCP Tool Catalog → `analyze_bottleneck`
- `_bmad-output/planning-artifacts/architecture.md` §Structure Patterns (module dependency direction)
- `_bmad-output/planning-artifacts/epics.md` Epic 4, Story 4.1
- `src/atc_mcp/domain/models.py` — `BottleneckResult`, `Placement`, `Schedule`, `FlightState`
- `src/atc_mcp/domain/state.py` — `AppState`
- `src/atc_mcp/tools.py` — `analyze_bottleneck` stub
- `src/atc_mcp/bottleneck.py` — implementation target
- `tests/conftest.py` — `VALID_ENV`, `valid_env` fixture

## Definition of Done

- [ ] `longest_active_chain(state, config)` implemented in `bottleneck.py`
- [ ] Returns `EMPTY` when `state.latest_schedule is None`
- [ ] Returns `EMPTY` when no scheduled flight has a scheduled dep (no chain of ≥2)
- [ ] DP correctly computes longest chain with `dep_buffer_sec` between each pair
- [ ] Tie-break by lex-smallest starting flight_number works correctly
- [ ] Cancelled/unschedulable middle flights break chains correctly (only `FlightState.scheduled` flights included)
- [ ] `analyze_bottleneck()` in `tools.py` wired to `longest_active_chain`, returns dict
- [ ] Tool returns architecture-pinned empty JSON on empty state (no server error)
- [ ] Repeated calls with identical state return byte-identical JSON
- [ ] `tests/test_bottleneck.py` created with all 8 required scenarios passing
- [ ] No new imports of `mcp`, `os`, `time`, `datetime`, `random` in `bottleneck.py`
- [ ] All pre-existing tests continue to pass (zero regressions)
- [ ] `BottleneckResult` model NOT duplicated — using the one in `domain/models.py`

## Notes for Developer

### Critical Pitfalls

❌ **Don't** filter by `state.latest_schedule.placements` alone for "scheduled" status — a placement exists for every scheduled flight, but you must ALSO verify `state.flights[fn].state == FlightState.scheduled`. After a cancellation + re-schedule, some flights may have placements from a previous schedule while their current state is `cancelled`.

❌ **Don't** return a single-flight "chain" — the spec requires a consecutive-pair dependency relationship. A flight with no scheduled deps is a chain of length 1, which does NOT qualify. Return `EMPTY`.

❌ **Don't** use Python `set` iteration to drive output order — topological order must be computed deterministically.

❌ **Don't** iterate `state.flights.values()` in an arbitrary set-like manner — always use `sorted()` for any deterministic output.

❌ **Don't** forget the lex tie-break on `chain_start` when two tails have identical `dp` values — this is required for determinism and is tested explicitly.

❌ **Don't** add `analyze_bottleneck` to `server.py` — it's already registered there (line 24).

### Why `chain_start` Tracking Matters

The architecture tie-break is "chain whose **starting** flight has lex-smallest flight_number." When two chains have equal total duration, you must pick based on where the chain BEGINS, not where it ends. This requires tracking `chain_start[f]` propagated through the DP, not just comparing tail flight numbers.

### Dependency Graph Invariant

By the time Story 4.1 executes, the scheduler (Epic 3) guarantees that scheduled flights form a DAG. Flights in dependency cycles are marked `unschedulable` by the scheduler, so they will NOT appear in `scheduled_placements`. Kahn's algorithm on the scheduled subgraph will therefore always complete without leaving unprocessed nodes.

---

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2026-05-21: Story created

---

**Story Status:** ready-for-dev
**Last Updated:** 2026-05-21
**Context Engine:** Ultimate BMad Method story context completed
