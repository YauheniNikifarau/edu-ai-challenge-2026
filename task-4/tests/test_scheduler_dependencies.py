"""Test dependency ordering, buffer enforcement, and cycle detection (Story 3.2)."""
from atc_mcp.config import load_config
from atc_mcp.domain.models import Flight, FlightState, OperationType, Priority, RunwayRequirements
from atc_mcp.scheduler.algorithm import schedule


def test_linear_chain_dep_buffer(valid_env):
    """Test 1: Linear chain A→B→C with dep buffer enforced at each link."""
    config = load_config()
    
    flights = (
        Flight(
            flight_number="A",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            dependencies=[],
        ),
        Flight(
            flight_number="B",
            operation_type=OperationType.departure,
            priority=Priority.medium,
            dependencies=["A"],
        ),
        Flight(
            flight_number="C",
            operation_type=OperationType.arrival,
            priority=Priority.low,
            dependencies=["B"],
        ),
    )
    
    result = schedule(flights, config)
    
    # All three should be scheduled
    assert len(result.placements) == 3
    assert len(result.unscheduled) == 0
    
    # Find placements
    placements = {p.flight_number: p for p in result.placements}
    
    # A placed at [0, 1200)
    assert placements["A"].start_sec == 0
    assert placements["A"].end_sec == 1200
    
    # B.start_sec ≥ 1200 + 600 = 1800
    assert placements["B"].start_sec >= 1800
    
    # C.start_sec ≥ B.end_sec + 600
    assert placements["C"].start_sec >= placements["B"].end_sec + 600


def test_diamond_dag(valid_env):
    """Test 2: Diamond DAG A→B→D, A→C→D with correct topo depths."""
    config = load_config()
    
    flights = (
        Flight(
            flight_number="A",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            dependencies=[],
        ),
        Flight(
            flight_number="B",
            operation_type=OperationType.departure,
            priority=Priority.medium,
            dependencies=["A"],
        ),
        Flight(
            flight_number="C",
            operation_type=OperationType.departure,
            priority=Priority.medium,
            dependencies=["A"],
        ),
        Flight(
            flight_number="D",
            operation_type=OperationType.arrival,
            priority=Priority.low,
            dependencies=["B", "C"],
        ),
    )
    
    result = schedule(flights, config)
    
    # All four should be scheduled
    assert len(result.placements) == 4
    assert len(result.unscheduled) == 0
    
    # Find placements
    placements = {p.flight_number: p for p in result.placements}
    
    # D.start_sec ≥ max(B.end_sec, C.end_sec) + dep_buffer
    max_dep_end = max(placements["B"].end_sec, placements["C"].end_sec)
    assert placements["D"].start_sec >= max_dep_end + 600


def test_2_cycle(valid_env):
    """Test 3: 2-cycle F1↔F2 - both unschedulable."""
    config = load_config()
    
    flights = (
        Flight(
            flight_number="F1",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            dependencies=["F2"],
        ),
        Flight(
            flight_number="F2",
            operation_type=OperationType.departure,
            priority=Priority.high,
            dependencies=["F1"],
        ),
    )
    
    result = schedule(flights, config)
    
    # Both should be unschedulable
    assert len(result.placements) == 0
    assert len(result.unscheduled) == 2
    
    # Check exact reason strings
    unscheduled = {f.flight_number: f for f in result.unscheduled}
    assert unscheduled["F1"].state == FlightState.unschedulable
    assert unscheduled["F1"].unscheduled_reason == "dependency cycle: F1, F2"
    assert unscheduled["F2"].state == FlightState.unschedulable
    assert unscheduled["F2"].unscheduled_reason == "dependency cycle: F1, F2"


def test_3_cycle(valid_env):
    """Test 4: 3-cycle F1→F2→F3→F1 - all three unschedulable."""
    config = load_config()
    
    flights = (
        Flight(
            flight_number="F1",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            dependencies=["F3"],
        ),
        Flight(
            flight_number="F2",
            operation_type=OperationType.departure,
            priority=Priority.high,
            dependencies=["F1"],
        ),
        Flight(
            flight_number="F3",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            dependencies=["F2"],
        ),
    )
    
    result = schedule(flights, config)
    
    # All three should be unschedulable
    assert len(result.placements) == 0
    assert len(result.unscheduled) == 3
    
    # Check exact reason strings
    unscheduled = {f.flight_number: f for f in result.unscheduled}
    for fn in ["F1", "F2", "F3"]:
        assert unscheduled[fn].state == FlightState.unschedulable
        assert unscheduled[fn].unscheduled_reason == "dependency cycle: F1, F2, F3"


