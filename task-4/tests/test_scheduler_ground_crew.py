"""Tests for ground crew capacity constraint (Story 3.3)."""
import pytest
from atc_mcp.config import load_config
from atc_mcp.domain.models import Flight, FlightState, OperationType, Priority
from atc_mcp.scheduler.algorithm import schedule


def test_k1_serializes_all_operations(valid_env, monkeypatch):
    """K=1 forces all operations to be sequential with no overlap."""
    monkeypatch.setenv("ATC_GROUND_CREW_COUNT", "1")
    config = load_config()
    
    flights = (
        Flight(
            flight_number="A1",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            state=FlightState.queued,
            dependencies=(),
            runway_requirements=None,
        ),
        Flight(
            flight_number="A2",
            operation_type=OperationType.arrival,
            priority=Priority.medium,
            state=FlightState.queued,
            dependencies=(),
            runway_requirements=None,
        ),
        Flight(
            flight_number="A3",
            operation_type=OperationType.arrival,
            priority=Priority.low,
            state=FlightState.queued,
            dependencies=(),
            runway_requirements=None,
        ),
    )
    
    result = schedule(flights, config)
    
    assert len(result.placements) == 3
    
    for i, p_i in enumerate(result.placements):
        for j, p_j in enumerate(result.placements):
            if i != j:
                overlaps = p_i.start_sec < p_j.end_sec and p_j.start_sec < p_i.end_sec
                assert not overlaps, f"Placements {i} and {j} overlap with K=1"


def test_k2_allows_two_concurrent_operations(valid_env, monkeypatch):
    """K=2 allows 2 concurrent operations on different runways."""
    monkeypatch.setenv("ATC_GROUND_CREW_COUNT", "2")
    config = load_config()
    
    flights = (
        Flight(
            flight_number="A1",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            state=FlightState.queued,
            dependencies=(),
            runway_requirements=None,
        ),
        Flight(
            flight_number="A2",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            state=FlightState.queued,
            dependencies=(),
            runway_requirements=None,
        ),
        Flight(
            flight_number="A3",
            operation_type=OperationType.arrival,
            priority=Priority.medium,
            state=FlightState.queued,
            dependencies=(),
            runway_requirements=None,
        ),
    )
    
    result = schedule(flights, config)
    
    assert len(result.placements) == 3
    
    p1 = next(p for p in result.placements if p.flight_number == "A1")
    p2 = next(p for p in result.placements if p.flight_number == "A2")
    p3 = next(p for p in result.placements if p.flight_number == "A3")
    
    assert p1.start_sec == 0
    assert p2.start_sec == 0
    assert p1.runway_id != p2.runway_id
    
    overlap_1_2 = p1.start_sec < p2.end_sec and p2.start_sec < p1.end_sec
    assert overlap_1_2, "First two high-priority flights should overlap with K=2"
    
    earliest_end = min(p1.end_sec, p2.end_sec)
    assert p3.start_sec >= earliest_end, "Third flight should be delayed until one of the first two completes"


def test_crew_delayed_placement(valid_env, monkeypatch):
    """Flight is delayed by crew constraint until a slot opens."""
    monkeypatch.setenv("ATC_GROUND_CREW_COUNT", "1")
    config = load_config()
    
    flights = (
        Flight(
            flight_number="A1",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            state=FlightState.queued,
            dependencies=(),
            runway_requirements=None,
        ),
        Flight(
            flight_number="A2",
            operation_type=OperationType.arrival,
            priority=Priority.medium,
            state=FlightState.queued,
            dependencies=(),
            runway_requirements=None,
        ),
    )
    
    result = schedule(flights, config)
    
    assert len(result.placements) == 2
    
    p1 = next(p for p in result.placements if p.flight_number == "A1")
    p2 = next(p for p in result.placements if p.flight_number == "A2")
    
    assert p1.start_sec == 0
    assert p1.end_sec == config.duration_arrival_sec
    
    assert p2.start_sec >= p1.end_sec


def test_crew_induced_horizon_overflow(valid_env, monkeypatch):
    """Crew delay that pushes flight beyond horizon marks it unschedulable."""
    monkeypatch.setenv("ATC_GROUND_CREW_COUNT", "1")
    monkeypatch.setenv("ATC_SCHEDULING_HORIZON_SEC", "1500")
    config = load_config()
    
    flights = (
        Flight(
            flight_number="A1",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            state=FlightState.queued,
            dependencies=(),
            runway_requirements=None,
        ),
        Flight(
            flight_number="A2",
            operation_type=OperationType.arrival,
            priority=Priority.medium,
            state=FlightState.queued,
            dependencies=(),
            runway_requirements=None,
        ),
    )
    
    result = schedule(flights, config)
    
    assert len(result.placements) == 1
    assert len(result.unscheduled) == 1
    
    placed = result.placements[0]
    assert placed.flight_number == "A1"
    
    unscheduled = result.unscheduled[0]
    assert unscheduled.flight_number == "A2"
    assert unscheduled.state == FlightState.unschedulable
    assert unscheduled.unscheduled_reason == "would exceed scheduling horizon"
