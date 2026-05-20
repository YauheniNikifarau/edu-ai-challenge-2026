    # Specification — Air Traffic Control MCP Server (task-4)

**Author:** Mary (Business Analyst)
**Date:** 2026-05-18
**Source:** `task-4/original-task` (single source of truth)
**Status:** Ready for architect handoff
**Scope discipline:** This spec restates and structures the original task. No requirement is added, removed, or weakened. Every item carries a traceability tag (`§OT:<lines>`) pointing back to the original task lines.

---

## 1. Purpose & Goal

Build a **lightweight Model Context Protocol (MCP) server** that acts as an **AI-ready Air Traffic Control system**, coordinating flight operations at a busy airport. The server must:

- Accept incoming flight plans. `§OT:4`
- Schedule arrivals and departures safely. `§OT:4`
- Manage limited airport resources. `§OT:4`
- React to disruptions. `§OT:4`
- Expose airport state to AI clients through MCP tools and resources. `§OT:4`

**Focus:** scheduling logic and coordination. `§OT:6`

---

## 2. Scope

### 2.1 In scope
- MCP server implementation. `§OT:2,4`
- Flight submission, scheduling, cancellation, status, and bottleneck analysis capabilities (see §5). `§OT:32–37`
- Inspection resources for queue, runway availability/usage, and operation timeline (see §6). `§OT:39–42`
- Environment-variable-driven airport configuration (see §4). `§OT:19–29`

### 2.2 Out of scope (explicit)
- **Visual interface.** `§OT:6`
- **Simulating real aircraft physics.** `§OT:6`

> Anything not listed in §3–§8 is **out of scope** for this task. The architect must not add features beyond what is specified here.

---

## 3. Domain Glossary

These terms appear in the original task and must be used consistently across architecture, code, README, and report. The architect may extend (not redefine) these.

| Term | Meaning (as used in original task) | Source |
|------|-------------------------------------|--------|
| Flight | Submittable unit with a flight number, operation type, priority, optional dependencies, optional runway requirements. | `§OT:11–17` |
| Operation type | One of: **arrival**, **departure**. | `§OT:13` |
| Priority | One of: **high**, **medium**, **low**. | `§OT:14` |
| Dependency | A relationship where one flight must not start before another has completed. | `§OT:15` |
| Runway requirement | Capability requirement a flight places on the runway it can use (the Heavy Hauler scenario uses runway *length capability* as an example). | `§OT:16, 67–76` |
| Runway / Gate / Ground crew | Limited airport resources with counts set by configuration. | `§OT:22–24` |
| Separation buffer | Configured time gap between consecutive runway operations, defined separately for takeoffs, landings, and mixed operations. | `§OT:25` |
| Gate turnaround time | Configured time a gate is occupied after a flight before reuse. | `§OT:26` |
| Dependency buffer time | Configured time gap enforced between a dependency's completion and its dependent flight's start. | `§OT:27` |
| Scheduling horizon | Maximum time window over which the scheduler will place operations. | `§OT:28` |
| Schedule | The computed plan placing flights on runways/gates over time. Replaced each time the schedule tool is invoked. | `§OT:34` |
| Bottleneck (dependency chain) | The longest active scheduled chain of dependent flights driving the total schedule duration. | `§OT:37, 101` |

---

## 4. Configuration Requirements

All airport limits **must** be loaded from environment variables. `§OT:19, 93`

### FR-CFG-1 — Required configuration values `§OT:21–28`
The server must accept (at minimum) configuration for:

| Key (concept) | Description | Source |
|---|---|---|
| Runway count | Number of runways available. | `§OT:22` |
| Gate count | Number of gates available. | `§OT:23` |
| Ground crew count | Ground crew capacity. | `§OT:24` |
| Runway separation buffer — takeoffs | Separation time between consecutive takeoffs on a runway. | `§OT:25` |
| Runway separation buffer — landings | Separation time between consecutive landings on a runway. | `§OT:25` |
| Runway separation buffer — mixed operations | Separation time when consecutive operations on a runway differ in type. | `§OT:25` |
| Gate turnaround time | Minimum gate occupancy/cleanup time. | `§OT:26` |
| Dependency buffer time | Minimum gap enforced between a dependency completion and a dependent flight start. | `§OT:27` |
| Maximum scheduling horizon | Upper bound for scheduling time window. | `§OT:28` |

### FR-CFG-2 — Startup validation `§OT:30`
Invalid configuration must cause the server to **fail clearly at startup** (clear error indicating which value is invalid and why).

> **Architect decision deferred:** exact env-var names, units (e.g., minutes vs. seconds), and accepted value ranges. See `plan.md §3 Decision DD-2`.

---

## 5. MCP Tools (Required Capabilities)

The server must expose MCP tools providing the following capabilities. **Tool names are at the architect's discretion** `§OT:44`; only the capabilities are mandatory.

