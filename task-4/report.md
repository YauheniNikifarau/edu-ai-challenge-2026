# Air Traffic Control MCP Server — Engineering Report

## 1. Scheduling Approach

The scheduler implements a **deterministic greedy constructive placement algorithm** with explicit tie-break policies at every decision point. This approach was chosen over alternatives (LP/ILP solvers, backtracking search) because it is sufficient for the constraint set, trivially deterministic, and avoids external solver dependencies that would conflict with the lightweight requirement.

### Algorithm Overview

**Sort key:** Flights are processed in a total order defined by the tuple `(topo_depth, priority_rank, flight_number)`:
- `topo_depth`: Topological depth in the dependency graph. Leaves (flights with no dependencies) have depth 0; a flight's depth is `1 + max(depth of dependencies)`. This ensures dependencies are always placed before their dependents.
- `priority_rank`: `high=0, medium=1, low=2`. Higher-priority flights win under resource contention at the same topological level.
- `flight_number`: Lexicographic tie-break. Since flight numbers are unique, this guarantees a total ordering.

**Placement loop:** For each flight in sort order, the scheduler finds the earliest `(runway, gate)` pair (lexicographically ascending by `(runway_id, gate_id)`) that satisfies all constraints simultaneously:

1. **Runway capability filter:** Only runways where `runway.length_m >= flight.min_length_m` are considered. If no runways match, the flight is marked unschedulable with a reason naming the requirement and listing available runway capabilities.
2. **Dependency floor:** The earliest start time is `max(dep.end_sec + ATC_DEPENDENCY_BUFFER_SEC)` across all scheduled dependencies. If any dependency is unschedulable or cancelled, the flight is marked unschedulable with reason `"dependency <flight_number> is not scheduled"`.
3. **Runway separation:** The operation must respect separation buffers based on the operation-type pair (takeoff/landing/mixed flavour) from `ATC_RUNWAY_SEP_TAKEOFF_SEC`, `ATC_RUNWAY_SEP_LANDING_SEC`, `ATC_RUNWAY_SEP_MIXED_SEC`.
4. **Gate turnaround:** The gate occupancy window `[start_sec - ATC_GATE_TURNAROUND_SEC, end_sec)` must not overlap any existing gate placement.
5. **Ground-crew capacity:** The operation window `[start_sec, end_sec)` must not cause concurrent operations to exceed `ATC_GROUND_CREW_COUNT` at any point in time.
6. **Scheduling horizon:** The operation must complete within the horizon: `start_sec + duration <= ATC_SCHEDULING_HORIZON_SEC`.

The scheduler selects the `(runway, gate)` pair with the minimum start time. Ties are broken lexicographically by `(runway_id, gate_id)`.

**Cycle detection:** Before placement, a DFS traversal detects dependency cycles. All flights in a cycle are marked unschedulable with reason `"dependency cycle: <sorted flight numbers>"`.

### Why Not LP/ILP?

Linear programming or integer linear programming solvers would be overkill for this problem scale. The greedy constructive approach is O(n²) worst-case (n = number of flights × runway/gate combinations), which is entirely adequate for the expected workload. Adding a solver dependency would conflict with NFR-1 (lightweight, minimal dependencies) and introduce non-determinism unless carefully configured. The greedy approach already satisfies FR-SCH-3 (priority ordering) because higher-priority flights are processed first within each topological level.

### Why Not Backtracking?

Backtracking search would only be necessary to prove global optimality, which is not a requirement. The greedy constructive approach is sufficient because priority-ordered placement already satisfies the functional requirements. Backtracking would introduce non-deterministic performance characteristics (worst-case exponential time) without delivering additional value for this use case.

### Determinism Guarantee

The algorithm is deterministic by construction:
- All inputs are sorted by a total order on `(topo_depth, priority_rank, flight_number)`.
- Iteration over runways and gates is by sorted `id` — no set or hash iteration drives output.
- Time arithmetic uses integer seconds only — no floating-point rounding.
- Tie-breaks at every choice point are lexicographic on stable string ids.
- No use of `random`, no time-seeded RNG, no wall-clock reads.
- Cycle detection uses sorted DFS — the unschedulable list ordering is deterministic.
- Python 3.7+ guarantees insertion-ordered dicts; `set` is never iterated to produce output.

This determinism is verified by `tests/test_determinism.py`, which asserts byte-identical JSON output across 100 runs of a ≥10-flight fixture with mixed priorities, dependency chains, and runway-requirement-binding flights.

---

## 2. Key Decisions

All architectural decisions are documented in `_bmad-output/planning-artifacts/architecture.md`. The ten core decisions are summarized below.

### DD-1: Tool & Resource Catalog

**Decision:** Pin exact input/output JSON shapes upfront for all five MCP tools and three MCP resources. Use `snake_case` field names matching Python idiom.

