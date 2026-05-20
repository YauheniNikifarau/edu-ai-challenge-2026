"""Regression test for AC-5: server module exits non-zero with a clear message (Story 1.1)."""
import sys
import subprocess


def test_server_placeholder_exits_nonzero_with_message():
    result = subprocess.run(
        [sys.executable, "-m", "atc_mcp.server"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, "Expected non-zero exit code from atc_mcp.server placeholder"
    assert "configuration not loaded" in result.stderr, (
        f"Expected 'configuration not loaded' in stderr, got: {result.stderr!r}"
    )
