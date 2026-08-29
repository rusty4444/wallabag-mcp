# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -e '.[dev]'          # setup
ruff check .                     # lint (line-length 120, rules E,F,I,UP,B,SIM)
pytest                           # tests
pytest tests/test_client.py::test_oauth_token_requested_and_used   # single test
python scripts/live_docs_test.py # hits live wallabag docs; also runs in CI
```

CI (`.github/workflows/ci.yml`) runs exactly those four on Python 3.11.

`scripts/model_validate.py` is an optional, unwired LLM-endpoint check — not part of CI.

## Architecture

Three layers, stdio MCP server:

- `client.py` — thin httpx wrapper over the wallabag REST API. **All config and the OAuth token live in module-level globals**, set via `configure()` (falling back to env vars per-read). There is no client object to pass around; tests must call `client.configure(...)` in a fixture. `_token()` does the password grant against `/oauth/v2/token` and caches the token with a 30s expiry margin. Every failure raises `WallabagError`.
- `tools.py` — `register_tools(mcp)` defines all ~17 tools inside one function closing over the MCPServer instance. Tools return **strings, never structured data**, and each wraps its call in `except Exception` returning `f"Error ...: {exc}"` so the MCP client sees a message rather than a protocol error.
- `__init__.py` — builds the `MCPServer` singleton at import time, `main()` reads env vars → `configure()` → `mcp.run(transport="stdio")`.

Details that bite:

- `_api_path()` appends `.json` to every path (`/api/entries.json`) — mock URLs in tests must include it.
- wallabag responses are HAL-ish; `_items()` unwraps `_embedded.items`, plain `items`, or a bare list. Mutating endpoints sometimes return 204/empty, so client functions fall back to re-fetching the entry.
- Booleans cross the API as `0`/`1` via `_bool_int()`; tags are comma-separated strings, not lists.
- `tests/test_protocol.py` spawns the server as a subprocess and asserts every tool **and every parameter** has a non-empty description. New `Field(description=...)` is mandatory, and the tool count assertion (`>= 17`) is a floor.

## Release metadata

The package version appears in three places that must move together: `pyproject.toml` and `server.json` (twice: top level and inside `packages[0]`). `skill/SKILL.md` carries its own `version` frontmatter that tracks the skill's content, not the server release — leave it alone unless the skill's own instructions change. `server.json` is the MCP registry manifest; the `<!-- mcp-name: ... -->` comment in `README.md` is required for registry validation — don't remove it.
