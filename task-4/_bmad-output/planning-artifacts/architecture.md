---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - _bmad-output/planning-artifacts/architect-brief.md
  - _bmad-output/planning-artifacts/spec.md
  - _bmad-output/planning-artifacts/plan.md
  - original-task
workflowType: 'architecture'
project_name: 'task-4'
user_name: 'Yauheni.nikifarau'
date: '2026-05-18'
lastStep: 8
status: 'complete'
completedAt: '2026-05-19'
---

# Architecture Decision Document — Air Traffic Control MCP Server (task-4)

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements (17 total, grouped):**

- **Configuration (FR-CFG-1, FR-CFG-2):** All airport limits load from env vars; invalid config aborts startup with a clear, variable-named error. → Architecturally: a single config-loader module is the validation boundary. After startup, config is an immutable struct.
- **MCP Tools (FR-TOOL-1..5):** Submit flight, refresh schedule, airport status, cancel flight (with cascade), bottleneck analysis. → A request-handler layer translates MCP calls into domain commands; the domain core is MCP-agnostic.
- **MCP Resources (FR-RES-1..3):** Flight queue, runway availability/usage, operation timeline. → Resources are projections over the domain state; no separate storage.
- **Scheduling (FR-SCH-1..7):** No resource overlap; full constraint compliance (runway requirements, gate availability, three separation-buffer flavors, dependency buffers, capacity limits); priority earlier under contention; unschedulable flights remain visible with reason; dependency ordering; **determinism**; cancellation cascade.

**Non-Functional Requirements:**

- **NFR-1 Lightweight** — single-process, in-memory, minimal deps.
- **NFR-2 Startup correctness** — clean config → server up; all tools and resources discoverable via MCP.
- **NFR-3 Determinism** — same inputs + same config → identical schedule. Drives data structure choice, tie-break policy, no time-based RNG, no hash-randomized iteration, no implicit parallelism.
- **NFR-4 Documentation coverage** — README must enumerate tools, resources, env vars, and run/connect steps.
- **NFR-5 MCP compatibility** — tools and resources discoverable per the MCP specification.

**Scale & Complexity:**

- Primary domain: backend MCP server (no UI per `§OT:6`).
- Complexity level: **medium** — single service, but multi-constraint scheduling + dependency cascades + bottleneck analysis + strict determinism.
- Estimated architectural components: ~8 (MCP transport, config loader, flight store, scheduler, status reporter, bottleneck analyzer, resource/timeline projector, cancellation handler).

### Technical Constraints & Dependencies

- **Determinism (`FR-SCH-6`)** — hardest cross-cutting constraint. All ordering must be explicit; tie-breaks defined; iteration over sets/maps uses deterministic ordering or sorted views.
- **In-memory by default (`plan.md DD-5`)** — no persistence assumed; full state reset on restart.
- **MCP SDK choice is open (`DD-3`)** — language/runtime/SDK left to the architect; constraint is "lightweight" and MCP-spec compliance.
- **No external integrations** — no databases, no APIs, no auth. Boundaries are: env vars in, MCP I/O out.
- **Explicit non-requirements (`spec.md §11`)** — no auth, no persistence, no metrics, no UI, no aircraft physics, no SLAs. Guard rails against scope creep.

### Cross-Cutting Concerns Identified

1. **Determinism enforcement** — touches scheduling algorithm, data structures, logging order, and the bottleneck tool's chain ordering.
2. **Time model consistency** — every component (config buffers, schedule placements, timeline events, bottleneck durations) must speak the same time unit and same epoch. Defined once in DD-6.
3. **Reason-string propagation** — unschedulable flights and resource constraints carry human-readable reasons all the way out to FR-TOOL-3 status and FR-RES-1 queue. Reasons are first-class fields, not logs.
4. **Cancellation flow** — cancellation must trigger dependent re-evaluation; the cleanest model is "cancel marks state, then schedule tool produces the new plan" — to be confirmed in the algorithm step.
5. **Traceability to spec.md §12** — every architecture section must map to at least one `§OT:` row; a final traceability check is part of DoD.
6. **Fail-fast startup** — config validation is the only validation boundary; every env var has a documented error shape (DD-2).

## Tech Stack & Project Bootstrap (resolves DD-3)

### Primary Technology Domain

**Backend MCP server.** No UI (`§OT:6`), no external integrations, no persistence by default. The only I/O surfaces are env-var configuration at startup and MCP tool/resource calls at runtime.

### Tech Stack Decision

| Concern | Choice | Rationale |
|---|---|---|
| Language | **Python 3.11+** | Insertion-ordered dicts (3.7+) help determinism; `match` statements help dispatch readability; 3.11 perf improvements; broad MCP example coverage. |
| MCP SDK | **Official `mcp` PyPI package** | Reference implementation maintained by the MCP project; covers tools, resources, stdio transport; pairs with Pydantic for schemas. |
| Transport | **stdio** | Canonical for local MCP servers; what MCP-compatible clients launch by default; no network surface, lower attack/complexity surface — fits "lightweight" (`§OT:4`). |
| Validation | **Pydantic v2** | Used by the MCP SDK for tool input schemas; deterministic; doubles as the data model for flights, runways, gates, etc. |
| Dep / build | **`pyproject.toml` (PEP 621) + `pip`** | Standardized, no extra tooling required to install. `uv` is an acceptable optional accelerator for local development; not required. |
| Test runner | **`pytest`** | Boring, well-supported, deterministic when used without parallelism. |
| Lint / format | **`ruff`** | Single fast tool covering both, low config overhead. Optional, project-level decision. |
| Type checking | **Type hints + Pydantic** | Optional `mypy` pass; not required for delivery. |

### Why no traditional "starter template"

The MCP ecosystem does not have a canonical CLI starter equivalent to `create-next-app`. The conventional approach is a hand-rolled minimal layout using the official SDK's example server as reference. We adopt that convention rather than introducing a third-party scaffolder.

### Project Layout (bootstrap convention)

```
task-4/
├── pyproject.toml          # PEP 621 metadata + deps
├── README.md               # §OT:106 — install, env vars, tools, resources
├── report.md               # §OT:107 — approach, decisions, what worked
├── src/atc_mcp/
│   ├── __init__.py
│   ├── __main__.py         # entrypoint: `python -m atc_mcp`
│   ├── server.py           # MCP server wiring (tools + resources)
│   ├── config.py           # env-var loader, fail-fast validation
│   ├── time_model.py       # epoch + granularity (see DD-6)
│   ├── domain/
│   │   ├── models.py       # Flight, Runway, Gate, ScheduleEntry, …
│   │   └── state.py        # in-memory store
│   ├── scheduler/
│   │   ├── algorithm.py    # deterministic placement
│   │   └── constraints.py  # buffer/overlap/dep checks
│   ├── tools.py            # MCP tool handlers
│   ├── resources.py        # MCP resource handlers
│   ├── status.py           # FR-TOOL-3 payload builder
│   └── bottleneck.py       # FR-TOOL-5 longest-chain analysis
└── tests/
    ├── test_vs1_morning_rush.py
    ├── test_vs2_heavy_hauler.py
    ├── test_vs3_connecting_flight.py
    ├── test_determinism.py
    ├── test_config.py
    └── test_cancellation.py
```

### Initialization Steps (will land in the README)

```bash
# Create venv + install
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .

# Run the server (stdio)
python -m atc_mcp
```

`pyproject.toml` declares the entrypoint, the `mcp` and `pydantic` dependencies, and a `[project.scripts]` entry so the server can also be launched via a single command from an MCP client config.

### Architectural Decisions Provided by This Bootstrap

**Language & runtime:** Python 3.11+, single-process, synchronous core with `async` only where the MCP SDK requires it.

**Determinism guarantees from the stack:**

- `dict` iteration order is insertion order (3.7+).
- `sorted()` is stable.
- No reliance on `set` iteration order for any user-visible output — sets are used internally only; outputs use sorted lists.
- No use of `random` or time-seeded RNG anywhere in the scheduling path.
- Pydantic models with `model_config = ConfigDict(frozen=True)` for value types where appropriate.

**Code organization:**

- `domain/` is MCP-agnostic and dependency-free — pure scheduling logic.
- `tools.py` / `resources.py` are the only MCP-facing layers; they translate MCP calls into domain commands.
- `config.py` is the validation boundary; nothing else validates env vars.
- `time_model.py` is the single source of truth for time units and epoch (see DD-6).

**Note:** Project initialization using the layout above should be the first implementation story. Version pins (Python minor, `mcp`, `pydantic`, `pytest`, `ruff`) will be set at that time against then-current releases.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical (Block Implementation):**
- DD-1 — Tool & resource catalog (input/output schemas)
- DD-2 — Environment-variable contract
- DD-4 — Scheduling algorithm + determinism argument
- DD-6 — Time model
- DD-7 — Operation duration source
- DD-8 — Runway capability schema
- DD-10 — Ground crew semantics in scheduling

