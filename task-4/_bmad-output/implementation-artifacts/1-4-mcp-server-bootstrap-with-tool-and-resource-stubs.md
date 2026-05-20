# Story 1.4: MCP Server Bootstrap with Tool & Resource Stubs

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an MCP-compatible client,
I want to connect to the running server over stdio and discover all five tools and three resources,
So that I can verify the server is wired correctly before any business logic is implemented.

## Acceptance Criteria

1. **AC-1 — Server starts on valid config.** Given all `ATC_*` env vars are valid, running `python -m atc_mcp.server` (or `python -m atc_mcp`) starts an MCP server on stdio transport using the official `mcp` SDK, writing only JSON-RPC frames to stdout (no stray prints).
2. **AC-2 — Tool catalog is correct.** `tools/list` returns exactly five tools — `submit_flight`, `generate_schedule`, `get_airport_status`, `cancel_flight`, `analyze_bottleneck` — each with its Pydantic v2 input schema (`extra="forbid"`) declared per architecture.
3. **AC-3 — Resource catalog is correct.** `resources/list` returns exactly three resources: `atc://flights`, `atc://runways`, `atc://timeline`.
4. **AC-4 — Tool stubs return "not yet implemented".** Invoking any stub tool returns a clearly-marked "not yet implemented" error response; full behaviour lands in later epics.
5. **AC-5 — Resource stubs return documented empty shapes.** Reading each resource stub returns the architecture-pinned JSON shape with empty collections: `atc://flights` → `{"flights": []}`, `atc://runways` → `{"runways": []}`, `atc://timeline` → `{"events": []}`.
6. **AC-6 — Bootstrap test passes.** `tests/test_server_bootstrap.py` verifies the tool/resource catalog in-process: exactly 5 tool names and exactly 3 resource URIs, all matching the expected sets.
7. **AC-7 — Config-failure exit test passes.** `tests/test_config_failure_exit.py` verifies that running the server with a missing `ATC_*` var prints a `CONFIG ERROR:` line to stderr and exits with code 1.
8. **AC-8 — Import discipline test updated and green.** `tests/test_imports.py` is updated so `server.py` is added to the allowed set of modules that may import `mcp` (alongside `tools.py` and `resources.py`). All existing assertions remain in force. `pytest -q tests/test_imports.py` passes.
9. **AC-9 — `__main__.py` wired.** `python -m atc_mcp` launches the server identically to `python -m atc_mcp.server`.

## Tasks / Subtasks

- [ ] **Task 1 — Add Pydantic input schemas and stub handlers to `tools.py`** (AC: 2, 4)
  - [ ] Define `RunwayRequirementsInput(BaseModel)` with `model_config = ConfigDict(extra="forbid")` and field `min_length_m: int = Field(ge=1)`.
  - [ ] Define `SubmitFlightInput(BaseModel)` with `model_config = ConfigDict(extra="forbid")` and fields: `flight_number: str`, `operation_type: Literal["arrival", "departure"]`, `priority: Literal["high", "medium", "low"]`, `dependencies: list[str] = []`, `runway_requirements: RunwayRequirementsInput | None = None`.
  - [ ] Define `CancelFlightInput(BaseModel)` with `model_config = ConfigDict(extra="forbid")` and field `flight_number: str`.
  - [ ] For no-parameter tools (`generate_schedule`, `get_airport_status`, `analyze_bottleneck`), use zero-argument handler functions (FastMCP generates `{"type":"object","properties":{}}` automatically — no need for an explicit empty model).
  - [ ] Implement stub handler functions with matching names (used verbatim as MCP tool names): `submit_flight(data: SubmitFlightInput)`, `cancel_flight(data: CancelFlightInput)`, `generate_schedule()`, `get_airport_status()`, `analyze_bottleneck()`. Each raises `NotImplementedError("not yet implemented")`.
  - [ ] Add a one-line docstring to each function — FastMCP uses the docstring as the tool description.
  - [ ] `tools.py` must NOT import `mcp` in this story. It needs only `pydantic` and stdlib. (`mcp.types.McpError` is added in story 2.x when real logic lands.)

