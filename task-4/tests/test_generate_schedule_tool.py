import json

import pytest

from atc_mcp.config import load_config
from atc_mcp.domain.models import FlightState
from atc_mcp.domain.state import state
from atc_mcp.tools import SubmitFlightInput, cancel_flight, generate_schedule, submit_flight, CancelFlightInput


@pytest.fixture(autouse=True)
def clean_state(valid_env):
    state.reset()
    yield
    state.reset()


@pytest.fixture
def cfg(valid_env):
    c = load_config()
    state.set_config(c)
    return c


def test_happy_path_scheduled_flights(cfg):
    submit_flight(SubmitFlightInput(flight_number="AA123", operation_type="arrival", priority="high"))
    submit_flight(SubmitFlightInput(flight_number="BB456", operation_type="departure", priority="medium"))
    
    result = generate_schedule()
    
    assert "schedule" in result
    assert "unscheduled" in result
    assert "completion_time_seconds" in result
    assert "summary" in result
    
    assert result["summary"]["scheduled_count"] == 2
    assert result["summary"]["unscheduled_count"] == 0
    assert result["summary"]["cancelled_count"] == 0
    
    assert len(result["schedule"]) == 2
    assert len(result["unscheduled"]) == 0
    
    assert state.latest_schedule is not None
    assert len(state.latest_schedule.placements) == 2
    
    for fn in ["AA123", "BB456"]:
        assert state.flights[fn].state == FlightState.scheduled


def test_unschedulable_flight(cfg):
    submit_flight(SubmitFlightInput(
        flight_number="HUGE1",
        operation_type="arrival",
        priority="high",
        runway_requirements={"min_length_m": 5000}
    ))
    
    result = generate_schedule()
    
    assert result["summary"]["scheduled_count"] == 0
    assert result["summary"]["unscheduled_count"] == 1
    assert len(result["unscheduled"]) == 1
    
    unscheduled_item = result["unscheduled"][0]
    assert unscheduled_item["flight_number"] == "HUGE1"
    assert unscheduled_item["reason"] != ""
    assert "length" in unscheduled_item["reason"].lower()
    
    assert state.flights["HUGE1"].state == FlightState.unschedulable
    assert state.flights["HUGE1"].unscheduled_reason is not None


def test_flight_state_mutation(cfg):
    submit_flight(SubmitFlightInput(flight_number="F1", operation_type="arrival", priority="high"))
    submit_flight(SubmitFlightInput(flight_number="F2", operation_type="departure", priority="medium"))
    
    assert state.flights["F1"].state == FlightState.queued
    assert state.flights["F2"].state == FlightState.queued
    
    generate_schedule()
    
    assert state.flights["F1"].state == FlightState.scheduled
    assert state.flights["F2"].state == FlightState.scheduled


def test_empty_queue(cfg):
    result = generate_schedule()
    
    assert result["schedule"] == []
    assert result["unscheduled"] == []
    assert result["completion_time_seconds"] is None
    assert result["summary"]["scheduled_count"] == 0
    assert result["summary"]["unscheduled_count"] == 0
    assert result["summary"]["cancelled_count"] == 0


def test_cancelled_flights_preserved(cfg):
    submit_flight(SubmitFlightInput(flight_number="F1", operation_type="arrival", priority="high"))
    submit_flight(SubmitFlightInput(flight_number="F2", operation_type="departure", priority="medium"))
    
    cancel_flight(CancelFlightInput(flight_number="F1"))
    
    result = generate_schedule()
    
    assert result["summary"]["scheduled_count"] == 1
    assert result["summary"]["unscheduled_count"] == 0
    assert result["summary"]["cancelled_count"] == 1
    
    assert state.flights["F1"].state == FlightState.cancelled
    assert state.flights["F2"].state == FlightState.scheduled
    
    scheduled_numbers = {item["flight_number"] for item in result["schedule"]}
    assert "F1" not in scheduled_numbers
    assert "F2" in scheduled_numbers


def test_determinism(cfg):
    submit_flight(SubmitFlightInput(flight_number="F1", operation_type="arrival", priority="high"))
    submit_flight(SubmitFlightInput(flight_number="F2", operation_type="departure", priority="medium"))
    
    result1 = generate_schedule()
    
    state.reset()
    state.set_config(cfg)
    submit_flight(SubmitFlightInput(flight_number="F1", operation_type="arrival", priority="high"))
    submit_flight(SubmitFlightInput(flight_number="F2", operation_type="departure", priority="medium"))
    
    result2 = generate_schedule()
    
    assert json.dumps(result1, sort_keys=True) == json.dumps(result2, sort_keys=True)
