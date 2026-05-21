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


def _compute_topo_and_cycles(
    flight_map: dict[str, Flight]
) -> tuple[dict[str, int], dict[str, frozenset[str]]]:
    """Compute topological depths and detect cycles via DFS.

    Returns:
        (topo_depths, which_cycle) where:
        - topo_depths: flight_number -> depth (0 for leaves)
        - which_cycle: flight_number -> frozenset of cycle members (only for cycled flights)
    """
    color: dict[str, int] = {fn: 0 for fn in flight_map}  # 0=unvisited, 1=GRAY, 2=BLACK
    cycles: list[frozenset[str]] = []

    def _dfs_cycles(fn: str, stack: list[str]) -> None:
        color[fn] = 1  # GRAY
        stack.append(fn)
        flight = flight_map[fn]
        for dep_fn in flight.dependencies:
            if dep_fn not in flight_map:
                continue  # dep was deleted / doesn't exist
            if color[dep_fn] == 1:  # back-edge → cycle
                cycle_start = stack.index(dep_fn)
                cycle_members = frozenset(stack[cycle_start:])
                cycles.append(cycle_members)
            elif color[dep_fn] == 0:
                _dfs_cycles(dep_fn, stack)
        stack.pop()
        color[fn] = 2  # BLACK

    # Run DFS from all unvisited nodes
    for fn in flight_map:
        if color[fn] == 0:
            _dfs_cycles(fn, [])

    # Build which_cycle mapping
    which_cycle: dict[str, frozenset[str]] = {}
    for cycle in cycles:
        for fn in cycle:
            which_cycle[fn] = cycle

    # Compute topological depths for non-cycled flights
    cycled_set = set(which_cycle.keys())
    depth: dict[str, int] = {}

    def _topo_depth(fn: str) -> int:
        if fn in depth:
            return depth[fn]
        flight = flight_map[fn]
        if not flight.dependencies:
            depth[fn] = 0
            return 0
        # Only consider non-cycled dependencies that exist
        valid_deps = [
            d for d in flight.dependencies
            if d in flight_map and d not in cycled_set
        ]
        if not valid_deps:
            depth[fn] = 0
        else:
            max_dep_depth = max(_topo_depth(d) for d in valid_deps)
            depth[fn] = max_dep_depth + 1
        return depth[fn]

    # Compute depths for all non-cycled flights
    for fn in flight_map:
        if fn not in cycled_set:
            _topo_depth(fn)

    return depth, which_cycle


def schedule(flights: tuple[Flight, ...], config: Config) -> Schedule:
    """Return a Schedule for the given flights using greedy deterministic placement.

    Story 3.2: Includes dependency ordering, cycle detection, and dependency buffer enforcement.
    """
    # Split cancelled out — they are never placed
    active = [f for f in flights if f.state != FlightState.cancelled]
    flight_map = {f.flight_number: f for f in active}

    # Phase 1: Cycle detection + topo depth
    topo_depths, which_cycle = _compute_topo_and_cycles(flight_map)

    # Mark cycled flights immediately (build updated flight objects)
    result_flights: dict[str, Flight] = {}
    unscheduled: list[Flight] = []
    
    for f in flights:
        if f.flight_number in which_cycle:
            cycle_members = sorted(which_cycle[f.flight_number])
            cycled_flight = f.model_copy(update={
                "state": FlightState.unschedulable,
                "unscheduled_reason": "dependency cycle: " + ", ".join(cycle_members),
            })
            result_flights[f.flight_number] = cycled_flight
            unscheduled.append(cycled_flight)
        else:
            result_flights[f.flight_number] = f

    # Sort non-cycled active flights by (topo_depth, priority_rank, flight_number)
    schedulable = [
        result_flights[f.flight_number]
        for f in flights
        if f.flight_number not in which_cycle and f.state != FlightState.cancelled
    ]
    sorted_flights = sorted(
        schedulable,
        key=lambda f: (topo_depths.get(f.flight_number, 0), _PRIORITY_RANK[f.priority], f.flight_number),
    )

    gates: list[str] = [f"G{i}" for i in range(1, config.gate_count + 1)]
    runway_ops: dict[str, list[Placement]] = {r.id: [] for r in config.runways}
    gate_ops: dict[str, list[Placement]] = {g: [] for g in gates}

    placements_dict: dict[str, Placement] = {}

    for flight in sorted_flights:
        # Compute dependency floor
        dep_floor = 0
        dep_blocked = False
        for dep_fn in sorted(flight.dependencies):  # sorted for determinism
            if dep_fn not in result_flights:
                continue  # dep doesn't exist
            dep_state = result_flights[dep_fn].state
            if dep_state in (FlightState.unschedulable, FlightState.cancelled):
                result_flights[flight.flight_number] = result_flights[flight.flight_number].model_copy(update={
                    "state": FlightState.unschedulable,
                    "unscheduled_reason": f"dependency {dep_fn} is not scheduled",
                })
                unscheduled.append(result_flights[flight.flight_number])
                dep_blocked = True
                break
            if dep_fn in placements_dict:
                dep_floor = max(dep_floor, placements_dict[dep_fn].end_sec + config.dependency_buffer_sec)

        if dep_blocked:
            continue
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
            result_flights[flight.flight_number] = result_flights[flight.flight_number].model_copy(update={
                "state": FlightState.unschedulable,
                "unscheduled_reason": reason,
            })
            unscheduled.append(result_flights[flight.flight_number])
            continue

        best_t: int | None = None
        best_runway_id = ""
        best_gate_id = ""

        for runway in feasible:
            for gate in gates:
                t = max(
                    dep_floor,
                    earliest_runway_start(runway_ops[runway.id], flight.operation_type, dep_floor, config),
                    earliest_gate_start(gate_ops[gate], dep_floor, config),
                )
                if best_t is None or t < best_t:
                    best_t = t
                    best_runway_id = runway.id
                    best_gate_id = gate

        assert best_t is not None

        if best_t + duration > config.scheduling_horizon_sec:
            result_flights[flight.flight_number] = result_flights[flight.flight_number].model_copy(update={
                "state": FlightState.unschedulable,
                "unscheduled_reason": "would exceed scheduling horizon",
            })
            unscheduled.append(result_flights[flight.flight_number])
            continue

        placement = Placement(
            flight_number=flight.flight_number,
            operation_type=flight.operation_type,
            runway_id=best_runway_id,
            gate_id=best_gate_id,
            start_sec=best_t,
            end_sec=best_t + duration,
        )
        placements_dict[flight.flight_number] = placement
        runway_ops[best_runway_id].append(placement)
        gate_ops[best_gate_id].append(placement)
        result_flights[flight.flight_number] = result_flights[flight.flight_number].model_copy(update={
            "state": FlightState.scheduled,
        })

    # Build final Schedule with placements sorted by (start_sec, flight_number)
    placed = tuple(
        placements_dict[fn]
        for fn in sorted(placements_dict, key=lambda fn: (placements_dict[fn].start_sec, fn))
    )
    completion = max((p.end_sec for p in placed), default=None)
    return Schedule(
        placements=placed,
        unscheduled=tuple(unscheduled),
        completion_time_seconds=completion,
    )
