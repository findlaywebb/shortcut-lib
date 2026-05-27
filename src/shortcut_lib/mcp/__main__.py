"""Stdio entrypoint: ``python -m shortcut_lib.mcp`` or ``shortcut-mcp``."""

from __future__ import annotations

from shortcut_lib.mcp.server import build_server


def main() -> None:
    """Launch the server over stdio.

    Default transport for local MCP hosts (Claude Code, Claude Desktop).
    For remote / multi-tenant use, swap to FastMCP's Streamable HTTP
    transport — out of scope for this build.

    Banner is suppressed: on stdio, FastMCP's startup banner lands on
    stderr but is pure noise for an automated client.
    """
    build_server().run(show_banner=False)


if __name__ == "__main__":
    main()
