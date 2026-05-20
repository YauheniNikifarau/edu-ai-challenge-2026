# Story 1.1: Project Skeleton & Module Boundaries

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer onboarding to the project,
I want a Python project skeleton with the agreed source layout, dependencies, and module-import discipline,
So that all subsequent work has a stable, lint-clean substrate that enforces the architectural import direction from day one.

## Acceptance Criteria

1. **AC-1 — Installable PEP 621 project.** Running `pip install -e .[dev]` against a clean checkout of `task-4/` installs `mcp`, `pydantic>=2`, and `pytest` successfully from a `pyproject.toml` declaring PEP 621 metadata, the `mcp` and `pydantic>=2` runtime deps, and a `[project.optional-dependencies] dev` extra containing `pytest` (and optionally `ruff`).
2. **AC-2 — Source tree exists at agreed paths.** The following files exist under `task-4/src/atc_mcp/` as empty (or near-empty placeholder) modules:
   - `__init__.py`, `__main__.py`, `config.py`, `time_model.py`, `server.py`, `tools.py`, `resources.py`, `status.py`, `bottleneck.py`
   - `domain/__init__.py`, `domain/models.py`, `domain/state.py`
   - `scheduler/__init__.py`, `scheduler/algorithm.py`, `scheduler/constraints.py`
3. **AC-3 — Import-discipline test exists.** `task-4/tests/test_imports.py` exists and asserts all of the following statically (e.g. via `ast` parse of each source file — do **not** execute the modules, since they may raise on import in later stories):
   - No module under `src/atc_mcp/domain/` imports `mcp` or `os` (env access).
   - No module under `src/atc_mcp/scheduler/` imports `mcp` or `os`.
   - `src/atc_mcp/config.py` is the only module under `src/atc_mcp/` that imports `os` (or `os.environ`).
   - `src/atc_mcp/tools.py` and `src/atc_mcp/resources.py` are the only modules under `src/atc_mcp/` that import `mcp`.
4. **AC-4 — Import-discipline test passes.** `pytest -q tests/test_imports.py` exits 0.
5. **AC-5 — Server module fails clearly without config.** Running `python -m atc_mcp.server` (with no `ATC_*` env vars set) exits with a non-zero status code and prints a clear "configuration not loaded" style message to stderr. Full bootstrap is intentionally deferred to Story 1.4 — this AC just guarantees the entrypoint exists and does not silently no-op.

## Tasks / Subtasks

