"""Tests for bottleneck chain detection (Story 4.1)."""
import pytest

from atc_mcp.bottleneck import longest_active_chain
from atc_mcp.config import load_config
from atc_mcp.domain.models import Flight, FlightState, OperationType, Placement, Priority, Schedule
from atc_mcp.domain.state import AppState


@pytest.fixture
def config(valid_env):
    return load_config()


def test_empty_state_returns_empty_chain(config):
    """Test that empty state with no flights returns empty chain."""
    state = AppState()
    result = longest_active_chain(state, config)
    assert result.chain == []
    assert result.total_duration_seconds is None
    assert result.operation_durations == []
    assert result.dependency_buffers == []


def test_no_schedule_returns_empty_chain(config):
    """Test that state with flights but no schedule returns empty chain."""
    state = AppState()
    state.add_flight(Flight(
        flight_number="AA100",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.queued,
    ))
    result = longest_active_chain(state, config)
    assert result.chain == []
    assert result.total_duration_seconds is None


def test_single_scheduled_flight_no_deps_returns_empty(config):
    """Test that a single scheduled flight with no dependencies returns empty chain."""
    state = AppState()
    state.add_flight(Flight(
        flight_number="AA100",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
    ))
    state.set_latest_schedule(Schedule(
        placements=(
            Placement(
                flight_number="AA100",
                operation_type=OperationType.arrival,
                runway_id="R1",
                gate_id="G1",
                start_sec=0,
                end_sec=1200,
            ),
        ),
        unscheduled=(),
        completion_time_seconds=1200,
    ))
    result = longest_active_chain(state, config)
    assert result.chain == []
    assert result.total_duration_seconds is None


def test_two_chain(config):
    """Test a simple 2-flight chain."""
    state = AppState()
    state.add_flight(Flight(
        flight_number="AA100",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=[],
    ))
    state.add_flight(Flight(
        flight_number="AA200",
        operation_type=OperationType.departure,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=["AA100"],
    ))
    state.set_latest_schedule(Schedule(
        placements=(
            Placement(
                flight_number="AA100",
                operation_type=OperationType.arrival,
                runway_id="R1",
                gate_id="G1",
                start_sec=0,
                end_sec=1200,
            ),
            Placement(
                flight_number="AA200",
                operation_type=OperationType.departure,
                runway_id="R1",
                gate_id="G1",
                start_sec=2100,
                end_sec=3300,
            ),
        ),
        unscheduled=(),
        completion_time_seconds=3300,
    ))
    result = longest_active_chain(state, config)
    assert result.chain == ["AA100", "AA200"]
    assert result.operation_durations == [1200, 1200]
    assert result.dependency_buffers == [600]
    assert result.total_duration_seconds == 3000


def test_three_chain(config):
    """Test a 3-flight chain."""
    state = AppState()
    state.add_flight(Flight(
        flight_number="AA100",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=[],
    ))
    state.add_flight(Flight(
        flight_number="AA200",
        operation_type=OperationType.departure,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=["AA100"],
    ))
    state.add_flight(Flight(
        flight_number="AA300",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=["AA200"],
    ))
    state.set_latest_schedule(Schedule(
        placements=(
            Placement(
                flight_number="AA100",
                operation_type=OperationType.arrival,
                runway_id="R1",
                gate_id="G1",
                start_sec=0,
                end_sec=1200,
            ),
            Placement(
                flight_number="AA200",
                operation_type=OperationType.departure,
                runway_id="R1",
                gate_id="G1",
                start_sec=2100,
                end_sec=3300,
            ),
            Placement(
                flight_number="AA300",
                operation_type=OperationType.arrival,
                runway_id="R1",
                gate_id="G1",
                start_sec=4200,
                end_sec=5400,
            ),
        ),
        unscheduled=(),
        completion_time_seconds=5400,
    ))
    result = longest_active_chain(state, config)
    assert result.chain == ["AA100", "AA200", "AA300"]
    assert result.operation_durations == [1200, 1200, 1200]
    assert result.dependency_buffers == [600, 600]
    assert result.total_duration_seconds == 4800


def test_equal_length_chains_lex_tiebreak(config):
    """Test that equal-length chains tie-break by lex-smallest starting flight."""
    state = AppState()
    state.add_flight(Flight(
        flight_number="AA100",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=[],
    ))
    state.add_flight(Flight(
        flight_number="AA200",
        operation_type=OperationType.departure,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=["AA100"],
    ))
    state.add_flight(Flight(
        flight_number="BB100",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=[],
    ))
    state.add_flight(Flight(
        flight_number="BB200",
        operation_type=OperationType.departure,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=["BB100"],
    ))
    state.set_latest_schedule(Schedule(
        placements=(
            Placement(
                flight_number="AA100",
                operation_type=OperationType.arrival,
                runway_id="R1",
                gate_id="G1",
                start_sec=0,
                end_sec=1200,
            ),
            Placement(
                flight_number="AA200",
                operation_type=OperationType.departure,
                runway_id="R1",
                gate_id="G1",
                start_sec=2100,
                end_sec=3300,
            ),
            Placement(
                flight_number="BB100",
                operation_type=OperationType.arrival,
                runway_id="R2",
                gate_id="G2",
                start_sec=0,
                end_sec=1200,
            ),
            Placement(
                flight_number="BB200",
                operation_type=OperationType.departure,
                runway_id="R2",
                gate_id="G2",
                start_sec=2100,
                end_sec=3300,
            ),
        ),
        unscheduled=(),
        completion_time_seconds=3300,
    ))
    result = longest_active_chain(state, config)
    assert result.chain == ["AA100", "AA200"]
    assert result.total_duration_seconds == 3000


