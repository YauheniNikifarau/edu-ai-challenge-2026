---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/planning-artifacts/spec.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/implementation-readiness-report-2026-05-19.md
project_name: task-4
user_name: Yauheni.nikifarau
date: 2026-05-19
---

# task-4 — Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for **task-4 — Air Traffic Control MCP Server**, decomposing the requirements from `spec.md` (PRD), `architecture.md` (technical design with all 10 deferred decisions resolved), and the readiness-report findings into implementable, capability-scoped stories.

The project is a **lightweight Python MCP server** that coordinates flight operations at a busy airport: accepts flight plans, schedules arrivals/departures safely, manages limited airport resources, reacts to disruptions, and exposes state to AI clients via MCP tools and resources. No UI, no physics simulation, no persistence across restarts.

## Requirements Inventory

### Functional Requirements

**Configuration**

- **FR-CFG-1** — Required configuration values. Server must accept env-var configuration for: runway count, gate count, ground crew count, runway separation buffers (takeoffs / landings / mixed), gate turnaround time, dependency buffer time, maximum scheduling horizon. (`spec.md §4`, `§OT:21–28`)
- **FR-CFG-2** — Startup validation. Invalid configuration must cause the server to fail clearly at startup with an error indicating which value is invalid and why. (`spec.md §4`, `§OT:30`)

**MCP Tools** (capability-level; tool names at architect discretion per `§OT:44`)

- **FR-TOOL-1** — Submit flight. Accept a new arrival or departure submission carrying flight number, operation type (arrival|departure), priority (high|medium|low), optional dependencies (list of flight numbers), and optional runway requirements. (`spec.md §5`, `§OT:33,94`)
- **FR-TOOL-2** — Generate / refresh schedule. Replace the current schedule with a freshly computed one based on the current flight queue and current airport configuration, satisfying all scheduling rules (FR-SCH-1..7). (`spec.md §5`, `§OT:34`)
- **FR-TOOL-3** — Get airport status. Return structured operational status including: flight counts by state and by operation type; runway/gate capacity and usage; resource constraint indicators; unscheduled/blocked flights with reasons; current schedule completion time when available. (`spec.md §5`, `§OT:35,100`)
- **FR-TOOL-4** — Cancel flight. Cancel a flight (mark cancelled) and cause dependent operations to be re-evaluated. (`spec.md §5`, `§OT:36,99`)
- **FR-TOOL-5** — Bottleneck analysis. Identify the longest active scheduled dependency chain; result includes the ordered flights in the chain and the total elapsed duration accounting for operation durations and required dependency buffers. (`spec.md §5`, `§OT:37,101`)

**MCP Resources** (inspection surfaces; resource names at architect discretion)

- **FR-RES-1** — Flight queue. Expose the current flight queue, including unscheduled and cancelled flights. (`spec.md §6`, `§OT:40`)
- **FR-RES-2** — Runway availability and usage. Expose runway availability and usage information. (`spec.md §6`, `§OT:41`)
- **FR-RES-3** — Operation timeline. Expose a chronological timeline of scheduled airport operations. (`spec.md §6`, `§OT:42`)

**Scheduling Rules**

- **FR-SCH-1** — No resource overlap. Scheduling must avoid overlapping usage of the same runway or same gate. (`spec.md §7`, `§OT:95`)
- **FR-SCH-2** — Constraint compliance. Scheduling must respect runway requirements, gate availability, separation buffers (takeoffs/landings/mixed), dependency buffers, and airport capacity limits (including ground-crew capacity per architecture DD-10). (`spec.md §7`, `§OT:96`)
- **FR-SCH-3** — Priority ordering under contention. When resources are constrained, higher-priority flights must be scheduled earlier where possible. (`spec.md §7`, `§OT:97`)
- **FR-SCH-4** — Unschedulable visibility. Flights that cannot be scheduled must remain visible with a clear reason. (`spec.md §7`, `§OT:98`)
- **FR-SCH-5** — Dependency ordering. A dependent flight must not start before its dependency has completed; the configured dependency buffer must be applied between them. (`spec.md §7`, `§OT:15,87,101`)
- **FR-SCH-6** — Determinism. Repeated scheduling with the same inputs and configuration must produce deterministic results (byte-identical schedule across N runs). (`spec.md §7`, `§OT:102`)
- **FR-SCH-7** — Cancellation cascade. Cancelling a flight marks it cancelled and causes dependent operations to be re-evaluated. (`spec.md §7`, `§OT:99`)

### NonFunctional Requirements

- **NFR-1** — Lightweight. Single-process, in-memory, minimal dependencies; no quantitative targets defined or invented. (`spec.md §8`, `§OT:4`)
- **NFR-2** — Startup correctness. Server starts successfully when configuration is valid; all tools and resources are accessible from a connected MCP client. (`spec.md §8`, `§OT:30,92`)
- **NFR-3** — Determinism. See FR-SCH-6. (`spec.md §8`, `§OT:102`)
- **NFR-4** — Documentation coverage. README must enumerate all exposed tools and resources with short descriptions, all env vars and their accepted values, install/build/run steps, and how to connect an MCP-compatible client. `report.md` must describe scheduling approach, key decisions, tools/techniques used, and what worked and what did not. (`spec.md §8`, `§OT:44,106,107`)
- **NFR-5** — Compatibility. Server must be usable from an MCP-compatible client; tools and resources must be discoverable/accessible per the MCP specification. (`spec.md §8`, `§OT:44,92`)

### Additional Requirements

These come from `architecture.md` and the readiness report — architectural decisions, structural conventions, and validation scenarios that constrain implementation but are not raw functional requirements.

**Tech stack & bootstrap (resolves DD-3; architecture.md §Tech Stack)**

- Language: Python 3.11+ (insertion-ordered dicts; stable `sorted`; supports the determinism argument from the language layer).
- MCP SDK: official `mcp` PyPI package; **stdio** transport (no HTTP, no WebSocket, no network surface).
- Validation: Pydantic v2 (used by the MCP SDK for tool input schemas; doubles as the data model with `ConfigDict(frozen=True)` value types and `ConfigDict(extra="forbid")` tool inputs).
- Build/deps: `pyproject.toml` (PEP 621) + `pip`; `pytest` for tests; `ruff` optional for lint/format.

**Project structure & module dependency direction (architecture.md §Project Structure & Boundaries)**

