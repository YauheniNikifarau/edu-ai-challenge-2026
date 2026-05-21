"""VS-1 Morning Rush acceptance test — spec.md §9 VS-1.

Fixture config (recorded per epics AC):
  ATC_RUNWAYS=[{"id":"R1","length_m":3500},{"id":"R2","length_m":3000}]
  ATC_GATE_COUNT=4, ATC_GROUND_CREW_COUNT=3
  ATC_RUNWAY_SEP_TAKEOFF_SEC=120, ATC_RUNWAY_SEP_LANDING_SEC=180, ATC_RUNWAY_SEP_MIXED_SEC=240
  ATC_GATE_TURNAROUND_SEC=300, ATC_DEPENDENCY_BUFFER_SEC=600
  ATC_SCHEDULING_HORIZON_SEC=86400
  ATC_DURATION_ARRIVAL_SEC=1200, ATC_DURATION_DEPARTURE_SEC=1200

Flights submitted (6, no deps, exercising runway contention from flight 3 onward):
  AA001 arrival  high
  AA002 departure high
  AA003 arrival  medium
  AA004 departure medium
  AA005 arrival  low
  AA006 departure low
"""
import json
from collections import defaultdict

import pytest

from atc_mcp.config import load_config
from atc_mcp.domain.state import state
from atc_mcp.resources import timeline_resource
from atc_mcp.tools import SubmitFlightInput, generate_schedule, get_airport_status, submit_flight

PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}

FLIGHTS = [
    ("AA001", "arrival",   "high"),
    ("AA002", "departure", "high"),
    ("AA003", "arrival",   "medium"),
    ("AA004", "departure", "medium"),
    ("AA005", "arrival",   "low"),
    ("AA006", "departure", "low"),
]


def setup_function(function):
    state.reset()


def _submit_all():
    """Submit all FLIGHTS to clean state; return {flight_number: priority} map."""
    priority_map = {}
    for flight_number, op_type, priority in FLIGHTS:
        res = submit_flight(SubmitFlightInput(
            flight_number=flight_number,
            operation_type=op_type,
            priority=priority,
        ))
        assert "error" not in res, f"submit_flight failed: {res}"
        priority_map[flight_number] = priority
    return priority_map


def test_all_flights_scheduled(valid_env):
    state.config = load_config()
    priority_map = _submit_all()
    result = generate_schedule()
    assert result["unscheduled"] == [], f"Unexpected unscheduled: {result['unscheduled']}"
    assert len(result["schedule"]) == len(FLIGHTS)


def test_no_runway_overlap(valid_env):
    state.config = load_config()
    _submit_all()
    result = generate_schedule()
    by_runway = defaultdict(list)
    for p in result["schedule"]:
        by_runway[p["runway_id"]].append(p)
    for runway_id, placements in by_runway.items():
        placements.sort(key=lambda p: p["start_sec"])
        for i in range(len(placements) - 1):
            assert placements[i]["end_sec"] <= placements[i + 1]["start_sec"], (
                f"Runway {runway_id} overlap between {placements[i]} and {placements[i+1]}"
            )


def test_no_gate_overlap(valid_env):
    state.config = load_config()
    _submit_all()
    result = generate_schedule()
    by_gate = defaultdict(list)
    for p in result["schedule"]:
        by_gate[p["gate_id"]].append(p)
    for gate_id, placements in by_gate.items():
        placements.sort(key=lambda p: p["start_sec"])
        for i in range(len(placements) - 1):
            assert placements[i]["end_sec"] <= placements[i + 1]["start_sec"], (
                f"Gate {gate_id} overlap between {placements[i]} and {placements[i+1]}"
            )


def test_priority_ordering_per_runway(valid_env):
    state.config = load_config()
    priority_map = _submit_all()
    result = generate_schedule()
    by_runway = defaultdict(list)
    for p in result["schedule"]:
        by_runway[p["runway_id"]].append(p)
    for runway_id, placements in by_runway.items():
        placements.sort(key=lambda p: p["start_sec"])
        ranks = [PRIORITY_RANK[priority_map[p["flight_number"]]] for p in placements]
        assert ranks == sorted(ranks), (
            f"Runway {runway_id}: priority ordering violated. "
            f"Flights by start: {[p['flight_number'] for p in placements]}, ranks: {ranks}"
        )


def test_airport_status_no_unscheduled(valid_env):
    state.config = load_config()
    _submit_all()
    generate_schedule()
    status = get_airport_status()
    assert status["unscheduled"] == []


def test_determinism(valid_env):
    outputs = []
    for _ in range(5):
        state.reset()
        state.config = load_config()
        _submit_all()
        run = generate_schedule()
        outputs.append(json.dumps(run, sort_keys=True, separators=(",", ":")))
    assert len(set(outputs)) == 1, "generate_schedule is not deterministic across 5 runs"


def test_timeline_consistent_with_schedule(valid_env):
    state.config = load_config()
    _submit_all()
    result = generate_schedule()
    events = json.loads(timeline_resource())["events"]
    assert len(events) == len(FLIGHTS)
    sched_keys = {(p["flight_number"], p["runway_id"]) for p in result["schedule"]}
    for ev in events:
        assert (ev["flight_number"], ev["runway_id"]) in sched_keys
