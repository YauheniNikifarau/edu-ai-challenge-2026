# Plan — Analyst → Architect Handoff (task-4)

**Author:** Mary (Business Analyst)
**Date:** 2026-05-18
**Companion spec:** `_bmad-output/planning-artifacts/spec.md` (single source of truth for *what*)
**This document:** the *handoff* — who does what next, which decisions are open, what risks to watch, and what "done" looks like at each gate.

> **Scope guardrail:** This plan does **not** add product requirements. It only sequences the work and flags decisions the original task explicitly or implicitly leaves to the implementer. If a section appears to imply a new requirement, treat it as an error and reconcile against `spec.md` §12 (traceability matrix).

---

## 1. Handoff Status

| Phase | Owner | Status | Output |
|---|---|---|---|
| Analysis (this phase) | Mary (Analyst) | ✅ Complete | `spec.md`, `plan.md` |
| Architecture | Architect (next) | ⏳ Pending | See §4 below |
| Implementation | Developer | ⏳ Not started | Source code under `task-4/`, README, report |
| Validation | Developer / QA | ⏳ Not started | Demonstrated VS-1, VS-2, VS-3 (`spec.md §9`) |

**Hand to the architect:** `spec.md` + this `plan.md` + `original-task` (for back-reference).

---

## 2. What the Architect Must Read First

1. `original-task` — the ground truth.
2. `spec.md` — structured restatement; pay particular attention to the **traceability matrix (§12)** and **explicit non-requirements (§11)**.
3. This `plan.md` — for the open decisions in §3 below.

If the architect believes any requirement is missing, ambiguous, or contradictory, the resolution path is: **ask the user**. Do not silently add requirements.

---

## 3. Deferred Decisions (Owned by the Architect)

These are choices the original task does **not** specify. The architect must record each decision (e.g., as ADRs or in the architecture document) and ensure consistency with `spec.md`.

### DD-1 — Tool names, resource names, data structures
- **Why deferred:** `§OT:44` explicitly delegates naming and data structures to the implementer.
- **Constraint:** capabilities in `spec.md §5–§6` must be fully covered and clearly documented.
- **Architect must produce:** the complete catalog of tool names, input/output schemas, resource URIs/names, and shared data structures (flight, schedule entry, runway, gate, etc.).

### DD-2 — Environment variable names, units, accepted ranges
- **Why deferred:** original task names the configuration **concepts** (`§OT:21–28`) but not env-var keys, units, or ranges.
- **Constraint:** must cover every concept in `spec.md §4 FR-CFG-1`; invalid configs must fail at startup with a clear message (`§OT:30`).
- **Architect must produce:** env-var contract (name, type, unit, default if any, accepted range, failure message shape).

### DD-3 — Tech stack
- **Why deferred:** original task does not specify language, runtime, MCP SDK, or build tooling.
- **Constraint:** server must be lightweight (`§OT:4`) and usable from an MCP-compatible client (`§OT:44, 92`).
- **Architect must produce:** language/runtime/SDK choice with rationale, build/install steps that will land in the README (`§OT:106`).

### DD-4 — Scheduling algorithm
- **Why deferred:** original task specifies scheduling **rules** (`§OT:95–98, 102`) but not the algorithm.
- **Hard constraints the algorithm must satisfy (from `spec.md §7`):**
  - FR-SCH-1: no runway/gate overlap.
  - FR-SCH-2: respects runway requirements, gate availability, separation buffers (takeoff/landing/mixed), dependency buffers, and airport capacity limits.
  - FR-SCH-3: higher priority earlier when resources are contested.
  - FR-SCH-4: unschedulable flights remain visible with a clear reason.
  - FR-SCH-5: dependency ordering with configured dependency buffer.
  - FR-SCH-6: deterministic results for identical inputs and configuration.
  - FR-SCH-7: cancellation cascades to dependents.
