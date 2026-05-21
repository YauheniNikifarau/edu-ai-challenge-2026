"""Config-failure exit tests — verify missing ATC_* var exits 1 (AC-7, Story 1.4)."""
import subprocess
import sys

import pytest

BASE_ENV = {
    "ATC_RUNWAYS": '[{"id":"R1","length_m":3500}]',
    "ATC_GATE_COUNT": "4",
    "ATC_GROUND_CREW_COUNT": "3",
    "ATC_RUNWAY_SEP_TAKEOFF_SEC": "120",
    "ATC_RUNWAY_SEP_LANDING_SEC": "180",
    "ATC_RUNWAY_SEP_MIXED_SEC": "240",
    "ATC_GATE_TURNAROUND_SEC": "300",
    "ATC_DEPENDENCY_BUFFER_SEC": "600",
    "ATC_SCHEDULING_HORIZON_SEC": "86400",
    "ATC_DURATION_ARRIVAL_SEC": "1200",
    "ATC_DURATION_DEPARTURE_SEC": "1200",
}

MISSING_VAR_CASES = [
    "ATC_RUNWAYS",
    "ATC_GATE_COUNT",
    "ATC_DURATION_ARRIVAL_SEC",
]


@pytest.mark.parametrize("missing_var", MISSING_VAR_CASES)
def test_missing_var_exits_1(missing_var):
    env = {k: v for k, v in BASE_ENV.items() if k != missing_var}
    result = subprocess.run(
        [sys.executable, "-m", "atc_mcp.server"],
        capture_output=True,
        env=env,
        timeout=5,
    )
    assert result.returncode == 1
    assert b"CONFIG ERROR:" in result.stderr
