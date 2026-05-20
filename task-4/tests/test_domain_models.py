"""Unit tests for domain model pinning, FlightState enum, and AppState (Story 1.3, AC-7)."""
import pytest
from pydantic import ValidationError

from atc_mcp.domain.models import (
    BottleneckResult,
    Flight,
    FlightState,
    OperationType,
    Placement,
    Priority,
    Runway,
    RunwayRequirements,
    Schedule,
)
from atc_mcp.domain.state import state


@pytest.fixture(autouse=True)
def reset_state():
    state.reset()
    yield
    state.reset()


class TestFlightState:
    def test_exact_values(self):
        assert set(FlightState) == {"queued", "scheduled", "unschedulable", "cancelled"}

    def test_values_are_lowercase_strings(self):
        for member in FlightState:
            assert member == member.value
            assert member.value == member.value.lower()


class TestFlight:
    def test_valid_flight_construction(self):
        flight = Flight(
            flight_number="F1",
            operation_type=OperationType.arrival,
            priority=Priority.high,
        )
        assert flight.flight_number == "F1"
        assert flight.state == FlightState.queued
        assert flight.unscheduled_reason is None

    def test_rejects_unknown_fields(self):
        with pytest.raises(ValidationError):
            Flight(
                flight_number="F1",
                operation_type="arrival",
                priority="high",
                _extra_field="x",
            )

    def test_frozen_cannot_reassign(self):
        flight = Flight(
            flight_number="F1",
            operation_type=OperationType.arrival,
            priority=Priority.high,
        )
        with pytest.raises(ValidationError):
            flight.state = "scheduled"

    def test_model_copy_update(self):
        flight = Flight(
            flight_number="F1",
            operation_type=OperationType.arrival,
            priority=Priority.high,
        )
        updated = flight.model_copy(update={"state": FlightState.scheduled})
        assert updated.state == FlightState.scheduled
        assert flight.state == FlightState.queued

    def test_default_dependencies_empty_list(self):
        flight = Flight(
            flight_number="F2",
            operation_type=OperationType.departure,
            priority=Priority.low,
        )
        assert flight.dependencies == []


class TestAppState:
    def test_reset_clears_flights_and_schedule(self):
        flight = Flight(
            flight_number="F1",
            operation_type=OperationType.arrival,
            priority=Priority.high,
        )
        placement = Placement(
            flight_number="F1",
            operation_type=OperationType.arrival,
            runway_id="R1",
            gate_id="G1",
            start_sec=0,
            end_sec=600,
        )
        schedule = Schedule(placements=(placement,), unscheduled=())
        state.add_flight(flight)
        state.set_latest_schedule(schedule)
        state.reset()
        assert state.flights == {}
        assert state.latest_schedule is None

    def test_add_and_get_flight_round_trip(self):
        flight = Flight(
            flight_number="F1",
            operation_type=OperationType.arrival,
            priority=Priority.high,
        )
        state.add_flight(flight)
        result = state.get_flight("F1")
        assert result == flight

    def test_get_flight_returns_none_for_missing(self):
        assert state.get_flight("NONEXISTENT") is None

    def test_replace_flights_after_schedule(self):
        flight_a = Flight(
            flight_number="A1",
            operation_type=OperationType.arrival,
            priority=Priority.high,
        )
        flight_b = Flight(
            flight_number="B1",
            operation_type=OperationType.departure,
            priority=Priority.medium,
        )
        state.add_flight(flight_a)
        updated = {"B1": flight_b}
        state.replace_flights_after_schedule(updated)
        assert state.flights == {"B1": flight_b}
        assert state.get_flight("A1") is None