- **Architect must produce:** algorithmic approach + tie-break policy (priority tie-breaking, equal-time placement) that demonstrably yields determinism.

### DD-5 — State persistence
- **Why deferred:** original task is silent on persistence across restarts.
- **Recommendation:** assume **in-memory** state unless the user explicitly expands scope. Do not introduce a database without authorization.
- **Architect must produce:** an explicit statement of where state lives and what happens on restart.

### DD-6 — Time representation
- **Why deferred:** original task uses scheduling time concepts (horizon, buffers, completion time, timeline) but does not fix a time model.
- **Architect must produce:** decision on epoch anchor (wall clock vs. logical time at "now"), granularity (e.g., seconds vs. minutes), and how the timeline resource expresses time.

### DD-7 — Operation durations
- **Why deferred:** `§OT:101` requires the bottleneck analysis to account for **operation durations**, but the original task does not state how durations are determined.
- **Architect must produce:** a single, documented source of truth for operation duration (e.g., fixed per operation type via config, per-flight, or other). This must integrate with `spec.md §4` configuration concepts without inventing user-facing requirements.

### DD-8 — Runway capability schema
- **Why deferred:** `§OT:16` mentions "runway requirements (optional)"; `§OT:67–76` (VS-2 Heavy Hauler) implies runway *length capability* is one such requirement.
- **Architect must produce:** the data schema for runway capabilities and the matching schema for a flight's runway requirements, sufficient for VS-2 to pass deterministically.

### DD-9 — "Active scheduled dependency chain"
- **Why deferred:** `§OT:101` requires the bottleneck analysis to surface the longest **active scheduled** dependency chain. "Active scheduled" is not defined.
- **Architect must produce:** a precise definition (e.g., chains restricted to currently scheduled, non-cancelled flights), recorded in the architecture document, and reflected in the tool's response schema.

### DD-10 — Ground crew semantics in scheduling
- **Why deferred:** `§OT:24` lists ground crew count among airport limits; `§OT:96` requires scheduling to respect airport capacity limits. The original task does not state how ground crew demand attaches to operations.
- **Architect must produce:** a definition of how ground crew capacity gates scheduling (e.g., concurrent-operation cap from ground crew), consistent with FR-SCH-2 and reportable via airport status (FR-TOOL-3).

> **Rule for all DD-x decisions:** the architect's choice must be *minimal* — sufficient to satisfy `spec.md`, no more. If a decision would introduce new user-facing requirements, escalate to the user instead.

---

## 4. Expected Architect Deliverables

The architect's output must enable a developer to implement without re-reading the original task. Produce, at minimum:

1. **Architecture document** in `_bmad-output/planning-artifacts/` (e.g., `architecture.md`) covering:
   - Tech stack + rationale (DD-3).
   - Component decomposition (e.g., MCP transport layer, configuration loader, flight queue, scheduler, status reporter, bottleneck analyzer, resource/timeline projector).
   - Data model: flight, runway, gate, ground crew slot, schedule entry, timeline event, status payload, bottleneck result.
   - MCP tool catalog with full input/output schemas (resolves DD-1).
   - MCP resource catalog with URIs and payload shapes (resolves DD-1).
   - Environment variable contract (resolves DD-2).
   - Scheduling algorithm description with determinism argument (resolves DD-4).
   - State/persistence statement (resolves DD-5).
   - Time model (resolves DD-6).
   - Operation duration source (resolves DD-7).
   - Runway capability schema (resolves DD-8).
   - "Active scheduled dependency chain" definition (resolves DD-9).
   - Ground crew scheduling semantics (resolves DD-10).
   - Startup validation contract (which env vars trigger which clear errors).
   - Cancellation re-evaluation flow (FR-SCH-7).

2. **Sequence / flow descriptions** for the three mandatory scenarios in `spec.md §9` (VS-1, VS-2, VS-3) showing how the chosen design produces the expected outcomes.

3. **Traceability check**: a short section verifying each row of `spec.md §12` is addressed in the architecture. If a row cannot be addressed, escalate to the user.