- [ ] **Task 2 — Add stub resource handlers to `resources.py`** (AC: 3, 5)
  - [ ] Implement `flights_resource() -> str` — returns `'{"flights": []}'`.
  - [ ] Implement `runways_resource() -> str` — returns `'{"runways": []}'`.
  - [ ] Implement `timeline_resource() -> str` — returns `'{"events": []}'`.
  - [ ] Add a one-line docstring to each (FastMCP uses it as the resource description).
  - [ ] `resources.py` must NOT import `mcp` in this story. It needs only `json` (or inline string literals).

- [ ] **Task 3 — Implement `server.py` with FastMCP bootstrap** (AC: 1, 2, 3, 4, 5)
  - [ ] Import `FastMCP` from `mcp.server.fastmcp`.
  - [ ] Import `load_config` and `ConfigError` from `atc_mcp.config`.
  - [ ] Import all tool handler functions from `atc_mcp.tools`.
  - [ ] Import all resource handler functions from `atc_mcp.resources`.
  - [ ] Define `create_app(config) -> FastMCP`: instantiate `FastMCP("atc-mcp")`, register tools and resources, return the instance. Do NOT call `run()` inside `create_app()`.
  - [ ] Register tools using `@mcp.tool()` decorator OR `mcp.add_tool(fn)`. The function names (`submit_flight`, `cancel_flight`, `generate_schedule`, `get_airport_status`, `analyze_bottleneck`) become the MCP tool names verbatim — verify they match architecture exactly.
  - [ ] Register resources with exact URIs: `mcp.resource("atc://flights")(flights_resource)`, etc.
  - [ ] Define `main()`: call `load_config()`, catch `ConfigError` → `sys.exit(1)`, call `create_app(config)`, call `app.run(transport="stdio")`.
  - [ ] Add `if __name__ == "__main__": main()` guard.
  - [ ] Never write to stdout outside `app.run()`. Any startup log goes to stderr only.

- [ ] **Task 4 — Wire `__main__.py`** (AC: 9)
  - [ ] Replace the inert placeholder with exactly: `from atc_mcp.server import main; main()`.
  - [ ] Do NOT import `mcp` in `__main__.py`.

- [ ] **Task 5 — Update `tests/test_imports.py`** (AC: 8)
  - [ ] Find the assertion that checks only `{tools.py, resources.py}` may import `mcp`. Extend the allowed set to `{tools.py, resources.py, server.py}`.
  - [ ] All other assertions from stories 1.1 and 1.3 remain untouched: `domain/` and `scheduler/` must not import `mcp`, `os`, `time`, `datetime`, or `random`; `config.py` is the sole `os` importer.
  - [ ] Run `pytest -q tests/test_imports.py` and confirm it exits 0.

- [ ] **Task 6 — Create `tests/conftest.py` with shared env fixture** (AC: 6, 7)
  - [ ] Create `tests/conftest.py` (it does not exist yet — story 1.1 explicitly deferred it).
  - [ ] Define a `valid_env` pytest fixture that `monkeypatches` or returns a dict of all 11 `ATC_*` vars set to the reference config values (see Dev Notes §Reference Config).
  - [ ] Keep `conftest.py` minimal — one fixture only; no imports beyond `pytest` and `os`.

- [ ] **Task 7 — Write `tests/test_server_bootstrap.py`** (AC: 6)
  - [ ] Import `os`, `pytest`, `load_config` from `atc_mcp.config`, `create_app` from `atc_mcp.server`.
  - [ ] Use the `valid_env` fixture to set env vars before calling `load_config()`.
  - [ ] Call `create_app(config)` to get the `FastMCP` instance.
  - [ ] Assert tool count == 5 and resource count == 3 using FastMCP introspection (see Dev Notes §Testing Without pytest-asyncio for the exact attribute path).
  - [ ] Assert exact name sets: `{"submit_flight", "generate_schedule", "get_airport_status", "cancel_flight", "analyze_bottleneck"}` and `{"atc://flights", "atc://runways", "atc://timeline"}`.
  - [ ] Test is synchronous (no `asyncio.run()` needed for FastMCP introspection).

