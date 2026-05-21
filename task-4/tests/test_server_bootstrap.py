"""Bootstrap tests — verify tool and resource catalog (AC-6, Story 1.4)."""
import pytest
from atc_mcp.config import load_config
from atc_mcp.server import create_app

EXPECTED_TOOL_NAMES = {
    "submit_flight",
    "generate_schedule",
    "get_airport_status",
    "cancel_flight",
    "analyze_bottleneck",
}

EXPECTED_RESOURCE_URIS = {
    "atc://flights",
    "atc://runways",
    "atc://timeline",
}


@pytest.fixture
def app(valid_env):
    config = load_config()
    return create_app(config)


def _list_tools(app):
    try:
        return app._tool_manager.list_tools()
    except AttributeError:
        import asyncio
        return asyncio.run(app.list_tools())


def _list_resources(app):
    try:
        return app._resource_manager.list_resources()
    except AttributeError:
        import asyncio
        return asyncio.run(app.list_resources())


def test_tool_count(app):
    assert len(_list_tools(app)) == 5


def test_tool_names(app):
    names = {t.name for t in _list_tools(app)}
    assert names == EXPECTED_TOOL_NAMES


def test_resource_count(app):
    assert len(_list_resources(app)) == 3


def test_resource_uris(app):
    uris = {str(r.uri) for r in _list_resources(app)}
    assert uris == EXPECTED_RESOURCE_URIS