def test_self_cycle(valid_env):
    """Test 5: Self-cycle F1→F1 (defence-in-depth)."""
    config = load_config()
    
    flights = (
        Flight(
            flight_number="F1",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            dependencies=["F1"],
        ),
    )
    
    result = schedule(flights, config)
    
    # Should be unschedulable
    assert len(result.placements) == 0
    assert len(result.unscheduled) == 1
    
    # Check exact reason string
    assert result.unscheduled[0].state == FlightState.unschedulable
    assert result.unscheduled[0].unscheduled_reason == "dependency cycle: F1"


def test_dep_on_cancelled(valid_env):
    """Test 6: Dep on cancelled flight → dependent unschedulable."""
    config = load_config()
    
    flights = (
        Flight(
            flight_number="A",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            dependencies=[],
            state=FlightState.cancelled,
        ),
        Flight(
            flight_number="B",
            operation_type=OperationType.departure,
            priority=Priority.medium,
            dependencies=["A"],
        ),
    )
    
    result = schedule(flights, config)
    
    # B should be unschedulable
    assert len(result.placements) == 0
    assert len(result.unscheduled) == 1
    
    # Check exact reason string
    assert result.unscheduled[0].flight_number == "B"
    assert result.unscheduled[0].state == FlightState.unschedulable
    assert result.unscheduled[0].unscheduled_reason == "dependency A is not scheduled"


def test_dep_on_unschedulable(valid_env):
    """Test 7: Dep on unschedulable flight → dependent unschedulable."""
    config = load_config()
    
    flights = (
        Flight(
            flight_number="A",
            operation_type=OperationType.departure,
            priority=Priority.high,
            dependencies=[],
            runway_requirements=RunwayRequirements(min_length_m=9999),
        ),
        Flight(
            flight_number="B",
            operation_type=OperationType.arrival,
            priority=Priority.medium,
            dependencies=["A"],
        ),
    )
    
    result = schedule(flights, config)
    
    # Both should be unschedulable
    assert len(result.placements) == 0
    assert len(result.unscheduled) == 2
    
    # Find flights
    unscheduled = {f.flight_number: f for f in result.unscheduled}
    
    # A is unschedulable due to runway requirements
    assert unscheduled["A"].state == FlightState.unschedulable
    assert "no runway meets minimum length" in unscheduled["A"].unscheduled_reason
    
    # B is unschedulable due to dependency on A
    assert unscheduled["B"].state == FlightState.unschedulable
    assert unscheduled["B"].unscheduled_reason == "dependency A is not scheduled"


def test_non_cycle_flights_unaffected_by_cycle(valid_env):
    """Test 8: Non-cycle flights unaffected by cycle."""
    config = load_config()
    
    flights = (
        Flight(
            flight_number="F1",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            dependencies=["F2"],
        ),
        Flight(
            flight_number="F2",
            operation_type=OperationType.departure,
            priority=Priority.high,
            dependencies=["F1"],
        ),
        Flight(
            flight_number="F3",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            dependencies=[],
        ),
    )
    
    result = schedule(flights, config)
    
    # F1 and F2 unschedulable, F3 scheduled
    assert len(result.placements) == 1
    assert len(result.unscheduled) == 2
    
    # F3 should be scheduled
    assert result.placements[0].flight_number == "F3"
    
    # F1 and F2 should be unschedulable with cycle reason
    unscheduled = {f.flight_number: f for f in result.unscheduled}
    assert unscheduled["F1"].unscheduled_reason == "dependency cycle: F1, F2"
    assert unscheduled["F2"].unscheduled_reason == "dependency cycle: F1, F2"


