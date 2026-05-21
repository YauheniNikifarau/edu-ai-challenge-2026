"""Airport and flight status query helpers (Story 2+)."""
from atc_mcp.config import Config
from atc_mcp.domain.models import FlightState, Placement
from atc_mcp.domain.state import AppState


def _peak_concurrent(placements: tuple[Placement, ...]) -> int:
    """Compute peak concurrent resource usage using event-based algorithm."""
    events: list[tuple[int, int]] = []
    for p in placements:
        events.append((p.start_sec, +1))
        events.append((p.end_sec, -1))
    events.sort()
    peak = current = 0
    for _, delta in events:
        current += delta
        if current > peak:
            peak = current
    return peak


def _count_at_time(placements: tuple[Placement, ...], time_sec: int) -> int:
    """Count how many placements are active at a specific time."""
    count = 0
    for p in placements:
        if p.start_sec < time_sec <= p.end_sec:
            count += 1
    return count


def build_status(state: AppState, config: Config) -> dict:
    """Build structured airport operational status from current state.
    
    This is a pure projection of in-memory state - never triggers scheduling.
    """
    by_state = {s.value: 0 for s in FlightState}
    for f in state.flights.values():
        by_state[f.state.value] += 1
    
    by_op = {"arrival": 0, "departure": 0}
    for f in state.flights.values():
        by_op[f.operation_type.value] += 1
    
    flight_counts = {
        "by_state": by_state,
        "by_operation_type": by_op,
    }
    
    placements = state.latest_schedule.placements if state.latest_schedule else ()
    
    runways = []
    for runway in config.runways:
        usage_sec = sum(
            p.end_sec - p.start_sec
            for p in placements
            if p.runway_id == runway.id
        )
        capacity_sec = config.scheduling_horizon_sec
        usage_pct = round(usage_sec / capacity_sec * 100, 2) if capacity_sec > 0 else 0.0
        runways.append({
            "id": runway.id,
            "length_m": runway.length_m,
            "capacity_sec": capacity_sec,
            "usage_sec": usage_sec,
            "usage_pct": usage_pct,
        })
    runways.sort(key=lambda r: r["id"])
    
    gates_peak = _peak_concurrent(placements) if placements else 0
    completion_time = state.latest_schedule.completion_time_seconds if state.latest_schedule else None
    gates_at_completion = _count_at_time(placements, completion_time) if completion_time and placements else 0
    
    gates = {
        "capacity": config.gate_count,
        "in_use_peak": gates_peak,
        "in_use_at_completion": gates_at_completion,
    }
    
    ground_crew = {
        "capacity": config.ground_crew_count,
        "in_use_peak": gates_peak,
        "in_use_at_completion": gates_at_completion,
    }
    
    resource_constraints = []
    if gates_peak >= config.gate_count:
        resource_constraints.append("gates_at_capacity")
    if gates_peak >= config.ground_crew_count:
        resource_constraints.append("ground_crew_at_capacity")
    
    unscheduled = sorted(
        [
            {"flight_number": f.flight_number, "reason": f.unscheduled_reason or ""}
            for f in state.flights.values()
            if f.state == FlightState.unschedulable
        ],
        key=lambda x: x["flight_number"],
    )
    
    return {
        "flight_counts": flight_counts,
        "runways": runways,
        "gates": gates,
        "ground_crew": ground_crew,
        "resource_constraints": resource_constraints,
        "unscheduled": unscheduled,
        "completion_time_seconds": completion_time,
    }
