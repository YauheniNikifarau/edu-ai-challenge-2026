"""Scheduling constraint definitions and validators (Story 3.1+)."""
from atc_mcp.config import Config, Runway
from atc_mcp.domain.models import OperationType, Placement, RunwayRequirements


def get_separation(prev_op: OperationType, new_op: OperationType, config: Config) -> int:
    """Return runway separation seconds for the given consecutive op-type pair."""
    if prev_op == OperationType.departure and new_op == OperationType.departure:
        return config.runway_sep_takeoff_sec
    if prev_op == OperationType.arrival and new_op == OperationType.arrival:
        return config.runway_sep_landing_sec
    return config.runway_sep_mixed_sec


def earliest_runway_start(
    placements: list[Placement],
    new_op: OperationType,
    floor: int,
    config: Config,
) -> int:
    """Return the earliest second a new op may start on a runway, given prior placements."""
    return max(
        (p.end_sec + get_separation(p.operation_type, new_op, config) for p in placements),
        default=floor,
    )


def earliest_gate_start(
    placements: list[Placement],
    floor: int,
    config: Config,
) -> int:
    """Return the earliest second a new op may start at a gate, given prior placements."""
    return max(
        (p.end_sec + config.gate_turnaround_sec for p in placements),
        default=floor,
    )


def feasible_runways(
    runways: tuple[Runway, ...],
    req: RunwayRequirements | None,
) -> list[Runway]:
    """Return runways satisfying req, sorted lexicographically by id."""
    filtered = [r for r in runways if req is None or r.length_m >= req.min_length_m]
    return sorted(filtered, key=lambda r: r.id)


def runway_unschedulable_reason(n: int, runways: tuple[Runway, ...]) -> str:
    """Return the exact unschedulable reason string when no runway meets minimum length n metres."""
    available = ", ".join(
        f"{r.id} {r.length_m}m"
        for r in sorted(runways, key=lambda r: r.id)
    )
    return f"no runway meets minimum length {n}m (available runways: {available})"


def earliest_crew_feasible_start(
    candidate: int,
    duration: int,
    committed: list[tuple[int, int]],
    capacity: int,
) -> int:
    """Return earliest t >= candidate where [t, t+duration) has peak crew < capacity.
    
    Args:
        candidate: Earliest candidate start time in seconds
        duration: Duration of the operation in seconds
        committed: List of (start_sec, end_sec) intervals for already committed operations
        capacity: Maximum number of concurrent operations allowed
        
    Returns:
        Earliest start time where the operation can be scheduled without exceeding capacity
    """
    t = candidate
    while True:
        conflicting = [
            (s, e) for (s, e) in committed
            if s < t + duration and e > t
        ]
        if len(conflicting) < capacity:
            return t
        t = min(e for (_, e) in conflicting)
