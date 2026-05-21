import json

from atc_mcp.config import load_config
from atc_mcp.domain.state import state
from atc_mcp.resources import timeline_resource
from atc_mcp.tools import SubmitFlightInput, analyze_bottleneck, generate_schedule, submit_flight


def setup_function(function):
    state.reset()


def test_vs3_both_flights_scheduled(valid_env):
    config = load_config()
    state.config = config
    
    submit_flight(SubmitFlightInput(
        flight_number="IN001",
        operation_type="arrival",
        priority="medium"
    ))
    submit_flight(SubmitFlightInput(
        flight_number="OUT002",
        operation_type="departure",
        priority="medium",
        dependencies=["IN001"]
    ))
    
    sched = generate_schedule()
    
    assert sched["unscheduled"] == [], "Both flights must be scheduled"
    assert len(sched["schedule"]) == 2, "Expected exactly 2 scheduled flights"
    
    scheduled_flights = {p["flight_number"]: p for p in sched["schedule"]}
    assert "IN001" in scheduled_flights, "IN001 must be scheduled"
    assert "OUT002" in scheduled_flights, "OUT002 must be scheduled"
    
    in001 = scheduled_flights["IN001"]
    out002 = scheduled_flights["OUT002"]
    
    assert in001["start_sec"] == 0, "IN001 should start at t=0"
    assert in001["end_sec"] == 1200, "IN001 should end at t=1200"
    assert out002["start_sec"] == 1800, "OUT002 should start at t=1800"
    assert out002["end_sec"] == 3000, "OUT002 should end at t=3000"


def test_vs3_dependency_buffer_enforced(valid_env):
    config = load_config()
    state.config = config
    
    submit_flight(SubmitFlightInput(
        flight_number="IN001",
        operation_type="arrival",
        priority="medium"
    ))
    submit_flight(SubmitFlightInput(
        flight_number="OUT002",
        operation_type="departure",
        priority="medium",
        dependencies=["IN001"]
    ))
    
    sched = generate_schedule()
    
    scheduled_flights = {p["flight_number"]: p for p in sched["schedule"]}
    in001 = scheduled_flights["IN001"]
    out002 = scheduled_flights["OUT002"]
    
    dep_buffer = 600
    assert out002["start_sec"] >= in001["end_sec"] + dep_buffer, \
        "Dependency buffer must be enforced (inequality)"
    assert out002["start_sec"] - in001["end_sec"] == dep_buffer, \
        "Dependency buffer should be exactly 600 seconds (binding constraint)"


def test_vs3_timeline_order(valid_env):
    config = load_config()
    state.config = config
    
    submit_flight(SubmitFlightInput(
        flight_number="IN001",
        operation_type="arrival",
        priority="medium"
    ))
    submit_flight(SubmitFlightInput(
        flight_number="OUT002",
        operation_type="departure",
        priority="medium",
        dependencies=["IN001"]
    ))
    
    generate_schedule()
    
    timeline_json = json.loads(timeline_resource())
    events = timeline_json["events"]
    
    assert len(events) == 2, "Timeline should contain exactly 2 events"
    assert events[0]["flight_number"] == "IN001", "IN001 should appear first in timeline"
    assert events[1]["flight_number"] == "OUT002", "OUT002 should appear second in timeline"
    
    assert events[0]["start_sec"] == 0
    assert events[0]["end_sec"] == 1200
    assert events[0]["operation_type"] == "arrival"
    assert events[0]["runway_id"] == "R1"
    assert events[0]["gate_id"] == "G1"
    assert events[0]["depends_on"] == []
    
    assert events[1]["start_sec"] == 1800
    assert events[1]["end_sec"] == 3000
    assert events[1]["operation_type"] == "departure"
    assert events[1]["runway_id"] == "R1"
    assert events[1]["gate_id"] == "G1"
    assert events[1]["depends_on"] == ["IN001"], "OUT002 dependency should be visible in timeline"


def test_vs3_bottleneck_chain(valid_env):
    config = load_config()
    state.config = config
    
    submit_flight(SubmitFlightInput(
        flight_number="IN001",
        operation_type="arrival",
        priority="medium"
    ))
    submit_flight(SubmitFlightInput(
        flight_number="OUT002",
        operation_type="departure",
        priority="medium",
        dependencies=["IN001"]
    ))
    
    generate_schedule()
    
    result = analyze_bottleneck()
    
    assert result["chain"] == ["IN001", "OUT002"], "Chain should contain IN001 followed by OUT002"
    assert result["total_duration_seconds"] == 3000, "Total duration should be 3000 seconds"
    assert result["operation_durations"] == [1200, 1200], "Operation durations should be [1200, 1200]"
    assert result["dependency_buffers"] == [600], "Dependency buffers should be [600]"
    
    assert len(result["operation_durations"]) == len(result["chain"]), \
        "operation_durations length must equal chain length"
    assert len(result["dependency_buffers"]) == len(result["chain"]) - 1, \
        "dependency_buffers length must equal chain length - 1"


def test_vs3_determinism(valid_env):
    results = []
    for _ in range(5):
        state.reset()
        config = load_config()
        state.config = config
        
        submit_flight(SubmitFlightInput(
            flight_number="IN001",
            operation_type="arrival",
            priority="medium"
        ))
        submit_flight(SubmitFlightInput(
            flight_number="OUT002",
            operation_type="departure",
            priority="medium",
            dependencies=["IN001"]
        ))
        
        sched = generate_schedule()
        serialised = json.dumps(sched, sort_keys=True, separators=(",", ":"))
        results.append(serialised)
    
    assert len(set(results)) == 1, "generate_schedule is not deterministic across runs"
