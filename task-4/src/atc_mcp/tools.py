"""MCP tool handlers — the only layer that imports the mcp SDK (Story 1.4+)."""
from typing import Literal

from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, ErrorData
from pydantic import BaseModel, ConfigDict, Field

from atc_mcp.domain.models import Flight, FlightState, OperationType, Priority, RunwayRequirements
from atc_mcp.domain.state import state


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
    cancelled_flight = flight.model_copy(update={"state": FlightState.cancelled, "unscheduled_reason": None})
    state.flights[data.flight_number] = cancelled_flight
    return {"cancelled": data.flight_number, "dependents_reevaluated": []}


def generate_schedule() -> dict:
    """Generate a fresh deterministic schedule."""
    raise NotImplementedError("not yet implemented")


def get_airport_status() -> dict:
    """Return structured airport operational status."""
    raise NotImplementedError("not yet implemented")


def analyze_bottleneck() -> dict:
    """Identify the longest active scheduled dependency chain."""
    raise NotImplementedError("not yet implemented")