- [x] **Task 1 — Create `pyproject.toml`** (AC: 1)
  - [x] Declare PEP 621 metadata: `name = "atc-mcp"`, `version = "0.1.0"`, `requires-python = ">=3.11"`, short `description`.
  - [x] Configure src-layout: `[tool.setuptools.packages.find] where = ["src"]` (or equivalent if a different build backend is chosen — setuptools is the default and matches the architecture's "minimal dependencies" stance).
  - [x] Build backend: setuptools >= 68 (`[build-system] requires = ["setuptools>=68"]`, `build-backend = "setuptools.build_meta"`).
  - [x] Runtime deps: `mcp` (latest stable), `pydantic>=2`.
  - [x] Optional dev extra: `[project.optional-dependencies] dev = ["pytest>=8"]` (add `ruff` if convenient — optional per architecture).
  - [x] `[project.scripts]` entry `atc-mcp = "atc_mcp.__main__:main"` is **out of scope for this story** — leave it out until Story 1.4. Adding it now would force `__main__.py` to define a real `main()`.
- [x] **Task 2 — Create source tree skeleton** (AC: 2)
  - [x] Create `src/atc_mcp/__init__.py` (empty or just a `__version__ = "0.1.0"` line — no other imports).
  - [x] Create `src/atc_mcp/__main__.py` containing a single-line `# Real entrypoint lands in Story 1.4` placeholder. Do **not** import `server` here — Story 1.4 will wire that.
  - [x] Create empty module files for: `config.py`, `time_model.py`, `tools.py`, `resources.py`, `status.py`, `bottleneck.py`. Each may contain a single docstring describing its responsibility (one line, taken from architecture §Component Decomposition). No imports beyond `__future__` if needed.
  - [x] Create `src/atc_mcp/server.py` containing a small `if __name__ == "__main__":` block (or top-level guard) that prints `configuration not loaded: full server bootstrap lands in Story 1.4` to **stderr** and calls `sys.exit(1)`. This is the only file in this story that imports `sys`. Do **not** import `mcp`, `config`, `tools`, or `resources` — those land in Story 1.4.
  - [x] Create `src/atc_mcp/domain/__init__.py`, `src/atc_mcp/domain/models.py`, `src/atc_mcp/domain/state.py`. Each empty or with a one-line docstring only.
  - [x] Create `src/atc_mcp/scheduler/__init__.py`, `src/atc_mcp/scheduler/algorithm.py`, `src/atc_mcp/scheduler/constraints.py`. Same one-line-docstring rule.
- [x] **Task 3 — Create `tests/test_imports.py`** (AC: 3, 4)
  - [x] Create `tests/__init__.py` (empty) and `tests/test_imports.py`.
  - [x] Use the `ast` module to walk every `.py` file under `src/atc_mcp/` and collect `Import` / `ImportFrom` nodes. Do **not** `importlib.import_module(...)` — modules may raise in later stories before all dependencies are wired, and we want this guard to remain green throughout.
  - [x] Helper: `def imports_of(path: Path) -> set[str]` returning the set of top-level imported module names (the part before any `.`).
  - [x] Assert: every file under `src/atc_mcp/domain/` has `{"mcp", "os"}.isdisjoint(imports_of(path))` is True.
  - [x] Assert: every file under `src/atc_mcp/scheduler/` has `{"mcp", "os"}.isdisjoint(imports_of(path))` is True.
  - [x] Assert: among all files under `src/atc_mcp/`, the only one whose imports contain `"os"` is `config.py` — and in this story that set is empty, so the assertion is "for every file != config.py: 'os' not in imports". `config.py` itself may but is not required to import `os` in this story.
  - [x] Assert: among all files under `src/atc_mcp/`, the only ones whose imports may contain `"mcp"` are `tools.py` and `resources.py`. In this story none of them import `mcp` yet, so the assertion is "for every file not in {tools.py, resources.py}: 'mcp' not in imports".
  - [x] Pin the rules as a single parametrized test or four focused tests — either is fine; clarity wins.
  - [x] `pytest -q tests/test_imports.py` must pass.
- [x] **Task 4 — Verify `python -m atc_mcp.server` exit behaviour** (AC: 5)
  - [x] Manual smoke: with a fresh shell and no `ATC_*` env vars, run `python -m atc_mcp.server`. Confirm exit code is non-zero (likely `1`) and stderr contains the placeholder message from Task 2.
  - [x] Optional (recommended, low-cost) regression test: `tests/test_server_placeholder.py` invokes the module via `subprocess.run([sys.executable, "-m", "atc_mcp.server"], capture_output=True)` and asserts `returncode != 0` and a substring of the placeholder message in stderr. This guards AC-5 against Story 1.4 accidentally removing it before the full bootstrap is wired. **Skip this test if it would block Story 1.4's normal-path bootstrap design** — coordinate with Story 1.4's author. Default: include it; Story 1.4 will update or replace.
- [x] **Task 5 — Verify the install path end-to-end** (AC: 1)
  - [x] In a fresh virtualenv: `pip install -e .[dev]` succeeds.
  - [x] `python -c "import atc_mcp"` succeeds.
  - [x] `pytest -q` from `task-4/` runs and passes (only `test_imports.py`, and `test_server_placeholder.py` if included).

### Review Findings

- [ ] [Review][Patch] Vacuous-pass: no existence guard before `rglob` loops in `test_imports.py` [tests/test_imports.py:31,44,57,72]
- [ ] [Review][Patch] `.gitignore` missing `.env` pattern [.gitignore:8]
- [x] [Review][Defer] `test_server_placeholder.py` subprocess test silently fails with `ModuleNotFoundError` when run without `pip install -e .` [tests/test_server_placeholder.py:7] — deferred, pre-existing
- [x] [Review][Defer] `ast.walk` descends into `TYPE_CHECKING` blocks — future stories using `if TYPE_CHECKING: import mcp` in domain/scheduler will trip import-discipline tests as false positives [tests/test_imports.py:17] — deferred, pre-existing
- [x] [Review][Defer] `ast.parse` raises `SyntaxError` on malformed files with no error-handling wrapper — unclear test failure messages [tests/test_imports.py:15] — deferred, pre-existing

## Dev Notes

### Relevant Architecture Patterns & Constraints

- **Tech stack (architecture.md §Tech Stack Decision):** Python 3.11+ (insertion-ordered dicts and stable `sorted` are part of the determinism argument), official `mcp` SDK over stdio, Pydantic v2, `pytest`. `ruff` is optional. No third-party scaffolder — hand-rolled minimal layout is the convention.
- **Project layout (architecture.md §Project Layout / §Complete Project Directory Structure):** src-layout under `src/atc_mcp/`. See "File Structure Requirements" below for the exact tree this story must produce.
- **Module dependency direction (architecture.md §Structure Patterns):** strict one-way import graph — `domain/` and `scheduler/` must be MCP-agnostic and free of env-var access; `config.py` is the only env reader; `tools.py` and `resources.py` are the only MCP-facing layers. This is the most important invariant this story locks in.
- **Determinism guard-rails (architecture.md §Ordering Patterns):** later stories will also ban `time.time()`, `datetime.now()`, `datetime.utcnow()`, and `random` in `domain/` and `scheduler/`. Story 1.3 extends `test_imports.py` to assert this. Don't add those bans here — keep this story's test minimal so Story 1.3's extension is a clean diff.
- **`__main__.py` vs `server.py` (architecture.md §Project Layout):** the architecture shows both `python -m atc_mcp` (via `__main__.py`) and `server.py` as the MCP boot file. Story 1.4 wires both. This story only needs `server.py`'s placeholder to satisfy AC-5; `__main__.py` exists but is intentionally inert until Story 1.4.
- **No `.env` files (architecture.md §File Organization Patterns):** env vars are runtime config only. Do not create `.env`, `.env.example`, `dotenv` dependencies, or `.envrc`. This is a hard "do not" from the architecture.
- **Test layout (architecture.md §Structure Patterns / §Complete Project Directory Structure):** flat `tests/` directory, no `unit/`/`integration/` split. `tests/conftest.py` will host shared fixtures (added in later stories — don't create it empty here, that's noise).

### Source Tree Components to Touch (NEW files only — this is the bootstrap story)

```
task-4/
├── pyproject.toml                          # NEW (Task 1)
├── .python-version                         # OPTIONAL (3.11) — add if convenient, not required by AC
├── .gitignore                              # NEW or augment — at minimum: __pycache__/, *.egg-info/, .venv/, .pytest_cache/
├── src/
│   └── atc_mcp/
│       ├── __init__.py                     # NEW
│       ├── __main__.py                     # NEW (inert placeholder)
│       ├── config.py                       # NEW (empty module + docstring)
│       ├── time_model.py                   # NEW (empty module + docstring)
│       ├── server.py                       # NEW (placeholder that exits non-zero with stderr message)
│       ├── tools.py                        # NEW (empty)
│       ├── resources.py                    # NEW (empty)
│       ├── status.py                       # NEW (empty)
│       ├── bottleneck.py                   # NEW (empty)
│       ├── domain/
│       │   ├── __init__.py                 # NEW
│       │   ├── models.py                   # NEW (empty)
│       │   └── state.py                    # NEW (empty)
│       └── scheduler/
│           ├── __init__.py                 # NEW
│           ├── algorithm.py                # NEW (empty)
│           └── constraints.py              # NEW (empty)
└── tests/
    ├── __init__.py                         # NEW (empty)
    ├── test_imports.py                     # NEW (Task 3)
    └── test_server_placeholder.py          # NEW (Task 4, optional but recommended)
```

No existing files are modified — this is a greenfield bootstrap. There is no UPDATE work this story needs to scan.

### Library / Framework Requirements

| Concern | Choice | Version policy | Where it lives |
|---|---|---|---|
| Language | Python | `>=3.11` (pin in `requires-python` and `.python-version`) | `pyproject.toml` |
| MCP SDK | `mcp` | latest stable on PyPI at time of install (don't hard-pin in this story; let `pip install` resolve) | runtime dep in `pyproject.toml` |
| Validation | `pydantic` | `>=2` (Pydantic v2 only; v1 is excluded — `field_validator` style, `ConfigDict`) | runtime dep in `pyproject.toml` |
| Testing | `pytest` | `>=8` | `dev` optional dep |
| Lint/format (optional) | `ruff` | latest | `dev` optional dep — include only if developer prefers |

**Critical:** do not add `dotenv`, `pydantic-settings`, `typer`, `click`, `rich`, `structlog`, or any other "convenience" dependency. The architecture is deliberately spartan — see architecture.md §"Lightweight (NFR-1)" and §Anti-Patterns. `config.py` will use stdlib `os.environ` only.

### Testing Standards Summary

- Framework: `pytest` only. No plugins beyond what ships by default. No `pytest-asyncio`, no `pytest-mock` — both are unnecessary for the project's synchronous, pure-function core.
- Test layout: flat `tests/` (no `tests/unit/`, `tests/integration/`).
- This story's tests are **static analysis tests** (parse source with `ast`) not runtime imports. Rationale: later stories will leave modules in intentionally non-runnable states between commits (e.g. `state.py` with type annotations referencing types defined elsewhere). A static-`ast`-based `test_imports.py` survives those churns. **Do not** use `importlib.import_module` in `test_imports.py`.
- Run command for this story: `pytest -q` from the `task-4/` directory.

### Project Structure Notes

- **Alignment:** the file tree in §"Source Tree Components to Touch" is a strict subset of architecture.md §Complete Project Directory Structure (lines around the `task-4/` block). Every file listed there that belongs to module-skeleton scope is created here. Files that belong to later stories (`conftest.py`, the VS test files, `test_determinism.py`, `test_status.py`, etc.) are explicitly **not** created — they would be misleading empty stubs.
- **Detected variance — none.** The story's AC-2 list and the architecture file tree match.
- **README / report:** architecture.md §Complete Project Directory Structure lists `README.md` and `report.md`. NFR-4 assigns them to Epic 4 (per epics.md §FR Coverage Map). **Do not create them in this story** — Story 4.x owns their content. If you create empty placeholders here, the reader cannot tell whether the file is "done" or "todo".

### References

- [Source: _bmad-output/planning-artifacts/epics.md §"Story 1.1: Project Skeleton & Module Boundaries"] — AC source.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Tech Stack & Project Bootstrap (resolves DD-3)"] — tech stack, Python version, dep set, init steps.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Project Layout (bootstrap convention)"] — initial file tree.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Structure Patterns" / "Module dependency direction (strict)"] — the import-discipline graph this story's `test_imports.py` encodes.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Complete Project Directory Structure"] — full target tree (this story builds a subset).
- [Source: _bmad-output/planning-artifacts/architecture.md §"Architectural Decisions Provided by This Bootstrap"] — Python 3.11+, sync core, async only where SDK demands.
- [Source: _bmad-output/planning-artifacts/architecture.md §"Anti-Patterns (What to Avoid)"] — do not add convenience deps; do not wrap MCP outputs; do not introduce dotenv.
- [Source: _bmad-output/planning-artifacts/epics.md §"Story 1.2"] — the next story will fill `config.py`; do not pre-empt its env-var loading.
- [Source: _bmad-output/planning-artifacts/epics.md §"Story 1.3"] — the next-next story will extend `test_imports.py` with `time`, `datetime`, `random` bans; do not add those here.
- [Source: _bmad-output/planning-artifacts/epics.md §"Story 1.4"] — full MCP server bootstrap; this story leaves `server.py` and `__main__.py` intentionally inert.

