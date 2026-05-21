"""MCP server entrypoint — full bootstrap lands in Story 1.4."""
import sys

from mcp.server.fastmcp import FastMCP

from atc_mcp.config import ConfigError, load_config
from atc_mcp.resources import flights_resource, runways_resource, timeline_resource
from atc_mcp.tools import (
    analyze_bottleneck,
    cancel_flight,
    generate_schedule,
    get_airport_status,
    submit_flight,
)


def create_app(config) -> FastMCP:
    from atc_mcp.domain.state import state
    
    mcp = FastMCP("atc-mcp")

    mcp.add_tool(submit_flight)
    mcp.add_tool(cancel_flight)
    mcp.add_tool(generate_schedule)
    mcp.add_tool(get_airport_status)
    mcp.add_tool(analyze_bottleneck)

    mcp.resource("atc://flights")(flights_resource)
    mcp.resource("atc://runways")(runways_resource)
    mcp.resource("atc://timeline")(timeline_resource)

    state.set_config(config)
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
