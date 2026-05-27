"""MCP server surface for shortcut-lib.

Exposes registry introspection and shortcut authoring as MCP tools, so any
MCP host (Claude Code, Claude Desktop, ChatGPT, Cursor, …) can drive the
library by name. Local stdio transport only; remote / OAuth is out of scope.

Install with the optional extra::

    uv pip install -e ".[mcp]"

Run::

    python -m shortcut_lib.mcp        # stdio
    shortcut-mcp                       # same, via console script
"""

from shortcut_lib.mcp.server import build_server

__all__ = ["build_server"]
