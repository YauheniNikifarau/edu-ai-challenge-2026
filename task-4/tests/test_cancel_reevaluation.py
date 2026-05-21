import pytest

from atc_mcp.config import load_config
from atc_mcp.domain.models import Flight, FlightState, OperationType, Priority
from atc_mcp.domain.state import state
from atc_mcp.tools import CancelFlightInput, SubmitFlightInput, cancel_flight, generate_schedule, submit_flight


def setup_function(function):
    state.reset()


def test_cancel_root_of_chain(valid_env):
    state.config = load_config()
    
    submit_flight(SubmitFlightInput(
        flight_number="A",
        operation_type="arrival",
        priority="high",
    ))
    submit_flight(SubmitFlightInput(
        flight_number="B",
        operation_type="departure",
        priority="high",
        dependencies=["A"],
    ))
    submit_flight(SubmitFlightInput(
        flight_number="C",
        operation_type="arrival",
        priority="high",
        dependencies=["B"],
    ))
    
    generate_schedule()
    
    assert state.get_flight("A").state == FlightState.scheduled
    assert state.get_flight("B").state == FlightState.scheduled
    assert state.get_flight("C").state == FlightState.scheduled
    
    result = cancel_flight(CancelFlightInput(flight_number="A"))
    
    assert result["cancelled"] == "A"
    assert len(result["dependents_reevaluated"]) == 2
    
    assert state.get_flight("A").state == FlightState.cancelled
    assert state.get_flight("B").state == FlightState.unschedulable
    assert state.get_flight("C").state == FlightState.unschedulable
    
    dependents = result["dependents_reevaluated"]
    assert dependents[0]["flight_number"] == "B"
    assert dependents[0]["previous_state"] == "scheduled"
    assert dependents[0]["new_state"] == "unschedulable"
    assert "dependency A is not scheduled" in dependents[0]["reason"]
    
    assert dependents[1]["flight_number"] == "C"
    assert dependents[1]["previous_state"] == "scheduled"
    assert dependents[1]["new_state"] == "unschedulable"
    assert "dependency B is not scheduled" in dependents[1]["reason"]


def test_cancel_leaf(valid_env):
    state.config = load_config()
    
    submit_flight(SubmitFlightInput(
        flight_number="F1",
        operation_type="arrival",
        priority="high",
    ))
    
    generate_schedule()
    
    assert state.get_flight("F1").state == FlightState.scheduled
    
    result = cancel_flight(CancelFlightInput(flight_number="F1"))
    
    assert result["cancelled"] == "F1"
    assert result["dependents_reevaluated"] == []
    assert state.get_flight("F1").state == FlightState.cancelled
    assert state.latest_schedule is not None


def test_cancel_middle_of_diamond(valid_env):
    state.config = load_config()
    
    submit_flight(SubmitFlightInput(
        flight_number="A",
        operation_type="arrival",
        priority="high",
    ))
    submit_flight(SubmitFlightInput(
        flight_number="B",
        operation_type="departure",
        priority="high",
        dependencies=["A"],
    ))
    submit_flight(SubmitFlightInput(
        flight_number="C",
        operation_type="arrival",
        priority="high",
        dependencies=["A"],
    ))
    submit_flight(SubmitFlightInput(
        flight_number="D",
        operation_type="departure",
        priority="high",
        dependencies=["B", "C"],
    ))
    
    generate_schedule()
    
    assert state.get_flight("A").state == FlightState.scheduled
    assert state.get_flight("B").state == FlightState.scheduled
    assert state.get_flight("C").state == FlightState.scheduled
    assert state.get_flight("D").state == FlightState.scheduled
    
    result = cancel_flight(CancelFlightInput(flight_number="B"))
    
    assert result["cancelled"] == "B"
    assert len(result["dependents_reevaluated"]) == 1
    
    assert state.get_flight("A").state == FlightState.scheduled
    assert state.get_flight("B").state == FlightState.cancelled
    assert state.get_flight("C").state == FlightState.scheduled
    assert state.get_flight("D").state == FlightState.unschedulable
    
    dependents = result["dependents_reevaluated"]
    assert dependents[0]["flight_number"] == "D"
    assert dependents[0]["previous_state"] == "scheduled"
    assert dependents[0]["new_state"] == "unschedulable"
    assert "dependency B is not scheduled" in dependents[0]["reason"]


def test_cancel_frees_resource(valid_env, monkeypatch):
    monkeypatch.setenv("ATC_RUNWAYS", '[{"id":"R1","length_m":3500}]')
    monkeypatch.setenv("ATC_GATE_COUNT", "1")
    monkeypatch.setenv("ATC_GROUND_CREW_COUNT", "1")
    monkeypatch.setenv("ATC_SCHEDULING_HORIZON_SEC", "1800")
    
    state.config = load_config()
    
    submit_flight(SubmitFlightInput(
        flight_number="F1",
        operation_type="arrival",
        priority="high",
    ))
    submit_flight(SubmitFlightInput(
        flight_number="F2",
        operation_type="arrival",
        priority="low",
    ))
    
    generate_schedule()
    
    f1_state = state.get_flight("F1").state
    f2_state = state.get_flight("F2").state
    
    if f1_state == FlightState.scheduled and f2_state == FlightState.unschedulable:
        result = cancel_flight(CancelFlightInput(flight_number="F1"))
        
        assert result["cancelled"] == "F1"
        assert len(result["dependents_reevaluated"]) == 1
        
        assert state.get_flight("F1").state == FlightState.cancelled
        assert state.get_flight("F2").state == FlightState.scheduled
        
        dependents = result["dependents_reevaluated"]
        assert dependents[0]["flight_number"] == "F2"
        assert dependents[0]["previous_state"] == "unschedulable"
        assert dependents[0]["new_state"] == "scheduled"
        assert dependents[0]["reason"] is None
    elif f2_state == FlightState.scheduled and f1_state == FlightState.unschedulable:
        result = cancel_flight(CancelFlightInput(flight_number="F2"))
        
        assert result["cancelled"] == "F2"
        assert len(result["dependents_reevaluated"]) == 1
        
        assert state.get_flight("F2").state == FlightState.cancelled
        assert state.get_flight("F1").state == FlightState.scheduled
        
        dependents = result["dependents_reevaluated"]
        assert dependents[0]["flight_number"] == "F1"
        assert dependents[0]["previous_state"] == "unschedulable"
        assert dependents[0]["new_state"] == "scheduled"
        assert dependents[0]["reason"] is None
    else:
        pytest.fail(f"Expected one flight scheduled and one unschedulable, got F1={f1_state}, F2={f2_state}")
