# Architect Kick-off Brief — task-4 (ATC MCP Server)

> Paste this verbatim into the architect's session (or hand it to Winston via `bmad-agent-architect`). It is self-contained: a fresh agent should be able to start work from this brief alone.

---

## Mission

Design the architecture for a **lightweight Model Context Protocol (MCP) server** that acts as an **AI-ready Air Traffic Control system** for a busy airport. Scheduling logic and coordination are the focus; no UI, no aircraft physics.

You are picking up the work **after** the analyst phase. The requirements are already locked. **Your job is design, not requirements gathering.**

---

## Inputs (read in this order)

1. `task-4/original-task` — ground truth from the user; do not deviate from it.
2. `_bmad-output/planning-artifacts/spec.md` — structured spec with full traceability back to `original-task` (every requirement carries a `§OT:<lines>` tag; see the matrix in §12).
3. `_bmad-output/planning-artifacts/plan.md` — the handoff plan. Pay special attention to:
   - **§3 Deferred Decisions (DD-1 … DD-10)** — these are *yours* to resolve.
   - **§4 Expected Architect Deliverables** — your output contract.
   - **§6 Risks** — things to actively defend against.

---

## Hard guardrails

- **Do not add requirements.** Cross-check every component against `spec.md §11` (Explicit Non-Requirements) and `spec.md §12` (Traceability Matrix). If something feels missing, ambiguous, or contradictory, **ask the user** — do not invent.
- **Naming and data structures are yours** (per `§OT:44`), but every capability in `spec.md §5–§6` must be fully covered and clearly documented.
- **No code in this phase.** Schemas, contracts, diagrams, and decision records only. Implementation is the next phase.
- **Determinism is non-negotiable** (`FR-SCH-6`). Make your determinism argument explicit when you describe the scheduling algorithm.
- **Fail-fast configuration** (`FR-CFG-2`) — invalid env vars must produce a clear startup error pointing at the offending variable.

---

## Deliverables (output contract)

Produce, at minimum, an `architecture.md` in `_bmad-output/planning-artifacts/` containing:

1. **Tech stack** (language, runtime, MCP SDK, build tooling) — resolves DD-3.
2. **Component decomposition** (MCP transport, config loader, flight queue, scheduler, status reporter, bottleneck analyzer, resource/timeline projector, cancellation flow).
3. **Data model** (flight, runway, gate, ground-crew slot, schedule entry, timeline event, status payload, bottleneck result).
4. **MCP tool catalog** with full input/output schemas — resolves DD-1.
5. **MCP resource catalog** with URIs/names and payload shapes — resolves DD-1.
6. **Environment variable contract** (name, type, unit, accepted range, error shape) — resolves DD-2.
7. **Scheduling algorithm** with explicit determinism argument and tie-break policy — resolves DD-4.
8. **State & persistence statement** (recommend in-memory unless user expands scope) — resolves DD-5.
9. **Time model** (epoch anchor, granularity, timeline representation) — resolves DD-6.
10. **Operation duration source** (single, documented source of truth) — resolves DD-7.
11. **Runway capability schema** (sufficient for VS-2 Heavy Hauler) — resolves DD-8.
12. **Definition of "active scheduled dependency chain"** for the bottleneck tool — resolves DD-9.
13. **Ground-crew scheduling semantics** (how crew capacity gates scheduling) — resolves DD-10.
14. **Cancellation re-evaluation flow** (`FR-SCH-7`).
15. **Scenario walkthroughs** for VS-1, VS-2, VS-3 (`spec.md §9`) showing how the design produces the expected outcomes.
16. **Test plan outline** (no code) — the three mandatory scenarios plus any extra coverage you deem necessary, noting that extras are test coverage only, **not** new product requirements.
17. **README.md outline** (structure only) aligned with `§OT:106`.
18. **report.md outline** (structure only) aligned with `§OT:107`.
19. **Traceability check** — a short section confirming every row of `spec.md §12` is addressed somewhere in the architecture. If a row cannot be addressed, escalate to the user before proceeding.

---

## Definition of Done (architect phase)

- All ten deferred decisions (DD-1 … DD-10) are resolved and documented.
- Every row of `spec.md §12` is traceably addressed in `architecture.md`.
- A developer could implement from your output **without re-reading `original-task`**.
- No new product requirements have been introduced; only design choices that satisfy the existing spec.

When all four bullets above are checked, hand back to the user for review before implementation begins.

---

## First action

Read `original-task`, then `spec.md`, then `plan.md`. Then either (a) start drafting `architecture.md` and resolve DDs as you go, or (b) if you find an actual blocker, surface one tight question to the user. Do not surface questions to broaden scope.