- Source layout under `task-4/src/atc_mcp/` with `config.py`, `time_model.py`, `server.py`, `tools.py`, `resources.py`, `status.py`, `bottleneck.py`, `domain/{models.py,state.py}`, `scheduler/{algorithm.py,constraints.py}`. Tests under `task-4/tests/` with one file per VS and one per cross-cutting concern.
- Strict import direction: `domain/` and `scheduler/` must not import `mcp` or read `os.environ`; `config.py` is the only env-var reader; `tools.py`/`resources.py` are the only MCP-facing layers. Enforced by `tests/test_imports.py`.

**Environment variable contract (resolves DD-2; architecture.md §Environment Variable Contract)**

- All env vars use the `ATC_` prefix; all are required (no silent defaults); time values are integer seconds with `_SEC` suffix.
- Variables: `ATC_RUNWAYS` (JSON array of `{id, length_m}` — resolves DD-8 runway capability schema), `ATC_GATE_COUNT`, `ATC_GROUND_CREW_COUNT`, `ATC_RUNWAY_SEP_TAKEOFF_SEC`, `ATC_RUNWAY_SEP_LANDING_SEC`, `ATC_RUNWAY_SEP_MIXED_SEC`, `ATC_GATE_TURNAROUND_SEC`, `ATC_DEPENDENCY_BUFFER_SEC`, `ATC_SCHEDULING_HORIZON_SEC`, `ATC_DURATION_ARRIVAL_SEC` (DD-7), `ATC_DURATION_DEPARTURE_SEC` (DD-7).
- Startup failure format: single stderr line `CONFIG ERROR: <ENV_VAR_NAME> is invalid: <reason>` followed by `sys.exit(1)`.

**Time model (resolves DD-6; architecture.md §Time Model)**

- Relative-time epoch: `t=0` is the moment a schedule is generated; the scheduler never reads wall-clock time.
- Granularity: integer seconds (`int`); all durations, buffers, and placements are integer pairs `(start_sec, end_sec)`.
- Ban on `time.time()`, `datetime.now()`, `datetime.utcnow()`, `random` in `domain/` and `scheduler/`.

**Scheduling algorithm (resolves DD-4; architecture.md §Scheduling Algorithm)**

- Deterministic greedy constructive placement with explicit tie-break policy:
  1. Sort flights ascending by `(topo_depth, priority_rank, flight_number)`.
  2. For each flight, find earliest feasible `(runway, gate)` placement; tie-break by `(runway_id, gate_id)` lex.
  3. Apply separation buffer (takeoff/landing/mixed flavor by op-type pair), gate turnaround on gate boundary, dependency-buffer floor, ground-crew capacity invariant.
  4. If `t + duration > horizon`, mark unschedulable with reason.
  5. Cycle detection: cycles mark all participating flights unschedulable with reason `"dependency cycle: <flight_numbers>"`.
- Determinism argument explicit in the algorithm step (sort keys total-ordered; no set iteration drives output; integer-only time math; no RNG; no wall-clock).

**Cancellation re-evaluation flow (resolves FR-SCH-7; architecture.md §Cancellation Re-evaluation Flow)**

- `cancel_flight` mutates the flight state then internally calls `generate_schedule`; the cancellation response includes `dependents_reevaluated` with previous_state/new_state/reason for each affected dependent.
- Re-cancellation returns error `"flight ... is already cancelled"`.

**Active scheduled dependency chain (resolves DD-9; architecture.md §"Active Scheduled Dependency Chain" Definition)**

- Definition: ordered sequence of currently-scheduled, non-cancelled flights where each consecutive pair is in the `dependencies` relationship; chain duration = `f_n.end_sec - f_1.start_sec` (equiv. `sum(durations) + sum(buffers)`).
- "Longest" tie-break: chain whose starting flight has the lex-smallest `flight_number`.
- Empty case returns `{chain: [], total_duration_seconds: null, operation_durations: [], dependency_buffers: []}`.

**Ground-crew scheduling semantics (resolves DD-10; architecture.md §Ground Crew Scheduling Semantics)**

- Ground crew = shared capacity counter equal to `ATC_GROUND_CREW_COUNT`; each scheduled operation occupies one crew unit for `[start_sec, end_sec)`.
- Invariant: at any `t`, concurrent operations ≤ capacity. Status payload reports `ground_crew: {capacity, in_use_peak, in_use_at_completion}`.

**Persistence (resolves DD-5; architecture.md §State Persistence)**

- In-memory only. `flights: dict[str, Flight]`, `latest_schedule: Schedule | None`. Restart resets state. Single seam at `domain/state.py` should scope expand later.

**Tool & resource catalog (resolves DD-1; architecture.md §MCP Tool Catalog and §MCP Resource Catalog)**

- Tools (snake_case verbs): `submit_flight`, `generate_schedule`, `get_airport_status`, `cancel_flight`, `analyze_bottleneck` — exact input/output JSON shapes pinned in architecture.
- Resources (URIs `atc://<noun-plural>`): `atc://flights`, `atc://runways`, `atc://timeline` — exact payload shapes and sort orders pinned in architecture.
- JSON convention: `snake_case` field names; integer seconds with `_sec` suffix; string-enum literals for `operation_type`/`priority`/`state`; `null` for "not yet computed", `[]` for "computed and empty".

**Reason-string propagation (FR-SCH-4 enforcement; architecture.md §Format Patterns)**

- `Flight.unscheduled_reason: str | None` is a first-class field stored on the flight (not log-only); propagates to `atc://flights`, `get_airport_status`, and `generate_schedule` output.
- Reason format: lowercase sentence, no trailing period, names the offending value (e.g., `"No runway meets minimum length 4500m (available runways: R1 3500m, R2 3000m)"`).

**Determinism enforcement (architecture.md §Ordering Patterns)**

- Every list returned to MCP must be sorted before emission (sort keys documented per list in architecture).
- `set` iteration never drives output; use `sorted(my_set)` or keep an explicitly ordered structure.
- Property test `tests/test_determinism.py` asserts byte-identical `(schedule, unscheduled, completion_time_seconds)` across 100 runs.

**Mandatory acceptance / validation scenarios (`spec.md §9`)**

- **VS-1 — Morning Rush**: mixed-priority arrivals/departures on clean state; verify all schedulable flights placed, no overlaps, priority-earlier under contention, queue indicates any unscheduled.
- **VS-2 — Heavy Hauler**: oversized high-priority departure with no suitable runway; flight remains unscheduled with reason naming the unmet requirement; other valid flights unaffected.
- **VS-3 — Connecting Flight**: inbound arrival + dependent outbound departure; both scheduled if resources allow; outbound start ≥ inbound end + dependency buffer; timeline makes dependency order clear.

