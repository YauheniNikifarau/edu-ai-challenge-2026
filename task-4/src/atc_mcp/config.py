"""Runtime configuration loader — reads ATC_* env vars via os.environ (Story 1.2)."""
import json
import os
import sys

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ConfigError(Exception):
    pass


class Runway(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(min_length=1)
    length_m: int = Field(ge=1)


class Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    runways: tuple[Runway, ...]
    gate_count: int = Field(ge=1)
    ground_crew_count: int = Field(ge=1)
    runway_sep_takeoff_sec: int = Field(ge=0)
    runway_sep_landing_sec: int = Field(ge=0)
    runway_sep_mixed_sec: int = Field(ge=0)
    gate_turnaround_sec: int = Field(ge=0)
    dependency_buffer_sec: int = Field(ge=0)
    scheduling_horizon_sec: int = Field(ge=1)
    duration_arrival_sec: int = Field(ge=1)
    duration_departure_sec: int = Field(ge=1)


def _fail(var_name: str, reason: str) -> None:
    print(f"CONFIG ERROR: {var_name} is invalid: {reason}", file=sys.stderr)
    raise ConfigError(f"{var_name}: {reason}")


def _parse_int(var_name: str, min_val: int) -> int:
    value = os.environ.get(var_name)
    if not value:
        _fail(var_name, "variable not set")
        return 0  # unreachable; satisfies type checkers
    try:
        parsed = int(value)
    except ValueError:
        _fail(var_name, f'expected integer, got "{value}"')
        return 0  # unreachable
    if parsed < min_val:
        _fail(var_name, f"must be >= {min_val}, got {parsed}")
    return parsed


def load_config() -> "Config":
    # --- ATC_RUNWAYS ---
    raw = os.environ.get("ATC_RUNWAYS")
    if not raw:
        _fail("ATC_RUNWAYS", "variable not set")
    try:
        parsed_list = json.loads(raw)  # type: ignore[arg-type]
    except json.JSONDecodeError as e:
        _fail("ATC_RUNWAYS", f"not valid JSON: {e}")
        return Config.__new__(Config)  # unreachable
    if not isinstance(parsed_list, list) or len(parsed_list) == 0:
        _fail("ATC_RUNWAYS", "must contain at least one runway")
    runways: list[Runway] = []
    for i, item in enumerate(parsed_list):
        try:
            runways.append(Runway.model_validate(item))
        except ValidationError as e:
            _fail("ATC_RUNWAYS", f"item {i}: {e}")
    seen: set[str] = set()
    for r in runways:
        if r.id in seen:
            _fail("ATC_RUNWAYS", f'duplicate runway id "{r.id}"')
        seen.add(r.id)

    # --- Integer fields (in env-var table order) ---
    gate_count = _parse_int("ATC_GATE_COUNT", 1)
    ground_crew_count = _parse_int("ATC_GROUND_CREW_COUNT", 1)
    runway_sep_takeoff_sec = _parse_int("ATC_RUNWAY_SEP_TAKEOFF_SEC", 0)
    runway_sep_landing_sec = _parse_int("ATC_RUNWAY_SEP_LANDING_SEC", 0)
    runway_sep_mixed_sec = _parse_int("ATC_RUNWAY_SEP_MIXED_SEC", 0)
    gate_turnaround_sec = _parse_int("ATC_GATE_TURNAROUND_SEC", 0)
    dependency_buffer_sec = _parse_int("ATC_DEPENDENCY_BUFFER_SEC", 0)
    scheduling_horizon_sec = _parse_int("ATC_SCHEDULING_HORIZON_SEC", 1)
    duration_arrival_sec = _parse_int("ATC_DURATION_ARRIVAL_SEC", 1)
    duration_departure_sec = _parse_int("ATC_DURATION_DEPARTURE_SEC", 1)

    return Config(
        runways=tuple(runways),
        gate_count=gate_count,
        ground_crew_count=ground_crew_count,
        runway_sep_takeoff_sec=runway_sep_takeoff_sec,
        runway_sep_landing_sec=runway_sep_landing_sec,
        runway_sep_mixed_sec=runway_sep_mixed_sec,
        gate_turnaround_sec=gate_turnaround_sec,
        dependency_buffer_sec=dependency_buffer_sec,
        scheduling_horizon_sec=scheduling_horizon_sec,
        duration_arrival_sec=duration_arrival_sec,
        duration_departure_sec=duration_departure_sec,
    )
