"""Bottleneck detection and analysis helpers (Story 3+)."""
from atc_mcp.config import Config
from atc_mcp.domain.models import BottleneckResult, FlightState
from atc_mcp.domain.state import AppState

EMPTY = BottleneckResult(
    chain=[],
    total_duration_seconds=None,
    operation_durations=[],
    dependency_buffers=[],
)


def longest_active_chain(state: AppState, config: Config) -> BottleneckResult:
    """Compute the longest active scheduled dependency chain.
    
    Returns EMPTY if:
    - No schedule exists
    - No scheduled flight has a scheduled dependency
    - Only single flights exist (chain length must be >= 2)
    
    For equal-length chains, tie-breaks by lex-smallest starting flight_number.
    """
    if state.latest_schedule is None:
        return EMPTY

    scheduled_placements = {
        p.flight_number: p
        for p in state.latest_schedule.placements
        if state.flights.get(p.flight_number) is not None
        and state.flights[p.flight_number].state == FlightState.scheduled
    }

    scheduled_deps = {
        fn: [d for d in state.flights[fn].dependencies if d in scheduled_placements]
        for fn in scheduled_placements
    }

    if not any(scheduled_deps.values()):
        return EMPTY

    in_degree = {fn: 0 for fn in scheduled_placements}
    dependents_of = {fn: [] for fn in scheduled_placements}
    for fn, deps in scheduled_deps.items():
        for d in deps:
            in_degree[fn] += 1
            dependents_of[d].append(fn)

    queue = [fn for fn, deg in in_degree.items() if deg == 0]
    topo_order = []
    while queue:
        queue.sort()
        fn = queue.pop(0)
        topo_order.append(fn)
        for dependent in sorted(dependents_of[fn]):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    def dur(fn: str) -> int:
        p = scheduled_placements[fn]
        return p.end_sec - p.start_sec

    buf = config.dependency_buffer_sec
    dp: dict[str, int] = {}
    parent: dict[str, str | None] = {}
    chain_start: dict[str, str] = {}

    for fn in topo_order:
        deps = scheduled_deps[fn]
        if not deps:
            dp[fn] = dur(fn)
            parent[fn] = None
            chain_start[fn] = fn
        else:
            best = min(deps, key=lambda d: (-dp[d], chain_start[d]))
            dp[fn] = dp[best] + buf + dur(fn)
            parent[fn] = best
            chain_start[fn] = chain_start[best]

    best_tail = min(scheduled_placements, key=lambda fn: (-dp[fn], chain_start[fn]))

    if parent[best_tail] is None and not scheduled_deps[best_tail]:
        return EMPTY

    chain = []
    fn = best_tail
    while fn is not None:
        chain.append(fn)
        fn = parent[fn]
    chain.reverse()

    op_durs = [dur(fn) for fn in chain]
    dep_bufs = [buf] * (len(chain) - 1)
    total = sum(op_durs) + sum(dep_bufs)
    return BottleneckResult(
        chain=chain,
        total_duration_seconds=total,
        operation_durations=op_durs,
        dependency_buffers=dep_bufs,
    )
