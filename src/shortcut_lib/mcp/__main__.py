"""Stdio entrypoint: ``python -m shortcut_lib.mcp`` or ``shortcut-mcp``."""

from __future__ import annotations

from shortcut_lib.mcp.server import build_server


def main() -> None:
    """Launch the server over stdio.

    Default transport for local MCP hosts (Claude Code, Claude Desktop).
    For remote / multi-tenant use, swap to FastMCP's Streamable HTTP
    transport — out of scope for this build.
    """
    build_server().run()


if __name__ == "__main__":
    main()
