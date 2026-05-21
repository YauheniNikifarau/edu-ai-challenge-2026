---
story_id: "4.6"
story_key: "4-6-report-md-engineering-report"
epic: "Epic 4: Bottleneck Analysis, Validation & Project Delivery"
title: "`report.md` — Engineering Report"
status: "ready-for-dev"
created: "2026-05-21"
dependencies: ["4.1", "4.2", "4.3", "4.4", "4.5"]
---

# Story 4.6: `report.md` — Engineering Report

## User Story

**As a** grader / future maintainer,
**I want** a written report explaining the scheduling approach, key decisions, tools used, and lessons learned,
**So that** the design rationale is captured alongside the code.

## Acceptance Criteria

1. **Given** the project is feature-complete (Epics 1–3 done, Stories 4.1–4.5 done)  
   **When** I read `task-4/report.md`  
   **Then** it contains all five required sections below:

   **(1) Scheduling approach** — describes the deterministic greedy constructive placement algorithm: sort key `(topo_depth, priority_rank, flight_number)`, tie-break by `(runway_id, gate_id)` lex, constraint layering order (runway filter → floor start from deps → earliest (R,G) with separation/turnaround/crew/horizon), and an explicit argument for why greedy-constructive beats alternatives (LP/ILP, backtracking) at this problem scale.

   **(2) Key decisions** — covers **all ten architectural DDs** (DD-1 through DD-10), each with a one-paragraph rationale that references the decision:
   - DD-1: Tool & resource catalog — snake_case names, exact input/output shapes pinned
   - DD-2: Env-var contract — `ATC_` prefix, all required, `CONFIG ERROR:` format
   - DD-3: Tech stack — Python 3.11+, official `mcp` SDK, stdio transport, Pydantic v2
   - DD-4: Scheduling algorithm — greedy deterministic constructive with explicit tie-break
   - DD-5: State persistence — in-memory only; single seam at `domain/state.py`
   - DD-6: Time model — relative epoch `t=0`, integer seconds, no wall-clock reads
   - DD-7: Operation duration source — two env vars (`ATC_DURATION_ARRIVAL_SEC`, `ATC_DURATION_DEPARTURE_SEC`); no per-flight override
   - DD-8: Runway capability schema — `{id, length_m}` JSON array; `min_length_m` on flight
   - DD-9: Active scheduled dependency chain definition — only `scheduled` non-cancelled flights; chain duration = `end_n - start_1`; lex tie-break on starting flight
   - DD-10: Ground-crew shared capacity counter — one unit per concurrent operation; constraint layered into the placement loop

   **(3) Tools/techniques used** — covers: Pydantic v2 frozen models + `extra="forbid"` for both config and domain types; official `mcp` SDK over stdio; deterministic sort keys (total order prevents any hash/set non-determinism); property-based determinism test (`tests/test_determinism.py` — 100 byte-identical runs); import-direction enforcement test (`tests/test_imports.py` — AST-level checks that `domain/` and `scheduler/` never import `mcp` or `os`).

   **(4) What worked** — explicit and concrete (e.g., relative-time epoch eliminating all wall-clock non-determinism; Pydantic `ConfigDict(frozen=True)` catching accidental mutation at runtime; `tests/test_imports.py` catching cross-layer boundary violations early; property test catching subtle ordering bugs introduced during development).

   **(5) What didn't work / open questions / future-scope** — honest about at least: in-memory-only state (restart resets everything); no persistence, no auth, no quantitative SLAs; single-process model limits throughput; future work could include WebSocket transport, persistent store via `domain/state.py` seam, per-flight duration overrides.

2. **And** the report references specific tests as evidence (e.g., `"determinism is guaranteed by tests/test_determinism.py"`, `"import discipline enforced by tests/test_imports.py"`).

3. **And** the report is honest about limitations: no persistence across restarts, no authentication/authorisation, single-process in-memory, no quantitative SLAs, no UI.

