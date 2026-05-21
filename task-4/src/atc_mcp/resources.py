"""MCP resource handlers — the only other layer that imports the mcp SDK (Story 1.4+)."""
import json

from atc_mcp.domain.models import FlightState
from atc_mcp.domain.state import state


def flights_resource() -> str:
    """Current flight queue including unscheduled and cancelled."""
    _STATE_RANK = {
        FlightState.scheduled: 0,
        FlightState.queued: 1,
        FlightState.unschedulable: 2,
        FlightState.cancelled: 3,
    }
    sorted_flights = sorted(
        state.flights.values(),
        key=lambda f: (_STATE_RANK[f.state], f.flight_number),
    )
    return json.dumps({"flights": [f.model_dump() for f in sorted_flights]})


def runways_resource() -> str:
    """Runway availability and usage."""
    if state.config is None:
        return json.dumps({"runways": []})
    
    placements_by_runway: dict[str, list] = {r.id: [] for r in state.config.runways}
    if state.latest_schedule is not None:
        for p in state.latest_schedule.placements:
            placements_by_runway[p.runway_id].append(p)
    
    runways_data = []
    for runway in sorted(state.config.runways, key=lambda r: r.id):
        ops = sorted(placements_by_runway[runway.id], key=lambda p: p.start_sec)
        scheduled_ops = [
            {
                "flight_number": p.flight_number,
                "operation_type": p.operation_type,
                "start_sec": p.start_sec,
                "end_sec": p.end_sec,
            }
            for p in ops
        ]
        busy = [[p.start_sec, p.end_sec] for p in ops]
        next_free = max((p.end_sec for p in ops), default=0)
        runways_data.append({
            "id": runway.id,
            "length_m": runway.length_m,
            "scheduled_operations": scheduled_ops,
            "busy_intervals_sec": busy,
            "next_free_sec": next_free,
        })
    
    return json.dumps({"runways": runways_data})


def timeline_resource() -> str:
    """Chronological timeline of scheduled operations."""
    if state.latest_schedule is None:
        return json.dumps({"events": []})
    
    events = sorted(
        state.latest_schedule.placements,
        key=lambda p: (p.start_sec, p.runway_id, p.flight_number),
    )
    events_data = [
        {
            "start_sec": p.start_sec,
            "end_sec": p.end_sec,
            "flight_number": p.flight_number,
            "operation_type": p.operation_type,
            "runway_id": p.runway_id,
            "gate_id": p.gate_id,
            "depends_on": state.flights[p.flight_number].dependencies
            if p.flight_number in state.flights else [],
        }
        for p in events
    ]
    return json.dumps({"events": events_data})
