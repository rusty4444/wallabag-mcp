"""wallabag MCP server package."""

from __future__ import annotations

import os
import sys
from importlib.metadata import PackageNotFoundError, version

from mcp.server.mcpserver import MCPServer

from . import client as api
from .tools import register_tools

try:
    __version__ = version("wallabag-mcp")
except PackageNotFoundError:  # running from a source checkout without an install
    __version__ = "0.0.0"

mcp = MCPServer("wallabag-mcp", version=__version__)
register_tools(mcp)


def main() -> None:
    """Run the wallabag MCP server over stdio."""
    base_url = os.environ.get("WALLABAG_BASE_URL", "").strip()
    if not base_url:
        print("Error: WALLABAG_BASE_URL is required", file=sys.stderr)
        sys.exit(1)

    api.configure(
        base_url=base_url,
        client_id=os.environ.get("WALLABAG_CLIENT_ID"),
        client_secret=os.environ.get("WALLABAG_CLIENT_SECRET"),
        username=os.environ.get("WALLABAG_USERNAME"),
        password=os.environ.get("WALLABAG_PASSWORD"),
        access_token=os.environ.get("WALLABAG_ACCESS_TOKEN"),
        refresh_token=os.environ.get("WALLABAG_REFRESH_TOKEN"),
        timeout=float(os.environ.get("WALLABAG_TIMEOUT", "20")),
    )
    mcp.run(transport="stdio")


__all__ = ["__version__", "main", "mcp"]