- [ ] **Task 8 — Write `tests/test_config_failure_exit.py`** (AC: 7)
  - [ ] Use `subprocess.run([sys.executable, "-m", "atc_mcp.server"], capture_output=True, env={...}, timeout=5)`.
  - [ ] Pass an explicit `env` dict that is missing one `ATC_*` var (do NOT inherit parent env — parent may have valid vars set).
  - [ ] Assert `result.returncode == 1`.
  - [ ] Assert `b"CONFIG ERROR:"` in `result.stderr`.
  - [ ] Parametrize over at least three different missing vars (e.g., `ATC_RUNWAYS`, `ATC_GATE_COUNT`, `ATC_DURATION_ARRIVAL_SEC`).
  - [ ] Always pass `timeout=5` — a running server never returns without it.

- [ ] **Task 9 — Smoke verify** (AC: 1)
  - [ ] Set all `ATC_*` env vars and run `python -m atc_mcp`. Confirm no stray stdout before the JSON-RPC handshake. Stop with Ctrl-C or connect via MCP Inspector.
  - [ ] Run `pytest -q` from `task-4/` and confirm all tests pass.

## Dev Notes

### What Stories 1.1–1.3 Established (Read Before Touching Any File)

**Story 1.1** left `server.py` as a placeholder that exits 1 with a "configuration not loaded" message, and `tools.py`, `resources.py`, `__main__.py` as empty stubs. It also created `tests/test_imports.py` with an assertion that only `{tools.py, resources.py}` may import `mcp`. **This story must update that assertion to add `server.py`** — see Task 5. Failing to do so will cause `test_imports.py` to fail as soon as `server.py` imports FastMCP.

