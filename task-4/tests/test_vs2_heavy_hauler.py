import json

import pytest

from atc_mcp.domain.models import FlightState
from atc_mcp.domain.state import state
from atc_mcp.tools import SubmitFlightInput, generate_schedule, get_airport_status, submit_flight


@pytest.fixture(autouse=True)
def reset_state(valid_env):
    state.reset()
    yield
    state.reset()


def _submit_scenario():
    """Submit heavy hauler + 3 valid flights for VS-2 scenario."""
    submit_flight(
        SubmitFlightInput(
            flight_number="HH1",
            operation_type="departure",
            priority="high",
            runway_requirements={"min_length_m": 4500},
        )
    )
    submit_flight(SubmitFlightInput(flight_number="F1", operation_type="arrival", priority="medium"))
    submit_flight(SubmitFlightInput(flight_number="F2", operation_type="departure", priority="low"))
    submit_flight(SubmitFlightInput(flight_number="F3", operation_type="arrival", priority="high"))


def test_heavy_hauler_unschedulable():
    _submit_scenario()
    result = generate_schedule()
    
    heavy_flight = state.get_flight("HH1")
    assert heavy_flight.state == FlightState.unschedulable
    assert (
        heavy_flight.unscheduled_reason
        == "no runway meets minimum length 4500m (available runways: R1 3500m, R2 3000m)"
    )
    
    assert len(result["unscheduled"]) == 1
    assert result["unscheduled"][0]["flight_number"] == "HH1"
    assert (
        result["unscheduled"][0]["reason"]
        == "no runway meets minimum length 4500m (available runways: R1 3500m, R2 3000m)"
    )


def test_valid_flights_all_scheduled():
    _submit_scenario()
    generate_schedule()
    
    for flight_number in ["F1", "F2", "F3"]:
        flight = state.get_flight(flight_number)
        assert flight.state == FlightState.scheduled


def test_airport_status_unscheduled_contains_only_heavy():
    _submit_scenario()
    generate_schedule()
    
    status = get_airport_status()
    assert len(status["unscheduled"]) == 1
    assert status["unscheduled"][0]["flight_number"] == "HH1"


def test_determinism():
    results = []
    for _ in range(5):
        state.reset()
        _submit_scenario()
        result = generate_schedule()
        results.append(json.dumps(result, sort_keys=True, separators=(",", ":")))
    assert len(set(results)) == 1