4. **And** every architecture decision reference (DD-N) cites the source file `_bmad-output/planning-artifacts/architecture.md`.

5. **And** the report does **not** invent requirements or decisions not present in `spec.md`, `architecture.md`, or `epics.md`.

## Tasks / Subtasks

- [ ] Create `task-4/report.md` (AC: 1–5)
  - [ ] Write Section 1 — Scheduling Approach
  - [ ] Write Section 2 — Key Decisions (all 10 DDs, one paragraph each)
  - [ ] Write Section 3 — Tools / Techniques Used
  - [ ] Write Section 4 — What Worked
  - [ ] Write Section 5 — What Didn't Work / Open Questions / Future Scope
  - [ ] Add test citations as evidence throughout
  - [ ] Proof-read for accuracy against `architecture.md` (no invented claims)

## Dev Notes

### Nature of This Story

**Pure documentation task.** No Python source changes, no new tests, no modifications to existing tests. The only deliverable is `task-4/report.md` (markdown, placed at the project root alongside `README.md`).

### Report Structure (Required Sections in Order)

The report MUST contain these five sections at minimum. Additional subsections are allowed; do not reorder or omit.

```
# Air Traffic Control MCP Server — Engineering Report

## 1. Scheduling Approach
## 2. Key Decisions
### DD-1 ... through DD-10 (subsections)
## 3. Tools and Techniques
## 4. What Worked
## 5. What Didn't Work / Open Questions / Future Scope
```

### Section 1 — Scheduling Approach: Required Content Points

Source: `_bmad-output/planning-artifacts/architecture.md §Scheduling Algorithm (resolves DD-4)`

- Algorithm type: **deterministic greedy constructive placement** — not backtracking, not LP/ILP.
- Sort key: `(topo_depth, priority_rank, flight_number)` — three-part total order guaranteeing determinism.
  - `topo_depth`: ensures dependencies always placed before dependents.
  - `priority_rank`: `high=0, medium=1, low=2` — higher priority wins under contention.
  - `flight_number`: lex tie-break — unique, stable, deterministic.
- Placement loop: for each flight in sort order, find earliest `(runway, gate)` pair (lex ascending by `(R.id, G.id)`) such that ALL constraints are satisfied simultaneously:
  1. Runway capability (`min_length_m` match)
  2. Dependency floor (`dep.end_sec + ATC_DEPENDENCY_BUFFER_SEC`)
  3. Runway separation (takeoff/landing/mixed flavour from op-type pair)
  4. Gate turnaround (`ATC_GATE_TURNAROUND_SEC` on gate boundary)
  5. Ground-crew capacity (concurrent operations ≤ `ATC_GROUND_CREW_COUNT`)
  6. Scheduling horizon (`start + duration ≤ ATC_SCHEDULING_HORIZON_SEC`)
- Cycle detection: DFS on dependency graph before placement; all flights in a cycle are marked `unschedulable` with reason `"dependency cycle: <sorted lex flight numbers>"`.
- Why not LP/ILP: overkill for this scale; adds a solver dependency conflicting with NFR-1 (lightweight, minimal deps); greedy is O(n²) worst-case, entirely adequate.
- Why not backtracking: non-deterministic performance; the greedy constructive approach is sufficient because priority-ordered placement already satisfies FR-SCH-3; backtracking would only be needed to prove global optimality, which is not a requirement.

### Section 2 — Key Decisions: Required Content per DD

Source: `_bmad-output/planning-artifacts/architecture.md` — each DD subsection.