**Important (Shape Architecture):**
- DD-5 — State persistence (in-memory, recommended)
- DD-9 — "Active scheduled dependency chain" definition

**Already decided in Step 3:**
- DD-3 — Tech stack (Python 3.11+, official `mcp` SDK, stdio, Pydantic v2)

**No decisions deferred** beyond the architect phase.

---

### Time Model (resolves DD-6)

**Epoch:** logical relative time. `t=0` is the moment a schedule is generated. The scheduler never reads wall-clock time. This is the single biggest determinism guarantee at the design level.

**Granularity:** integer seconds (`int`). All durations and buffers in env vars are seconds. All schedule placements are `(start_sec, end_sec)` integer pairs.

**Timeline representation:** ordered list of `TimelineEvent` objects sorted by `(start_sec, runway_id, flight_number)`. Wall-clock projection (if ever needed by clients) is added at the resource layer without touching the scheduler — out of scope for this task.

**Why relative time, not wall-clock:** the original task says "scheduling horizon" (`§OT:28`) and "completion time" (`§OT:100`) but never says "the schedule starts at wall-clock now." Relative time eliminates a non-deterministic input.

---

### Environment Variable Contract (resolves DD-2)

All env vars use the `ATC_` prefix. All are **required**; no silent defaults (`§OT:30` / `FR-CFG-2`). All values are positive integers unless noted. Validation happens once at startup in `config.py`; on any failure, the server exits with a single error line of the form:

```
CONFIG ERROR: <ENV_VAR_NAME> is invalid: <reason>
```

| Env var | Type | Unit | Accepted range | Maps to spec |
|---|---|---|---|---|
| `ATC_RUNWAYS` | JSON array | — | non-empty, see schema (DD-8) | `§OT:22`, `§OT:16,67–76` |
| `ATC_GATE_COUNT` | int | count | ≥ 1 | `§OT:23` |
| `ATC_GROUND_CREW_COUNT` | int | count | ≥ 1 | `§OT:24` |
| `ATC_RUNWAY_SEP_TAKEOFF_SEC` | int | seconds | ≥ 0 | `§OT:25` |
| `ATC_RUNWAY_SEP_LANDING_SEC` | int | seconds | ≥ 0 | `§OT:25` |
| `ATC_RUNWAY_SEP_MIXED_SEC` | int | seconds | ≥ 0 | `§OT:25` |
| `ATC_GATE_TURNAROUND_SEC` | int | seconds | ≥ 0 | `§OT:26` |
| `ATC_DEPENDENCY_BUFFER_SEC` | int | seconds | ≥ 0 | `§OT:27` |
| `ATC_SCHEDULING_HORIZON_SEC` | int | seconds | ≥ 1 | `§OT:28` |
| `ATC_DURATION_ARRIVAL_SEC` | int | seconds | ≥ 1 | DD-7 (`§OT:101`) |
| `ATC_DURATION_DEPARTURE_SEC` | int | seconds | ≥ 1 | DD-7 (`§OT:101`) |

**Note on "runway count":** spec §4 lists "Runway count" as a concept (`§OT:22`). We satisfy it via `ATC_RUNWAYS` — the count is `len(ATC_RUNWAYS)`, and each entry carries its capabilities. This collapses runway count and runway capability into one source of truth (see DD-8) and avoids consistency bugs between two env vars.

**Startup validation failure shapes** (representative):

- Missing var: `CONFIG ERROR: ATC_GATE_COUNT is invalid: variable not set`
- Non-integer: `CONFIG ERROR: ATC_GATE_COUNT is invalid: expected integer, got "three"`
- Out of range: `CONFIG ERROR: ATC_GATE_COUNT is invalid: must be >= 1, got 0`
- Malformed JSON: `CONFIG ERROR: ATC_RUNWAYS is invalid: not valid JSON: <parser-message>`
- Empty list: `CONFIG ERROR: ATC_RUNWAYS is invalid: must contain at least one runway`
- Duplicate runway id: `CONFIG ERROR: ATC_RUNWAYS is invalid: duplicate runway id "R1"`

---

### Operation Duration Source (resolves DD-7)

**Single source of truth:** two env vars `ATC_DURATION_ARRIVAL_SEC` and `ATC_DURATION_DEPARTURE_SEC`.

Operation duration is determined **solely** by operation type. The submit-flight tool does **not** accept a duration override — adding that would introduce a user-facing requirement not in `spec.md`.

Used by:
- Scheduler — duration drives end_sec = start_sec + duration.
- Bottleneck analyzer — `§OT:101` requires accounting for operation durations.
- Status payload — derives capacity/usage windows.

---

### Runway Capability Schema (resolves DD-8)

`ATC_RUNWAYS` shape (JSON array, each entry):

```json
{
  "id": "R1",
  "length_m": 3500
}
```

**Validation:**
- `id`: string, non-empty, unique within the array.
- `length_m`: positive integer, meters.

**Flight runway requirements** (optional field on `submit_flight.runway_requirements`):

```json
{
  "min_length_m": 4500
}
```

**Matching rule:** a runway R is feasible for flight F iff `R.length_m >= F.runway_requirements.min_length_m` (or F has no `min_length_m`).

**VS-2 (Heavy Hauler) behavior:** the flight is unschedulable; its reason is `"No runway meets minimum length 4500m (available runways: R1 3500m, R2 3000m)"`. This is sufficient and minimal.

> Schema is intentionally limited to `length_m` because VS-2 is the only scenario in `spec.md §9` requiring capability matching. Other capabilities (surface type, ILS, weight class) are **not** in the original task and are not added.

---

### Ground Crew Scheduling Semantics (resolves DD-10)

**Model:** ground crew is a single shared capacity counter equal to `ATC_GROUND_CREW_COUNT`. Each scheduled flight operation occupies one crew unit for its full operation duration `[start_sec, end_sec)`.

**Constraint:** at any time `t`, the number of operations whose interval contains `t` must not exceed `ATC_GROUND_CREW_COUNT`.

**Scheduler integration:** when computing the earliest feasible start time for a flight, the scheduler advances start_sec until the candidate window `[start_sec, start_sec + duration)` does not overlap with `crew_capacity` existing intervals at any point.

**Reportable via status (`FR-TOOL-3` / `§OT:100`):** `ground_crew: {capacity, in_use_peak, in_use_at_completion}`.

---

### State Persistence (resolves DD-5)

**In-memory only.** The server holds:
- `config: Config` — immutable after startup.
- `flights: dict[str, Flight]` — keyed by flight_number, insertion-ordered.
- `latest_schedule: Schedule | None` — replaced atomically on every `generate_schedule` call (`§OT:34`).
- (Cancellation is a state field on `Flight`, not a separate set.)

**Restart behavior:** all state is lost. The server restarts to a clean airport (matches "clean airport state" in every VS scenario setup).

**Rationale:** `spec.md §11` lists persistence as a non-requirement; adding it would broaden scope. If the user later expands scope, the in-memory store has a single seam (`domain/state.py`) for replacement.

---

### Scheduling Algorithm (resolves DD-4)

**Approach:** deterministic greedy constructive scheduler with explicit tie-break policy. Constraint-satisfaction-by-construction, no backtracking, no LP/ILP solver. Sufficient for the constraint set in `spec.md §7` and trivially deterministic.

**Step 1 — Build sort order.**
1. Compute topological depth `topo[f]` for each non-cancelled flight, where leaves (no deps) have depth 0 and a flight's depth is `1 + max(topo[d] for d in deps)`. If the dep graph has a cycle, mark all flights in the cycle unschedulable with reason `"dependency cycle: <flight_numbers>"`.
2. Compute `priority_rank: high=0, medium=1, low=2`.
3. Sort flights ascending by tuple `(topo[f], priority_rank[f], flight_number)`.
   - `topo` first: a dependency cannot be placed after its dependent.
   - `priority_rank` second: among flights with no ordering constraint between them, higher priority wins.
   - `flight_number` third: total ordering tiebreak, ensures determinism.

**Step 2 — Place each flight in sort order.**

For each flight `f`:

1. **Filter feasible runways** by `f.runway_requirements`. If empty, mark unschedulable; reason names the requirement and lists available runway capabilities. Continue.
2. **Compute floor start time** = max of:
   - `0` (relative epoch),
   - for each dep `d` of `f`: `schedule[d].end_sec + ATC_DEPENDENCY_BUFFER_SEC`. (If any dep is unschedulable or cancelled, mark `f` unschedulable with reason `"dependency <d> is not scheduled"`. Continue.)
3. **For each (runway R, gate G) candidate**, in deterministic order (lex ascending by `(R.id, G.id)`), compute the earliest feasible start time `t_R_G` such that:
   - `t_R_G >= floor_start`,
   - `[t_R_G, t_R_G + duration)` does not overlap any existing placement on R,
   - the separation buffer between R's previous op and `f` is respected (takeoff/landing/mixed flavor by op-type pair),
   - `[t_R_G - turnaround, t_R_G + duration)` does not overlap any existing placement on G (turnaround applied to gate occupancy boundaries),
   - the crew-capacity invariant (DD-10) holds throughout `[t_R_G, t_R_G + duration)`.