**Submission artifacts (`spec.md §10`, `§OT:103–108`)**

- Source code under `task-4/` folder; public repository; `README.md` per NFR-4; `report.md` per NFR-4.

**Hardening recommendation (readiness-report Recommendation R-A)**

- Pin the `FlightState` enum explicitly in `domain/models.py` (e.g., `queued | scheduled | unschedulable | cancelled`) rather than leaving it bound only by `test_status.py` assertions.

**Explicit non-requirements (`spec.md §11` — guardrails against scope creep)**

- NO auth/authz/multi-tenant isolation; NO persistence across restarts; NO audit logs/metrics dashboards/monitoring; NO web UI/CLI client/visualization; NO aircraft physics/weather/radar; NO quantitative SLAs; NO i18n/a11y (no human UI); NO external integrations beyond MCP.

### UX Design Requirements

**Not applicable — by design.** The product is an MCP server consumed only by MCP-compatible clients over JSON-RPC stdio. `spec.md §2.2` and `§11` explicitly exclude any visual interface, web UI, CLI client, or visualization (`§OT:6`). No UX design document was authored, and none is needed; NFR-4 (Documentation) covers the only human-facing surfaces (README + report.md), which are text artifacts, not UX.

### FR Coverage Map

| Requirement | Epic | Notes |
|---|---|---|
| FR-CFG-1 | Epic 1 | Required env-var configuration values |
| FR-CFG-2 | Epic 1 | Startup validation with clear error |
| FR-TOOL-1 | Epic 2 | `submit_flight` tool |
| FR-TOOL-2 | Epic 3 | `generate_schedule` tool |
| FR-TOOL-3 | Epic 3 | `get_airport_status` tool |
| FR-TOOL-4 | Epic 2 | `cancel_flight` tool (mutation + state) |
| FR-TOOL-5 | Epic 4 | `analyze_bottleneck` tool |
| FR-RES-1 | Epic 2 | `atc://flights` resource |
| FR-RES-2 | Epic 3 | `atc://runways` resource |
| FR-RES-3 | Epic 3 | `atc://timeline` resource |
| FR-SCH-1 | Epic 3 | No resource overlap |
| FR-SCH-2 | Epic 3 | Constraint compliance (separation, gate, dep buffer, ground crew) |
| FR-SCH-3 | Epic 3 | Priority ordering under contention |
| FR-SCH-4 | Epic 3 | Unschedulable visibility with reason |
| FR-SCH-5 | Epic 3 | Dependency ordering with buffer |
| FR-SCH-6 | Epic 3 | Determinism (= NFR-3) |
| FR-SCH-7 | Epic 2 + Epic 3 | Cancel marks state (E2); dependent re-eval flow (E3) |
| NFR-1 | Epic 1 | Lightweight, single-process, in-memory |
| NFR-2 | Epic 1 | Startup correctness; tools/resources accessible |
| NFR-3 | Epic 3 | Determinism property test |
| NFR-4 | Epic 4 | README + report.md coverage |
| NFR-5 | Epic 1 | MCP compatibility (stdio transport, discoverability) |
| VS-1 | Epic 4 | Morning Rush acceptance scenario |
| VS-2 | Epic 4 | Heavy Hauler acceptance scenario |
| VS-3 | Epic 4 | Connecting Flight acceptance scenario |

All functional requirements, non-functional requirements, and validation scenarios are mapped to an epic with no gaps.

## Epic List

### Epic 1: Project Bootstrap & Operational Core

A developer can install, configure, and run a working MCP server. The server starts correctly with valid configuration, fails clearly on invalid configuration with the exact `CONFIG ERROR: <ENV_VAR_NAME> is invalid: <reason>` format, and all MCP tools and resources are registered and discoverable by a connected MCP-compatible client over stdio (returning empty/stub data at this stage). Establishes the project structure, tech stack, module-import discipline, and time-model invariants that all subsequent epics rely on.

**FRs covered:** FR-CFG-1, FR-CFG-2, NFR-1, NFR-2, NFR-5

**Key deliverables:** `pyproject.toml` (PEP 621), `src/atc_mcp/config.py` (only env-var reader, `ATC_` prefix, all-required), `src/atc_mcp/time_model.py`, `src/atc_mcp/domain/models.py` (frozen Pydantic v2 value types incl. `FlightState` enum), `src/atc_mcp/domain/state.py` (in-memory store seam), `src/atc_mcp/server.py` (stdio MCP server bootstrap), tool/resource stub registration in `tools.py` and `resources.py`, `tests/test_imports.py` (enforces module dependency direction), `tests/test_config.py`.

### Epic 2: Flight Queue Management

An AI client can submit new flights (arrival or departure) with runway requirements, priority, and dependencies, and can cancel flights. The `atc://flights` resource exposes the full queue including unscheduled and cancelled flights with their reason strings. The flight state machine (`queued | scheduled | unschedulable | cancelled`) is in place so subsequent scheduling work has a stable substrate.

**FRs covered:** FR-TOOL-1, FR-TOOL-4, FR-RES-1, FR-SCH-7 (state transition portion)

**Key deliverables:** `submit_flight` tool with Pydantic `extra="forbid"` input schema, `cancel_flight` tool (mutation + re-cancellation error), `atc://flights` resource with documented sort order, `Flight.unscheduled_reason` first-class field, expanded `domain/state.py`, validation tests for inputs, dependency-list validation, and cancellation behavior.

### Epic 3: Deterministic Scheduling Engine & Airport Operations

An AI client can generate a deterministic schedule that respects every scheduling rule (no resource overlap, runway requirements, separation buffers by op-type pair, gate turnaround, dependency buffer floor, ground-crew capacity, priority under contention, scheduling horizon, cycle detection). The client can also retrieve full airport status with resource utilisation indicators, view the chronological operation timeline, and inspect runway availability and usage. Cancellation re-evaluates dependents and reports the cascade. Determinism is property-tested.

**FRs covered:** FR-TOOL-2, FR-TOOL-3, FR-RES-2, FR-RES-3, FR-SCH-1, FR-SCH-2, FR-SCH-3, FR-SCH-4, FR-SCH-5, FR-SCH-6, FR-SCH-7 (re-evaluation flow), NFR-3

