import json

import pytest

from atc_mcp.config import load_config
from atc_mcp.domain.state import state
from atc_mcp.resources import runways_resource, timeline_resource
from atc_mcp.tools import SubmitFlightInput, generate_schedule, submit_flight


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


def test_timeline_no_schedule_yet(cfg):
    result = timeline_resource()
    data = json.loads(result)
    
    assert data == {"events": []}


def test_runways_no_schedule_yet(cfg):
    result = runways_resource()
    data = json.loads(result)
    
    assert "runways" in data
    assert len(data["runways"]) == 2
    
    for runway in data["runways"]:
        assert "id" in runway
        assert "length_m" in runway
        assert runway["scheduled_operations"] == []
        assert runway["busy_intervals_sec"] == []
        assert runway["next_free_sec"] == 0


def test_timeline_after_schedule(cfg):
    submit_flight(SubmitFlightInput(flight_number="F1", operation_type="arrival", priority="high"))
    submit_flight(SubmitFlightInput(flight_number="F2", operation_type="departure", priority="medium"))
    
    generate_schedule()
    
    result = timeline_resource()
    data = json.loads(result)
    
    assert "events" in data
    assert len(data["events"]) == 2
    
    for event in data["events"]:
        assert "start_sec" in event
        assert "end_sec" in event
        assert "flight_number" in event
        assert "operation_type" in event
        assert "runway_id" in event
        assert "gate_id" in event
        assert "depends_on" in event
    
    events = data["events"]
    for i in range(len(events) - 1):
        e1, e2 = events[i], events[i + 1]
        key1 = (e1["start_sec"], e1["runway_id"], e1["flight_number"])
        key2 = (e2["start_sec"], e2["runway_id"], e2["flight_number"])
        assert key1 <= key2


def test_timeline_depends_on_field(cfg):
    submit_flight(SubmitFlightInput(flight_number="F1", operation_type="arrival", priority="high"))
    submit_flight(SubmitFlightInput(
        flight_number="F2",
        operation_type="departure",
        priority="medium",
        dependencies=["F1"]
    ))
    
    generate_schedule()
    
    result = timeline_resource()
    data = json.loads(result)
    
    events_by_fn = {e["flight_number"]: e for e in data["events"]}
    
    assert events_by_fn["F1"]["depends_on"] == []
    assert events_by_fn["F2"]["depends_on"] == ["F1"]


def test_runways_after_schedule(cfg):
    submit_flight(SubmitFlightInput(flight_number="F1", operation_type="arrival", priority="high"))
    submit_flight(SubmitFlightInput(flight_number="F2", operation_type="departure", priority="medium"))
    
    generate_schedule()
    
    result = runways_resource()
    data = json.loads(result)
    
    assert "runways" in data
    
    total_ops = sum(len(r["scheduled_operations"]) for r in data["runways"])
    assert total_ops == 2
    
    for runway in data["runways"]:
        ops = runway["scheduled_operations"]
        for op in ops:
            assert "flight_number" in op
            assert "operation_type" in op
            assert "start_sec" in op
            assert "end_sec" in op
        
        if len(ops) > 0:
            assert len(runway["busy_intervals_sec"]) == len(ops)
            assert runway["next_free_sec"] > 0
            
            for i in range(len(ops) - 1):
                assert ops[i]["start_sec"] <= ops[i + 1]["start_sec"]


def test_runways_sorted_by_id_lex(cfg):
    result = runways_resource()
    data = json.loads(result)
    
    runway_ids = [r["id"] for r in data["runways"]]
    assert runway_ids == sorted(runway_ids)


def test_determinism_timeline(cfg):
    submit_flight(SubmitFlightInput(flight_number="F1", operation_type="arrival", priority="high"))
    submit_flight(SubmitFlightInput(flight_number="F2", operation_type="departure", priority="medium"))
    
    generate_schedule()
    
    results = [timeline_resource() for _ in range(10)]
    
    for i in range(1, len(results)):
        assert results[i] == results[0]


def test_determinism_runways(cfg):
    submit_flight(SubmitFlightInput(flight_number="F1", operation_type="arrival", priority="high"))
    submit_flight(SubmitFlightInput(flight_number="F2", operation_type="departure", priority="medium"))
    
    generate_schedule()
    
    results = [runways_resource() for _ in range(10)]
    
    for i in range(1, len(results)):
        assert results[i] == results[0]
