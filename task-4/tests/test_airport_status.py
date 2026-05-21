"""Tests for build_status() and get_airport_status tool (Story 3.5)."""
import json

import pytest

from atc_mcp.config import load_config
from atc_mcp.domain.models import Flight, FlightState, OperationType, Placement, Priority, Schedule
from atc_mcp.domain.state import state
from atc_mcp.status import build_status


@pytest.fixture(autouse=True)
def reset_state():
    """Reset state before and after each test."""
    state.reset()
    yield
    state.reset()


def test_empty_state(valid_env):
    """Test status with no flights and no schedule."""
    config = load_config()
    
    result = build_status(state, config)
    
    assert result["flight_counts"]["by_state"] == {
        "queued": 0,
        "scheduled": 0,
        "unschedulable": 0,
        "cancelled": 0,
    }
    assert result["flight_counts"]["by_operation_type"] == {
        "arrival": 0,
        "departure": 0,
    }
    
    assert len(result["runways"]) == 2
    assert result["runways"][0]["id"] == "R1"
    assert result["runways"][0]["length_m"] == 3500
    assert result["runways"][0]["capacity_sec"] == 86400
    assert result["runways"][0]["usage_sec"] == 0
    assert result["runways"][0]["usage_pct"] == 0.0
    
    assert result["runways"][1]["id"] == "R2"
    assert result["runways"][1]["length_m"] == 3000
    assert result["runways"][1]["capacity_sec"] == 86400
    assert result["runways"][1]["usage_sec"] == 0
    assert result["runways"][1]["usage_pct"] == 0.0
    
    assert result["gates"] == {
        "capacity": 4,
        "in_use_peak": 0,
        "in_use_at_completion": 0,
    }
    
    assert result["ground_crew"] == {
        "capacity": 3,
        "in_use_peak": 0,
        "in_use_at_completion": 0,
    }
    
    assert result["resource_constraints"] == []
    assert result["unscheduled"] == []
    assert result["completion_time_seconds"] is None


def test_queue_only_no_schedule(valid_env):
    """Test status with queued flights but no schedule generated."""
    config = load_config()
    
    state.add_flight(Flight(
        flight_number="AA100",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.queued,
    ))
    state.add_flight(Flight(
        flight_number="BB200",
        operation_type=OperationType.departure,
        priority=Priority.medium,
        state=FlightState.queued,
    ))
    
    result = build_status(state, config)
    
    assert result["flight_counts"]["by_state"]["queued"] == 2
    assert result["flight_counts"]["by_state"]["scheduled"] == 0
    assert result["flight_counts"]["by_operation_type"]["arrival"] == 1
    assert result["flight_counts"]["by_operation_type"]["departure"] == 1
    
    assert result["runways"][0]["usage_sec"] == 0
    assert result["runways"][1]["usage_sec"] == 0
    
    assert result["completion_time_seconds"] is None


def test_fully_scheduled_state(valid_env):
    """Test status with all flights scheduled."""
    config = load_config()
    
    state.add_flight(Flight(
        flight_number="AA100",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
    ))
    state.add_flight(Flight(
        flight_number="BB200",
        operation_type=OperationType.departure,
        priority=Priority.medium,
        state=FlightState.scheduled,
    ))
    state.add_flight(Flight(
        flight_number="CC300",
        operation_type=OperationType.arrival,
        priority=Priority.low,
        state=FlightState.scheduled,
    ))
    
    placements = (
        Placement(
            flight_number="AA100",
            operation_type=OperationType.arrival,
            runway_id="R1",
            gate_id="G1",
            start_sec=0,
            end_sec=1200,
        ),
        Placement(
            flight_number="BB200",
            operation_type=OperationType.departure,
            runway_id="R2",
            gate_id="G2",
            start_sec=1200,
            end_sec=2400,
        ),
        Placement(
            flight_number="CC300",
            operation_type=OperationType.arrival,
            runway_id="R1",
            gate_id="G3",
            start_sec=2400,
            end_sec=3600,
        ),
    )
    
    schedule = Schedule(
        placements=placements,
        unscheduled=(),
        completion_time_seconds=3600,
    )
    state.set_latest_schedule(schedule)
    
    result = build_status(state, config)
    
    assert result["flight_counts"]["by_state"]["scheduled"] == 3
    assert result["flight_counts"]["by_state"]["queued"] == 0
    
    r1 = next(r for r in result["runways"] if r["id"] == "R1")
    assert r1["usage_sec"] == 2400
    assert r1["usage_pct"] == round(2400 / 86400 * 100, 2)
    
    r2 = next(r for r in result["runways"] if r["id"] == "R2")
    assert r2["usage_sec"] == 1200
    assert r2["usage_pct"] == round(1200 / 86400 * 100, 2)
    
    assert result["completion_time_seconds"] == 3600