def test_chain_broken_by_cancelled_middle_flight(config):
    """Test that a cancelled middle flight breaks the chain."""
    state = AppState()
    state.add_flight(Flight(
        flight_number="AA100",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=[],
    ))
    state.add_flight(Flight(
        flight_number="AA200",
        operation_type=OperationType.departure,
        priority=Priority.high,
        state=FlightState.cancelled,
        dependencies=["AA100"],
    ))
    state.add_flight(Flight(
        flight_number="AA300",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=["AA200"],
    ))
    state.set_latest_schedule(Schedule(
        placements=(
            Placement(
                flight_number="AA100",
                operation_type=OperationType.arrival,
                runway_id="R1",
                gate_id="G1",
                start_sec=0,
                end_sec=1200,
            ),
            Placement(
                flight_number="AA300",
                operation_type=OperationType.arrival,
                runway_id="R1",
                gate_id="G1",
                start_sec=4200,
                end_sec=5400,
            ),
        ),
        unscheduled=(),
        completion_time_seconds=5400,
    ))
    result = longest_active_chain(state, config)
    assert result.chain == []
    assert result.total_duration_seconds is None


def test_chain_broken_by_unschedulable_middle_flight(config):
    """Test that an unschedulable middle flight breaks the chain."""
    state = AppState()
    state.add_flight(Flight(
        flight_number="AA100",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=[],
    ))
    state.add_flight(Flight(
        flight_number="AA200",
        operation_type=OperationType.departure,
        priority=Priority.high,
        state=FlightState.unschedulable,
        unscheduled_reason="dependency cycle",
        dependencies=["AA100"],
    ))
    state.add_flight(Flight(
        flight_number="AA300",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=["AA200"],
    ))
    state.set_latest_schedule(Schedule(
        placements=(
            Placement(
                flight_number="AA100",
                operation_type=OperationType.arrival,
                runway_id="R1",
                gate_id="G1",
                start_sec=0,
                end_sec=1200,
            ),
            Placement(
                flight_number="AA300",
                operation_type=OperationType.arrival,
                runway_id="R1",
                gate_id="G1",
                start_sec=4200,
                end_sec=5400,
            ),
        ),
        unscheduled=(
            Flight(
                flight_number="AA200",
                operation_type=OperationType.departure,
                priority=Priority.high,
                state=FlightState.unschedulable,
                unscheduled_reason="dependency cycle",
                dependencies=["AA100"],
            ),
        ),
        completion_time_seconds=5400,
    ))
    result = longest_active_chain(state, config)
    assert result.chain == []
    assert result.total_duration_seconds is None


def test_diamond_dag_longest_path(config):
    """Test diamond DAG where longest path through diamond wins."""
    state = AppState()
    state.add_flight(Flight(
        flight_number="F1",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=[],
    ))
    state.add_flight(Flight(
        flight_number="F2",
        operation_type=OperationType.departure,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=["F1"],
    ))
    state.add_flight(Flight(
        flight_number="F3",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=["F1"],
    ))
    state.add_flight(Flight(
        flight_number="F4",
        operation_type=OperationType.departure,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=["F2", "F3"],
    ))
    state.set_latest_schedule(Schedule(
        placements=(
            Placement(
                flight_number="F1",
                operation_type=OperationType.arrival,
                runway_id="R1",
                gate_id="G1",
                start_sec=0,
                end_sec=1200,
            ),
            Placement(
                flight_number="F2",
                operation_type=OperationType.departure,
                runway_id="R1",
                gate_id="G1",
                start_sec=2100,
                end_sec=3300,
            ),
            Placement(
                flight_number="F3",
                operation_type=OperationType.arrival,
                runway_id="R2",
                gate_id="G2",
                start_sec=2100,
                end_sec=2700,
            ),
            Placement(
                flight_number="F4",
                operation_type=OperationType.departure,
                runway_id="R1",
                gate_id="G1",
                start_sec=4200,
                end_sec=5400,
            ),
        ),
        unscheduled=(),
        completion_time_seconds=5400,
    ))
    result = longest_active_chain(state, config)
    assert result.chain == ["F1", "F2", "F4"]
    assert result.operation_durations == [1200, 1200, 1200]
    assert result.dependency_buffers == [600, 600]
    assert result.total_duration_seconds == 4800


def test_determinism_repeated_calls(config):
    """Test that repeated calls with identical state return identical results."""
    state = AppState()
    state.add_flight(Flight(
        flight_number="AA100",
        operation_type=OperationType.arrival,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=[],
    ))
    state.add_flight(Flight(
        flight_number="AA200",
        operation_type=OperationType.departure,
        priority=Priority.high,
        state=FlightState.scheduled,
        dependencies=["AA100"],
    ))
    state.set_latest_schedule(Schedule(
        placements=(
            Placement(
                flight_number="AA100",
                operation_type=OperationType.arrival,
                runway_id="R1",
                gate_id="G1",
                start_sec=0,
                end_sec=1200,
            ),
            Placement(
                flight_number="AA200",
                operation_type=OperationType.departure,
                runway_id="R1",
                gate_id="G1",
                start_sec=2100,
                end_sec=3300,
            ),
        ),
        unscheduled=(),
        completion_time_seconds=3300,
    ))
    
    result1 = longest_active_chain(state, config)
    result2 = longest_active_chain(state, config)
    
    assert result1.model_dump(mode="json") == result2.model_dump(mode="json")
    assert result1.chain == result2.chain
    assert result1.total_duration_seconds == result2.total_duration_seconds
    assert result1.operation_durations == result2.operation_durations
    assert result1.dependency_buffers == result2.dependency_buffers