4. **Select the (R, G) with minimum `t_R_G`**; ties broken by `(R.id, G.id)` lex ascending.
5. If `t_R_G + duration > ATC_SCHEDULING_HORIZON_SEC`, mark `f` unschedulable with reason `"would exceed scheduling horizon (placement t=… + duration=… > horizon=…)"`. Continue.
6. Else commit the placement: update R's and G's busy intervals, update crew intervals, write `ScheduleEntry(f, R, G, t_R_G, t_R_G + duration)`.

**Step 3 — Compute completion time** as `max(entry.end_sec for entry in schedule, default=None)`.

**Determinism argument (explicit per FR-SCH-6 / `§OT:102`):**
1. Inputs are sorted by a total order on `(topo, priority_rank, flight_number)`; `flight_number` is unique.
2. Iteration over runways and gates is by sorted `(id)`; no set or hash iteration drives output.
3. Time math is pure integer arithmetic — no floats, no rounding.
4. Tie-breaks at every choice point are by lex on stable string ids.
5. No use of `random`, no time-seeded RNG, no wall-clock reads.
6. Cycle detection uses sorted DFS — the unschedulable list ordering is deterministic.
7. `dict` and `list` iteration are insertion-ordered in Python 3.7+; `set` is **never** iterated to produce output.

A property test (see test plan) will assert: for a fixed config and fixed flight-submission ordering, the schedule (as a list of ScheduleEntry tuples) is byte-identical across 100 runs.

**Priority handling under contention:** because priority is the second sort key (after topological depth), a higher-priority flight earns first claim on resources at its topological level. A high-priority dependent of a low-priority flight still waits for its dep — this matches `FR-SCH-3` and is the only sane reading of `§OT:97`.

---

### Cancellation Re-evaluation Flow (`FR-SCH-7` / `§OT:99`)

**Model:** cancellation is a state mutation on `Flight`. Re-evaluation of dependents happens by **regenerating the schedule from current state** — the schedule tool is the single re-evaluation path.

**Sequence:**
1. `cancel_flight(flight_number)` sets `flights[flight_number].state = "cancelled"`.
2. Any dependents are not eagerly updated; they remain in their previous state until the next `generate_schedule` call.
3. `cancel_flight` triggers an internal `generate_schedule()` so that the cancellation is reflected in the returned state, and the response carries the list of dependents whose status changed.

**Response shape:**
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

**Determinism note:** because `generate_schedule` is itself deterministic, the cancellation cascade is deterministic for any given flight state.

---

### "Active Scheduled Dependency Chain" Definition (resolves DD-9)

**Definition:** an ordered sequence of flights `f_1 → f_2 → … → f_n` (n ≥ 1) where:

1. Every `f_i` is **currently scheduled** in the latest `generate_schedule` result (has a `ScheduleEntry`) AND is **not cancelled**.
2. For each consecutive pair `(f_i, f_{i+1})`, `f_i` is in the `dependencies` list of `f_{i+1}`.

**Chain duration:** `f_n.end_sec - f_1.start_sec`. Equivalently: `sum(duration_i) + sum(dependency_buffer between consecutive pairs)` in the steady-state placement.

**"Longest":** the chain with the **maximum chain duration**. If multiple chains tie, the chain whose starting flight has the lexicographically smallest `flight_number` wins (deterministic tie-break).

**Algorithm:** DP over the dependency DAG restricted to scheduled, non-cancelled flights:
- For each such flight `f`, define `longest_to[f] = max(longest_to[d] + buffer + duration_f) for d in scheduled deps of f`, with `longest_to[f] = duration_f` for flights with no scheduled dep.
- Track parent pointers to reconstruct the chain.
- Pick the `f` with max `longest_to[f]`; reconstruct.

**Tool response shape:**
```json
{
  "chain": ["AA100", "AA200", "AA300"],
  "total_duration_seconds": 5400,
  "operation_durations": [1200, 1200, 1200],
  "dependency_buffers": [600, 600]
}
```

If no flights are scheduled, response is `{"chain": [], "total_duration_seconds": null, "operation_durations": [], "dependency_buffers": []}`.

---

### MCP Tool Catalog (resolves DD-1, part 1)

All tools use the official `mcp` SDK's tool registration; input schemas are Pydantic v2 models — the SDK derives JSON Schema automatically.

#### Tool: `submit_flight`

**Purpose:** `FR-TOOL-1` — register a new flight in the queue.

**Input:**
```json
{
  "flight_number": "AA123",
  "operation_type": "arrival",
  "priority": "high",
  "dependencies": ["AA001", "AA002"],
  "runway_requirements": {
    "min_length_m": 3500
  }
}
```

- `operation_type` ∈ {`"arrival"`, `"departure"`} (enum).
- `priority` ∈ {`"high"`, `"medium"`, `"low"`} (enum).
- `dependencies` defaults to `[]` if omitted.
- `runway_requirements` is optional.

**Validation:**
- `flight_number`: non-empty, must be unique among non-cancelled flights; conflicts return error `"flight_number AA123 already exists"`.
- `dependencies`: each must reference an existing flight; otherwise error `"unknown dependency: AA999"`.

**Output:**
```json
{
  "flight": {
    "flight_number": "AA123",
    "operation_type": "arrival",
    "priority": "high",
    "dependencies": [],
    "runway_requirements": {"min_length_m": 3500},
    "state": "queued"
  }
}
```

#### Tool: `generate_schedule`

**Purpose:** `FR-TOOL-2` — replace the current schedule with a freshly computed one (`§OT:34`).

**Input:** `{}` (no parameters).

**Output:**
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

#### Tool: `get_airport_status`

**Purpose:** `FR-TOOL-3` — five-piece payload from `§OT:100`.

**Input:** `{}`.

**Output:**
```json
{
  "flight_counts": {
    "by_state": {"queued": 1, "scheduled": 4, "unschedulable": 1, "cancelled": 0},
    "by_operation_type": {"arrival": 3, "departure": 3}
  },
  "runways": [
    {"id": "R1", "length_m": 3500, "capacity_sec": 86400, "usage_sec": 2400, "usage_pct": 2.78}
  ],
  "gates": {"capacity": 4, "in_use_peak": 2, "in_use_at_completion": 0},
  "ground_crew": {"capacity": 3, "in_use_peak": 2, "in_use_at_completion": 0},
  "resource_constraints": ["ground_crew_at_capacity_at_t=600..1200"],
  "unscheduled": [
    {"flight_number": "AA999", "reason": "No runway meets minimum length 4500m"}
  ],
  "completion_time_seconds": 1200
}
```

#### Tool: `cancel_flight`

**Purpose:** `FR-TOOL-4` — cancel a flight; trigger dependent re-evaluation (`§OT:99`, `FR-SCH-7`).

**Input:**
```json
{"flight_number": "AA123"}
```

**Output:** see Cancellation Re-evaluation Flow above.

**Error cases:** `"unknown flight_number AA123"`, `"flight AA123 is already cancelled"`.

#### Tool: `analyze_bottleneck`

**Purpose:** `FR-TOOL-5` — longest active scheduled dependency chain (`§OT:101`).

**Input:** `{}`.

**Output:** see "Active Scheduled Dependency Chain" section above.

---

### MCP Resource Catalog (resolves DD-1, part 2)

#### Resource: `atc://flights`

**Purpose:** `FR-RES-1` — flight queue including unscheduled and cancelled (`§OT:40`).

**Payload (JSON):**
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

Ordering: by `(state_rank, flight_number)` where `state_rank` is `scheduled=0, queued=1, unschedulable=2, cancelled=3` — deterministic.

#### Resource: `atc://runways`

**Purpose:** `FR-RES-2` — runway availability and usage (`§OT:41`).

**Payload:**
```json
{
  "runways": [
    {
      "id": "R1",
      "length_m": 3500,
      "scheduled_operations": [
        {"flight_number": "AA123", "operation_type": "arrival", "start_sec": 0, "end_sec": 1200}
      ],
      "busy_intervals_sec": [[0, 1200]],
      "next_free_sec": 1200
    }
  ]
}
```

Ordering: by `id` lex.

#### Resource: `atc://timeline`

**Purpose:** `FR-RES-3` — chronological scheduled operations (`§OT:42`).

**Payload:**
```json
{
  "events": [
    {
      "start_sec": 0, "end_sec": 1200,
      "flight_number": "AA123",
      "operation_type": "arrival",
      "runway_id": "R1", "gate_id": "G3",
      "depends_on": []
    }
  ]
}
```

Ordering: by `(start_sec, runway_id, flight_number)`.

---

### Decision Impact Analysis