def test_mixed_state_with_unschedulables(valid_env):
    """Test status with mix of scheduled and unschedulable flights."""
    config = load_config()
    
    state.add_flight(Flight(
        flight_number="AA100",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
    ))
    state.add_flight(Flight(
        flight_number="BB200",
        operation_type=OperationType.departure,
        priority=Priority.medium,
        state=FlightState.scheduled,
    ))
    state.add_flight(Flight(
        flight_number="ZZ999",
        operation_type=OperationType.arrival,
        priority=Priority.low,
        state=FlightState.unschedulable,
        unscheduled_reason="no runway meets minimum length 4500m (available runways: R1 3500m, R2 3000m)",
    ))
    state.add_flight(Flight(
        flight_number="AA999",
        operation_type=OperationType.departure,
        priority=Priority.high,
        state=FlightState.unschedulable,
        unscheduled_reason="dependency cycle detected",
    ))
    
    placements = (
        Placement(
            flight_number="AA100",
            operation_type=OperationType.arrival,
            runway_id="R1",
            gate_id="G1",
            start_sec=0,
            end_sec=1200,
        ),
        Placement(
            flight_number="BB200",
            operation_type=OperationType.departure,
            runway_id="R2",
            gate_id="G2",
            start_sec=1200,
            end_sec=2400,
        ),
    )
    
    schedule = Schedule(
        placements=placements,
        unscheduled=(
            Flight(
                flight_number="ZZ999",
                operation_type=OperationType.arrival,
                priority=Priority.low,
                state=FlightState.unschedulable,
                unscheduled_reason="no runway meets minimum length 4500m (available runways: R1 3500m, R2 3000m)",
            ),
            Flight(
                flight_number="AA999",
                operation_type=OperationType.departure,
                priority=Priority.high,
                state=FlightState.unschedulable,
                unscheduled_reason="dependency cycle detected",
            ),
        ),
        completion_time_seconds=2400,
    )
    state.set_latest_schedule(schedule)
    
    result = build_status(state, config)
    
    assert result["flight_counts"]["by_state"]["scheduled"] == 2
    assert result["flight_counts"]["by_state"]["unschedulable"] == 2
    
    assert len(result["unscheduled"]) == 2
    assert result["unscheduled"][0]["flight_number"] == "AA999"
    assert result["unscheduled"][0]["reason"] == "dependency cycle detected"
    assert result["unscheduled"][1]["flight_number"] == "ZZ999"
    assert result["unscheduled"][1]["reason"] == "no runway meets minimum length 4500m (available runways: R1 3500m, R2 3000m)"


def test_ground_crew_peak_math(valid_env):
    """Test ground crew peak calculation with overlapping placements."""
    config = load_config()
    
    state.add_flight(Flight(
        flight_number="AA100",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
    ))
    state.add_flight(Flight(
        flight_number="BB200",
        operation_type=OperationType.departure,
        priority=Priority.medium,
        state=FlightState.scheduled,
    ))
    state.add_flight(Flight(
        flight_number="CC300",
        operation_type=OperationType.arrival,
        priority=Priority.low,
        state=FlightState.scheduled,
    ))
    
    placements = (
        Placement(
            flight_number="AA100",
            operation_type=OperationType.arrival,
            runway_id="R1",
            gate_id="G1",
            start_sec=0,
            end_sec=1200,
        ),
        Placement(
            flight_number="BB200",
            operation_type=OperationType.departure,
            runway_id="R2",
            gate_id="G2",
            start_sec=600,
            end_sec=1800,
        ),
        Placement(
            flight_number="CC300",
            operation_type=OperationType.arrival,
            runway_id="R1",
            gate_id="G3",
            start_sec=1500,
            end_sec=2700,
        ),
    )
    
    schedule = Schedule(
        placements=placements,
        unscheduled=(),
        completion_time_seconds=2700,
    )
    state.set_latest_schedule(schedule)
    
    result = build_status(state, config)
    
    assert result["ground_crew"]["in_use_peak"] == 2
    
    assert result["ground_crew"]["in_use_at_completion"] == 1


def test_determinism_property(valid_env):
    """Test that repeated calls with identical state return byte-identical payloads."""
    config = load_config()
    
    state.add_flight(Flight(
        flight_number="AA100",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
    ))
    state.add_flight(Flight(
        flight_number="BB200",
        operation_type=OperationType.departure,
        priority=Priority.medium,
        state=FlightState.unschedulable,
        unscheduled_reason="test reason",
    ))
    
    placements = (
        Placement(
            flight_number="AA100",
            operation_type=OperationType.arrival,
            runway_id="R1",
            gate_id="G1",
            start_sec=0,
            end_sec=1200,
        ),
    )
    
    schedule = Schedule(
        placements=placements,
        unscheduled=(
            Flight(
                flight_number="BB200",
                operation_type=OperationType.departure,
                priority=Priority.medium,
                state=FlightState.unschedulable,
                unscheduled_reason="test reason",
            ),
        ),
        completion_time_seconds=1200,
    )
    state.set_latest_schedule(schedule)
    
    results = {
        json.dumps(build_status(state, config), sort_keys=True, separators=(",", ":"))
        for _ in range(100)
    }
    
    assert len(results) == 1


def test_resource_constraints_at_capacity(valid_env):
    """Test resource_constraints when gates or ground crew are at capacity."""
    config = load_config()
    
    for i in range(4):
        state.add_flight(Flight(
            flight_number=f"FL{i}",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            state=FlightState.scheduled,
        ))
    
    placements = tuple(
        Placement(
            flight_number=f"FL{i}",
            operation_type=OperationType.arrival,
            runway_id="R1",
            gate_id=f"G{i}",
            start_sec=0,
            end_sec=1200,
        )
        for i in range(4)
    )
    
    schedule = Schedule(
        placements=placements,
        unscheduled=(),
        completion_time_seconds=1200,
    )
    state.set_latest_schedule(schedule)
    
    result = build_status(state, config)
    
    assert result["gates"]["in_use_peak"] == 4
    assert result["ground_crew"]["in_use_peak"] == 4
    
    assert "gates_at_capacity" in result["resource_constraints"]
    assert "ground_crew_at_capacity" in result["resource_constraints"]