### FR-TOOL-1 — Submit flight `§OT:33, 94`
Accepts a new arrival or departure submission carrying:
- Flight number. `§OT:12`
- Operation type (arrival | departure). `§OT:13`
- Priority (high | medium | low). `§OT:14`
- Dependencies (optional, list of flights this flight depends on). `§OT:15`
- Runway requirements (optional). `§OT:16`

### FR-TOOL-2 — Generate / refresh schedule `§OT:34`
Replaces the current schedule with a freshly computed one based on the current flight queue and current airport configuration.

Scheduling must satisfy all rules in §7.

### FR-TOOL-3 — Get airport status `§OT:35, 100`
Returns a structured operational status derived from current airport state, including:

- Flight counts by **state** and by **operation type**. `§OT:100`
- Runway and gate **capacity** and **usage**. `§OT:100`
- Resource constraint indicators. `§OT:100`
- Unscheduled or blocked flights with reasons. `§OT:100`
- Current schedule completion time when available. `§OT:100`

### FR-TOOL-4 — Cancel flight `§OT:36, 99`
Cancels a flight and causes dependent operations to be re-evaluated:
- The flight is marked as cancelled. `§OT:99`
- Dependent flights are re-evaluated in light of the cancellation. `§OT:99`

### FR-TOOL-5 — Bottleneck analysis `§OT:37, 101`
Identifies the **longest active scheduled dependency chain**, if one exists. Result must include:

- The ordered flights in the chain. `§OT:101`
- The total elapsed duration based on the generated schedule, **accounting for operation durations and required dependency buffers**. `§OT:101`

---

## 6. MCP Resources (Required Inspection Surfaces)

The server must expose MCP resources for inspection. **Resource names are at the architect's discretion** `§OT:44`; only the capabilities are mandatory.

### FR-RES-1 — Flight queue `§OT:40`
Exposes the current flight queue, including **unscheduled** and **cancelled** flights.

### FR-RES-2 — Runway availability and usage `§OT:41`
Exposes runway availability and usage information.

### FR-RES-3 — Operation timeline `§OT:42`
Exposes a chronological timeline of scheduled airport operations.

---

## 7. Scheduling Rules (Behavioral Requirements)

The scheduler must obey **all** of the following rules:

### FR-SCH-1 — No resource overlap `§OT:95`
Scheduling avoids overlapping usage of the **same runway** or **same gate**.

### FR-SCH-2 — Constraint compliance `§OT:96`
Scheduling respects:
- Runway requirements. `§OT:96`
- Gate availability. `§OT:96`
- Separation buffers (takeoffs, landings, mixed). `§OT:25, 96`
- Dependency buffers. `§OT:27, 96`
- Airport capacity limits. `§OT:96`

### FR-SCH-3 — Priority ordering under contention `§OT:97`
When resources are constrained, higher-priority flights must be scheduled earlier where possible.

### FR-SCH-4 — Unschedulable visibility `§OT:98`
Flights that cannot be scheduled must remain visible with a **clear reason**.

### FR-SCH-5 — Dependency ordering `§OT:15, 87, 101`
A dependent flight must not start before its dependency has completed; the configured dependency buffer must be applied between them.

### FR-SCH-6 — Determinism `§OT:102`
Repeated scheduling with the same inputs and configuration must produce **deterministic results**.

### FR-SCH-7 — Cancellation cascade `§OT:99`
Cancelling a flight marks it as cancelled and causes dependent operations to be re-evaluated.

---

## 8. Non-Functional Requirements

### NFR-1 — Lightweight `§OT:4`
The server is described as "lightweight." No additional NFR (performance targets, scale, latency) is specified in the original task; the architect must not invent quantitative targets beyond this qualitative directive.

### NFR-2 — Startup correctness `§OT:30, 92`
Server starts successfully when configuration is valid; all tools and resources are accessible from a connected MCP client.

### NFR-3 — Determinism `§OT:102`
See FR-SCH-6.

### NFR-4 — Documentation coverage `§OT:44, 106`
- Tool and resource capabilities must be clearly documented.
- README must enumerate all exposed tools and resources with short descriptions, all env vars and their accepted values, install/build steps, run steps, and how to connect an MCP-compatible client.

### NFR-5 — Compatibility `§OT:44, 92`
The server must be usable from an MCP-compatible client; tools and resources must be discoverable/accessible per the MCP specification.

---

## 9. Validation Scenarios (Acceptance Criteria from the Source)

These three scenarios are **mandatory** acceptance tests. The architect must ensure the design can satisfy each; the implementer must demonstrate each passes.

### VS-1 — Morning Rush `§OT:48–64`
**Setup:** clean airport state.
**Submit:**
- 1× high-priority arrival
- 1× medium-priority departure
- 1× low-priority arrival
- 1× low-priority departure

**Steps:** generate schedule → inspect flight queue → inspect operation timeline.

**Expected:**
- All schedulable flights scheduled.
- No runway or gate has overlapping operations.
- Higher-priority flights scheduled earlier when resources are contested.
- Queue clearly indicates any unscheduled flights.

