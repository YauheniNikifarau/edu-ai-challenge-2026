"""Regression test for AC-5 (updated for Story 1.4): server exits non-zero on missing config."""
import sys
import subprocess


def test_server_exits_nonzero_without_config():
    result = subprocess.run(
        [sys.executable, "-m", "atc_mcp.server"],
        capture_output=True,
        env={},
        timeout=5,
    )
    assert result.returncode != 0, "Expected non-zero exit code when ATC_* vars are missing"
    assert b"CONFIG ERROR:" in result.stderr, (
        f"Expected 'CONFIG ERROR:' in stderr, got: {result.stderr!r}"
    )