**Implementation sequence (suggested story order):**
1. Project bootstrap (`pyproject.toml`, layout, entrypoint).
2. `config.py` — env-var loader + fail-fast validation (DD-2, DD-8).
3. `time_model.py` — relative epoch + integer seconds (DD-6).
4. `domain/models.py` — Flight, Runway, Gate, ScheduleEntry, etc.
5. `domain/state.py` — in-memory store (DD-5).
6. `scheduler/constraints.py` — buffer / overlap / crew helpers.
7. `scheduler/algorithm.py` — deterministic greedy placement (DD-4, DD-7, DD-10).
8. `bottleneck.py` — longest-chain DP (DD-9).
9. `status.py` — five-piece status payload (FR-TOOL-3).
10. `tools.py`, `resources.py` — MCP wiring (DD-1).
11. `server.py` — MCP server boot.
12. `tests/` — VS-1, VS-2, VS-3 plus determinism + config + cancel.

**Cross-component dependencies:**
- Every component depends on `time_model.py` for unit consistency.
- `tools.py` and `resources.py` depend on `domain/state.py`; the reverse must not hold.
- `bottleneck.py` reads `latest_schedule` from state; runs only after a `generate_schedule`.
- `config.py` is loaded once at server boot and passed by reference; never reloaded.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

Twelve potential conflict points identified — places where two independently-working implementers (or AI agents) could make inconsistent choices unless pinned down.

---

### Naming Patterns

**Python code (per PEP 8):**
- Modules / files: `snake_case.py` (`scheduler/algorithm.py`).
- Functions / variables: `snake_case` (`compute_floor_start_time`).
- Classes / Pydantic models: `PascalCase` (`Flight`, `ScheduleEntry`).
- Constants: `UPPER_SNAKE_CASE` (`MAX_HORIZON_SEC`).
- Private helpers: `_leading_underscore`.

**Env vars:** `ATC_<NOUN>_<UNIT>` — `ATC_GATE_TURNAROUND_SEC`, `ATC_DURATION_ARRIVAL_SEC`. Every time-valued env var ends in `_SEC` to make the unit unmistakable at the call site.

**MCP tool / resource names:**
- Tool names: `snake_case` verbs (`submit_flight`, `generate_schedule`, `cancel_flight`, `analyze_bottleneck`, `get_airport_status`).
- Resource URIs: `atc://<noun-plural>` (`atc://flights`, `atc://runways`, `atc://timeline`).

**JSON field convention (MCP I/O):** `snake_case`. Reasons:
1. Matches Python idiom — no per-call camelCase ↔ snake_case mapping.
2. Matches env var convention — single naming style across the external surface.
3. JSON Schema generated by Pydantic uses field names verbatim — no alias layer needed.

**Flight numbers:** treated as opaque strings, case-sensitive, non-empty, max 16 chars. No format enforcement beyond non-empty.

---

### Structure Patterns

**Module dependency direction (strict):**

```
domain/        ← no MCP imports, no env var reads
scheduler/     ← imports domain only
bottleneck.py  ← imports domain only
status.py      ← imports domain only
tools.py       ← imports domain, scheduler, bottleneck, status
resources.py   ← imports domain
server.py      ← imports tools, resources, mcp SDK
config.py      ← imports stdlib only
__main__.py    ← imports config, server only
```

Any import that crosses these arrows in the wrong direction is a review-block. The intent: `domain/` and `scheduler/` are implementation-agnostic and can be unit-tested without booting an MCP server.

**Test layout:**
- `tests/` mirrors the `src/` shape only where useful.
- Scenario tests live as `test_vs1_morning_rush.py` etc. — one file per VS in `spec.md §9`.
- Cross-cutting tests live at the top of `tests/` (e.g. `test_determinism.py`, `test_config.py`).
- No test framework beyond `pytest`; no plugins beyond what `pytest` ships with by default.

**Where things go:**
- Pydantic models — `domain/models.py` only.
- Constraint helpers — `scheduler/constraints.py`.
- The scheduling algorithm — `scheduler/algorithm.py`.
- The five-piece status payload — `status.py`.
- Bottleneck DP — `bottleneck.py`.
- MCP tool handlers — `tools.py`.
- MCP resource handlers — `resources.py`.
- Server boot wiring — `server.py`.

---

### Format Patterns

**MCP tool error format:** Pydantic `ValidationError` is allowed to propagate (the SDK surfaces it). Domain-level errors are raised as `McpError` from the SDK with code `INVALID_PARAMS` and a message of the form `"<noun>: <reason>"` — e.g., `"flight_number AA123 already exists"`.

**Unschedulable reason format:** lowercase sentence, no trailing period, names the offending value where applicable. Examples:
- `"No runway meets minimum length 4500m"`
- `"dependency AA123 is not scheduled"`
- `"would exceed scheduling horizon (placement t=82800+1200 > horizon=82800)"`

Reasons are stored as `Flight.unscheduled_reason: str | None` — **first-class field**, not log-only. They propagate to the queue resource, status payload, and schedule tool output.

**Time format in JSON:** all time values are integer **seconds**, in relative epoch (t=0 at schedule generation). Field names end in `_sec`. No ISO strings, no wall-clock timestamps anywhere in the public API.

**Boolean representation:** JSON `true` / `false`. Never `0/1`.

**Null handling:** `null` is used for "not yet computed" or "not applicable" (e.g., `completion_time_seconds: null` when nothing is scheduled). Empty list `[]` is used for "computed and empty" (e.g., `unscheduled: []`).

**Enums in JSON:** string literals. `operation_type`: `"arrival"` / `"departure"`. `priority`: `"high"` / `"medium"` / `"low"`. `state`: `"queued"` / `"scheduled"` / `"unschedulable"` / `"cancelled"`.

---

### Ordering Patterns (Determinism Enforcement)

These are not stylistic — they are correctness rules tied to `FR-SCH-6`.

**MUST sort before emitting:**
- Any list returned to MCP — schedule entries, runways, flights, timeline events, unscheduled list, bottleneck chain.
- The exact sort key for each list is documented in the resource / tool catalog (Step 4).

**MUST NOT iterate sets to produce output.** Use `sorted(my_set)` or keep an explicitly ordered structure (`list`, `dict`).

**MUST NOT read wall-clock time** anywhere on the scheduling / bottleneck path. `time.time()`, `datetime.now()`, and `datetime.utcnow()` are banned in `domain/` and `scheduler/`. Logging in `server.py` may use wall-clock; the scheduling state must not.

**MUST NOT use `random` or any non-deterministic source.** No exceptions in `domain/`, `scheduler/`, `bottleneck.py`, `status.py`.

---

### Communication Patterns

**Within process:** all MCP tool handlers operate by calling pure functions in `domain/` and `scheduler/` and returning structured results. No event bus, no observers, no async-queues. One process, one call stack.

**Logging:** minimal. `server.py` logs (a) startup config summary, (b) fatal errors. No `INFO`-level chatter in the scheduling path — helpful for determinism (no timestamp-laden output to compare against) and lightweight (`NFR-1`). Format: single-line key=value, stderr only.

**Cancellation cascade:** see Step 4 — `cancel_flight` mutates state then internally calls `generate_schedule`. No publish/subscribe.

---

### Process Patterns

**Error handling tiers:**

1. **Config errors** (`config.py`): print `CONFIG ERROR: ...` to stderr and `sys.exit(1)`. Fail-fast (`FR-CFG-2`).
2. **Tool input validation errors**: raise `ValidationError` (Pydantic) or `McpError(INVALID_PARAMS)`; SDK surfaces to client.
3. **Domain invariants violated** (should be unreachable): raise `AssertionError` — bug, not a user error.
4. **Unschedulability** is **not an error.** It is data — see the reason format above. The schedule tool returns `unscheduled: [...]` without raising.

**Loading/state patterns:**
- No async loading. The server is synchronous past the `mcp` SDK boundary. `async def` appears only where the SDK requires it.
- No retries anywhere. There is nothing to retry — no network, no I/O.
- No caching. Schedules are recomputed on each `generate_schedule` call (`§OT:34` says replaces, not memoize).

---

### Pydantic Model Conventions

- Tool inputs: Pydantic `BaseModel` with `model_config = ConfigDict(extra="forbid")` — unknown fields rejected, prevents silent typos.
- Value types (Flight, Runway, ScheduleEntry, …): `ConfigDict(frozen=True)` — immutable; mutations are state-store concerns, not value-type concerns.
- Field validators use `field_validator` (Pydantic v2 style), not `@validator` (v1 legacy).
- All time-valued fields are `int`, with `Field(ge=...)` for positivity guards.

---

### Enforcement Guidelines

**All implementations MUST:**

1. Pass every test in `tests/test_determinism.py` — same inputs + config produce byte-identical output across 100 runs.
2. Pass VS-1, VS-2, VS-3 from `spec.md §9`.
3. Use `snake_case` for every JSON field on the MCP surface.
4. Express every duration in integer seconds with `_sec` suffix.
5. Honor the strict import direction in §Structure Patterns.