**Key deliverables:** `scheduler/algorithm.py` (deterministic greedy constructive placement with explicit tie-break), `scheduler/constraints.py` (separation, dep-buffer, gate turnaround, ground-crew capacity, horizon, cycle detection), `generate_schedule` tool, `get_airport_status` tool (incl. `ground_crew: {capacity, in_use_peak, in_use_at_completion}`), `atc://runways` and `atc://timeline` resources, cancellation re-evaluation flow with `dependents_reevaluated` payload, `tests/test_determinism.py` (100-run byte-identical property test), per-rule unit tests.

### Epic 4: Bottleneck Analysis, Validation & Project Delivery

An AI client can identify the longest active scheduled dependency chain with ordered flights, total elapsed duration, per-operation durations, and per-buffer durations, with the empty-case contract honored. All three mandatory validation scenarios (VS-1 Morning Rush, VS-2 Heavy Hauler, VS-3 Connecting Flight) pass end-to-end. The project is fully documented per NFR-4 (README enumerates tools, resources, env vars, install/build/run, MCP client connection; `report.md` describes scheduling approach, key decisions, tools/techniques, what worked and what did not) and is deliverable.

**FRs covered:** FR-TOOL-5, NFR-4 + acceptance scenarios VS-1, VS-2, VS-3

**Key deliverables:** `bottleneck.py` (longest active chain algorithm with lex tie-break), `analyze_bottleneck` tool, `tests/test_vs1_morning_rush.py`, `tests/test_vs2_heavy_hauler.py`, `tests/test_vs3_connecting_flight.py`, `README.md`, `report.md`.

## Epic 1: Project Bootstrap & Operational Core

**Goal:** Working MCP server that starts on valid config, fails clearly on invalid config, and exposes all tool/resource stubs over stdio. Establishes module-import discipline, time-model invariants, frozen value types, and the in-memory state seam.

### Story 1.1: Project Skeleton & Module Boundaries

**As a** developer onboarding to the project,
**I want** a Python project skeleton with the agreed source layout, dependencies, and module-import discipline,
**So that** all subsequent work has a stable, lint-clean substrate that enforces the architectural import direction from day one.

**Acceptance Criteria:**

**Given** a clean checkout of the `task-4/` folder
**When** I run `pip install -e .[dev]`
**Then** `mcp`, `pydantic>=2`, `pytest` install successfully from a PEP 621 `pyproject.toml`
**And** the source tree exists at `src/atc_mcp/` with empty modules: `config.py`, `time_model.py`, `server.py`, `tools.py`, `resources.py`, `status.py`, `bottleneck.py`, `domain/__init__.py`, `domain/models.py`, `domain/state.py`, `scheduler/__init__.py`, `scheduler/algorithm.py`, `scheduler/constraints.py`
**And** `tests/test_imports.py` exists and asserts: `domain/` and `scheduler/` modules import neither `mcp` nor `os` (env access); `config.py` is the only module that reads `os.environ`; `tools.py` and `resources.py` are the only modules importing `mcp`
**And** `pytest -q tests/test_imports.py` passes
**And** running `python -m atc_mcp.server` exits non-zero with a clear "configuration not loaded" style message (full bootstrap comes in Story 1.4)

### Story 1.2: Configuration Loading & Startup Validation

**As an** operator running the server,
**I want** all `ATC_*` environment variables to be required, validated, and produce a precise stderr error on misconfiguration,
**So that** I never run with silently-defaulted values and can diagnose config errors in one line.

**Acceptance Criteria** (FR-CFG-1, FR-CFG-2)

**Given** `config.py` is the only module reading `os.environ`
**When** I call its `load_config()` function with all `ATC_*` env vars set to valid values
**Then** it returns a frozen Pydantic v2 `Config` model containing: `runways: tuple[Runway, ...]` parsed from `ATC_RUNWAYS` JSON `[{id, length_m}]`, `gate_count: int`, `ground_crew_count: int`, `runway_sep_takeoff_sec`, `runway_sep_landing_sec`, `runway_sep_mixed_sec`, `gate_turnaround_sec`, `dependency_buffer_sec`, `scheduling_horizon_sec`, `duration_arrival_sec`, `duration_departure_sec`
**And When** any required `ATC_*` env var is missing, empty, non-integer (for `_SEC` fields), non-positive, or fails `ATC_RUNWAYS` JSON schema validation
**Then** `load_config()` writes exactly one line to stderr in the format `CONFIG ERROR: <ENV_VAR_NAME> is invalid: <reason>` and raises a `ConfigError` (caller is responsible for `sys.exit(1)`)
**And** `tests/test_config.py` covers: happy path; each missing var; each invalid type; malformed `ATC_RUNWAYS` JSON; non-positive numeric; unknown extra keys in `ATC_RUNWAYS` items rejected
**And** all `Config` value types use `ConfigDict(frozen=True, extra="forbid")`

### Story 1.3: Domain Models, Time Model & In-Memory State Seam

**As the** scheduling engine,
**I want** frozen value types for `Flight`, `Schedule`, `Placement`, the `FlightState` enum, and integer-second time aliases, plus a single-seam in-memory store,
**So that** later stories have a stable, immutable data model and a clear mutation boundary.

**Acceptance Criteria** (NFR-1, hardening recommendation R-A)

**Given** the architecture's value-type contract
**When** I import from `domain.models`
**Then** `Flight`, `Schedule`, `Placement`, `Runway`, `BottleneckResult` are Pydantic v2 models with `ConfigDict(frozen=True, extra="forbid")`
**And** `FlightState` is a pinned `StrEnum` with exactly the values `queued`, `scheduled`, `unschedulable`, `cancelled` (per readiness recommendation R-A)
**And** `Flight` has a first-class field `unscheduled_reason: str | None = None`
**And** `time_model.py` exports `Seconds = int` plus a docstring-documented invariant that all times are non-negative integers and `t=0` is "schedule-generation moment"
**And** `domain/state.py` exposes a single `AppState` instance with `flights: dict[str, Flight]` (insertion-ordered) and `latest_schedule: Schedule | None` and helper methods `add_flight`, `get_flight`, `replace_flights_after_schedule`, `set_latest_schedule`, `reset()`; no other module mutates these fields directly
**And** `tests/test_imports.py` is extended to assert `domain/` and `scheduler/` import none of: `time`, `datetime`, `random`
**And** unit tests verify `FlightState` literal pinning and that `Flight(...)` rejects unknown fields

### Story 1.4: MCP Server Bootstrap with Tool & Resource Stubs

