import pytest

from atc_mcp.config import load_config
from atc_mcp.domain.models import Flight, FlightState, OperationType, Priority
from atc_mcp.domain.state import state
from atc_mcp.tools import CancelFlightInput, cancel_flight
from mcp.shared.exceptions import McpError


def setup_function(function):
    """Reset state before each test."""
    state.reset()


def test_cancel_queued_flight(valid_env):
    state.config = load_config()
    flight = Flight(
        flight_number="F1",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.queued,
    )
    state.add_flight(flight)
    result = cancel_flight(CancelFlightInput(flight_number="F1"))
    assert state.get_flight("F1").state == FlightState.cancelled
    assert state.get_flight("F1").unscheduled_reason is None
    assert result == {"cancelled": "F1", "dependents_reevaluated": []}


def test_cancel_scheduled_flight(valid_env):
    state.config = load_config()
    flight = Flight(
        flight_number="F2",
        operation_type=OperationType.departure,
        priority=Priority.medium,
        state=FlightState.scheduled,
    )
    state.add_flight(flight)
    result = cancel_flight(CancelFlightInput(flight_number="F2"))
    assert state.get_flight("F2").state == FlightState.cancelled
    assert result == {"cancelled": "F2", "dependents_reevaluated": []}


def test_cancel_already_cancelled_raises_error():
    flight = Flight(
        flight_number="F",
        operation_type=OperationType.arrival,
        priority=Priority.low,
        state=FlightState.cancelled,
    )
    state.add_flight(flight)
    with pytest.raises(McpError) as exc_info:
        cancel_flight(CancelFlightInput(flight_number="F"))
    assert str(exc_info.value.error.message) == "flight F is already cancelled"


def test_cancel_unknown_flight_raises_error():
    with pytest.raises(McpError) as exc_info:
        cancel_flight(CancelFlightInput(flight_number="XYZ"))
    assert str(exc_info.value.error.message) == "flight XYZ does not exist"


def test_cancel_payload_shape(valid_env):
    state.config = load_config()
    flight = Flight(
        flight_number="F3",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.queued,
    )
    state.add_flight(flight)
    result = cancel_flight(CancelFlightInput(flight_number="F3"))
    assert set(result.keys()) == {"cancelled", "dependents_reevaluated"}
    assert result["dependents_reevaluated"] == []