### Latest Technical Information

- **`mcp` Python SDK (modelcontextprotocol/python-sdk):** the official SDK supports stdio transport via the `stdio_server` async context manager and registers tools/resources on a `Server` instance. The exact integration is Story 1.4's concern. For this story, **do not** import `mcp` anywhere — the import-discipline test is the only mechanism guarding the architectural boundary, and adding the import in `server.py`'s placeholder would weaken Story 1.4's design freedom.
- **Pydantic v2:** use `from pydantic import BaseModel, ConfigDict, Field, field_validator`. The legacy `from pydantic import validator` (v1) is banned by architecture.md §"Pydantic Model Conventions". This story does not define any models, but the rule is in force from the moment `domain/models.py` gets its first line of code in Story 1.3.
- **setuptools src-layout:** with PEP 621 `[project]` metadata, the minimal setuptools config is `[tool.setuptools.packages.find] where = ["src"]` and `[tool.setuptools.package-dir] "" = "src"`. Verify the editable install actually picks up `atc_mcp` from `src/` — a common gotcha is forgetting `package-dir`, which causes `pip install -e .` to silently install nothing.

### Project Context Reference

No `project-context.md` was discovered under `task-4/` at the time this story was created. The persistent-facts hook is configured to load it if it appears later, but no project-specific rule overrides apply right now. All implementation rules come from `architecture.md` and `epics.md`.

