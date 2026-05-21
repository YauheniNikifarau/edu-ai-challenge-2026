"""MCP tool handlers — the only layer that imports the mcp SDK (Story 1.4+)."""
from typing import Literal

from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, ErrorData
from pydantic import BaseModel, ConfigDict, Field

from atc_mcp.domain.models import Flight, FlightState, OperationType, Priority, RunwayRequirements
from atc_mcp.domain.state import state
from atc_mcp.scheduler.algorithm import schedule
from atc_mcp.status import build_status


class RunwayRequirementsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_length_m: int = Field(ge=1)


class SubmitFlightInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    flight_number: str
    operation_type: Literal["arrival", "departure"]
    priority: Literal["high", "medium", "low"]
    dependencies: list[str] = []
    runway_requirements: RunwayRequirementsInput | None = None


class CancelFlightInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    flight_number: str


def submit_flight(data: SubmitFlightInput) -> dict:
    """Submit a new flight to the queue."""
    if state.get_flight(data.flight_number) is not None:
        return {"error": f"flight {data.flight_number} already exists"}
    if data.flight_number in data.dependencies:
        return {"error": "flight cannot depend on itself"}
    for dep in data.dependencies:
        if state.get_flight(dep) is None:
            return {"error": f"unknown dependency: {dep}"}
    runway_requirements = (
        RunwayRequirements(min_length_m=data.runway_requirements.min_length_m)
        if data.runway_requirements
        else None
    )
    flight = Flight(
        flight_number=data.flight_number,
        operation_type=OperationType(data.operation_type),
        priority=Priority(data.priority),
        dependencies=data.dependencies,
        runway_requirements=runway_requirements,
        state=FlightState.queued,
        unscheduled_reason=None,
    )
    state.add_flight(flight)
    return {"flight": flight.model_dump(mode="json")}


def cancel_flight(data: CancelFlightInput) -> dict:
    """Cancel a flight and re-evaluate dependents."""
    flight = state.get_flight(data.flight_number)
    if flight is None:
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"flight {data.flight_number} does not exist"))
    if flight.state == FlightState.cancelled:
        raise McpError(ErrorData(code=INVALID_PARAMS, message=f"flight {data.flight_number} is already cancelled"))
    
    prev_states = {fn: f.state for fn, f in state.flights.items()}
    
    cancelled_flight = flight.model_copy(update={"state": FlightState.cancelled, "unscheduled_reason": None})
    state.flights[data.flight_number] = cancelled_flight
    
    _run_schedule()
    
    dependents_reevaluated = []
    for fn, flight in state.flights.items():
        if fn == data.flight_number:
            continue
        if flight.state != prev_states[fn]:
            dependents_reevaluated.append({
                "flight_number": fn,
                "previous_state": str(prev_states[fn].value),
                "new_state": str(flight.state.value),
                "reason": flight.unscheduled_reason if flight.state == FlightState.unschedulable else None,
            })
    dependents_reevaluated.sort(key=lambda x: x["flight_number"])
    
    return {"cancelled": data.flight_number, "dependents_reevaluated": dependents_reevaluated}


def _run_schedule() -> dict:
    """Internal shared scheduling function called by generate_schedule and cancel_flight."""
    assert state.config is not None, "Config must be set before calling _run_schedule"
    
    result = schedule(tuple(state.flights.values()), state.config)
    state.set_latest_schedule(result)
    
    scheduled_numbers = {p.flight_number for p in result.placements}
    unscheduled_map = {f.flight_number: f for f in result.unscheduled}
    
    updated: dict[str, Flight] = {}
    for fn, flight in state.flights.items():
        if flight.state == FlightState.cancelled:
            updated[fn] = flight
        elif fn in scheduled_numbers:
            updated[fn] = flight.model_copy(update={
                "state": FlightState.scheduled,
                "unscheduled_reason": None,
            })
        elif fn in unscheduled_map:
            unscheduled_flight = unscheduled_map[fn]
            updated[fn] = flight.model_copy(update={
                "state": FlightState.unschedulable,
                "unscheduled_reason": unscheduled_flight.unscheduled_reason,
            })
        else:
            updated[fn] = flight
    
    state.replace_flights_after_schedule(updated)
    
    scheduled_placements = [
        {
            "flight_number": p.flight_number,
            "operation_type": p.operation_type,
            "runway_id": p.runway_id,
            "gate_id": p.gate_id,
            "start_sec": p.start_sec,
            "end_sec": p.end_sec,
        }
        for p in result.placements
    ]
    
    unscheduled_list = [
        {"flight_number": f.flight_number, "reason": f.unscheduled_reason or ""}
        for f in result.unscheduled
    ]
    
    cancelled_count = sum(
        1 for f in state.flights.values() if f.state == FlightState.cancelled
    )
    
    return {
        "schedule": scheduled_placements,
        "unscheduled": unscheduled_list,
        "completion_time_seconds": result.completion_time_seconds,
        "summary": {
            "scheduled_count": len(result.placements),
            "unscheduled_count": len(result.unscheduled),
            "cancelled_count": cancelled_count,
        },
    }


def generate_schedule() -> dict:
    """Generate a fresh deterministic schedule."""
    return _run_schedule()


def get_airport_status() -> dict:
    """Return structured airport operational status."""
    assert state.config is not None, "Config must be set before calling get_airport_status"
    return build_status(state, state.config)


def analyze_bottleneck() -> dict:
    """Identify the longest active scheduled dependency chain."""
    raise NotImplementedError("not yet implemented")