4. **Test plan outline** (not test code): the validation scenarios from `spec.md §9` plus any additional coverage scenarios the architect considers necessary, with the explicit note that additional scenarios are **test coverage only**, not new product requirements (`§OT:47`).

5. **README.md outline** (structure only, content to be filled by implementer): aligned with `§OT:106` requirements.

6. **Report.md outline** (structure only): aligned with `§OT:107` requirements.

---

## 5. Sequencing

```
[Analyst]  ──►  [Architect]  ──►  [Developer]  ──►  [Validation]
  done           next             after design        after impl
```

Gate from Architect → Developer: every DD-x in §3 resolved and every row in `spec.md §12` traceable in the architecture document.

Gate from Developer → Done: VS-1, VS-2, VS-3 demonstrably pass; README and report.md complete per `§OT:106–107`; repo public per `§OT:108`.

---

## 6. Risks & Watch-Outs (For the Architect)

| ID | Risk | Mitigation |
|---|---|---|
| R-1 | Non-determinism slipping in via map/set iteration order, time-based RNG, or floating-point. | Choose data structures and tie-break rules that make ordering explicit; document the determinism argument (DD-4). |
| R-2 | Over-engineering — adding auth, persistence, metrics, UI not in the original task. | Cross-check every component against `spec.md §11` (Explicit Non-Requirements). |
| R-3 | Silent reinterpretation of ambiguous terms (e.g., "active scheduled dependency chain"). | Capture every interpretive choice as a DD-x decision in the architecture doc. |
| R-4 | Status payload missing one of the five required pieces (`spec.md §5 FR-TOOL-3` / `§OT:100`). | Build the status payload schema directly from the FR-TOOL-3 bullet list; cross-check. |
| R-5 | Cancellation does not re-evaluate dependents (`§OT:99`). | Define the cancellation flow explicitly; include in scenario coverage. |
| R-6 | Unschedulable flights losing their reason (`§OT:98, 75`). | Reason strings must be modelled as first-class fields on flight state, not log-only. |
| R-7 | Bottleneck analysis ignoring buffers (`§OT:101`). | Include dependency-buffer accounting in the bottleneck calculation; assert in tests. |
| R-8 | Configuration silently defaulting on invalid input (`§OT:30`). | Implement fail-fast startup with explicit error per offending variable. |

---

## 7. Open Questions for the User (if architect cannot decide alone)

These are questions the architect may need answered by the user **only if** they materially affect the design beyond what `spec.md` constrains. The analyst position is: don't ask unless blocked.

- Q-1: Is in-memory state acceptable, or is restart-survivability required? *(Default assumption: in-memory; flagged in DD-5.)*
- Q-2: Are there preferred languages, runtimes, or MCP SDKs the user wants used? *(If none stated, architect chooses per DD-3.)*
- Q-3: Should operation durations be configurable per operation type, or fixed defaults? *(Architect to pick the minimal model; user only needed if DD-7 has a strong preference.)*

The architect should **not** broaden these into a requirements-gathering session. The goal is to unblock design with the minimum change set against `spec.md`.

---

## 8. Definition of Done (Plan-Level)

This handoff is "done" when:

- [x] `spec.md` exists and traces every requirement back to `original-task`.
- [x] `plan.md` exists and lists every deferred decision the architect must make.
- [ ] Architect has read both, produced the deliverables in §4, and resolved every DD-x in §3.
- [ ] Architect has confirmed (in writing) that no row of `spec.md §12` is unaddressed.

The first two are complete with this commit. The rest pass to the architect.

---

## 9. Quick Index

- Requirements: `spec.md §4–§7`
- Acceptance scenarios: `spec.md §9`
- Submission artifacts: `spec.md §10`
- Things we are **not** building: `spec.md §11`
- Deferred decisions: this doc §3
- Architect deliverables: this doc §4
- Risks: this doc §6