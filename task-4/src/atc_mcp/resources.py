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
    return json.dumps({"runways": []})


def timeline_resource() -> str:
    """Chronological timeline of scheduled operations."""
    return json.dumps({"events": []})
