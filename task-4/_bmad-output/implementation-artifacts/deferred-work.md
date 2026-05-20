# Deferred Work

## Deferred from: code review of 1-1-project-skeleton-and-module-boundaries (2026-05-20)

- `test_server_placeholder.py` subprocess test silently fails with `ModuleNotFoundError` when run without `pip install -e .` — no `[tool.pytest.ini_options] pythonpath` configured; by design (install step is required per story spec), but could confuse fresh contributors.
- `ast.walk` in `imports_of()` descends into `TYPE_CHECKING` blocks — future stories using `if TYPE_CHECKING: import mcp` (e.g. for type annotations in `domain/` or `scheduler/`) will cause import-discipline tests to fail as false positives. Re-visit in Story 1.3 when `test_imports.py` is extended.
- `ast.parse` in `imports_of()` raises `SyntaxError` on malformed source files with no wrapping try/except — produces an unclear pytest error message. Low risk while all source files are stubs; re-visit if a story introduces temporary syntax errors during development.