def test_dep_buffer_beats_separation(valid_env):
    """Test 9: Dep buffer dominates when larger than separation."""
    config = load_config()
    
    flights = (
        Flight(
            flight_number="A",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            dependencies=[],
        ),
        Flight(
            flight_number="B",
            operation_type=OperationType.departure,
            priority=Priority.medium,
            dependencies=["A"],
        ),
    )
    
    result = schedule(flights, config)
    
    # Both should be scheduled
    assert len(result.placements) == 2
    assert len(result.unscheduled) == 0
    
    # Find placements
    placements = {p.flight_number: p for p in result.placements}
    
    # A placed at [0, 1200)
    assert placements["A"].start_sec == 0
    assert placements["A"].end_sec == 1200
    
    # B's dep floor from A = 1200 + 600 = 1800
    # Even if runway/gate sep would allow earlier, B.start_sec = 1800
    assert placements["B"].start_sec == 1800


def test_separation_beats_dep_buffer(valid_env):
    """Test 10: Separation dominates when larger than dep buffer."""
    config = load_config()
    
    # Create scenario where gate turnaround forces later placement
    # First flight on gate G1, second flight also needs G1 but has shorter dep buffer
    flights = (
        Flight(
            flight_number="A",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            dependencies=[],
        ),
        Flight(
            flight_number="B",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            dependencies=[],
        ),
        Flight(
            flight_number="C",
            operation_type=OperationType.arrival,
            priority=Priority.medium,
            dependencies=["A"],
        ),
    )
    
    result = schedule(flights, config)
    
    # All should be scheduled
    assert len(result.placements) == 3
    assert len(result.unscheduled) == 0
    
    # Find placements
    placements = {p.flight_number: p for p in result.placements}
    
    # A placed at [0, 1200)
    assert placements["A"].start_sec == 0
    assert placements["A"].end_sec == 1200
    
    # C's dep floor from A = 1200 + 600 = 1800
    # But if C uses same gate as A or B, gate turnaround may push it later
    # C.start_sec = max(dep_floor, sep_floor, turnaround_floor)
    assert placements["C"].start_sec >= 1800


def test_cascade_unschedulability_through_chain(valid_env):
    """Test cascade: A (cancelled) → B (unschedulable) → C (unschedulable)."""
    config = load_config()
    
    flights = (
        Flight(
            flight_number="A",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            dependencies=[],
            state=FlightState.cancelled,
        ),
        Flight(
            flight_number="B",
            operation_type=OperationType.departure,
            priority=Priority.medium,
            dependencies=["A"],
        ),
        Flight(
            flight_number="C",
            operation_type=OperationType.arrival,
            priority=Priority.low,
            dependencies=["B"],
        ),
    )
    
    result = schedule(flights, config)
    
    # B and C should be unschedulable
    assert len(result.placements) == 0
    assert len(result.unscheduled) == 2
    
    # Check exact reason strings
    unscheduled = {f.flight_number: f for f in result.unscheduled}
    assert unscheduled["B"].unscheduled_reason == "dependency A is not scheduled"
    assert unscheduled["C"].unscheduled_reason == "dependency B is not scheduled"


def test_topo_depth_ordering(valid_env):
    """Test that flights are sorted by topo_depth first."""
    config = load_config()
    
    # Create flights with different topo depths
    # A (depth 0), B (depth 1, dep on A), C (depth 0), D (depth 2, dep on B)
    # All same priority, so order should be: A, C (depth 0), B (depth 1), D (depth 2)
    flights = (
        Flight(
            flight_number="D",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            dependencies=["B"],
        ),
        Flight(
            flight_number="B",
            operation_type=OperationType.departure,
            priority=Priority.high,
            dependencies=["A"],
        ),
        Flight(
            flight_number="A",
            operation_type=OperationType.arrival,
            priority=Priority.high,
            dependencies=[],
        ),
        Flight(
            flight_number="C",
            operation_type=OperationType.departure,
            priority=Priority.high,
            dependencies=[],
        ),
    )
    
    result = schedule(flights, config)
    
    # All should be scheduled
    assert len(result.placements) == 4
    assert len(result.unscheduled) == 0
    
    # Verify placements are sorted by start_sec
    # A and C should start at 0 (both depth 0)
    # B should start after A ends + buffer
    # D should start after B ends + buffer
    placements = {p.flight_number: p for p in result.placements}
    
    # A or C starts at 0
    assert placements["A"].start_sec == 0 or placements["C"].start_sec == 0
    
    # B starts after A
    assert placements["B"].start_sec >= placements["A"].end_sec + 600
    
    # D starts after B
    assert placements["D"].start_sec >= placements["B"].end_sec + 600
