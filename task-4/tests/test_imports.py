"""Static import-discipline tests for the atc_mcp source tree (AC-3, AC-4).

Uses ast to parse source files — never imports the modules at runtime so that
this guard stays green even when individual modules are intentionally left in
non-runnable states between stories.
"""
import ast
from pathlib import Path

SRC_ROOT = Path(__file__).parent.parent / "src" / "atc_mcp"


def imports_of(path: Path) -> set[str]:
    """Return the set of top-level module names imported by *path* (part before any '.')."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


# ---------------------------------------------------------------------------
# AC-3a: domain/ must not import mcp or os
# ---------------------------------------------------------------------------

def test_domain_no_mcp_no_os():
    domain_dir = SRC_ROOT / "domain"
    for path in domain_dir.rglob("*.py"):
        forbidden = {"mcp", "os"} & imports_of(path)
        assert not forbidden, (
            f"{path.relative_to(SRC_ROOT.parent.parent)} imports forbidden modules: {forbidden}"
        )


# ---------------------------------------------------------------------------
# AC-3b: scheduler/ must not import mcp or os
# ---------------------------------------------------------------------------

def test_scheduler_no_mcp_no_os():
    scheduler_dir = SRC_ROOT / "scheduler"
    for path in scheduler_dir.rglob("*.py"):
        forbidden = {"mcp", "os"} & imports_of(path)
        assert not forbidden, (
            f"{path.relative_to(SRC_ROOT.parent.parent)} imports forbidden modules: {forbidden}"
        )


# ---------------------------------------------------------------------------
# AC-3c: only config.py may import os under src/atc_mcp/
# ---------------------------------------------------------------------------

def test_only_config_imports_os():
    config_py = SRC_ROOT / "config.py"
    for path in SRC_ROOT.rglob("*.py"):
        if path == config_py:
            continue
        assert "os" not in imports_of(path), (
            f"{path.relative_to(SRC_ROOT.parent.parent)} must not import 'os' "
            f"(only config.py is allowed to)"
        )


# ---------------------------------------------------------------------------
# AC-3d: only tools.py and resources.py may import mcp under src/atc_mcp/
# ---------------------------------------------------------------------------

def test_only_tools_and_resources_import_mcp():
    allowed = {SRC_ROOT / "tools.py", SRC_ROOT / "resources.py"}
    for path in SRC_ROOT.rglob("*.py"):
        if path in allowed:
            continue
        assert "mcp" not in imports_of(path), (
            f"{path.relative_to(SRC_ROOT.parent.parent)} must not import 'mcp' "
            f"(only tools.py and resources.py are allowed to)"
        )