**Story 1.2** wired `config.py` completely. `load_config() -> Config` reads all 11 `ATC_*` env vars, validates, returns a frozen Pydantic v2 `Config` model. On any invalid var it writes exactly one line to stderr: `CONFIG ERROR: <ENV_VAR_NAME> is invalid: <reason>` then raises `ConfigError`. The **caller** (i.e., `server.py`'s `main()`) is responsible for `sys.exit(1)` — do not duplicate the error message in `server.py`.

**Story 1.3** populated `domain/models.py` with:
- `Flight`, `Schedule`, `Placement`, `BottleneckResult`, `Runway` — frozen Pydantic v2 models
- `FlightState(StrEnum)` — exactly `queued | scheduled | unschedulable | cancelled`
- `RunwayRequirements(BaseModel, frozen=True, extra="forbid")` with `min_length_m: int`
- `AppState` in `domain/state.py` with `flights: dict[str, Flight]` and `latest_schedule: Schedule | None`

**For this story:** `tools.py`'s `RunwayRequirementsInput` is an MCP input schema type (lives in `tools.py`, has `extra="forbid"`). `RunwayRequirements` from `domain/models.py` is a domain value type (frozen). They serve different purposes. Do **not** import `domain/models.py` into `tools.py` just for story 1.4 — the domain types are not needed until story 2.1. Define `RunwayRequirementsInput` as a standalone Pydantic model in `tools.py`.

### SDK Pattern — FastMCP (Official `mcp` Package)

This project uses **`FastMCP` from `mcp.server.fastmcp`**, which is part of the official `mcp` PyPI package already declared in `pyproject.toml`. Do **NOT** `pip install fastmcp` (that is PrefectHQ's separate package with a different API surface).

Canonical patterns for this story:

**`server.py` skeleton:**
```python
import sys
from mcp.server.fastmcp import FastMCP
from atc_mcp.config import load_config, ConfigError
from atc_mcp.tools import submit_flight, cancel_flight, generate_schedule, get_airport_status, analyze_bottleneck
from atc_mcp.resources import flights_resource, runways_resource, timeline_resource


def create_app(config) -> FastMCP:
    mcp = FastMCP("atc-mcp")

    mcp.add_tool(submit_flight)
    mcp.add_tool(cancel_flight)
    mcp.add_tool(generate_schedule)
    mcp.add_tool(get_airport_status)
    mcp.add_tool(analyze_bottleneck)

    mcp.add_resource_fn(flights_resource, uri="atc://flights", name="flights", description="Current flight queue")
    mcp.add_resource_fn(runways_resource, uri="atc://runways", name="runways", description="Runway availability and usage")
    mcp.add_resource_fn(timeline_resource, uri="atc://timeline", name="timeline", description="Chronological operation timeline")

    return mcp


def main() -> None:
    try:
        config = load_config()
    except ConfigError:
        sys.exit(1)

    app = create_app(config)
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
```

**API note:** `FastMCP.add_resource_fn()` is available in `mcp>=1.2`. If the installed version only has `add_resource()` (which expects a `Resource` object), use the decorator style instead:
```python
@mcp.resource("atc://flights")
def flights_resource() -> str:
    """Current flight queue."""
    return '{"flights": []}'
```
Decorator style is always safe across versions. Check the installed version with `pip show mcp`.

**`tools.py` pattern for stubs:**
```python
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
```

**`resources.py` pattern for stubs:**
```python
import json


def flights_resource() -> str:
    """Current flight queue including unscheduled and cancelled."""
    return json.dumps({"flights": []})


def runways_resource() -> str:
    """Runway availability and usage."""
    return json.dumps({"runways": []})


def timeline_resource() -> str:
    """Chronological timeline of scheduled operations."""
    return json.dumps({"events": []})
```

### Tool Registration — Exact Names Are Pinned

FastMCP registers tools using the **function name** unless overridden. The five function names in `tools.py` must be exactly:

| Function name in tools.py | MCP tool name (what the client sees) |
|---|---|
| `submit_flight` | `submit_flight` |
| `cancel_flight` | `cancel_flight` |
| `generate_schedule` | `generate_schedule` |
| `get_airport_status` | `get_airport_status` |
| `analyze_bottleneck` | `analyze_bottleneck` |

If you register via `mcp.add_tool(fn, name="override")` you can rename — but there is no reason to; just keep the function names as above.

### Resource Registration — Exact URIs Are Pinned

| Resource URI | Handler function |
|---|---|
| `atc://flights` | `flights_resource` |
| `atc://runways` | `runways_resource` |
| `atc://timeline` | `timeline_resource` |

URI casing matters. `atc://flights` not `atc://Flights`. `atc://timeline` not `atc://timelines`.

### Testing Without `pytest-asyncio`

The architecture forbids `pytest-asyncio`. For story 1.4 bootstrap tests, pure synchronous FastMCP introspection is sufficient — no async needed.

**FastMCP tool/resource introspection (sync, no asyncio required):**

```python
# tests/test_server_bootstrap.py
import os
import pytest
from atc_mcp.config import load_config
from atc_mcp.server import create_app

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


@pytest.fixture
def app(monkeypatch):
    for k, v in VALID_ENV.items():
        monkeypatch.setenv(k, v)
    config = load_config()
    return create_app(config)


def test_tool_count(app):
    # FastMCP exposes registered tools via ._tool_manager or .list_tools()
    # Try both; one will work depending on installed version.
    try:
        tools = app._tool_manager.list_tools()          # mcp >= 1.2 internal
    except AttributeError:
        import asyncio
        tools = asyncio.run(app.list_tools())           # fallback
    assert len(tools) == 5


def test_tool_names(app):
    try:
        tools = app._tool_manager.list_tools()
    except AttributeError:
        import asyncio
        tools = asyncio.run(app.list_tools())
    names = {t.name for t in tools}
    assert names == {
        "submit_flight", "generate_schedule", "get_airport_status",
        "cancel_flight", "analyze_bottleneck",
    }


def test_resource_count(app):
    try:
        resources = app._resource_manager.list_resources()
    except AttributeError:
        import asyncio
        resources = asyncio.run(app.list_resources())
    assert len(resources) == 3


def test_resource_uris(app):
    try:
        resources = app._resource_manager.list_resources()
    except AttributeError:
        import asyncio
        resources = asyncio.run(app.list_resources())
    uris = {str(r.uri) for r in resources}
    assert uris == {"atc://flights", "atc://runways", "atc://timeline"}
```

**If `_tool_manager` and `list_tools()` both fail** (version mismatch), escalate to the full in-process memory-transport approach:
```python
import asyncio
from mcp.shared.memory import create_client_server_memory_streams
from mcp.client.session import ClientSession

def test_catalog_via_protocol(monkeypatch):
    for k, v in VALID_ENV.items():
        monkeypatch.setenv(k, v)

    async def run():
        from atc_mcp.server import create_app
        from atc_mcp.config import load_config
        config = load_config()
        app = create_app(config)

        async with create_client_server_memory_streams() as (c_streams, s_streams):
            server_task = asyncio.create_task(
                app.run_async(*s_streams)  # or app._mcp_server.run(...)
            )
            async with ClientSession(*c_streams) as session:
                await session.initialize()
                tools = await session.list_tools()
                resources = await session.list_resources()
                assert {t.name for t in tools.tools} == {
                    "submit_flight", "generate_schedule", "get_airport_status",
                    "cancel_flight", "analyze_bottleneck",
                }
                assert {str(r.uri) for r in resources.resources} == {
                    "atc://flights", "atc://runways", "atc://timeline",
                }
            server_task.cancel()

    asyncio.run(run())
```

Use the introspection pattern first — it is simpler. Fall back to the protocol pattern only if the introspection API is unavailable.

### Config-Failure Test Pattern

```python
# tests/test_config_failure_exit.py
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
        env=env,          # explicit env — do NOT use env=os.environ (parent may have ATC_* set)
        timeout=5,
    )
    assert result.returncode == 1
    assert b"CONFIG ERROR:" in result.stderr
```

**Critical:** Pass `env=env` (not `env=None` or inheriting via `os.environ`). Without this, a developer's shell with valid `ATC_*` exports makes the test pass for the wrong reason, masking the failure path.

### Import Chain After This Story

```
__main__.py   → atc_mcp.server
server.py     → mcp.server.fastmcp (FastMCP), atc_mcp.config, atc_mcp.tools, atc_mcp.resources
tools.py      → pydantic (BaseModel, ConfigDict, Field, Literal) — NO mcp import yet
resources.py  → json — NO mcp import yet
config.py     → os, json, pydantic, sys
domain/       → pydantic — NO mcp, os, time, datetime, random
scheduler/    → domain/ — NO mcp, os, time, datetime, random
```

`server.py` is the **only new `mcp` importer** introduced by this story. `tools.py` and `resources.py` import `mcp` in later stories (when `McpError` is needed for domain-level errors). The `test_imports.py` update must extend the allowed set from `{tools.py, resources.py}` to `{tools.py, resources.py, server.py}`.

### Disaster Prevention

- **Do NOT use `@mcp.tool()` decorators in `tools.py`.** The `mcp` server instance lives in `server.py`. Importing it back into `tools.py` creates a circular dependency. Handler functions in `tools.py` are plain Python — `server.py` registers them with `mcp.add_tool()`.
- **Do NOT call `app.run()` inside `create_app()`.** `run()` is blocking; it must only be called from `main()`. `create_app()` constructs and returns the configured `FastMCP` instance without starting it.
- **Do NOT print to stdout before `app.run()`** or anywhere in the normal execution path. Any `print()` call that lacks `file=sys.stderr` corrupts the JSON-RPC stream. MCP clients expect the very first bytes on stdout to be a valid JSON-RPC message. Use `sys.stderr.write(...)` for any startup logs.
- **Do NOT re-print the config error in `server.py`.** `load_config()` already wrote the `CONFIG ERROR:` line to stderr. `server.py` catches `ConfigError` and calls `sys.exit(1)` only — no second message.
- **Do NOT let `test_config_failure_exit.py` inherit the parent environment.** Always pass an explicit `env=` dict to `subprocess.run()`. If a developer has `ATC_*` set in their shell the test will incorrectly pass for any missing-var scenario.
- **Do NOT import `server.py` at module level in test files before setting env vars.** `server.py` does not read env at import time (only in `main()`), so importing it is safe. But `load_config()` must be called after env vars are set via the fixture.
- **Do NOT add `pytest-asyncio` to `pyproject.toml`.** All tests in this story are sync-safe using `asyncio.run()` for any optional async path. The architecture explicitly forbids this plugin.
- **Story 1.1's `test_server_placeholder.py`** (if created) tested that the old placeholder exited non-zero. After story 1.4 replaces `server.py`, that test will fail if it asserts the placeholder message in stderr. Either update or remove it — do not leave a broken test in the suite.

### Reference Config for All Tests

Use these exact values (from architecture.md §Scenario Walkthroughs). Move to `conftest.py` so test files share it:

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

### Files Modified in This Story

**UPDATE (replace placeholder/empty content):**

```
src/atc_mcp/server.py        — real FastMCP bootstrap + create_app() + main()
src/atc_mcp/__main__.py      — wire: from atc_mcp.server import main; main()
src/atc_mcp/tools.py         — Pydantic input schemas + 5 stub handlers
src/atc_mcp/resources.py     — 3 stub resource handlers
tests/test_imports.py        — add server.py to allowed mcp-importer set
```

**NEW:**
```
tests/conftest.py                    — VALID_ENV fixture (first creation)
tests/test_server_bootstrap.py       — tool/resource catalog assertions
tests/test_config_failure_exit.py    — missing-var exit-code test
```

**Do NOT touch:**
```
src/atc_mcp/config.py        — owned by story 1.2
src/atc_mcp/domain/          — owned by story 1.3
src/atc_mcp/scheduler/       — owned by story 3.x
src/atc_mcp/status.py        — owned by story 3.x
src/atc_mcp/bottleneck.py    — owned by story 4.x
```

### Project Structure Notes

After this story, the full MCP layer is wired (stubs only). The project is runnable end-to-end for the first time — a connected client will discover all tools and resources, invoke stubs and receive "not yet implemented" errors, and read resources to receive empty-state JSON. All subsequent epic work fills in the stub implementations without changing the registration wiring.

The file tree matches architecture.md §Complete Project Directory Structure for everything in `src/atc_mcp/` (all top-level files now have real content). Tests tree gains `conftest.py`, `test_server_bootstrap.py`, `test_config_failure_exit.py`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md §Story 1.4] — AC source, story definition
- [Source: _bmad-output/planning-artifacts/architecture.md §MCP Tool Catalog] — tool names, input/output schemas
- [Source: _bmad-output/planning-artifacts/architecture.md §MCP Resource Catalog] — resource URIs, empty-state payload shapes
- [Source: _bmad-output/planning-artifacts/architecture.md §Structure Patterns / Module dependency direction] — import graph diagram, `server.py` allowed to import `mcp SDK`
- [Source: _bmad-output/planning-artifacts/architecture.md §Format Patterns] — McpError format, null vs empty-list convention
- [Source: _bmad-output/planning-artifacts/architecture.md §Process Patterns / Error handling tiers] — config errors → sys.exit(1); tool input errors → McpError
- [Source: _bmad-output/planning-artifacts/architecture.md §Complete Project Directory Structure] — final file tree
- [Source: _bmad-output/planning-artifacts/architecture.md §Pydantic Model Conventions] — `extra="forbid"` on tool inputs, `frozen=True` on value types
- [Source: _bmad-output/planning-artifacts/epics.md §Story 1.1] — test_imports.py assertions to update; test_server_placeholder.py to review
- [Source: _bmad-output/planning-artifacts/epics.md §Story 1.2] — load_config() and ConfigError interface; CONFIG ERROR: format owned by config.py
- [Source: _bmad-output/planning-artifacts/epics.md §Story 1.3] — domain models available; RunwayRequirements domain type vs RunwayRequirementsInput MCP type

### Latest Technical Information

- **`mcp` SDK (official PyPI package):** As of May 2026 the package is `mcp>=1.2`. `FastMCP` lives in `mcp.server.fastmcp`. Use `pip show mcp` to see the installed version. Do NOT install the separate `fastmcp` package from PrefectHQ — the official `mcp` package already bundles FastMCP.
- **`transport="stdio"` is required:** `app.run()` with no argument may default to streamable HTTP in newer SDK versions. Always call `app.run(transport="stdio")` explicitly to ensure stdio transport.
- **Resource registration API variance:** `mcp.add_resource_fn(fn, uri=..., name=..., description=...)` is available in `mcp>=1.2`. For older installs, use the `@mcp.resource("atc://flights")` decorator style. Decorator style is always safe. Check by inspecting `dir(mcp)` on the FastMCP instance.
- **Pydantic v2 `Literal` imports:** Use `from typing import Literal` (stdlib, Python 3.11+) — do NOT use `from pydantic.v1.typing import Literal`.
- **`NotImplementedError` in tool stubs:** FastMCP propagates unhandled exceptions as MCP tool error responses. Raising `NotImplementedError("not yet implemented")` from a stub produces an error response visible to the client — this satisfies AC-4 without needing `McpError` at this stage.

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.

### File List