### Disaster-Prevention Notes (read once, then forget)

- **Do not** define a real `main()` in `__main__.py`. Story 1.4 owns it. An accidental `main()` here that does anything beyond `pass` will silently take over from `server.py`'s placeholder and break AC-5 in a confusing way.
- **Do not** add `from __future__ import annotations` blindly to every file — it's only useful in modules that have forward references. Empty stub files don't need it.
- **Do not** create a `tests/conftest.py` yet. It is owned by Story 1.4+. An empty conftest is dead weight; a non-empty one pre-empts later design.
- **Do not** add `mypy`, `coverage`, `pre-commit`, `tox`, or a `Makefile`. None are required by architecture or epics. The project is small enough that `pip install -e .[dev] && pytest -q` is the entire workflow.
- **Do not** ship a `.env.example`. Architecture explicitly bans `.env` files.
- The placeholder string for AC-5 should be stable enough that Story 1.4's tests don't need to depend on it byte-for-byte. Suggested wording: `configuration not loaded: full server bootstrap lands in Story 1.4`. Story 1.4 will replace it; that's fine.

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (Windsurf / Cascade)

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implemented full Story 1.1 greenfield bootstrap. Created `pyproject.toml` (PEP 621, setuptools src-layout, `mcp`, `pydantic>=2`, `pytest>=8`, `ruff` dev deps). Created all 14 source skeleton files under `src/atc_mcp/` with one-line docstrings only; `server.py` is the sole file importing `sys` and exits 1 with stderr message for AC-5. Created `tests/__init__.py`, `tests/test_imports.py` (4 AST-based import-discipline tests covering all AC-3 assertions), and `tests/test_server_placeholder.py` (subprocess regression for AC-5). All 5 tests pass (`pytest -q` → 5 passed in 0.06s). Editable install via `.venv` verified (`import atc_mcp` ok).

