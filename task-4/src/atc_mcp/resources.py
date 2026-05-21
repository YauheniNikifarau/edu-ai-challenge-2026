"""MCP resource handlers — the only other layer that imports the mcp SDK (Story 1.4+)."""
import json


def flights_resource() -> str:
    """Current flight queue including unscheduled and cancelled."""
    return json.dumps({"flights": []})


def runways_resource() -> str:
    """Runway availability and usage."""
    return json.dumps({"runways": []})


def timeline_resource() -> str:
    """Chronological timeline of scheduled operations."""
    return json.dumps({"events": []})
