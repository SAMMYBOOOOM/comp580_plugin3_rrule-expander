from mcp.server.fastmcp import FastMCP

from plugin.expand_rrule import expand_rrule

mcp = FastMCP("rrule-expander")

IMPLEMENTATIONS = {
    "expand_rrule": expand_rrule,
}


@mcp.tool()
def expand_rrule_tool(
    dtstart: str,
    rrule: str,
    window_start: str,
    window_end: str,
    max_occurrences: int = 100,
) -> dict:
    """Validate and expand a supported RFC 5545 daily recurrence rule."""
    return expand_rrule(
        dtstart=dtstart,
        rrule=rrule,
        window_start=window_start,
        window_end=window_end,
        max_occurrences=max_occurrences,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")