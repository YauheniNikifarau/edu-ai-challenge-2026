"""MCP tool handlers — the only layer that imports the mcp SDK (Story 1.4+)."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
    raise NotImplementedError("not yet implemented")


def cancel_flight(data: CancelFlightInput) -> dict:
    """Cancel a flight and re-evaluate dependents."""
    raise NotImplementedError("not yet implemented")


def generate_schedule() -> dict:
    """Generate a fresh deterministic schedule."""
    raise NotImplementedError("not yet implemented")


def get_airport_status() -> dict:
    """Return structured airport operational status."""
    raise NotImplementedError("not yet implemented")


def analyze_bottleneck() -> dict:
    """Identify the longest active scheduled dependency chain."""
    raise NotImplementedError("not yet implemented")