**As an** MCP-compatible client,
**I want** to connect to the running server over stdio and discover all five tools and three resources,
**So that** I can verify the server is wired correctly before any business logic is implemented.

**Acceptance Criteria** (NFR-2, NFR-5)

**Given** all `ATC_*` env vars are set to valid values
**When** I run `python -m atc_mcp.server`
**Then** the server starts on stdio MCP transport using the official `mcp` SDK without writing to stdout (only JSON-RPC frames)
**And** `tools/list` returns exactly: `submit_flight`, `generate_schedule`, `get_airport_status`, `cancel_flight`, `analyze_bottleneck` — each with its Pydantic v2 input schema (`extra="forbid"`) declared per architecture
**And** `resources/list` returns exactly: `atc://flights`, `atc://runways`, `atc://timeline`
**And** invoking each tool stub returns a clearly-marked "not yet implemented" error response (full behaviour lands in later epics)
**And** reading each resource stub returns the documented JSON shape with empty arrays / null fields (e.g. `atc://flights` → `{"flights": []}`)
**And** `tests/test_server_bootstrap.py` spawns the server in-process via the MCP SDK test harness and asserts the tool/resource catalog exactly matches the expected names and counts
**And** `tests/test_config_failure_exit.py` verifies that running the server with a missing `ATC_*` var prints a `CONFIG ERROR:` line to stderr and exits with code 1

## Epic 2: Flight Queue Management

**Goal:** An AI client can submit and cancel flights; the `atc://flights` resource exposes the full queue with state and reason strings. The flight state machine is in place as the stable substrate for Epic 3.

### Story 2.1: `submit_flight` Tool with Strict Input Validation

**As an** AI client,
**I want** to submit a new flight (arrival or departure) with priority, dependencies, and optional runway requirements,
**So that** the airport queue grows in a controlled, well-validated way and downstream scheduling has clean inputs.

**Acceptance Criteria** (FR-TOOL-1)

**Given** the server is running with valid config
**When** I call the `submit_flight` tool with a Pydantic-validated payload `{flight_number: str, operation_type: "arrival"|"departure", priority: "high"|"medium"|"low", dependencies: list[str] = [], runway_requirements: {min_length_m: int} | null = null}`
**Then** the input schema is `ConfigDict(extra="forbid")` and rejects unknown fields with a clear error
**And** the flight is appended to `AppState.flights` (insertion-ordered) with `state = FlightState.queued`, `placement = null`, `unscheduled_reason = null`
**And** the tool returns the canonical `Flight` JSON payload in the exact shape pinned in architecture (`snake_case` field names; `null` vs `[]` per convention)
**And When** the submitted `flight_number` already exists in `AppState.flights`
**Then** the tool returns an error `"flight <flight_number> already exists"` and `AppState` is unchanged
**And When** `dependencies` references a `flight_number` that does not exist
**Then** the tool returns an error `"unknown dependency: <missing_flight_number>"` and `AppState` is unchanged
**And When** `dependencies` contains the submitting flight's own `flight_number`
**Then** the tool returns an error `"flight cannot depend on itself"` and `AppState` is unchanged
**And** `tests/test_submit_flight.py` covers: happy path arrival; happy path departure with deps; duplicate rejection; unknown-dep rejection; self-dep rejection; extra-field rejection; missing required-field rejection; invalid enum literal rejection

### Story 2.2: `cancel_flight` Tool (State Mutation Only)

