import json

import pytest

from atc_mcp.domain.models import Flight, FlightState, OperationType, Priority, RunwayRequirements
from atc_mcp.domain.state import state
from atc_mcp.resources import flights_resource


@pytest.fixture(autouse=True)
def reset_state():
    state.reset()
    yield
    state.reset()


def test_empty_state_returns_empty_flights():
    result = json.loads(flights_resource())
    assert result == {"flights": []}


def test_single_flight_all_fields_serialized():
    f = Flight(flight_number="AA123", operation_type=OperationType.arrival, priority=Priority.high)
    state.add_flight(f)
    result = json.loads(flights_resource())
    assert len(result["flights"]) == 1
    flight_data = result["flights"][0]
    assert flight_data["flight_number"] == "AA123"
    assert flight_data["operation_type"] == "arrival"
    assert flight_data["priority"] == "high"
    assert flight_data["state"] == "queued"
    assert flight_data["unscheduled_reason"] is None
    assert flight_data["dependencies"] == []
    assert flight_data["runway_requirements"] is None


def test_mixed_state_ordering():
    cancelled = Flight(
        flight_number="AA400",
        operation_type=OperationType.arrival,
        priority=Priority.low,
        state=FlightState.cancelled,
        unscheduled_reason="cancelled by operations",
    )
    unschedulable = Flight(
        flight_number="AA300",
        operation_type=OperationType.arrival,
        priority=Priority.medium,
        state=FlightState.unschedulable,
        unscheduled_reason="no runway available",
    )
    queued = Flight(flight_number="AA200", operation_type=OperationType.arrival, priority=Priority.high)
    scheduled = Flight(
        flight_number="AA100",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
    )
    for f in [cancelled, unschedulable, queued, scheduled]:
        state.add_flight(f)
    result = json.loads(flights_resource())
    states = [f["state"] for f in result["flights"]]
    assert states == ["scheduled", "queued", "unschedulable", "cancelled"]


def test_within_state_group_sorted_by_flight_number():
    q1 = Flight(flight_number="CC200", operation_type=OperationType.arrival, priority=Priority.low)
    q2 = Flight(flight_number="AA200", operation_type=OperationType.arrival, priority=Priority.low)
    q3 = Flight(flight_number="BB200", operation_type=OperationType.arrival, priority=Priority.low)
    for f in [q1, q2, q3]:
        state.add_flight(f)
    result = json.loads(flights_resource())
    numbers = [f["flight_number"] for f in result["flights"]]
    assert numbers == ["AA200", "BB200", "CC200"]


def test_reason_string_format():
    unschedulable = Flight(
        flight_number="U1",
        operation_type=OperationType.departure,
        priority=Priority.medium,
        state=FlightState.unschedulable,
        unscheduled_reason="no runway meets minimum length requirement",
    )
    scheduled = Flight(
        flight_number="S1",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
    )
    queued = Flight(flight_number="Q1", operation_type=OperationType.arrival, priority=Priority.low)
    for f in [unschedulable, scheduled, queued]:
        state.add_flight(f)
    result = json.loads(flights_resource())
    flights_by_number = {f["flight_number"]: f for f in result["flights"]}
    reason = flights_by_number["U1"]["unscheduled_reason"]
    assert reason == "no runway meets minimum length requirement"
    assert not reason.endswith(".")
    assert reason == reason.lower()
    assert flights_by_number["S1"]["unscheduled_reason"] is None
    assert flights_by_number["Q1"]["unscheduled_reason"] is None


def test_dependencies_empty_list_not_null():
    f = Flight(flight_number="F1", operation_type=OperationType.arrival, priority=Priority.low)
    state.add_flight(f)
    result = json.loads(flights_resource())
    assert result["flights"][0]["dependencies"] == []


def test_dependencies_list_with_values():
    f1 = Flight(flight_number="F1", operation_type=OperationType.arrival, priority=Priority.low)
    f2 = Flight(
        flight_number="F2",
        operation_type=OperationType.departure,
        priority=Priority.low,
        dependencies=["F1"],
    )
    state.add_flight(f1)
    state.add_flight(f2)
    result = json.loads(flights_resource())
    flights_by_number = {f["flight_number"]: f for f in result["flights"]}
    assert flights_by_number["F1"]["dependencies"] == []
    assert flights_by_number["F2"]["dependencies"] == ["F1"]


def test_runway_requirements_null_when_not_set():
    f = Flight(flight_number="F1", operation_type=OperationType.arrival, priority=Priority.low)
    state.add_flight(f)
    result = json.loads(flights_resource())
    assert result["flights"][0]["runway_requirements"] is None


def test_runway_requirements_object_when_set():
    f = Flight(
        flight_number="F1",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        runway_requirements=RunwayRequirements(min_length_m=3500),
    )
    state.add_flight(f)
    result = json.loads(flights_resource())
    assert result["flights"][0]["runway_requirements"] == {"min_length_m": 3500}


def test_determinism_100_reads():
    flights = [
        Flight(
            flight_number=f"F{i:03d}",
            operation_type=OperationType.arrival if i % 2 == 0 else OperationType.departure,
            priority=Priority.high,
            state=[FlightState.queued, FlightState.scheduled, FlightState.unschedulable, FlightState.cancelled][i % 4],
            unscheduled_reason="no available slot" if i % 4 in (2, 3) else None,
        )
        for i in range(5)
    ]
    for f in flights:
        state.add_flight(f)
    outputs = [flights_resource() for _ in range(100)]
    assert len(set(outputs)) == 1
