"""Core scheduling algorithm — assigns time slots to flights deterministically (Story 3.1+)."""
from atc_mcp.config import Config
from atc_mcp.domain.models import Flight, FlightState, OperationType, Placement, Priority, Schedule
from atc_mcp.scheduler.constraints import (
    earliest_gate_start,
    earliest_runway_start,
    feasible_runways,
    runway_unschedulable_reason,
)

_PRIORITY_RANK: dict[Priority, int] = {
    Priority.high: 0,
    Priority.medium: 1,
    Priority.low: 2,
}


def schedule(flights: tuple[Flight, ...], config: Config) -> Schedule:
    """Return a Schedule for the given flights using greedy deterministic placement.

    Story 3.1: single-flight resource constraints only (no dependency ordering, no ground crew).
    topo_depth is hard-coded to 0; Story 3.2 will replace it with a computed value.
    """
    sorted_flights = sorted(
        [f for f in flights if f.state != FlightState.cancelled],
        key=lambda f: (0, _PRIORITY_RANK[f.priority], f.flight_number),
    )

    gates: list[str] = [f"G{i}" for i in range(1, config.gate_count + 1)]
    runway_ops: dict[str, list[Placement]] = {r.id: [] for r in config.runways}
    gate_ops: dict[str, list[Placement]] = {g: [] for g in gates}

    placements: list[Placement] = []
    unscheduled: list[Flight] = []

    for flight in sorted_flights:
        duration = (
            config.duration_arrival_sec
            if flight.operation_type == OperationType.arrival
            else config.duration_departure_sec
        )

        feasible = feasible_runways(config.runways, flight.runway_requirements)

        if not feasible:
            assert flight.runway_requirements is not None
            reason = runway_unschedulable_reason(
                flight.runway_requirements.min_length_m,
                config.runways,
            )
            unscheduled.append(
                flight.model_copy(update={"state": FlightState.unschedulable, "unscheduled_reason": reason})
            )
            continue

        best_t: int | None = None
        best_runway_id = ""
        best_gate_id = ""

        for runway in feasible:
            for gate in gates:
                t = max(
                    0,
                    earliest_runway_start(runway_ops[runway.id], flight.operation_type, 0, config),
                    earliest_gate_start(gate_ops[gate], 0, config),
                )
                if best_t is None or t < best_t:
                    best_t = t
                    best_runway_id = runway.id
                    best_gate_id = gate

        assert best_t is not None

        if best_t + duration > config.scheduling_horizon_sec:
            unscheduled.append(
                flight.model_copy(
                    update={
                        "state": FlightState.unschedulable,
                        "unscheduled_reason": "would exceed scheduling horizon",
                    }
                )
            )
            continue

        placement = Placement(
            flight_number=flight.flight_number,
            operation_type=flight.operation_type,
            runway_id=best_runway_id,
            gate_id=best_gate_id,
            start_sec=best_t,
            end_sec=best_t + duration,
        )
        placements.append(placement)
        runway_ops[best_runway_id].append(placement)
        gate_ops[best_gate_id].append(placement)

    completion = max((p.end_sec for p in placements), default=None)
    return Schedule(
        placements=tuple(placements),
        unscheduled=tuple(unscheduled),
        completion_time_seconds=completion,
    )
