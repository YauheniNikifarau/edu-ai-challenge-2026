# Story 1.2: Configuration Loading & Startup Validation

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator running the server,
I want all `ATC_*` environment variables to be required, validated, and produce a precise stderr error on misconfiguration,
So that I never run with silently-defaulted values and can diagnose config errors in one line.

## Acceptance Criteria

1. **AC-1 — Happy-path load.** Given all `ATC_*` env vars are set to valid values, calling `load_config()` from `config.py` returns a frozen Pydantic v2 `Config` model with the following fields correctly populated:
   - `runways: tuple[Runway, ...]` — parsed from `ATC_RUNWAYS` JSON array of `{id, length_m}` objects.
   - `gate_count: int`
   - `ground_crew_count: int`
   - `runway_sep_takeoff_sec: int`
   - `runway_sep_landing_sec: int`
   - `runway_sep_mixed_sec: int`
   - `gate_turnaround_sec: int`
   - `dependency_buffer_sec: int`
   - `scheduling_horizon_sec: int`
   - `duration_arrival_sec: int`
   - `duration_departure_sec: int`
2. **AC-2 — Failure format.** When any required `ATC_*` env var is missing, empty, non-integer (for `_SEC`/count fields), out-of-range, or fails `ATC_RUNWAYS` JSON schema validation, `load_config()` writes **exactly one line** to stderr in the format `CONFIG ERROR: <ENV_VAR_NAME> is invalid: <reason>` and raises `ConfigError`. The caller (Story 1.4's `server.py`) is responsible for `sys.exit(1)`.
3. **AC-3 — Pydantic model constraints.** `Config` and `Runway` both use `model_config = ConfigDict(frozen=True, extra="forbid")`. `load_config()` returns an immutable `Config` instance; mutating any field after construction raises `ValidationError`.
4. **AC-4 — `ATC_RUNWAYS` schema validation.** `ATC_RUNWAYS` must be valid JSON, a non-empty array, each item must have exactly `{id: str (non-empty), length_m: int (>= 1)}` with no extra keys, and all `id` values must be unique. Each specific failure uses the representative error shapes documented in the Dev Notes.
5. **AC-5 — `config.py` import discipline.** `config.py` is the only module under `src/atc_mcp/` that imports `os`. `tests/test_imports.py` from Story 1.1 already asserts this; no regression must be introduced.
6. **AC-6 — Test coverage.** `tests/test_config.py` covers all of: happy path; each missing var; each invalid type; malformed `ATC_RUNWAYS` JSON; non-positive numeric values; unknown extra keys in `ATC_RUNWAYS` items rejected; duplicate `id` values in `ATC_RUNWAYS` rejected.

## Tasks / Subtasks

- [ ] **Task 1 — Define `Runway`, `Config`, and `ConfigError` in `config.py`** (AC: 1, 3)
  - [ ] Import `json`, `os`, `sys`, `pydantic` (`BaseModel`, `ConfigDict`, `Field`). Do **not** import `mcp`, anything from `domain/`, or `time`/`datetime`/`random`.
  - [ ] Define `class ConfigError(Exception): pass` at module top level — a plain exception subclass, no extra fields.
  - [ ] Define `class Runway(BaseModel): model_config = ConfigDict(frozen=True, extra="forbid"); id: str = Field(min_length=1); length_m: int = Field(ge=1)`. This model lives in `config.py` **for this story only** — Story 1.3 relocates it to `domain/models.py` and updates the import here; see Dev Notes.
  - [ ] Define `class Config(BaseModel): model_config = ConfigDict(frozen=True, extra="forbid")` with all 11 fields: `runways: tuple[Runway, ...]`, `gate_count: int = Field(ge=1)`, `ground_crew_count: int = Field(ge=1)`, `runway_sep_takeoff_sec: int = Field(ge=0)`, `runway_sep_landing_sec: int = Field(ge=0)`, `runway_sep_mixed_sec: int = Field(ge=0)`, `gate_turnaround_sec: int = Field(ge=0)`, `dependency_buffer_sec: int = Field(ge=0)`, `scheduling_horizon_sec: int = Field(ge=1)`, `duration_arrival_sec: int = Field(ge=1)`, `duration_departure_sec: int = Field(ge=1)`.

- [ ] **Task 2 — Implement `load_config()`** (AC: 1, 2, 4)
  - [ ] Validate and parse each env var in the order shown in the env-var table (Dev Notes). For each failure, call the private helper `_fail(var_name, reason)` immediately.
  - [ ] Implement `_fail(var_name: str, reason: str) -> None` that writes `CONFIG ERROR: {var_name} is invalid: {reason}` to `sys.stderr` and raises `ConfigError(f"{var_name}: {reason}")`.
  - [ ] **Integer fields (all except `ATC_RUNWAYS`):** read `os.environ.get(VAR_NAME)`. If `None` or empty string → `_fail(…, "variable not set")`. Try `int(value)` in a `try/except ValueError` → `_fail(…, f'expected integer, got "{value}"')`. Check range constraint → `_fail(…, f"must be >= {min_val}, got {parsed}")`.
  - [ ] **`ATC_RUNWAYS`:** read raw string; if missing/empty → `_fail("ATC_RUNWAYS", "variable not set")`. Parse with `json.loads`; catch `json.JSONDecodeError` → `_fail("ATC_RUNWAYS", f"not valid JSON: {e}")`. Check non-empty list → `_fail("ATC_RUNWAYS", "must contain at least one runway")`. For each item, use `Runway.model_validate(item)` inside a `try/except ValidationError` → `_fail("ATC_RUNWAYS", f"item {i}: {e}")`. After parsing all items, check duplicate `id` values → `_fail("ATC_RUNWAYS", f'duplicate runway id "{dup_id}"')`.
  - [ ] Construct and return `Config(runways=tuple(runways), gate_count=gate_count, ...)`.

- [ ] **Task 3 — Write `tests/test_config.py`** (AC: 6)
  - [ ] Use `pytest`'s `monkeypatch` fixture to set/unset env vars. Do **not** use `os.environ` directly in tests — always use `monkeypatch.setenv` / `monkeypatch.delenv`.
  - [ ] Define a module-level `VALID_ENV` dict with all 11 valid env vars (use the reference config values from Dev Notes).
  - [ ] `test_happy_path`: set all vars from `VALID_ENV`; call `load_config()`; assert each field value matches expectations; assert `config.runways` is a tuple of `Runway`; assert modifying a field raises.
  - [ ] `test_missing_var` — parametrize over every var name in `VALID_ENV`; for each: delete that var, call `load_config()`, catch `ConfigError`, assert stderr contains `CONFIG ERROR: <VAR> is invalid: variable not set`.
  - [ ] `test_invalid_integer` — parametrize over each integer var; set to `"three"` (or similar non-integer); assert `ConfigError` raised and stderr message contains `expected integer`.
  - [ ] `test_non_positive` — for each var with `ge=1`, set to `"0"`; assert `ConfigError` with `must be >= 1`; for `ge=0` vars verify `"0"` is accepted.
  - [ ] `test_runways_malformed_json`: set `ATC_RUNWAYS='not json'`; assert `ConfigError` with `not valid JSON`.
  - [ ] `test_runways_empty_array`: set `ATC_RUNWAYS='[]'`; assert `ConfigError` with `must contain at least one runway`.
  - [ ] `test_runways_extra_key`: set `ATC_RUNWAYS='[{"id":"R1","length_m":3500,"surface":"asphalt"}]'`; assert `ConfigError` (extra fields rejected by `extra="forbid"`).
  - [ ] `test_runways_duplicate_id`: set `ATC_RUNWAYS='[{"id":"R1","length_m":3500},{"id":"R1","length_m":3000}]'`; assert `ConfigError` with `duplicate runway id "R1"`.
  - [ ] `test_runways_non_positive_length`: set an item with `length_m=0`; assert `ConfigError`.
  - [ ] Capture stderr in tests using `capsys` fixture: `captured = capsys.readouterr(); assert "CONFIG ERROR:" in captured.err`.

- [ ] **Task 4 — Smoke-test the server placeholder still works** (AC: 5)
  - [ ] Verify `pytest -q tests/test_imports.py` still passes after updating `config.py` (it now imports `os`, `json`, `sys`, `pydantic` — import-discipline assertion allows `os` only in `config.py`).
  - [ ] Verify `pytest -q tests/test_config.py` passes.

## Dev Notes

### Relevant Architecture Patterns & Constraints

- **Config boundary (architecture.md §"Config boundary"):** `config.py` is the **only** module that reads `os.environ`. This boundary is enforced by `tests/test_imports.py`. Never read env vars elsewhere — not in `server.py`, not in `domain/`, not in `scheduler/`.
- **Fail-fast format (architecture.md §"Environment Variable Contract"):** the exact error format is `CONFIG ERROR: <ENV_VAR_NAME> is invalid: <reason>`. One line, one error. Write to stderr and raise `ConfigError`; do **not** call `sys.exit(1)` from `load_config()` itself — that is Story 1.4 server.py's job.
- **Pydantic conventions (architecture.md §"Pydantic Model Conventions"):** use `ConfigDict(frozen=True, extra="forbid")` on value types; `Field(ge=N)` for range guards; `field_validator` (v2 style) if custom validation logic is needed beyond `Field`. Do **not** use v1's `@validator`.
- **`Runway` placement across stories:** this story defines `Runway` in `config.py` because `domain/models.py` is still empty (Story 1.3 fills it). Story 1.3 will move `Runway` to `domain/models.py` and add a single import line to `config.py`: `from atc_mcp.domain.models import Runway`. The `Config` model may stay in `config.py` permanently (it is config-layer, not domain-layer). Alternatively the architecture component decomp lists `Config` under `domain/models.py` — either location is acceptable as long as `config.py` is the only env reader.
- **No `pydantic-settings` (architecture.md §"Anti-Patterns"):** use plain `os.environ` + manual parsing. `pydantic-settings` is a forbidden dependency.
- **Integer-only time model (architecture.md §"Time Model"):** all durations are `int` seconds. `load_config()` must reject floats (e.g., `"1.5"` for a `_SEC` field should fail with `expected integer`).

### Source Tree Components to Touch

```
task-4/
└── src/
│   └── atc_mcp/
│       └── config.py             # UPDATE — fill with Runway, Config, ConfigError, load_config()
└── tests/
    └── test_config.py            # NEW — all test cases for AC-6
```

`domain/models.py`, `domain/state.py`, `server.py`, `tools.py`, `resources.py` — do **not** touch.  
`tests/test_imports.py` — do **not** modify; it should pass as-is since `config.py` importing `os` is already allowed by the existing assertion.

### Environment Variable Contract

All 11 required vars (from architecture.md §"Environment Variable Contract"):

| Env var | Python field | Range | Notes |
|---|---|---|---|
| `ATC_RUNWAYS` | `runways: tuple[Runway, ...]` | non-empty JSON array | Schema: `[{id: str, length_m: int >= 1}]`, unique ids, no extra keys |
| `ATC_GATE_COUNT` | `gate_count: int` | ≥ 1 | |
| `ATC_GROUND_CREW_COUNT` | `ground_crew_count: int` | ≥ 1 | |
| `ATC_RUNWAY_SEP_TAKEOFF_SEC` | `runway_sep_takeoff_sec: int` | ≥ 0 | Zero is valid (no separation) |
| `ATC_RUNWAY_SEP_LANDING_SEC` | `runway_sep_landing_sec: int` | ≥ 0 | |
| `ATC_RUNWAY_SEP_MIXED_SEC` | `runway_sep_mixed_sec: int` | ≥ 0 | |
| `ATC_GATE_TURNAROUND_SEC` | `gate_turnaround_sec: int` | ≥ 0 | |
| `ATC_DEPENDENCY_BUFFER_SEC` | `dependency_buffer_sec: int` | ≥ 0 | |
| `ATC_SCHEDULING_HORIZON_SEC` | `scheduling_horizon_sec: int` | ≥ 1 | |
| `ATC_DURATION_ARRIVAL_SEC` | `duration_arrival_sec: int` | ≥ 1 | |
| `ATC_DURATION_DEPARTURE_SEC` | `duration_departure_sec: int` | ≥ 1 | |

### Representative Error Shapes (architecture.md §"Startup validation failure shapes")

```
CONFIG ERROR: ATC_GATE_COUNT is invalid: variable not set
CONFIG ERROR: ATC_GATE_COUNT is invalid: expected integer, got "three"
CONFIG ERROR: ATC_GATE_COUNT is invalid: must be >= 1, got 0
CONFIG ERROR: ATC_RUNWAYS is invalid: not valid JSON: Expecting value: line 1 column 1 (char 0)
CONFIG ERROR: ATC_RUNWAYS is invalid: must contain at least one runway
CONFIG ERROR: ATC_RUNWAYS is invalid: duplicate runway id "R1"
```

### Reference Config (for tests/test_config.py `VALID_ENV`)

Use these values as the basis for `VALID_ENV` in test_config.py (taken from architecture.md §"Reference config"):

```python
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
```

### Library / Framework Requirements

| Concern | Choice | Notes |
|---|---|---|
| Env-var access | `os.environ` (stdlib) | Only in `config.py`. No `dotenv`, no `pydantic-settings`. |
| JSON parsing | `json` (stdlib) | For `ATC_RUNWAYS`. |
| Validation models | `pydantic>=2` | `BaseModel`, `ConfigDict`, `Field` from `pydantic`. |
| Testing | `pytest>=8` | `monkeypatch`, `capsys` fixtures — both ship with pytest, no plugins needed. |

### Testing Standards Summary

- Framework: `pytest` only. Use `monkeypatch` and `capsys` — both are built-in fixtures, no plugins required.
- **Do not** import `config.py` at module level in test files without managing env vars, because `load_config()` reads `os.environ` at call time, not import time. Importing the module is safe; calling `load_config()` without env vars will raise.
- **Always** clean up env vars with `monkeypatch` (automatic teardown). Never use `os.environ[key] = ...` directly in tests.
- Test for stderr text with `capsys.readouterr().err` — `_fail()` writes to `sys.stderr`, so this is the correct capture mechanism.
- Run command: `pytest -q tests/test_imports.py tests/test_config.py` from the `task-4/` directory.

### Previous Story Intelligence (Story 1.1)

- **Story 1.1 established:** `config.py` exists as an empty placeholder module. All imports from `config.py` are currently `set()` — the test_imports.py assertion "config.py is the only module allowed to import `os`" is currently trivially true. After this story, `config.py` will import `os` (and `json`, `sys`, `pydantic`) — this is expected and allowable per the assertion logic.
- **Do not** add any logic to `__main__.py`, `server.py`, `tools.py`, `resources.py`, or `domain/state.py` in this story. They remain as Story 1.1 left them.
- **`tests/test_server_placeholder.py`** (if created in Story 1.1) must still pass — the placeholder in `server.py` must not be touched.

### Disaster-Prevention Notes

- **Do not** call `sys.exit(1)` inside `load_config()`. The function raises `ConfigError`; the caller (Story 1.4's server startup) handles the exit. This separation makes `load_config()` unit-testable without subprocess tricks.
- **Do not** produce multiple lines to stderr on a single failure. One call to `_fail()` = one `CONFIG ERROR:` line. Stop at the first error encountered; do not accumulate and report all.
- **Do not** define any module-level code in `config.py` that reads env vars eagerly. `load_config()` is the only entry point; importing the module must be side-effect-free.
- **Do not** add any `default=` values to `Config` or `Runway` fields that would silently absorb a missing env var. All fields are required; Pydantic will raise if a field is missing from the constructor call, but `load_config()` must have already reported the error before constructing `Config`.
- **`ATC_RUNWAYS` edge cases:** reject `null`, `{}` (not a list), a JSON string, or any non-list JSON value with a clear error. `isinstance(parsed, list)` after `json.loads` is the guard.
- **Runway `extra="forbid"`:** if a runway item has extra keys (e.g., `"surface": "asphalt"`), `Runway.model_validate(item)` raises `ValidationError`; surface this as `CONFIG ERROR: ATC_RUNWAYS is invalid: item 0: <pydantic error message>`.

### Project Structure Notes

- `config.py` is the single config boundary. After this story it will be the only file with `import os`.
- `Runway` in `config.py` is intentionally temporary. Story 1.3's AC explicitly lists `Runway` as a model in `domain/models.py`. The expected migration path: Story 1.3 defines `Runway` in `domain/models.py`, then updates `config.py` to `from atc_mcp.domain.models import Runway` and deletes the local definition. Coordinate with Story 1.3's author.
- No new top-level files are created by this story. Only `src/atc_mcp/config.py` (UPDATE) and `tests/test_config.py` (NEW).

### References

- [Source: _bmad-output/planning-artifacts/epics.md §"Story 1.2: Configuration Loading & Startup Validation"] — AC source, full acceptance criteria.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Environment Variable Contract (resolves DD-2)"] — all 11 env vars, accepted ranges, exact error format, representative failure shapes.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Runway Capability Schema (resolves DD-8)"] — `ATC_RUNWAYS` JSON schema, `{id, length_m}` only, matching rule.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Tech Stack & Project Bootstrap (resolves DD-3)"] — Pydantic v2, no `pydantic-settings`.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Pydantic Model Conventions"] — `ConfigDict(frozen=True, extra="forbid")`, `field_validator` v2 style.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Process Patterns / Error handling tiers"] — config errors: print + exit (tier 1); `load_config()` raises, server.py exits.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Structure Patterns / Module dependency direction"] — `config.py` imports stdlib only (plus Pydantic); no MCP, no domain imports.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Anti-Patterns"] — no `pydantic-settings`, no `.env` files, no dotenv.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Scenario Walkthroughs / Reference config"] — canonical valid config values for test fixtures.
- [Source: _bmad-output/planning-artifacts/epics.md §"Story 1.1"] — previous story's skeleton: what config.py looks like going in (empty placeholder).
- [Source: _bmad-output/planning-artifacts/epics.md §"Story 1.3"] — Runway will move to domain/models.py; do not duplicate work now.

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List
