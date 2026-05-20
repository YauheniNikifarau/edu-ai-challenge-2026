"""Tests for config.py — AC-6 (Story 1.2)."""
import pytest
from pydantic import ValidationError as PydanticValidationError

from atc_mcp.config import ConfigError, Runway, load_config

VALID_ENV = {
    "ATC_RUNWAYS": '[{"id":"R1","length_m":3500},{"id":"R2","length_m":3000}]',
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


def _set_all(monkeypatch, overrides=None):
    env = dict(VALID_ENV)
    if overrides:
        env.update(overrides)
    for k, v in env.items():
        monkeypatch.setenv(k, v)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_happy_path(monkeypatch, capsys):
    _set_all(monkeypatch)
    config = load_config()
    assert config.gate_count == 4
    assert config.ground_crew_count == 3
    assert config.runway_sep_takeoff_sec == 120
    assert config.runway_sep_landing_sec == 180
    assert config.runway_sep_mixed_sec == 240
    assert config.gate_turnaround_sec == 300
    assert config.dependency_buffer_sec == 600
    assert config.scheduling_horizon_sec == 86400
    assert config.duration_arrival_sec == 1200
    assert config.duration_departure_sec == 1200
    assert isinstance(config.runways, tuple)
    assert all(isinstance(r, Runway) for r in config.runways)
    assert config.runways[0].id == "R1"
    assert config.runways[0].length_m == 3500
    assert config.runways[1].id == "R2"
    assert config.runways[1].length_m == 3000
    with pytest.raises((PydanticValidationError, TypeError)):
        config.gate_count = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Missing vars
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("var_name", list(VALID_ENV.keys()))
def test_missing_var(monkeypatch, capsys, var_name):
    _set_all(monkeypatch)
    monkeypatch.delenv(var_name)
    with pytest.raises(ConfigError):
        load_config()
    captured = capsys.readouterr()
    assert f"CONFIG ERROR: {var_name} is invalid: variable not set" in captured.err


# ---------------------------------------------------------------------------
# Invalid integers
# ---------------------------------------------------------------------------

INTEGER_VARS = [k for k in VALID_ENV if k != "ATC_RUNWAYS"]


@pytest.mark.parametrize("var_name", INTEGER_VARS)
def test_invalid_integer(monkeypatch, capsys, var_name):
    _set_all(monkeypatch)
    monkeypatch.setenv(var_name, "three")
    with pytest.raises(ConfigError):
        load_config()
    captured = capsys.readouterr()
    assert "expected integer" in captured.err


# ---------------------------------------------------------------------------
# Non-positive values
# ---------------------------------------------------------------------------

GE1_VARS = [
    "ATC_GATE_COUNT",
    "ATC_GROUND_CREW_COUNT",
    "ATC_SCHEDULING_HORIZON_SEC",
    "ATC_DURATION_ARRIVAL_SEC",
    "ATC_DURATION_DEPARTURE_SEC",
]
GE0_VARS = [
    "ATC_RUNWAY_SEP_TAKEOFF_SEC",
    "ATC_RUNWAY_SEP_LANDING_SEC",
    "ATC_RUNWAY_SEP_MIXED_SEC",
    "ATC_GATE_TURNAROUND_SEC",
    "ATC_DEPENDENCY_BUFFER_SEC",
]


@pytest.mark.parametrize("var_name", GE1_VARS)
def test_non_positive_ge1(monkeypatch, capsys, var_name):
    _set_all(monkeypatch)
    monkeypatch.setenv(var_name, "0")
    with pytest.raises(ConfigError):
        load_config()
    captured = capsys.readouterr()
    assert "must be >= 1" in captured.err


@pytest.mark.parametrize("var_name", GE0_VARS)
def test_zero_accepted_ge0(monkeypatch, var_name):
    _set_all(monkeypatch)
    monkeypatch.setenv(var_name, "0")
    config = load_config()
    field_name = var_name.lower().removeprefix("atc_")
    assert getattr(config, field_name) == 0


# ---------------------------------------------------------------------------
# ATC_RUNWAYS schema validation
# ---------------------------------------------------------------------------

def test_runways_malformed_json(monkeypatch, capsys):
    _set_all(monkeypatch)
    monkeypatch.setenv("ATC_RUNWAYS", "not json")
    with pytest.raises(ConfigError):
        load_config()
    captured = capsys.readouterr()
    assert "not valid JSON" in captured.err


def test_runways_empty_array(monkeypatch, capsys):
    _set_all(monkeypatch)
    monkeypatch.setenv("ATC_RUNWAYS", "[]")
    with pytest.raises(ConfigError):
        load_config()
    captured = capsys.readouterr()
    assert "must contain at least one runway" in captured.err


def test_runways_extra_key(monkeypatch, capsys):
    _set_all(monkeypatch)
    monkeypatch.setenv("ATC_RUNWAYS", '[{"id":"R1","length_m":3500,"surface":"asphalt"}]')
    with pytest.raises(ConfigError):
        load_config()
    captured = capsys.readouterr()
    assert "CONFIG ERROR:" in captured.err


def test_runways_duplicate_id(monkeypatch, capsys):
    _set_all(monkeypatch)
    monkeypatch.setenv("ATC_RUNWAYS", '[{"id":"R1","length_m":3500},{"id":"R1","length_m":3000}]')
    with pytest.raises(ConfigError):
        load_config()
    captured = capsys.readouterr()
    assert 'duplicate runway id "R1"' in captured.err


def test_runways_non_positive_length(monkeypatch, capsys):
    _set_all(monkeypatch)
    monkeypatch.setenv("ATC_RUNWAYS", '[{"id":"R1","length_m":0}]')
    with pytest.raises(ConfigError):
        load_config()
    captured = capsys.readouterr()
    assert "CONFIG ERROR:" in captured.err
