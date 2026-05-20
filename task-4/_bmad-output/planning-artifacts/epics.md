---
stepsCompleted: [1]
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

{{requirements_coverage_map}}

## Epic List

{{epics_list}}
