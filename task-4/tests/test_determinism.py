"""Property test: 100-run byte-identical determinism for schedule() and resource functions (Story 3.7)."""
import json

import pytest

from atc_mcp.config import Config, Runway as ConfigRunway
from atc_mcp.domain.models import (
    Flight,
    FlightState,
    OperationType,
    Priority,
    RunwayRequirements,
)
from atc_mcp.domain.state import state
from atc_mcp.resources import flights_resource, runways_resource, timeline_resource
from atc_mcp.scheduler.algorithm import schedule

_CONFIG = Config(
    runways=(ConfigRunway(id="R1", length_m=3500), ConfigRunway(id="R2", length_m=3000)),
    gate_count=4,
    ground_crew_count=3,
    runway_sep_takeoff_sec=120,
    runway_sep_landing_sec=180,
    runway_sep_mixed_sec=240,
    gate_turnaround_sec=300,
    dependency_buffer_sec=600,
    scheduling_horizon_sec=86400,
    duration_arrival_sec=1200,
    duration_departure_sec=1200,
)

_FLIGHTS = (
    Flight(
        flight_number="DET01",
        operation_type=OperationType.arrival,
        priority=Priority.high,
    ),
    Flight(
        flight_number="DET02",
        operation_type=OperationType.departure,
        priority=Priority.high,
    ),
    Flight(
        flight_number="DET03",
        operation_type=OperationType.arrival,
        priority=Priority.medium,
    ),
    Flight(
        flight_number="DET04",
        operation_type=OperationType.departure,
        priority=Priority.medium,
        dependencies=["DET01"],
    ),
    Flight(
        flight_number="DET05",
        operation_type=OperationType.arrival,
        priority=Priority.low,
    ),
    Flight(
        flight_number="DET06",
        operation_type=OperationType.departure,
        priority=Priority.low,
        dependencies=["DET04"],
    ),
    Flight(
        flight_number="DET07",
        operation_type=OperationType.arrival,
        priority=Priority.medium,
        dependencies=["DET03"],
    ),
    Flight(
        flight_number="DET08",
        operation_type=OperationType.departure,
        priority=Priority.high,
        runway_requirements=RunwayRequirements(min_length_m=3200),
    ),
    Flight(
        flight_number="DET09",
        operation_type=OperationType.departure,
        priority=Priority.high,
        runway_requirements=RunwayRequirements(min_length_m=4000),
    ),
    Flight(
        flight_number="DET10",
        operation_type=OperationType.arrival,
        priority=Priority.low,
    ),
    Flight(
        flight_number="DET11",
        operation_type=OperationType.departure,
        priority=Priority.medium,
    ),
    Flight(
        flight_number="DET12",
        operation_type=OperationType.arrival,
        priority=Priority.high,
    ),
)


def canonical(sched) -> str:
    """Serialize Schedule to canonical JSON for byte-identical comparison."""
    return json.dumps(
        {
            "placements": [p.model_dump() for p in sched.placements],
            "unscheduled": [
                {"flight_number": f.flight_number, "reason": f.unscheduled_reason}
                for f in sched.unscheduled
            ],
            "completion_time_seconds": sched.completion_time_seconds,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def setup_function(function):
    """Reset state before each test."""
    state.reset()


def test_schedule_output_is_byte_identical_100_runs():
    """Phase 1: Pure function schedule() must produce byte-identical output across 100 runs."""
    results = [canonical(schedule(_FLIGHTS, _CONFIG)) for _ in range(100)]
    assert len(set(results)) == 1, "schedule() output is not deterministic"


@pytest.fixture
def det_state():
    """Set up state with scheduled/unschedulable flights for resource testing."""
    state.reset()
    state.set_config(_CONFIG)
    for f in _FLIGHTS:
        state.add_flight(f)
    
    sched = schedule(_FLIGHTS, _CONFIG)
    
    placed = {p.flight_number for p in sched.placements}
    unscheduled_map = {f.flight_number: f for f in sched.unscheduled}
    updated = {}
    for fn, flight in state.flights.items():
        if fn in placed:
            updated[fn] = flight.model_copy(update={"state": FlightState.scheduled})
        elif fn in unscheduled_map:
            updated[fn] = unscheduled_map[fn]
        else:
            updated[fn] = flight
    state.replace_flights_after_schedule(updated)
    state.set_latest_schedule(sched)
    yield
    state.reset()


def test_resources_are_byte_identical_100_reads(det_state):
    """Phase 2: Resource functions must produce byte-identical output across 100 reads."""
    flights_outputs = {flights_resource() for _ in range(100)}
    assert len(flights_outputs) == 1, "atc://flights not deterministic"

    timeline_outputs = {timeline_resource() for _ in range(100)}
    assert len(timeline_outputs) == 1, "atc://timeline not deterministic"

    runways_outputs = {runways_resource() for _ in range(100)}
    assert len(runways_outputs) == 1, "atc://runways not deterministic"


def test_unscheduled_flight_present_in_fixture():
    """Sanity check: DET09 must be unschedulable with correct reason."""
    sched = schedule(_FLIGHTS, _CONFIG)
    unscheduled_map = {f.flight_number: f for f in sched.unscheduled}
    assert "DET09" in unscheduled_map, "DET09 should be unschedulable"
    det09 = unscheduled_map["DET09"]
    assert det09.unscheduled_reason == "no runway meets minimum length 4000m (available runways: R1 3500m, R2 3000m)"


def test_scheduled_flight_count_matches_expected():
    """Sanity check: 11 flights scheduled, 1 unschedulable."""
    sched = schedule(_FLIGHTS, _CONFIG)
    assert len(sched.placements) == 11, f"Expected 11 placements, got {len(sched.placements)}"
    assert len(sched.unscheduled) == 1, f"Expected 1 unscheduled, got {len(sched.unscheduled)}"