**Pattern violations are caught by:**
- Determinism property test (catches set-iteration / RNG slip-ups).
- Module import graph test (caught by a one-line dependency rule in CI or a `pytest` import check).
- Pydantic `extra="forbid"` (catches field-name drift between client and server).
- `ruff` rules (optional, but recommended) — bans `time.time()` and `random` in `domain/` / `scheduler/`.

---

### Anti-Patterns (What to Avoid)

- Using `set` to hold "all flights" and iterating it for any output.
- Wrapping the MCP tool output in `{data: ..., error: ...}` — the SDK already has an error channel; double-wrapping is noise.
- Adding fields to `submit_flight` that aren't in DD-1 (e.g., per-flight duration, weight, surface preference). Those extend the product, not the architecture.
- Inventing capability fields beyond `length_m` on runways. VS-2 is the only scenario; YAGNI.
- Recording wall-clock timestamps in `ScheduleEntry`. Use relative seconds.
- Logging at `INFO` per scheduling decision — clutters output, hurts determinism comparability.
- Adding a "schedule diff" between subsequent generate calls — `§OT:34` says replaces; consumers reconcile if they care.

## Project Structure & Boundaries

### Complete Project Directory Structure

```
task-4/
├── README.md                    # §OT:106 — install, env vars, tools, resources, connect
├── report.md                    # §OT:107 — approach, decisions, what worked
├── pyproject.toml               # PEP 621 metadata, deps, [project.scripts]
├── .python-version              # pins Python 3.11
├── .gitignore                   # standard Python ignores
├── src/
│   └── atc_mcp/
│       ├── __init__.py
│       ├── __main__.py          # entrypoint: `python -m atc_mcp`
│       ├── config.py            # env-var loader, fail-fast validation
│       ├── time_model.py        # epoch + granularity constants
│       ├── server.py            # mcp.Server boot, tool/resource registration
│       ├── tools.py             # MCP tool handler functions
│       ├── resources.py         # MCP resource handler functions
│       ├── status.py            # FR-TOOL-3 five-piece payload builder
│       ├── bottleneck.py        # FR-TOOL-5 longest active chain (DP)
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── models.py        # Pydantic models: Flight, Runway, Gate,
│       │   │                    #   ScheduleEntry, TimelineEvent, Config,
│       │   │                    #   FlightState, OperationType, Priority,
│       │   │                    #   RunwayRequirements
│       │   └── state.py         # in-memory store: AirportState
│       └── scheduler/
│           ├── __init__.py
│           ├── algorithm.py     # deterministic greedy placement
│           └── constraints.py   # buffer / overlap / crew helpers
└── tests/
    ├── __init__.py
    ├── conftest.py              # shared fixtures (env, config, fresh state)
    ├── test_vs1_morning_rush.py    # VS-1 (§OT:48–64)
    ├── test_vs2_heavy_hauler.py    # VS-2 (§OT:65–76)
    ├── test_vs3_connecting_flight.py # VS-3 (§OT:77–89)
    ├── test_config.py              # FR-CFG-1/2 — fail-fast scenarios
    ├── test_determinism.py         # FR-SCH-6 — byte-identical N runs
    ├── test_cancellation.py        # FR-TOOL-4, FR-SCH-7 — cascade
    ├── test_bottleneck.py          # FR-TOOL-5 — chain + tie-break
    ├── test_status.py              # FR-TOOL-3 — five-piece payload
    ├── test_priority.py            # FR-SCH-3 — high earlier under contention
    ├── test_resources.py           # FR-RES-1/2/3 — payload shapes + ordering
    └── test_imports.py             # enforces module dependency direction
```

### Component Decomposition (resolves Architect-Brief Deliverable #2)

| Component | File(s) | Responsibility | FR(s) |
|---|---|---|---|
| MCP transport | `server.py` | Boot mcp.Server over stdio; register tools + resources; route to handlers. | `NFR-5`, `§OT:44, 92` |
| Config loader | `config.py` | Read every `ATC_*` env var, parse, validate, return immutable `Config`; exit on error. | `FR-CFG-1`, `FR-CFG-2`, `NFR-2` |
| Time model | `time_model.py` | Constants and helpers for relative-epoch integer seconds. | DD-6, `FR-SCH-6` support |
| Domain models | `domain/models.py` | Pydantic value types. No behavior beyond validation. | DD-1 schemas |
| State store | `domain/state.py` | In-memory `AirportState`: flights dict + latest_schedule. Mutations only via clearly named methods. | DD-5, `FR-TOOL-1/4` |
| Scheduler (algorithm) | `scheduler/algorithm.py` | Deterministic greedy placement; produces `Schedule`. | `FR-SCH-1..6`, `FR-TOOL-2` |
| Scheduler (constraints) | `scheduler/constraints.py` | Pure helpers: overlap, separation, turnaround, crew capacity. | `FR-SCH-1, FR-SCH-2` |
| Bottleneck analyzer | `bottleneck.py` | Longest active scheduled dependency chain (DP). | `FR-TOOL-5`, DD-9 |
| Status reporter | `status.py` | Five-piece `get_airport_status` payload. | `FR-TOOL-3`, `§OT:100` |
| Timeline / resource projector | `resources.py` | Project `AirportState` + `Schedule` onto resource payloads. | `FR-RES-1/2/3` |
| Cancellation handler | `tools.py::cancel_flight_tool` | Mutates state, triggers schedule regen, returns dependent diffs. | `FR-TOOL-4`, `FR-SCH-7` |
| MCP tool handlers | `tools.py` | Thin adapters: Pydantic-validated input → domain call → JSON-ready output. | `FR-TOOL-1..5` |

### Architectural Boundaries

**Stdio I/O boundary (`server.py`):** the only place where stdin/stdout bytes become Python objects. Everything past this is typed.

**MCP boundary (`tools.py` + `resources.py`):** the only place that knows about MCP `Tool` / `Resource` types and the `mcp` SDK. Everything past this is plain Python + Pydantic.

**Domain boundary (`domain/` + `scheduler/`):** pure scheduling logic. Zero awareness of MCP, stdin/stdout, env vars, or wall-clock time. Importable and testable in isolation. This is what `test_imports.py` enforces.

**Config boundary (`config.py`):** the only place that reads `os.environ`. After startup, config flows by reference into every component that needs it.

**No data boundary:** no database, no cache, no external API. The only "data store" is the in-memory `AirportState` (DD-5).

### Requirements-to-Structure Mapping

**Configuration (FR-CFG-1, FR-CFG-2 / `§OT:19–30`):**
- `config.py` — loader + validator.
- `tests/test_config.py` — fail-fast scenarios per env var.

**Submit flight (FR-TOOL-1 / `§OT:33, 94`):**
- `tools.py::submit_flight_tool` — handler.
- `domain/models.py::Flight, RunwayRequirements` — input/value types.
- `domain/state.py::AirportState.add_flight` — state mutation.
- `tests/test_vs1_morning_rush.py`, `tests/test_vs3_connecting_flight.py`.

**Generate schedule (FR-TOOL-2 / `§OT:34`):**
- `tools.py::generate_schedule_tool` — handler.
- `scheduler/algorithm.py::schedule(state, config)` — core algorithm.
- `scheduler/constraints.py` — feasibility helpers.
- `domain/state.py::AirportState.set_latest_schedule` — replacement.
- All VS tests + `test_determinism.py` + `test_priority.py`.

**Get airport status (FR-TOOL-3 / `§OT:35, 100`):**
- `tools.py::get_airport_status_tool` — handler.
- `status.py::build_status(state, schedule)` — payload builder.
- `tests/test_status.py` + `test_vs2_heavy_hauler.py` (asserts unscheduled-with-reason surfaces).

**Cancel flight (FR-TOOL-4 / `§OT:36, 99` + FR-SCH-7):**
- `tools.py::cancel_flight_tool` — handler.
- `domain/state.py::AirportState.cancel_flight` — state mutation.
- `scheduler/algorithm.py::schedule` — re-eval (called internally).
- `tests/test_cancellation.py`.

**Bottleneck analysis (FR-TOOL-5 / `§OT:37, 101` + DD-9):**
- `tools.py::analyze_bottleneck_tool` — handler.
- `bottleneck.py::longest_active_chain(schedule)` — DP.
- `tests/test_bottleneck.py`.

**Resources (FR-RES-1/2/3 / `§OT:40–42`):**
- `resources.py::flights_resource, runways_resource, timeline_resource`.
- `tests/test_resources.py`.

**Scheduling rules (FR-SCH-1..7 / `§OT:95–99, 102`):**
- `scheduler/algorithm.py` + `scheduler/constraints.py` — implementation.
- `domain/models.py` — invariants (frozen value types, enums).
- VS tests + `test_determinism.py` + `test_priority.py` + `test_cancellation.py`.

**Determinism (FR-SCH-6 / `§OT:102` + NFR-3):**
- `time_model.py` — relative epoch.
- `scheduler/algorithm.py` — sort order, tie-breaks.
- Module-wide ban on `random`, `time.time()`, `datetime.now()` in `domain/` + `scheduler/`.
- `tests/test_determinism.py` — property assertion.