| DD | One-sentence summary | Key rationale to include |
|----|----------------------|--------------------------|
| DD-1 | Tool & resource catalog | Exact input/output JSON shapes pinned upfront prevents drift between tools.py, resources.py, and tests; snake_case matches Python idiom avoiding alias layers |
| DD-2 | Env-var contract | All-required (no silent defaults) + single `CONFIG ERROR:` format makes misconfiguration immediately diagnosable; `ATC_` prefix prevents collision with OS/container vars |
| DD-3 | Tech stack | Python 3.11+ for insertion-ordered dicts (determinism); official `mcp` SDK = reference implementation; stdio = canonical for local MCP servers, zero network surface |
| DD-4 | Scheduling algorithm | Greedy constructive is trivially deterministic and sufficient; total sort order is the key insight — it collapses a multi-constraint problem into a single linear pass |
| DD-5 | In-memory state | `spec.md §11` lists persistence as a non-requirement; single seam at `domain/state.py` isolates the state boundary for future expansion |
| DD-6 | Time model | Relative `t=0` epoch eliminates wall-clock as a non-deterministic input; integer seconds avoids all float precision issues; `time_model.py` is the single source of truth |
| DD-7 | Duration from env vars | Durations determined solely by operation type (`ATC_DURATION_ARRIVAL_SEC` / `ATC_DURATION_DEPARTURE_SEC`); per-flight override not in `spec.md` — not added |
| DD-8 | Runway capability schema | `{id, length_m}` is minimal and sufficient for VS-2 (Heavy Hauler); collapses runway-count + capability into one env var, avoiding count/capability inconsistency |
| DD-9 | Active chain definition | "Scheduled non-cancelled only" is the only definition consistent with FR-TOOL-5 intent; lex tie-break on starting flight ensures determinism when chains tie on duration |
| DD-10 | Ground-crew semantics | Shared capacity counter (one unit per concurrent operation) is simple, auditable, and directly reportable via `ground_crew: {capacity, in_use_peak, in_use_at_completion}` in `get_airport_status` |

### Section 3 — Tools/Techniques: Required Content Points

- **Pydantic v2 frozen models** (`ConfigDict(frozen=True, extra="forbid")`): config and domain value types; catches accidental mutation at runtime; `extra="forbid"` rejects unknown tool input fields at the MCP layer — cite `domain/models.py`, `config.py`.
- **Official `mcp` SDK over stdio**: tools registered via `@server.tool()`, resources via `@server.resource()` — cite `server.py`, `tools.py`, `resources.py`.
- **Deterministic sort keys**: every list returned to MCP is explicitly sorted before emission (sort keys documented per list in `architecture.md §Ordering Patterns`) — eliminates Python set/dict hash non-determinism.
- **Property-based determinism test**: `tests/test_determinism.py` — builds a ≥10-flight fixture with mixed priorities, at least one dependency chain, at least one runway-requirement-binding flight; calls `generate_schedule` 100 times; asserts all serialised outputs byte-identical via `json.dumps(..., sort_keys=True, separators=(",", ":"))`.
- **Import-direction enforcement test**: `tests/test_imports.py` — AST-parses every `domain/` and `scheduler/` source file; asserts zero imports of `mcp`, `os`, `time`, `datetime`, `random`; catches cross-layer violations at CI time.

### Section 4 — What Worked: Concrete Examples to Reference

These are real outcomes from the implementation; use these as the basis for the section:
- **Relative-time epoch** (DD-6): eliminating wall-clock from the scheduler removed the single biggest source of non-determinism before any code was written.
- **Pydantic `ConfigDict(frozen=True)`**: caught several accidental mutations during development at runtime rather than at debugging time.
- **`tests/test_imports.py` (AST-level import checks)**: prevented `domain/` modules from accidentally pulling in `mcp` SDK symbols during refactors.
- **Single re-evaluation path for cancellation** (cancel → internal `generate_schedule` call): keeps the state machine simple; `dependents_reevaluated` diff is computed by comparing flight states before/after the re-run.
- **All-required env vars** (DD-2): the `CONFIG ERROR:` format immediately surfaced misconfiguration in integration tests without digging through tracebacks.

### Section 5 — What Didn't Work / Limitations: Required Honesty Points

