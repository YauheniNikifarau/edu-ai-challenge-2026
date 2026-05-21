import pytest
from pydantic import ValidationError

from atc_mcp.domain.state import state
from atc_mcp.tools import SubmitFlightInput, submit_flight


@pytest.fixture(autouse=True)
def reset_state(valid_env):
    state.reset()
    yield
    state.reset()


def test_submit_arrival_happy_path():
    data = SubmitFlightInput(flight_number="AA123", operation_type="arrival", priority="high")
    result = submit_flight(data)
    assert "flight" in result
    flight = result["flight"]
    assert flight["flight_number"] == "AA123"
    assert flight["operation_type"] == "arrival"
    assert flight["priority"] == "high"
    assert flight["state"] == "queued"
    assert flight["unscheduled_reason"] is None
    assert flight["dependencies"] == []
    assert state.get_flight("AA123") is not None


def test_submit_departure_with_dependencies():
    f1 = SubmitFlightInput(flight_number="F1", operation_type="departure", priority="low")
    submit_flight(f1)
    f2 = SubmitFlightInput(flight_number="F2", operation_type="departure", priority="medium", dependencies=["F1"])
    result = submit_flight(f2)
    assert "flight" in result
    assert result["flight"]["flight_number"] == "F2"
    assert state.get_flight("F2").dependencies == ["F1"]


def test_submit_with_runway_requirements():
    data = SubmitFlightInput(
        flight_number="RW1",
        operation_type="arrival",
        priority="high",
        runway_requirements={"min_length_m": 3500},
    )
    result = submit_flight(data)
    assert result["flight"]["runway_requirements"]["min_length_m"] == 3500


def test_duplicate_flight_rejected():
    data = SubmitFlightInput(flight_number="F1", operation_type="arrival", priority="low")
    submit_flight(data)
    result = submit_flight(data)
    assert result == {"error": "flight F1 already exists"}
    assert len(state.flights) == 1


def test_unknown_dependency_rejected():
    data = SubmitFlightInput(flight_number="F2", operation_type="arrival", priority="low", dependencies=["F999"])
    result = submit_flight(data)
    assert result == {"error": "unknown dependency: F999"}
    assert state.get_flight("F2") is None


def test_self_dependency_rejected():
    data = SubmitFlightInput(flight_number="F1", operation_type="arrival", priority="low", dependencies=["F1"])
    result = submit_flight(data)
    assert result == {"error": "flight cannot depend on itself"}
    assert state.get_flight("F1") is None


def test_extra_field_rejected():
    with pytest.raises(ValidationError) as exc_info:
        SubmitFlightInput(
            flight_number="X1",
            operation_type="arrival",
            priority="low",
            _unknown="x",
        )
    errors = exc_info.value.errors()
    assert any("extra" in str(e).lower() or "forbidden" in str(e).lower() for e in errors)


def test_missing_required_field():
    with pytest.raises(ValidationError):
        SubmitFlightInput(operation_type="arrival", priority="low")


def test_invalid_enum_literal():
    with pytest.raises(ValidationError):
        SubmitFlightInput(flight_number="X1", operation_type="takeoff", priority="low")
