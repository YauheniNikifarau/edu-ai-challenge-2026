"""Pydantic v2 domain models for flights, runways, and scheduling slots (Story 1.3)."""
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class FlightState(StrEnum):
    queued = "queued"
    scheduled = "scheduled"
    unschedulable = "unschedulable"
    cancelled = "cancelled"


class OperationType(StrEnum):
    arrival = "arrival"
    departure = "departure"


class Priority(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class RunwayRequirements(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    min_length_m: int = Field(gt=0)


class Runway(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    length_m: int = Field(gt=0)


class Flight(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    flight_number: str
    operation_type: OperationType
    priority: Priority
    dependencies: list[str] = Field(default_factory=list)
    runway_requirements: RunwayRequirements | None = None
    state: FlightState = FlightState.queued
    unscheduled_reason: str | None = None


class Placement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    flight_number: str
    operation_type: OperationType
    runway_id: str
    gate_id: str
    start_sec: int = Field(ge=0)
    end_sec: int = Field(ge=0)


class Schedule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    placements: tuple[Placement, ...]
    unscheduled: tuple[Flight, ...]
    completion_time_seconds: int | None = None


class BottleneckResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    chain: list[str]
    total_duration_seconds: int | None
    operation_durations: list[int]
    dependency_buffers: list[int]