### VS-2 — Heavy Hauler `§OT:65–76`
**Setup:** clean airport state.
**Submit:** 1× high-priority departure requiring a runway longer than any available runway.
**Steps:** generate schedule → inspect queue and airport status.

**Expected:**
- The oversized flight is **not** scheduled.
- The flight remains visible with unscheduled status.
- The reason clearly indicates "no suitable runway available."
- Other valid flights (if present) remain schedulable.

### VS-3 — Connecting Flight `§OT:77–89`
**Setup:** clean airport state.
**Submit:** 1× inbound arrival, then 1× outbound departure depending on the inbound.
**Steps:** generate schedule → inspect operation timeline.

**Expected:**
- Both flights scheduled if resources are available.
- Outbound does **not** start before inbound has completed.
- Configured dependency buffer is respected.
- Timeline makes the dependency order clear.

> The original task also says: *"Think about other validation scenarios as well to make sure your MCP server covers all the requirements and works as expected."* `§OT:47`
> **Architect note:** Additional scenarios are at the implementer's discretion **only as test coverage** — they must not introduce new product requirements.

---

## 10. Submission Artifacts (Repository Deliverables) `§OT:103–108`

The repository must include:

| Artifact | Required contents | Source |
|---|---|---|
| Source code | Located in a `task-4` folder. | `§OT:105` |
| `README.md` | Install/build instructions; all env vars and accepted values; how to run and connect from an MCP-compatible client; reference of all exposed tools and resources with short descriptions. | `§OT:106` |
| `report.md` | Scheduling approach and key decisions behind it; tools and techniques used; what worked and what did not. | `§OT:107` |
| Public repo | Repository must be public. | `§OT:108` |

---

## 11. Explicit Non-Requirements (Guardrails Against Scope Creep)

The original task does **not** require any of the following. The architect must not add them unless the user later expands scope:

- Authentication / authorization / multi-tenant isolation.
- Persistence across restarts (not stated either way; flagged as deferred — see `plan.md DD-5`).
- Audit logs, metrics dashboards, monitoring stacks.
- Web UI, CLI client, or visualization (UI is explicitly out of scope per `§OT:6`).
- Aircraft physics, weather modelling, real-time radar/ADS-B integration (physics simulation explicitly out of scope per `§OT:6`).
- Quantitative SLAs (throughput, latency, concurrent client targets) — not stated; only "lightweight" qualitative descriptor given.
- Internationalization, accessibility (no human UI exists).
- External integrations beyond MCP.

---

## 12. Traceability Matrix

Every spec section maps to original-task lines; conversely every original-task requirement has at least one spec section.

| Original-task line(s) | Topic | Spec section |
|---|---|---|
| 2, 4, 6 | Purpose, scope, focus | §1, §2 |
| 9 | Anyone can submit flights | §5 FR-TOOL-1 |
| 11–17 | Flight attributes (incl. optional deps, runway reqs) | §3 Glossary, §5 FR-TOOL-1 |
| 19, 21–29 | Env-var configuration | §4 FR-CFG-1 |
| 30 | Fail-fast startup validation | §4 FR-CFG-2, NFR-2 |
| 32–37 | MCP tools list (submit, schedule, status, cancel, bottleneck) | §5 FR-TOOL-1..5 |
| 39–42 | MCP resources (queue, runway info, timeline) | §6 FR-RES-1..3 |
| 44 | Tool/resource/data-structure naming flexibility, documentation | §5, §6 (architect deferred), NFR-4 |
| 47 | Optional additional validation scenarios | §9 (architect note) |
| 48–64 | Scenario 1: Morning Rush | §9 VS-1 |
| 65–76 | Scenario 2: Heavy Hauler | §9 VS-2 |
| 77–89 | Scenario 3: Connecting Flight | §9 VS-3 |
| 92 | Server starts, all tools/resources accessible | NFR-2, NFR-5 |
| 93 | Limits loaded from env vars | §4 FR-CFG-1 |
| 94 | Submit arrivals/departures with priorities and deps | §5 FR-TOOL-1 |
| 95 | No overlapping runway/gate usage | §7 FR-SCH-1 |
| 96 | Constraint compliance | §7 FR-SCH-2 |
| 97 | Priority ordering under contention | §7 FR-SCH-3 |
| 98 | Unschedulable flights visible with reason | §7 FR-SCH-4 |
| 99 | Cancellation cascade | §5 FR-TOOL-4, §7 FR-SCH-7 |
| 100 | Airport status payload contents | §5 FR-TOOL-3 |
| 101 | Bottleneck analysis output | §5 FR-TOOL-5 |
| 102 | Deterministic scheduling | §7 FR-SCH-6, NFR-3 |
| 103–108 | Submission artifacts | §10 |

---

## 13. Definition of Done (Spec-Level)

This spec is complete when, and only when, **all** rows in the traceability matrix (§12) are satisfied by the architect's design and the implementer's code. Any deviation must be explicitly approved by the user before merging.