### File List

- task-4/pyproject.toml
- task-4/.gitignore
- task-4/src/atc_mcp/__init__.py
- task-4/src/atc_mcp/__main__.py
- task-4/src/atc_mcp/config.py
- task-4/src/atc_mcp/time_model.py
- task-4/src/atc_mcp/server.py
- task-4/src/atc_mcp/tools.py
- task-4/src/atc_mcp/resources.py
- task-4/src/atc_mcp/status.py
- task-4/src/atc_mcp/bottleneck.py
- task-4/src/atc_mcp/domain/__init__.py
- task-4/src/atc_mcp/domain/models.py
- task-4/src/atc_mcp/domain/state.py
- task-4/src/atc_mcp/scheduler/__init__.py
- task-4/src/atc_mcp/scheduler/algorithm.py
- task-4/src/atc_mcp/scheduler/constraints.py
- task-4/tests/__init__.py
- task-4/tests/test_imports.py
- task-4/tests/test_server_placeholder.py

## Change Log

- 2026-05-20: Story 1.1 implemented — greenfield bootstrap. Created `pyproject.toml`, 14 source skeleton modules under `src/atc_mcp/`, `tests/test_imports.py` (4 AST import-discipline tests), `tests/test_server_placeholder.py` (AC-5 regression). All 5 tests pass. Status → review.
