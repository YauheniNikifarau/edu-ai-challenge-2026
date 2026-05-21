"""Placement tests for the scheduling algorithm (Story 3.1 AC)."""
from atc_mcp.config import load_config
from atc_mcp.domain.models import (
    Flight,
    FlightState,
    OperationType,
    Priority,
    RunwayRequirements,
)
from atc_mcp.scheduler.algorithm import schedule


# ---------------------------------------------------------------------------
# Test 1: single arrival is placed at t=0 on (R1, G1)
# ---------------------------------------------------------------------------

def test_single_arrival_placed_at_t0(valid_env):
    config = load_config()
    flight = Flight(
        flight_number="AA001",
        operation_type=OperationType.arrival,
        priority=Priority.medium,
    )
    result = schedule((flight,), config)

    assert len(result.placements) == 1
    assert len(result.unscheduled) == 0

    p = result.placements[0]
    assert p.flight_number == "AA001"
    assert p.runway_id == "R1"
    assert p.gate_id == "G1"
    assert p.start_sec == 0
    assert p.end_sec == config.duration_arrival_sec
    assert result.completion_time_seconds == config.duration_arrival_sec


# ---------------------------------------------------------------------------
# Test 2: two same-runway arrivals respect landing separation
# ---------------------------------------------------------------------------

def test_same_runway_arrivals_respect_separation(valid_env, monkeypatch):
    monkeypatch.setenv("ATC_RUNWAYS", '[{"id":"R1","length_m":3500}]')
    config = load_config()
    f1 = Flight(flight_number="AA001", operation_type=OperationType.arrival, priority=Priority.medium)
    f2 = Flight(flight_number="AA002", operation_type=OperationType.arrival, priority=Priority.medium)

    result = schedule((f1, f2), config)

    assert len(result.placements) == 2

    p1 = result.placements[0]
    p2 = result.placements[1]
    assert p1.flight_number == "AA001"
    assert p2.flight_number == "AA002"
    assert p1.runway_id == "R1"
    assert p2.runway_id == "R1"
    assert p1.start_sec == 0
    assert p1.end_sec == config.duration_arrival_sec
    # Runway landing separation must be respected; gate G2 is free so that constraint doesn't bind
    assert p2.start_sec == config.duration_arrival_sec + config.runway_sep_landing_sec
    assert p2.end_sec == p2.start_sec + config.duration_arrival_sec


# ---------------------------------------------------------------------------
# Test 3: two same-gate departures respect gate turnaround
# ---------------------------------------------------------------------------

def test_same_gate_departures_respect_turnaround(valid_env, monkeypatch):
    monkeypatch.setenv("ATC_GATE_COUNT", "1")
    config = load_config()
    f1 = Flight(flight_number="AA001", operation_type=OperationType.departure, priority=Priority.medium)
    f2 = Flight(flight_number="AA002", operation_type=OperationType.departure, priority=Priority.medium)

    result = schedule((f1, f2), config)

    assert len(result.placements) == 2

    p1 = result.placements[0]
    p2 = result.placements[1]
    assert p1.gate_id == "G1"
    assert p2.gate_id == "G1"
    assert p1.start_sec == 0
    assert p1.end_sec == config.duration_departure_sec
    # Gate turnaround (300) > runway takeoff sep (120): gate is the binding constraint
    assert p2.start_sec == config.duration_departure_sec + config.gate_turnaround_sec
    assert p2.end_sec == p2.start_sec + config.duration_departure_sec


# ---------------------------------------------------------------------------
# Test 4: arrival→departure on same runway uses mixed separation
# ---------------------------------------------------------------------------

def test_mixed_op_type_uses_mixed_separation(valid_env, monkeypatch):
    monkeypatch.setenv("ATC_RUNWAYS", '[{"id":"R1","length_m":3500}]')
    config = load_config()
    f1 = Flight(flight_number="AA001", operation_type=OperationType.arrival, priority=Priority.medium)
    f2 = Flight(flight_number="AA002", operation_type=OperationType.departure, priority=Priority.medium)

    result = schedule((f1, f2), config)

    assert len(result.placements) == 2

    p_arr = next(p for p in result.placements if p.operation_type == OperationType.arrival)
    p_dep = next(p for p in result.placements if p.operation_type == OperationType.departure)

    assert p_arr.runway_id == "R1"
    assert p_dep.runway_id == "R1"
    assert p_arr.start_sec == 0
    assert p_arr.end_sec == config.duration_arrival_sec
    # Mixed sep on same runway; departure will pick G2 (free, so gate doesn't bind)
    assert p_dep.start_sec == config.duration_arrival_sec + config.runway_sep_mixed_sec


# ---------------------------------------------------------------------------
# Test 5: runway-requirement matching (one schedules, one doesn't)
# ---------------------------------------------------------------------------

def test_runway_requirement_matching(valid_env):
    config = load_config()
    f_ok = Flight(
        flight_number="AA001",
        operation_type=OperationType.arrival,
        priority=Priority.medium,
    )
    f_big = Flight(
        flight_number="AA002",
        operation_type=OperationType.arrival,
        priority=Priority.medium,
        runway_requirements=RunwayRequirements(min_length_m=4500),
    )

    result = schedule((f_ok, f_big), config)

    assert len(result.placements) == 1
    assert len(result.unscheduled) == 1

    assert result.placements[0].flight_number == "AA001"
    unsch = result.unscheduled[0]
    assert unsch.flight_number == "AA002"
    assert unsch.state == FlightState.unschedulable
    assert unsch.unscheduled_reason == (
        "no runway meets minimum length 4500m (available runways: R1 3500m, R2 3000m)"
    )


# ---------------------------------------------------------------------------
# Test 6: horizon overflow → unschedulable with exact reason string
# ---------------------------------------------------------------------------

def test_horizon_overflow_unschedulable(valid_env, monkeypatch):
    monkeypatch.setenv("ATC_SCHEDULING_HORIZON_SEC", "100")
    config = load_config()
    flight = Flight(
        flight_number="AA001",
        operation_type=OperationType.arrival,
        priority=Priority.medium,
    )

    result = schedule((flight,), config)

    assert len(result.placements) == 0
    assert len(result.unscheduled) == 1
    assert result.completion_time_seconds is None

    unsch = result.unscheduled[0]
    assert unsch.state == FlightState.unschedulable
    assert unsch.unscheduled_reason == "would exceed scheduling horizon"


# ---------------------------------------------------------------------------
# Test 7: priority ordering — high before low regardless of submission order
# ---------------------------------------------------------------------------

def test_priority_ordering_high_before_low(valid_env, monkeypatch):
    monkeypatch.setenv("ATC_RUNWAYS", '[{"id":"R1","length_m":3500}]')
    config = load_config()
    f_low = Flight(flight_number="AA001", operation_type=OperationType.arrival, priority=Priority.low)
    f_high = Flight(flight_number="AA002", operation_type=OperationType.arrival, priority=Priority.high)

    # f_low submitted first; sort must elevate f_high
    result = schedule((f_low, f_high), config)

    assert len(result.placements) == 2

    high_p = next(p for p in result.placements if p.flight_number == "AA002")
    low_p = next(p for p in result.placements if p.flight_number == "AA001")

    # High-priority flight gets t=0; low-priority waits on single runway
    assert high_p.start_sec == 0
    assert low_p.start_sec == config.duration_arrival_sec + config.runway_sep_landing_sec