The following limitations MUST be acknowledged (do not omit any):
- **No persistence across restarts**: all flight state and schedules are lost on server restart. `spec.md §11` lists this as a non-requirement; the seam is `domain/state.py`.
- **No authentication/authorisation**: any connected MCP client can submit, cancel, or reschedule flights. `spec.md §11` explicitly excludes auth.
- **Single-process, single-threaded model**: no concurrent request handling; adequate for local/demo use, not production.
- **No quantitative performance SLAs**: NFR-1 says "lightweight" with no numeric targets; scheduler is O(n²) worst-case (n = number of flights × runway/gate combinations).
- **No per-flight duration overrides**: durations are operation-type-level only (DD-7); a future extension would add `duration_sec` to `submit_flight` input.
- **Ground-crew model is a simplified counter**: does not model crew skill levels, crew rest periods, or crew assignment to specific flight types.

### File to Create

**NEW:** `task-4/report.md`

Place at the project root (`task-4/`), alongside `README.md`. This is a **markdown** file. No code, no tests.

### Architecture Sources

All claims in the report must be traceable to:
- `_bmad-output/planning-artifacts/architecture.md` — for DD-1 through DD-10, scheduling algorithm, time model, env-var contract
- `_bmad-output/planning-artifacts/epics.md` — for FR/NFR references
- `_bmad-output/planning-artifacts/spec.md` — for explicit non-requirements (§11)

Do **not** invent capabilities, decisions, or requirements that are not in these documents.

### Test Evidence Citations (Required in Report)

The report must cite these tests by file name as evidence:

| Claim | Test file |
|-------|-----------|
| Determinism guaranteed across 100 runs | `tests/test_determinism.py` |
| Import discipline enforced (domain/scheduler layers) | `tests/test_imports.py` |
| Config fail-fast with exact error format | `tests/test_config.py`, `tests/test_config_failure_exit.py` |
| Runway-requirement failure (VS-2 Heavy Hauler) | `tests/test_vs2_heavy_hauler.py` |
| Dependency ordering with buffer (VS-3 Connecting Flight) | `tests/test_vs3_connecting_flight.py` |
| Mixed-priority scheduling (VS-1 Morning Rush) | `tests/test_vs1_morning_rush.py` |
| Bottleneck chain computation | `tests/test_bottleneck.py` |
| Cancellation cascade re-evaluation | `tests/test_cancel_reevaluation.py` |

### What NOT to Include

Per `spec.md §11` (explicit non-requirements) — **do not describe or imply** these as features:
- Authentication / multi-tenant isolation
- Persistence across restarts (beyond acknowledging it as a known limitation)
- Audit logs / metrics dashboards / monitoring
- Web UI / CLI client / visualisation
- Aircraft physics / weather / radar simulation
- Quantitative SLAs / throughput numbers
- i18n / accessibility
- External integrations beyond MCP

### Project Structure Notes

- Output file: `task-4/report.md` (root of the task-4 folder, same level as `README.md` and `pyproject.toml`)
- No source code files modified
- No test files created or modified
- `report.md` is referenced in `README.md` (Story 4.5) — ensure the filename matches exactly

### References

- `_bmad-output/planning-artifacts/architecture.md` — DD-1 through DD-10, scheduling algorithm, time model, env-var contract, resource catalog
- `_bmad-output/planning-artifacts/epics.md` — Epic 4 story 4.6 acceptance criteria; FR/NFR coverage map
- `_bmad-output/planning-artifacts/spec.md` — NFR-4 (documentation), §11 non-requirements
- `src/atc_mcp/` — all source modules (reference by name in report as needed)
- `tests/` — test files to cite as evidence

## Dev Agent Record

### Agent Model Used

_to be filled by dev agent_

### Debug Log References

### Completion Notes List

### File List

- `task-4/report.md` — created

### Change Log

- 2026-05-21: Story created

---

**Story Status:** ready-for-dev  
**Last Updated:** 2026-05-21  
**Context Engine:** Ultimate BMad Method story context completed