**Rationale:** Defining schemas before implementation prevents drift between `tools.py`, `resources.py`, and tests. The `snake_case` convention matches Python idiom and avoids alias layers between Python code and JSON Schema. Pydantic v2 models with `extra="forbid"` reject unknown fields at the MCP layer, catching client errors early.

### DD-2: Environment Variable Contract

**Decision:** All env vars use the `ATC_` prefix. All are required (no silent defaults). Invalid config aborts startup with a single error line: `CONFIG ERROR: <ENV_VAR_NAME> is invalid: <reason>`.

**Rationale:** All-required configuration makes misconfiguration immediately diagnosable — no silent fallback to defaults that might mask errors. The `ATC_` prefix prevents collision with OS or container variables. The single-line error format is parseable and unambiguous, verified by `tests/test_config.py` and `tests/test_config_failure_exit.py`.

### DD-3: Tech Stack

**Decision:** Python 3.11+, official `mcp` SDK, stdio transport, Pydantic v2.

**Rationale:** Python 3.11+ provides insertion-ordered dicts (determinism) and performance improvements. The official `mcp` PyPI package is the reference implementation maintained by the MCP project. Stdio transport is canonical for local MCP servers and has zero network surface, fitting the lightweight requirement (NFR-1). Pydantic v2 is used by the MCP SDK for tool input schemas and doubles as the domain data model.

### DD-4: Scheduling Algorithm

**Decision:** Deterministic greedy constructive placement with explicit tie-break policy (see Section 1).

**Rationale:** Greedy constructive is trivially deterministic and sufficient for the constraint set. The total sort order `(topo_depth, priority_rank, flight_number)` is the key insight — it collapses a multi-constraint problem into a single linear pass. No solver dependency, no backtracking complexity, no non-deterministic performance.

### DD-5: State Persistence

**Decision:** In-memory only. Single seam at `domain/state.py`.

**Rationale:** `spec.md §11` lists persistence as a non-requirement. In-memory state fits the lightweight requirement and simplifies the implementation. The single seam at `domain/state.py` isolates the state boundary for future expansion (e.g., persistent store, database backend) without touching the scheduler or domain logic.

### DD-6: Time Model

**Decision:** Relative epoch `t=0` at schedule generation. Integer seconds. No wall-clock reads.

**Rationale:** Relative time eliminates wall-clock as a non-deterministic input. Integer seconds avoids all floating-point precision issues. `time_model.py` is the single source of truth for time units and epoch, ensuring consistency across config buffers, schedule placements, timeline events, and bottleneck durations.

### DD-7: Operation Duration Source

**Decision:** Durations determined solely by operation type via two env vars: `ATC_DURATION_ARRIVAL_SEC` and `ATC_DURATION_DEPARTURE_SEC`. No per-flight duration override.

**Rationale:** Per-flight duration override is not in `spec.md` — adding it would introduce a user-facing requirement not in the original task. Operation-type-level durations are sufficient for all validation scenarios (VS-1, VS-2, VS-3) and keep the config surface minimal.

### DD-8: Runway Capability Schema

**Decision:** `ATC_RUNWAYS` is a JSON array of `{"id": str, "length_m": int}`. Flight runway requirements are `{"min_length_m": int}` (optional). Matching rule: `runway.length_m >= flight.min_length_m`.

**Rationale:** This schema is minimal and sufficient for VS-2 (Heavy Hauler). Collapsing runway count and runway capability into one env var avoids count/capability inconsistency bugs. Other capabilities (surface type, ILS, weight class) are not in the original task and are not added.

### DD-9: Active Scheduled Dependency Chain Definition

**Decision:** A chain is a sequence of flights `f_1 → f_2 → … → f_n` where every flight is currently scheduled (has a `ScheduleEntry`) and not cancelled, and each consecutive pair has a dependency relationship. Chain duration is `f_n.end_sec - f_1.start_sec`. Ties are broken by lexicographically smallest starting flight number.

**Rationale:** "Scheduled non-cancelled only" is the only definition consistent with FR-TOOL-5 intent. Including queued or unschedulable flights would make the bottleneck metric meaningless. Lexicographic tie-break on starting flight ensures determinism when chains tie on duration.

### DD-10: Ground Crew Shared Capacity Counter

**Decision:** Ground crew is modeled as a single shared capacity counter equal to `ATC_GROUND_CREW_COUNT`. Each scheduled operation occupies one crew unit for its full duration `[start_sec, end_sec)`. The constraint is layered into the placement loop.

**Rationale:** This model is simple, auditable, and directly reportable via `ground_crew: {capacity, in_use_peak, in_use_at_completion}` in `get_airport_status`. It does not model crew skill levels, rest periods, or assignment to specific flight types — those are not in the original task.

---

## 3. Tools and Techniques

### Pydantic v2 Frozen Models

All config and domain value types use `ConfigDict(frozen=True, extra="forbid")`. Frozen models catch accidental mutation at runtime. `extra="forbid"` rejects unknown tool input fields at the MCP layer, surfacing client errors immediately. Implemented in `src/atc_mcp/domain/models.py` and `src/atc_mcp/config.py`.