**As an** AI client,
**I want** to cancel a queued or scheduled flight,
**So that** I can remove it from operations; the full dependent re-evaluation cascade is handled by Epic 3 (this story only mutates the cancelled flight's own state).

**Acceptance Criteria** (FR-TOOL-4, FR-SCH-7 state-transition portion)

**Given** a flight `F` exists in `AppState.flights` with any state other than `cancelled`
**When** I call `cancel_flight({flight_number: "F"})`
**Then** `F.state` is set to `FlightState.cancelled`, its prior placement (if any) is cleared, and `F.unscheduled_reason` is set to `null`
**And** the tool returns the canonical cancellation payload in the architecture-pinned shape, with `dependents_reevaluated: []` (the cascade is wired in Epic 3 — leave it as an empty list here, do not silently swallow the field)
**And When** `F.state == cancelled`
**Then** the tool returns an error string exactly equal to `"flight F is already cancelled"` and `AppState` is unchanged
**And When** the flight does not exist
**Then** the tool returns an error `"flight <flight_number> does not exist"`
**And** `tests/test_cancel_flight.py` covers: cancel queued; cancel scheduled-stub (manually set state); re-cancel error message string-exact; unknown-flight error; payload shape conformance

### Story 2.3: `atc://flights` Resource

**As an** AI client,
**I want** to inspect the full flight queue including unscheduled and cancelled flights with their reason strings,
**So that** I always have ground truth for what the airport is tracking, regardless of scheduling state.

**Acceptance Criteria** (FR-RES-1, FR-SCH-4 reason-string surface)

**Given** `AppState.flights` contains a mix of `queued`, `scheduled`, `unschedulable`, and `cancelled` flights
**When** I read the `atc://flights` resource
**Then** the payload is the architecture-pinned JSON: `{"flights": [<Flight>, ...]}` with `snake_case` fields, `_sec` suffix on integer-second fields, `null` for "not yet computed" placement, `[]` for empty dependency lists
**And** the `flights` list is sorted by the documented sort order from architecture (`(state_rank, flight_number)` lex, with `state_rank` per the architecture spec)
**And** each entry's `unscheduled_reason` field is present (value `null` when not applicable, lowercase sentence with no trailing period when set)
**And** the resource never reads `os.environ`, never imports `mcp` directly from `domain/` (it lives in `resources.py` which does), and produces byte-identical output across N reads for identical state
**And** `tests/test_flights_resource.py` covers: empty state returns `{"flights": []}`; mixed-state ordering; reason-string format; determinism across 100 reads

## Epic 3: Deterministic Scheduling Engine & Airport Operations

**Goal:** An AI client can generate deterministic schedules respecting every scheduling rule, inspect airport status and timeline, and trigger cancellation cascades. Determinism is property-tested.

### Story 3.1: Scheduling Algorithm Core — Placement, Separation, Gate Turnaround, Runway Match, Horizon

**As the** scheduling engine,
**I want** a pure-function deterministic greedy placement algorithm that handles single-flight resource constraints,
**So that** I have a unit-testable foundation for layering dependency, ground-crew, and priority logic in later stories.

**Acceptance Criteria** (FR-SCH-1, FR-SCH-2 partial, FR-SCH-3 partial, FR-SCH-4)

**Given** `scheduler/algorithm.py` exposes `schedule(flights: tuple[Flight, ...], config: Config) -> Schedule`
**When** I call it with a tuple of flights (no dependencies, no ground-crew constraints — that comes in 3.2/3.3)
**Then** flights are sorted ascending by `(topo_depth=0, priority_rank, flight_number)` where `priority_rank` is `high=0, medium=1, low=2`
**And** for each flight, the earliest feasible `(runway, gate)` is selected, tie-broken by `(runway_id, gate_id)` lex
**And** separation buffer is applied between same-runway consecutive operations, using `ATC_RUNWAY_SEP_TAKEOFF_SEC` / `_LANDING_SEC` / `_MIXED_SEC` based on the op-type pair
**And** gate turnaround (`ATC_GATE_TURNAROUND_SEC`) is enforced on same-gate consecutive operations
**And** runway capability is matched against `runway_requirements.min_length_m` when present; flights with no matching runway are marked `unschedulable` with `unscheduled_reason` exactly `"no runway meets minimum length <N>m (available runways: <id> <len>m, ...)"`
**And** flights for which `t + duration > scheduling_horizon_sec` are marked `unschedulable` with `unscheduled_reason` exactly `"would exceed scheduling horizon"`
**And** the returned `Schedule` exposes `placements: tuple[Placement, ...]`, `unscheduled: tuple[Flight, ...]`, `completion_time_seconds: int | None`
**And** `scheduler/` does not import `mcp`, `os`, `time`, `datetime`, or `random` (verified by `tests/test_imports.py`)
**And** `tests/test_scheduler_placement.py` covers: single arrival placed at `t=0`; two same-runway arrivals respect separation; two same-gate departures respect turnaround; mixed op-type pair uses mixed separation; runway-requirement matching (one matches, one doesn't); horizon overflow → unschedulable with exact reason string; priority ordering (high before medium with one runway)

### Story 3.2: Dependency Ordering with Buffer & Cycle Detection

**As the** scheduling engine,
**I want** to honour explicit flight dependencies with a buffer floor and detect cycles,
**So that** dependent flights never start before their dependencies complete and the algorithm never loops or non-terminates.

**Acceptance Criteria** (FR-SCH-5, cycle detection from architecture)

**Given** `scheduler/algorithm.schedule()` from Story 3.1
**When** I call it with flights that have a dependency DAG
**Then** sort key is extended to true `(topo_depth, priority_rank, flight_number)` where `topo_depth` is computed from `dependencies`
**And** for any placed flight `F_dep` and its dependent `F`, the placement satisfies `F.start_sec ≥ F_dep.end_sec + ATC_DEPENDENCY_BUFFER_SEC`
**And** the dependency buffer floor coexists with separation/turnaround (whichever is later wins)
**And When** the dependency graph contains a cycle
**Then** every flight participating in the cycle is marked `unschedulable` with `unscheduled_reason` exactly `"dependency cycle: <sorted_lex_flight_numbers>"` (e.g. `"dependency cycle: F1, F2, F3"`)
**And** non-cycle flights are scheduled normally
**And When** a dependency is itself `unschedulable` or `cancelled`
**Then** the dependent flight is marked `unschedulable` with `unscheduled_reason` exactly `"dependency <flight_number> is not scheduled"`
**And** `tests/test_scheduler_dependencies.py` covers: chain of 3 with dep buffer enforced; diamond DAG; 2-cycle; 3-cycle; self-cycle (defence-in-depth beyond submit-time check); dep on cancelled; dep on unschedulable

### Story 3.3: Ground-Crew Capacity Invariant

**As the** scheduling engine,
**I want** to enforce that concurrent scheduled operations never exceed `ATC_GROUND_CREW_COUNT`,
**So that** the schedule reflects the realistic ground-side resource ceiling (DD-10).

**Acceptance Criteria** (FR-SCH-2 ground-crew portion, DD-10)

**Given** the algorithm from Stories 3.1 + 3.2
**When** I call `schedule()` with a config where `ground_crew_count = K`
**Then** for every instant `t` covered by any placement, the count of placements `p` with `p.start_sec ≤ t < p.end_sec` is `≤ K`
**And** when ground crew is the binding constraint, candidate flights are delayed (not dropped) until a crew slot opens within the horizon
**And** if the horizon is exceeded due to crew contention, the flight is marked `unschedulable` with `unscheduled_reason` exactly `"would exceed scheduling horizon"` (consistent with Story 3.1)
**And** `tests/test_scheduler_ground_crew.py` covers: `K=1` serializes everything; `K=2` allows 2 concurrent on different runways; crew-delayed flight is placed once crew frees up; crew-induced horizon overflow → unschedulable

### Story 3.4: Wire Algorithm to `generate_schedule` Tool + `atc://timeline` + `atc://runways` Resources

**As an** AI client,
**I want** to invoke `generate_schedule` and read the resulting timeline and runway-usage resources,
**So that** I can produce and inspect a deterministic schedule through the MCP surface.

**Acceptance Criteria** (FR-TOOL-2, FR-RES-2, FR-RES-3)

**Given** Stories 3.1–3.3 have produced a working `scheduler.algorithm.schedule()`
**When** I invoke the `generate_schedule` MCP tool (no input args, per architecture)
**Then** the tool reads `AppState.flights` and `Config`, calls `schedule()`, stores the result in `AppState.latest_schedule`, mutates each flight's `state` and `unscheduled_reason` to reflect the new outcome, and returns the architecture-pinned tool payload (placements list, unscheduled list, completion_time_seconds)
**And** `atc://timeline` returns `{"timeline": [<operation>, ...]}` sorted by `(start_sec, flight_number)` lex, with each operation containing `flight_number`, `operation_type`, `runway_id`, `gate_id`, `start_sec`, `end_sec`
**And** `atc://runways` returns `{"runways": [{"runway_id", "length_m", "placements": [...]}, ...]}` sorted by `runway_id` lex with per-runway placements sorted by `start_sec`
**And When** no schedule has yet been generated
**Then** `atc://timeline` returns `{"timeline": []}` and `atc://runways` returns `{"runways": [<runway with empty placements>, ...]}` (capacity exposed, usage empty)
**And** generating a schedule twice in a row with identical state produces byte-identical tool payload and resource payloads
**And** `tests/test_generate_schedule_tool.py` and `tests/test_timeline_runways_resources.py` cover the contract

### Story 3.5: `get_airport_status` Tool

**As an** AI client,
**I want** a single tool call that returns a structured operational snapshot,
**So that** I can answer "what's the state of the airport right now?" in one round-trip.

**Acceptance Criteria** (FR-TOOL-3)

**Given** Story 3.4 has wired `generate_schedule` and `AppState.latest_schedule` may be `null` or populated
**When** I invoke `get_airport_status` (no input args)
**Then** the response is the architecture-pinned payload containing: flight counts by state (`queued`, `scheduled`, `unschedulable`, `cancelled`) and by operation type; runway capacity and current usage; gate capacity and current usage; resource constraint indicators (which resource is the binding constraint, if any); `unscheduled_flights: [{flight_number, reason}, ...]` sorted by `flight_number` lex; `current_schedule_completion_seconds: int | null` (matches `Schedule.completion_time_seconds`, `null` if no schedule)
**And** `ground_crew: {"capacity": K, "in_use_peak": int, "in_use_at_completion": int}` is included, with `in_use_peak = 0` and `in_use_at_completion = 0` when no schedule exists
**And** repeated calls with identical state return byte-identical payloads
**And** `tests/test_airport_status.py` covers: empty state; queue-only state (no schedule yet); fully-scheduled state; mixed state with unschedulables; ground-crew peak math

### Story 3.6: Cancellation Re-Evaluation Flow with `dependents_reevaluated`

**As an** AI client,
**I want** cancelling a flight to re-evaluate its dependents and report the cascade,
**So that** I always know which downstream operations changed state as a result of my action (FR-SCH-7).

**Acceptance Criteria** (FR-SCH-7 cascade portion)

**Given** Story 2.2 implemented `cancel_flight` with `dependents_reevaluated: []` placeholder, and Story 3.4 wired `generate_schedule`
**When** I call `cancel_flight({flight_number: "F"})` on a scheduled flight `F` with downstream dependents `D1, D2`
**Then** `F.state` is set to `cancelled` (Story 2.2 behaviour preserved)
**And** `generate_schedule` is invoked internally and `AppState.latest_schedule` is replaced
**And** the response payload's `dependents_reevaluated` is a list (sorted by `flight_number` lex) of `{flight_number, previous_state, new_state, reason}` for every flight whose state changed as a result of the cancellation
**And** `reason` is the new `unscheduled_reason` when `new_state == "unschedulable"`, otherwise `null`
**And** the response also includes the updated full schedule snapshot (architecture-pinned shape)
**And When** the cancelled flight has no dependents
**Then** `dependents_reevaluated` is `[]` but the re-run of the algorithm still occurs and `latest_schedule` reflects the new state
**And** re-cancellation error from Story 2.2 (`"flight F is already cancelled"`) is preserved
**And** `tests/test_cancel_reevaluation.py` covers: cancel root of a chain → all dependents become unschedulable with correct reason; cancel leaf → empty `dependents_reevaluated`; cancel middle of diamond → only true dependents reported; cancel scheduled flight that frees crew/runway → previously unschedulable flight becomes scheduled (state change reported)

### Story 3.7: Determinism Property Test (100-Run Byte-Identical)

**As a** maintainer,
**I want** a property test that asserts the scheduling pipeline produces byte-identical output across many runs with identical input,
**So that** determinism (NFR-3, FR-SCH-6) is enforced automatically and any future regression is caught immediately.

**Acceptance Criteria** (FR-SCH-6, NFR-3, architecture determinism enforcement)

**Given** `generate_schedule` is fully wired (Stories 3.1–3.4)
**When** I run `tests/test_determinism.py`
**Then** the test builds a non-trivial fixture (≥ 10 flights, mixed priorities, at least one dependency chain, at least one runway-requirement-binding flight, configured to produce both scheduled and unschedulable outcomes)
**And** it calls `generate_schedule` 100 times, serializing the full output (placements, unscheduled, completion_time_seconds) to canonical JSON via `json.dumps(..., sort_keys=True, separators=(",", ":"))`
**And** all 100 serialized strings are byte-identical (asserted via set length == 1)
**And** the test also asserts byte-identical output for `atc://flights`, `atc://timeline`, `atc://runways` payloads across the same 100 iterations
**And** the test runs in under 5 seconds (lightweight per NFR-1)
**And** any introduction of `time.time()`, `datetime.now()`, `random`, or unsorted `set` iteration into `scheduler/` or `domain/` causes either `tests/test_imports.py` to fail or this test to fail

## Epic 4: Bottleneck Analysis, Validation & Project Delivery

**Goal:** An AI client can identify the longest active dependency chain. All three validation scenarios pass end-to-end. Project is fully documented per NFR-4 and is deliverable.

### Story 4.1: Bottleneck Chain Algorithm + `analyze_bottleneck` Tool

**As an** AI client,
**I want** to identify the longest active scheduled dependency chain with its total duration and per-operation/per-buffer breakdown,
**So that** I can pinpoint the critical path constraining airport throughput.

**Acceptance Criteria** (FR-TOOL-5, DD-9)

**Given** `bottleneck.py` exposes `longest_active_chain(state: AppState, config: Config) -> BottleneckResult`
**When** `AppState.latest_schedule` contains placements for flights whose `dependencies` form one or more chains
**Then** "active scheduled dependency chain" is defined as: ordered sequence of currently-`scheduled` (non-cancelled, non-unschedulable) flights where each consecutive pair `(f_i, f_{i+1})` satisfies `f_{i+1}.dependencies` contains `f_i.flight_number`
**And** chain duration = `f_n.end_sec - f_1.start_sec` (equivalent to `sum(operation_durations) + sum(dependency_buffers)`)
**And** "longest" tie-break selects the chain whose starting flight has the lex-smallest `flight_number`
**And** the `analyze_bottleneck` MCP tool returns `{chain: [<flight_number>, ...], total_duration_seconds: int, operation_durations: [int, ...], dependency_buffers: [int, ...]}` where `len(operation_durations) == len(chain)` and `len(dependency_buffers) == len(chain) - 1`
**And When** there is no schedule, or no scheduled flights have dependencies on other scheduled flights
**Then** the tool returns the architecture-pinned empty case: `{chain: [], total_duration_seconds: null, operation_durations: [], dependency_buffers: []}`
**And** repeated calls with identical state return byte-identical payloads
**And** `tests/test_bottleneck.py` covers: empty state; single scheduled flight (no chain); 2-chain; 3-chain; two equal-length chains → lex tie-break; chain broken by a cancelled middle flight (only contiguous scheduled segments count); chain broken by an unschedulable middle flight; diamond DAG (longest path through diamond wins)

### Story 4.2: VS-1 Morning Rush Acceptance Test

**As a** product stakeholder,
**I want** the end-to-end Morning Rush scenario from `spec.md §9` to pass automatically,
**So that** I have machine-checkable evidence the system handles mixed-priority arrivals/departures on a clean state.

**Acceptance Criteria** (VS-1)

**Given** `tests/test_vs1_morning_rush.py` spins up an MCP test client against the in-process server with a documented fixture config (recorded in the test docstring)
**When** the test submits a mix of arrivals and departures across `high`, `medium`, `low` priorities (≥ 6 flights, no dependencies, exercises at least one resource-contention point)
**And** invokes `generate_schedule`
**Then** every flight that can be scheduled IS scheduled (no false `unschedulable` outcomes)
**And** no two placements overlap on the same runway or same gate (asserted programmatically against `atc://timeline`)
**And** under contention, higher-priority flights have earlier `start_sec` than lower-priority same-runway peers (asserted)
**And** any unscheduled flights are reported in `get_airport_status.unscheduled_flights` with non-null reason strings
**And** the test runs deterministically (re-run 5 times in CI → identical assertions)

### Story 4.3: VS-2 Heavy Hauler Acceptance Test

**As a** product stakeholder,
**I want** the Heavy Hauler scenario from `spec.md §9` to pass automatically,
**So that** I have machine-checkable evidence the system reports runway-requirement failures without breaking other flights.

**Acceptance Criteria** (VS-2)

**Given** `tests/test_vs2_heavy_hauler.py` configures the server with runways of insufficient length for the heavy departure (e.g. `ATC_RUNWAYS=[{"id":"R1","length_m":3500},{"id":"R2","length_m":3000}]`) and submits a high-priority departure with `runway_requirements: {min_length_m: 4500}` plus 3+ other valid flights
**When** `generate_schedule` runs
**Then** the heavy flight ends in `state == unschedulable` with `unscheduled_reason` exactly matching the architecture-pinned pattern `"no runway meets minimum length 4500m (available runways: R1 3500m, R2 3000m)"`
**And** all other valid flights are scheduled normally (no collateral damage)
**And** `get_airport_status.unscheduled_flights` contains the heavy flight and only the heavy flight
**And** the test is deterministic

### Story 4.4: VS-3 Connecting Flight Acceptance Test

**As a** product stakeholder,
**I want** the Connecting Flight scenario from `spec.md §9` to pass automatically,
**So that** I have machine-checkable evidence the system correctly orders dependent operations.

**Acceptance Criteria** (VS-3)

**Given** `tests/test_vs3_connecting_flight.py` submits an inbound arrival `A1` and a dependent outbound departure `D1` with `dependencies: ["A1"]`
**When** `generate_schedule` runs
**Then** both flights are scheduled (resources allow)
**And** `D1.start_sec ≥ A1.end_sec + ATC_DEPENDENCY_BUFFER_SEC`
**And** `atc://timeline` lists `A1` before `D1` (sort by `start_sec`)
**And** `analyze_bottleneck` returns a chain containing `[A1, D1]` with the correct `operation_durations=[ATC_DURATION_ARRIVAL_SEC, ATC_DURATION_DEPARTURE_SEC]` and `dependency_buffers=[ATC_DEPENDENCY_BUFFER_SEC]`
**And** the test is deterministic

### Story 4.5: `README.md` — User-Facing Documentation

**As a** new user (or grader),
**I want** a single README that tells me everything I need to install, configure, run, connect to, and understand this server,
**So that** I can be productive in under five minutes.

**Acceptance Criteria** (NFR-4 README portion)

**Given** the project is feature-complete (Epics 1–3 done, Stories 4.1–4.4 done)
**When** I read `task-4/README.md`
**Then** it includes the following sections in order: (1) what this is (1-paragraph overview), (2) install / build steps (`pip install -e .[dev]`), (3) full environment variable reference (every `ATC_*` var with type, units, example value, validation rules), (4) run instructions (`python -m atc_mcp.server`), (5) how to connect an MCP-compatible client (with a concrete Claude Desktop or `mcp` CLI example), (6) full tool catalog (`submit_flight`, `generate_schedule`, `get_airport_status`, `cancel_flight`, `analyze_bottleneck` — each with one-line description, input schema summary, output shape summary), (7) full resource catalog (`atc://flights`, `atc://runways`, `atc://timeline` — each with one-line description and payload shape summary), (8) how to run the tests (`pytest -q`), (9) explicit non-features (from spec §11) to set expectations
**And** every env var listed in §3 matches exactly what `config.py` reads (no drift)
**And** every tool/resource listed in §6/§7 matches exactly what `server.py` registers (no drift)
**And** a quick manual cross-check confirms the README is sufficient to onboard without reading source code

### Story 4.6: `report.md` — Engineering Report

**As a** grader / future maintainer,
**I want** a written report explaining the scheduling approach, key decisions, tools used, and lessons learned,
**So that** the design rationale is captured alongside the code.

**Acceptance Criteria** (NFR-4 report portion)

**Given** the project is feature-complete
**When** I read `task-4/report.md`
**Then** it covers, with concrete references to architecture decisions: (1) **Scheduling approach** — the greedy deterministic placement algorithm, sort key, tie-break rules, constraint layering order, and why this beats alternatives for this problem size; (2) **Key decisions** — at minimum the 10 DDs from architecture (Python 3.11+, env-var contract with `ATC_` prefix, deferred-to-architect tool names, in-memory-only state, time-model with `t=0` epoch, integer-second granularity, durations from env, runway capability schema `{id, length_m}`, active chain definition, ground-crew shared capacity counter), each with a one-paragraph rationale; (3) **Tools/techniques used** — Pydantic v2 frozen models + `extra="forbid"`, official `mcp` SDK over stdio, deterministic sort keys, property-based determinism testing, import-direction enforcement test; (4) **What worked** — explicit, concrete; (5) **What didn't work** / open questions / future-scope items
**And** the report references specific tests as evidence (e.g. "determinism guaranteed by `tests/test_determinism.py`")
**And** the report is honest about limitations (no persistence, no auth, single-process, no quantitative SLAs)