### Integration Points

**Internal communication (single process):**

```
MCP client
  │ stdio (JSON-RPC)
  ▼
server.py
  │ python call
  ▼
tools.py / resources.py        ← MCP boundary
  │ python call (typed)
  ▼
domain/state.py + scheduler/   ← domain core
  │
  ▼
domain/models.py (value types)
```

**External integrations:** none. The server runs as a subprocess of an MCP client; that is the only relationship with the outside world.

**Data flow per tool call:**
1. MCP client sends JSON-RPC over stdin.
2. `mcp` SDK parses → dispatches to registered tool.
3. Tool handler validates input via Pydantic.
4. Handler calls into `state` / `scheduler` / `bottleneck` / `status` (depending on tool).
5. Handler shapes the result as a JSON-ready dict.
6. SDK serializes and writes to stdout.

### File Organization Patterns

**Configuration files:** every config knob lives in `pyproject.toml` (deps, build, scripts, optional `ruff` settings). Env vars are runtime config only — they never live in any file in the repo. `.env` files are explicitly **not** used (would invite drift between dev and the operator's environment).

**Source organization:** flat by responsibility, not by layer. `tools.py` and `resources.py` are deliberately top-level — they are the MCP-facing surface, equivalent to `app.py` in a Flask app.

**Test organization:** one file per VS + one file per cross-cutting concern. No nested `tests/unit/`, `tests/integration/` split — the project is small enough that one directory is clearer.

**No asset directories:** no static files, no templates, no fixtures-as-files. Test fixtures live as Python factories in `tests/conftest.py`.

### Development Workflow Integration

**Development server:** `python -m atc_mcp` with env vars set. To exercise the server interactively, point an MCP-compatible client (e.g., Claude Desktop) at it via its MCP config.

**Build process:** none beyond `pip install -e .`. Python is interpreted; no bundle, no transpile.

**Deployment:** the README documents how to register the server with an MCP client. There is no separate "deploy" step — the client launches the server as a subprocess.

**CI considerations (out of scope but noted):** if CI is added later, the natural job is `pytest -q` after `pip install -e .[dev]`. No `.github/workflows/` directory is mandated by the task.

## Scenario Walkthroughs

Each walkthrough uses the same reference config to make placements concrete and reproducible. Any conformant implementation must produce the placements below for the given inputs (timings may differ if the operator picks different durations or buffers — the derivation logic must not).

**Reference config used in these walkthroughs:**
```
ATC_RUNWAYS=[{"id":"R1","length_m":3500},{"id":"R2","length_m":3000}]
ATC_GATE_COUNT=4
ATC_GROUND_CREW_COUNT=3
ATC_RUNWAY_SEP_TAKEOFF_SEC=120
ATC_RUNWAY_SEP_LANDING_SEC=180
ATC_RUNWAY_SEP_MIXED_SEC=240
ATC_GATE_TURNAROUND_SEC=300
ATC_DEPENDENCY_BUFFER_SEC=600
ATC_SCHEDULING_HORIZON_SEC=86400
ATC_DURATION_ARRIVAL_SEC=1200
ATC_DURATION_DEPARTURE_SEC=1200
```

Gates are named `G1`..`G4`.

---

### VS-1 — Morning Rush (`§OT:48–64`, `spec.md §9 VS-1`)

**Inputs (submission order):**
| # | Flight | Op type | Priority | Deps |
|---|---|---|---|---|
| 1 | AA001 | arrival | high | — |
| 2 | AA002 | departure | medium | — |
| 3 | AA003 | arrival | low | — |
| 4 | AA004 | departure | low | — |

**Sort (topo=0 for all; sort by `(priority_rank, flight_number)`):**
AA001 (0) → AA002 (1) → AA003 (2) → AA004 (2).

**Placement trace:**
1. **AA001** (arrival): no deps. Candidate `(R1,G1)` at `t=0`; crew=1. Place `[0,1200)` on `R1/G1`.
2. **AA002** (departure): `(R2,G2)` at `t=0` is feasible (no R2 history, no G2 history). Place `[0,1200)` on `R2/G2`. Crew peak=2.
3. **AA003** (arrival): R1 just had an arrival → landing-landing sep `180s`; next free `1200+180=1380`. G1 turnaround → free `1500`. Best on R1: `(R1,G2)` at `t=1380` (G2 already free post-AA002 at `1500`? No — G2 free post-AA002 turnaround is `1200+300=1500`). Recompute: G2 next free = `1500`. Try `(R1,G3)`: R1 `1380`, G3 free `0` ⇒ `t=1380`. Pick `(R1,G3)` lex over `(R1,G4)`. Crew during `[1380,2580)`: AA001/AA002 done at 1200; peak=1. Place `[1380,2580)` on `R1/G3`.
4. **AA004** (departure): R2 last op departure → takeoff-takeoff sep `120s`; R2 next free `1200+120=1320`. Try `(R2,G3)`: G3 occupied by AA003 `[1380,2580)` ⇒ AA004 on G3 must end by `1380-300=1080` (turnaround backwards) or start after `2580+300=2880`. So G3 ⇒ `t=2880`. Try `(R2,G4)`: G4 free; `t=1320`. Pick `(R2,G4)`. Crew during `[1320,2520)`: overlaps AA003 `[1380,2520)`; peak=2. Place `[1320,2520)` on `R2/G4`.

**Resulting schedule:**
| Flight | Op | Runway | Gate | start_sec | end_sec |
|---|---|---|---|---|---|
| AA001 | arrival | R1 | G1 | 0 | 1200 |
| AA002 | departure | R2 | G2 | 0 | 1200 |
| AA004 | departure | R2 | G4 | 1320 | 2520 |
| AA003 | arrival | R1 | G3 | 1380 | 2580 |

**Acceptance vs. `spec.md §9 VS-1`:**
- ✅ All schedulable flights are scheduled (`unscheduled = []`).
- ✅ No runway or gate has overlapping operations (`FR-SCH-1`).
- ✅ Higher-priority `AA001` placed at `t=0`; medium `AA002` placed at `t=0`; low priorities `AA003`/`AA004` placed later — priority earlier under contention (`FR-SCH-3`).
- ✅ Queue clearly indicates no flights are unscheduled.
- ✅ Schedule generated deterministically (sort key and tie-break policy are total orders).

Note: AA004 ends *before* AA003 because they land on different runways with different post-history. This is correct constraint compliance, not a priority violation — AA003 and AA004 share priority rank, so flight-number lex ordering decides which gets the earlier *attempt*, but actual placement depends on per-runway history.

---

### VS-2 — Heavy Hauler (`§OT:65–76`, `spec.md §9 VS-2`)

**Inputs:**
| # | Flight | Op type | Priority | Deps | `runway_requirements` |
|---|---|---|---|---|---|
| 1 | HH001 | departure | high | — | `{"min_length_m": 4500}` |

**Sort:** HH001.

**Placement trace:**
1. **HH001**: filter feasible runways by `R.length_m >= 4500`. R1=3500 ✗, R2=3000 ✗. Feasible set is empty.
2. Mark HH001 `state="unschedulable"`, `unscheduled_reason = "No runway meets minimum length 4500m (available runways: R1 3500m, R2 3000m)"`.

**Resulting state:**
- `schedule = []`
- `unscheduled = [{"flight_number": "HH001", "reason": "No runway meets minimum length 4500m ..."}]`
- `completion_time_seconds = null`
- `airport_status.flight_counts.by_state.unschedulable = 1`

**Acceptance vs. `spec.md §9 VS-2`:**
- ✅ Oversized flight is not scheduled (no `ScheduleEntry`).
- ✅ Flight remains visible in `atc://flights` resource with `state="unschedulable"`.
- ✅ Reason clearly indicates no suitable runway, and lists what *is* available so the operator can act.
- ✅ Other valid flights, if present, are processed independently of HH001 and remain schedulable — runway-requirement filtering is per-flight, not global.

---

### VS-3 — Connecting Flight (`§OT:77–89`, `spec.md §9 VS-3`)

**Inputs (submission order):**
| # | Flight | Op type | Priority | Deps |
|---|---|---|---|---|
| 1 | IN001 | arrival | medium | — |
| 2 | OUT002 | departure | medium | `["IN001"]` |

**Sort:** topo(IN001)=0, topo(OUT002)=1. Order: IN001, OUT002.

**Placement trace:**
1. **IN001** (arrival): no deps, floor=0. Pick `(R1,G1)` at `t=0`. Place `[0,1200)` on `R1/G1`.
2. **OUT002** (departure):
   - Floor = max(0, IN001.end_sec + dep_buffer) = `1200 + 600 = 1800`.
   - `(R1,G1)`: R1 last op arrival; mixed sep 240 → R1 free `1440`. G1 turnaround `1500`. Max(1800, 1440, 1500) = `1800`.
   - `(R1,G2)`: R1 `1440`, G2 `0`, floor `1800` ⇒ `1800`.
   - `(R2,G1)`: R2 `0`, G1 `1500`, floor `1800` ⇒ `1800`.
   - `(R2,G2)`: R2 `0`, G2 `0`, floor `1800` ⇒ `1800`.
   - All four candidates yield `t=1800`. Tie-break by `(runway_id, gate_id)` lex → `(R1, G1)`.
   - Crew: at `[1800,3000)`, IN001 ended at 1200; peak=1.
   - Place `[1800, 3000)` on `R1/G1`.

**Resulting schedule:**
| Flight | Op | Runway | Gate | start_sec | end_sec | depends_on |
|---|---|---|---|---|---|---|
| IN001 | arrival | R1 | G1 | 0 | 1200 | — |
| OUT002 | departure | R1 | G1 | 1800 | 3000 | IN001 |

**Acceptance vs. `spec.md §9 VS-3`:**
- ✅ Both flights scheduled (`unscheduled = []`).
- ✅ OUT002.start_sec (1800) ≥ IN001.end_sec (1200) — outbound does not start before inbound completes (`FR-SCH-5`).
- ✅ OUT002.start_sec - IN001.end_sec = 600 = `ATC_DEPENDENCY_BUFFER_SEC` — buffer respected exactly.
- ✅ Timeline resource emits events sorted by `start_sec`; OUT002 carries `depends_on: ["IN001"]` — dependency order visible.

---

## Test Plan Outline

> **Note:** Per `spec.md §9` architect note, VS-1/2/3 are the **mandatory** product requirements; everything else below is **test coverage only**, not new product requirements (`§OT:47`).

### Mandatory scenario tests (one file each)

| File | Scope | Maps to |
|---|---|---|
| `tests/test_vs1_morning_rush.py` | The full VS-1 trace above, asserting all four placements and ordering invariants. | `spec.md §9 VS-1` |
| `tests/test_vs2_heavy_hauler.py` | HH001 unscheduled with the exact reason format; queue + status payload reflect it. | `spec.md §9 VS-2` |
| `tests/test_vs3_connecting_flight.py` | IN001 → OUT002 ordering; OUT002.start - IN001.end == dep_buffer; timeline `depends_on` correct. | `spec.md §9 VS-3` |

### Cross-cutting tests

| File | Asserts |
|---|---|
| `tests/test_config.py` | Each `ATC_*` env var: missing, non-integer, out-of-range, malformed JSON variants each produce the correct `CONFIG ERROR: …` line and `sys.exit(1)`. |
| `tests/test_determinism.py` | Property: for fixed config + fixed submission order, running `generate_schedule` 100 times produces byte-identical `(schedule, unscheduled, completion_time_seconds)` tuples. Also: changing submission order of equal-priority same-topology flights *does* change tie-breaks — verifying determinism keys are submission-order-stable for the canonical case. |
| `tests/test_cancellation.py` | (a) cancelling a flight with dependents marks dependents `unschedulable` with reason `"dependency <X> is not scheduled"`; (b) cancelling a leaf flight does not affect others; (c) repeated cancellation returns `"flight ... is already cancelled"`. |
| `tests/test_bottleneck.py` | (a) linear chain returns the chain in order; (b) two equal-length chains: lex-smallest start flight wins; (c) cancelled flights are excluded; (d) empty / no-deps case returns `chain: []`. |
| `tests/test_status.py` | The five-piece payload contains exactly: flight_counts (by_state + by_operation_type), runways[], gates, ground_crew, resource_constraints, unscheduled, completion_time_seconds. |
| `tests/test_priority.py` | With two single-runway flights of differing priority submitted in low-then-high order, the high-priority flight gets the earlier slot. |
| `tests/test_resources.py` | Each resource payload's ordering rule (documented in DD-1) is honored. |
| `tests/test_imports.py` | `domain/` and `scheduler/` do not transitively import `mcp` or `os.environ`. Enforces the module-dependency-direction rule. |

### Out-of-scope test coverage (not added)

- Performance / load tests (no quantitative NFR; `spec.md §11`).
- Multi-process / concurrency tests (server is single-process; no concurrency primitive used).
- Network protocol fuzzing (stdio framing is the SDK's responsibility).
- Persistence-across-restart tests (no persistence; `DD-5`).

---

## README.md Outline (resolves Architect-Brief Deliverable #17)

Aligned with `§OT:106`. Structure only; implementer fills content.

```
# task-4 — Air Traffic Control MCP Server

## Overview
- One-paragraph summary (lightweight MCP server for ATC scheduling).

## Requirements
- Python 3.11+
- An MCP-compatible client (Claude Desktop, etc.) for end-to-end use.

## Installation
- Clone the repo.
- `cd task-4`
- `python3.11 -m venv .venv && source .venv/bin/activate`
- `pip install -e .`

## Configuration
All limits are read from environment variables. Invalid configuration
aborts startup with a `CONFIG ERROR: <VAR> is invalid: <reason>` line.

| Env var | Type | Unit | Range | Description |
| ... full table copied from the Env Var Contract section above ... |

### Example
- A copy-paste-runnable example config covering all 11 env vars.

## Running the server
- `python -m atc_mcp` (stdio).
- The server is intended to be launched by an MCP client, not run
  standalone; connecting from a client is described next.

## Connecting from an MCP-compatible client
- Show the JSON snippet to add to an MCP client config (e.g., Claude
  Desktop) pointing at `python -m atc_mcp` with the env block.

## MCP Tools
- `submit_flight` — short description + input/output summary.
- `generate_schedule` — short description + input/output summary.
- `get_airport_status` — short description + input/output summary.
- `cancel_flight` — short description + input/output summary.
- `analyze_bottleneck` — short description + input/output summary.

## MCP Resources
- `atc://flights` — short description.
- `atc://runways` — short description.
- `atc://timeline` — short description.

## Validation scenarios
- Brief recap of VS-1, VS-2, VS-3 and how to run them via `pytest`.

## Development
- `pip install -e .[dev]`
- `pytest -q`
- (Optional) `ruff check src/ tests/`

## License
- (Implementer's choice.)
```

---

## report.md Outline (resolves Architect-Brief Deliverable #18)

Aligned with `§OT:107`. Structure only; implementer fills content.

```
# task-4 — Report

## Scheduling approach
- Brief summary of the deterministic greedy approach (sort key, tie-
  breaks, why no LP/ILP, why no backtracking).

## Key decisions
- Why Python + official `mcp` SDK over alternatives.
- Why relative-time epoch over wall-clock.
- Why a single `ATC_RUNWAYS` JSON env var instead of separate
  count + capabilities env vars.
- Why ground crew as a global capacity counter (not per-operation
  staffing).
- Why operation durations are env-var-driven and per-op-type only.
- Why "active scheduled dependency chain" is restricted to
  currently-scheduled non-cancelled flights.

## Tools and techniques used
- Pydantic v2 for validation and JSON Schema.
- pytest for tests.
- (Optional) ruff for linting.
- Architecture document `_bmad-output/planning-artifacts/
  architecture.md` as the single source of design truth.

## What worked
- The deterministic-by-construction algorithm passed
  `test_determinism.py` from the first complete implementation.
- Splitting `domain/` from `tools.py` made the scheduler testable
  without the MCP runtime.
- Pydantic's `extra="forbid"` caught (n) field-name drifts during
  development.

## What did not work / things tried and rejected
- Backtracking scheduler (rejected — added complexity for no observable
  scenario benefit).
- Per-flight operation durations (rejected — would extend
  `submit_flight` beyond `spec.md`).
- Wrapping outputs in `{data, error}` (rejected — MCP SDK already has
  an error channel).
- Persisting state to disk (out of scope per `spec.md §11`).

## Open questions / future work
- Multi-airport coordination is out of scope but would require
  separating `AirportState` per airport id.
- Persistence across restarts could be added at the `domain/state.py`
  seam without touching the scheduler.
```

---

## Architecture Validation Results

### Coherence Validation

**Decision compatibility:** all DDs were checked for internal consistency. Two interactions to call out:
1. **DD-3 (Python) × DD-4 (deterministic algorithm)** — Python 3.11+ `dict` and `list` are insertion-ordered, and `sorted()` is stable. The combination supports the determinism argument with no extra primitives.
2. **DD-6 (relative epoch) × DD-7 (env-var durations) × FR-SCH-6 (determinism)** — relative time + fixed durations + integer arithmetic = no float-rounding, no clock-skew, no time-zone, no DST. Determinism follows by construction.

**Pattern consistency:** naming conventions (env vars in `ATC_<NOUN>_<UNIT>`, JSON in `snake_case`, time fields ending in `_sec`) are consistently applied across env contract, tool catalog, resource catalog, and scenario walkthroughs.

**Structure alignment:** the module dependency direction enforced in `test_imports.py` matches the boundaries called out in the Component Decomposition table — `domain/` and `scheduler/` cleanly testable in isolation.

### Requirements Coverage Validation

All 17 FRs + 5 NFRs + 3 VSs are addressed by at least one architecture section. Coverage matrix:

| Spec section | Covered by architecture section(s) |
|---|---|
| §4 FR-CFG-1, FR-CFG-2 | Env Var Contract; Project Layout (`config.py`); Test Plan (`test_config.py`) |
| §5 FR-TOOL-1 | MCP Tool Catalog: `submit_flight`; Component Decomposition |
| §5 FR-TOOL-2 | MCP Tool Catalog: `generate_schedule`; Scheduling Algorithm |
| §5 FR-TOOL-3 | MCP Tool Catalog: `get_airport_status`; Component: status reporter |
| §5 FR-TOOL-4 | MCP Tool Catalog: `cancel_flight`; Cancellation Re-evaluation Flow |
| §5 FR-TOOL-5 | MCP Tool Catalog: `analyze_bottleneck`; Active Scheduled Dependency Chain |
| §6 FR-RES-1/2/3 | MCP Resource Catalog |
| §7 FR-SCH-1 | Scheduling Algorithm Step 2.3; Constraints helpers |
| §7 FR-SCH-2 | Scheduling Algorithm Step 2.3; Runway Capability Schema; Ground Crew Semantics; Env Var Contract (buffers/turnaround) |
| §7 FR-SCH-3 | Scheduling Algorithm Step 1 (priority_rank as sort key) |
| §7 FR-SCH-4 | Unschedulable Reason Format; Reason-string propagation pattern |
| §7 FR-SCH-5 | Scheduling Algorithm Step 1 (topo sort) + Step 2.2 (floor start = dep.end + buffer) |
| §7 FR-SCH-6 | Determinism Argument; Ordering Patterns; `test_determinism.py` |
| §7 FR-SCH-7 | Cancellation Re-evaluation Flow |
| §8 NFR-1 | Tech Stack section (lightweight Python + stdio) |
| §8 NFR-2 | Env Var Contract (fail-fast) |
| §8 NFR-3 | See FR-SCH-6 |
| §8 NFR-4 | README.md outline; report.md outline |
| §8 NFR-5 | Tech Stack section (official `mcp` SDK, stdio transport) |
| §9 VS-1 | Scenario Walkthrough VS-1 |
| §9 VS-2 | Scenario Walkthrough VS-2 |
| §9 VS-3 | Scenario Walkthrough VS-3 |
| §10 | README outline; report.md outline |
| §11 | Explicit Non-Requirements respected (no auth, no persistence, no metrics, no UI, no physics, no SLAs) |

### Traceability Check vs `spec.md §12`

Direct row-by-row mapping from spec's traceability matrix to this architecture document:

| `§OT` lines | Topic | Spec § | Architecture section(s) |
|---|---|---|---|
| 2, 4, 6 | Purpose, scope, focus | §1, §2 | Project Context Analysis (Requirements Overview, Scale & Complexity) |
| 9 | Anyone submits | §5 FR-TOOL-1 | Tool: `submit_flight` |
| 11–17 | Flight attributes | §3 Glossary, §5 FR-TOOL-1 | Tool: `submit_flight`; Pydantic Model Conventions; Runway Capability Schema |
| 19, 21–29 | Env-var config concepts | §4 FR-CFG-1 | Env Var Contract |
| 30 | Fail-fast | §4 FR-CFG-2, NFR-2 | Env Var Contract (validation failure shapes); Process Patterns Tier 1 |
| 32–37 | MCP tools | §5 FR-TOOL-1..5 | MCP Tool Catalog (all 5) |
| 39–42 | MCP resources | §6 FR-RES-1..3 | MCP Resource Catalog (all 3) |
| 44 | Naming flexibility, docs | §5, §6, NFR-4 | DD-1 catalog; README outline; report outline |
| 47 | Optional scenarios | §9 (architect note) | Test Plan Outline § "Cross-cutting tests" |
| 48–64 | VS-1 | §9 VS-1 | Scenario Walkthrough VS-1 |
| 65–76 | VS-2 | §9 VS-2 | Scenario Walkthrough VS-2 |
| 77–89 | VS-3 | §9 VS-3 | Scenario Walkthrough VS-3 |
| 92 | Server starts, accessible | NFR-2, NFR-5 | Tech Stack; Component Decomposition (`server.py`) |
| 93 | Limits from env | §4 FR-CFG-1 | Env Var Contract |
| 94 | Submit with priorities/deps | §5 FR-TOOL-1 | Tool: `submit_flight` |
| 95 | No runway/gate overlap | §7 FR-SCH-1 | Scheduling Algorithm Step 2.3; `constraints.py` |
| 96 | Constraint compliance | §7 FR-SCH-2 | Scheduling Algorithm; Runway Capability Schema; Ground Crew Semantics |
| 97 | Priority ordering | §7 FR-SCH-3 | Scheduling Algorithm Step 1 |
| 98 | Unschedulable visibility | §7 FR-SCH-4 | Unschedulable Reason Format; Reason-string propagation; Resource `atc://flights` |
| 99 | Cancellation cascade | §5 FR-TOOL-4, §7 FR-SCH-7 | Cancellation Re-evaluation Flow |
| 100 | Status payload contents | §5 FR-TOOL-3 | Tool: `get_airport_status` |
| 101 | Bottleneck output | §5 FR-TOOL-5 | Active Scheduled Dependency Chain (DD-9); Tool: `analyze_bottleneck` |
| 102 | Deterministic scheduling | §7 FR-SCH-6, NFR-3 | Determinism Argument; Ordering Patterns |
| 103–108 | Submission artifacts | §10 | README outline; report.md outline; Tech Stack (folder location) |

**Every row of `spec.md §12` is addressed. No row is unmapped.**

### Implementation Readiness Validation

**Decision completeness:**
- ✅ All 10 DDs (DD-1..DD-10) explicitly resolved.
- ✅ All env vars enumerated with type, unit, range, and failure shape.
- ✅ All tool input/output schemas specified.
- ✅ All resource payload shapes specified, with explicit ordering rules.

**Structure completeness:**
- ✅ Complete file tree provided.
- ✅ Per-file responsibilities documented in Component Decomposition.
- ✅ FR → file mapping is exhaustive.

**Pattern completeness:**
- ✅ Naming conventions specified for code, env vars, MCP names, JSON fields.
- ✅ Module dependency direction explicitly stated and test-enforced.
- ✅ Error-handling tiers specified.
- ✅ Determinism rules specified at the pattern level and test-asserted.

### Gap Analysis

**Critical gaps:** none. Implementation can begin without additional architect input.

**Important gaps:** none. All "active scheduled dependency chain", "ground-crew semantics", "operation durations" ambiguities are resolved in DD-9, DD-10, DD-7.

**Nice-to-have gaps:**
- `ruff` config is left to the implementer (not blocking).
- Exact MCP client config snippet for the README is left to the implementer (it varies per client).
- Version pins for `mcp`, `pydantic`, `pytest` are deferred to the bootstrap story (intentional — pin against then-current releases).

### Architecture Completeness Checklist

**Requirements Analysis:**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions:**
- [x] Critical decisions documented with versions (Python 3.11+; `mcp`, `pydantic`, `pytest`, `ruff` pins deferred to bootstrap as intentional flexibility)
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed (the only NFR is "lightweight" — addressed by single-process, in-memory, stdio)

**Implementation Patterns:**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure:**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION.

**Confidence Level:** high. The architecture resolves every deferred decision in the architect-brief, the traceability matrix is closed, and the three mandatory acceptance scenarios are walked through end-to-end against the design.

**Key strengths:**
- Determinism is enforced at three layers (algorithm sort key, language guarantees, test assertion).
- Module dependency direction makes the domain core testable without MCP.
- Reason-string propagation is structural, not log-only — VS-2 succeeds by construction.
- Cancellation re-evaluation reuses the schedule path; no second algorithm to keep in sync.

**Areas for future enhancement (post-MVP, out of scope here):**
- Multi-airport support (would split `AirportState` per airport id).
- Persistence at the `domain/state.py` seam if scope expands.
- Per-flight operation durations (would extend `submit_flight` schema).
- Richer runway capability schema (surface, ILS, weight class) if scenarios beyond VS-2 are introduced.

### Implementation Handoff

**AI Agent Guidelines:**
- Treat this `architecture.md` as the single source of design truth alongside `spec.md`. If a question is not answered here or in `spec.md`, escalate to the user — do not invent.
- Follow the module dependency direction strictly; `test_imports.py` will enforce it.
- Express every duration in integer seconds with the `_sec` suffix.
- Sort every list before emitting it on the MCP surface.

**First Implementation Priority:**
1. Bootstrap (`pyproject.toml`, `src/atc_mcp/__init__.py`, `__main__.py`).
2. `config.py` + `tests/test_config.py` — get fail-fast behavior in before any domain work.
3. `time_model.py` + `domain/models.py` — pin types before behavior.
4. `scheduler/algorithm.py` + VS-1/2/3 tests — the load-bearing slice.
5. Everything else (status, bottleneck, resources, MCP wiring).