### Official `mcp` SDK over stdio

Tools are registered via `@server.tool()`, resources via `@server.resource()`. The server uses stdio transport exclusively. Implemented in `src/atc_mcp/server.py`, `src/atc_mcp/tools.py`, and `src/atc_mcp/resources.py`.

### Deterministic Sort Keys

Every list returned to MCP is explicitly sorted before emission. Sort keys are documented per list in `_bmad-output/planning-artifacts/architecture.md §Ordering Patterns`. This eliminates Python set/dict hash non-determinism. Examples:
- Flight queue: sorted by `(state_rank, flight_number)` where `scheduled=0, queued=1, unschedulable=2, cancelled=3`.
- Timeline events: sorted by `(start_sec, runway_id, flight_number)`.
- Runways: sorted by `id` lex.

### Property-Based Determinism Test

`tests/test_determinism.py` builds a ≥10-flight fixture with mixed priorities, at least one dependency chain, and at least one runway-requirement-binding flight. It calls `generate_schedule` 100 times and asserts all serialized outputs are byte-identical via `json.dumps(..., sort_keys=True, separators=(",", ":"))`. This test caught subtle ordering bugs during development.

### Import-Direction Enforcement Test

`tests/test_imports.py` AST-parses every `domain/` and `scheduler/` source file and asserts zero imports of `mcp`, `os`, `time`, `datetime`, `random`. This catches cross-layer boundary violations at CI time, preventing `domain/` modules from accidentally pulling in MCP SDK symbols during refactors.

---

## 4. What Worked

### Relative-Time Epoch (DD-6)

Eliminating wall-clock from the scheduler removed the single biggest source of non-determinism before any code was written. All time values are integer seconds relative to `t=0` at schedule generation. This decision cascaded through the entire implementation, making determinism trivial to verify.

### Pydantic `ConfigDict(frozen=True)`

Frozen models caught several accidental mutations during development at runtime rather than at debugging time. For example, an early implementation attempted to mutate a `Flight` object's state field directly, which raised an immediate `ValidationError`. This forced the correct pattern (rebuild the object) from the start.

### `tests/test_imports.py` (AST-Level Import Checks)

This test prevented `domain/` modules from accidentally pulling in `mcp` SDK symbols during refactors. On one occasion, a developer attempted to import `McpError` in `domain/models.py` for error handling; the test failed immediately, surfacing the cross-layer violation before it reached code review.

### Single Re-Evaluation Path for Cancellation

Cancellation triggers an internal `generate_schedule` call, which re-evaluates all flights from current state. The `dependents_reevaluated` diff is computed by comparing flight states before/after the re-run. This keeps the state machine simple and avoids a separate "cascade" logic path that could diverge from the scheduler.

### All-Required Env Vars (DD-2)

The `CONFIG ERROR:` format immediately surfaced misconfiguration in integration tests without digging through tracebacks. For example, a typo in `ATC_RUNWAYS` JSON produced `CONFIG ERROR: ATC_RUNWAYS is invalid: not valid JSON: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)`, which was immediately actionable.

---

## 5. What Didn't Work / Open Questions / Future Scope

### No Persistence Across Restarts

All flight state and schedules are lost on server restart. `spec.md §11` lists this as a non-requirement. The seam is `domain/state.py` — a future extension could replace the in-memory dict with a persistent store (SQLite, Redis, etc.) without touching the scheduler or domain logic.

### No Authentication/Authorization

Any connected MCP client can submit, cancel, or reschedule flights. `spec.md §11` explicitly excludes auth. A production deployment would need multi-tenant isolation, API keys, or OAuth integration.

### Single-Process, Single-Threaded Model

No concurrent request handling. The server processes one MCP call at a time. This is adequate for local/demo use but would not scale to production. A future extension could use async request handling or a multi-process architecture.

### No Quantitative Performance SLAs

NFR-1 says "lightweight" with no numeric targets. The scheduler is O(n²) worst-case (n = number of flights × runway/gate combinations). No benchmarks were run to establish throughput limits. A production deployment would need load testing and performance budgets.

### No Per-Flight Duration Overrides

Durations are operation-type-level only (DD-7). A future extension would add `duration_sec` to `submit_flight` input, allowing per-flight duration overrides for special cases (e.g., maintenance operations, emergency landings).

### Ground-Crew Model is a Simplified Counter

The model does not account for crew skill levels, crew rest periods, or crew assignment to specific flight types. It treats all crew units as interchangeable. A realistic model would need crew rostering, fatigue rules, and type ratings.

### No Metrics or Observability

No audit logs, metrics dashboards, or monitoring. The server writes only JSON-RPC frames to stdout. A production deployment would need structured logging, Prometheus metrics, and distributed tracing.

### No UI or Visualization

The server is a headless MCP backend. There is no web UI, CLI client, or Gantt chart visualization. Clients interact via MCP tools and resources only. A future extension could add a web dashboard for operational visibility.
