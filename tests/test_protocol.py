"""MCP protocol and tool schema tests."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_mcp(messages: list[dict]) -> list[dict]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["WALLABAG_BASE_URL"] = "https://wallabag.example"
    env["WALLABAG_ACCESS_TOKEN"] = "test-token"
    proc = subprocess.Popen(
        [sys.executable, "-m", "wallabag_mcp"],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    stdin = proc.stdin
    stdout = proc.stdout
    stderr_pipe = proc.stderr
    assert stdin is not None
    assert stdout is not None
    assert stderr_pipe is not None
    stdout_lines: queue.Queue[str | None] = queue.Queue()

    def read_stdout() -> None:
        for line in stdout:
            stdout_lines.put(line)
        stdout_lines.put(None)

    threading.Thread(target=read_stdout, daemon=True).start()
    responses: list[dict] = []
    try:
        for message in messages:
            stdin.write(json.dumps(message) + "\n")
            stdin.flush()
            if "id" not in message:
                continue
            while True:
                line = stdout_lines.get(timeout=30)
                assert line is not None, "MCP server exited before replying"
                response = json.loads(line)
                responses.append(response)
                if response.get("id") == message["id"]:
                    break
    finally:
        stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)

    stderr = stderr_pipe.read()
    assert "Traceback" not in stderr
    return responses


def test_tools_list_has_complete_descriptions() -> None:
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "1.0.0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    responses = _run_mcp(messages)
    listed = next(r for r in responses if r.get("id") == 2)
    tools = listed["result"]["tools"]

    assert len(tools) >= 17
    names = {t["name"] for t in tools}
    assert "wallabag_health_check" in names
    assert "wallabag_list_entries" in names
    assert "wallabag_add_entry" in names
    assert "wallabag_archive_entry" in names
    assert "wallabag_list_annotations" in names

    for tool in tools:
        assert tool.get("description"), f"missing tool description: {tool['name']}"
        properties = tool.get("inputSchema", {}).get("properties", {})
        for param_name, schema in properties.items():
            assert schema.get("description"), f"{tool['name']}.{param_name} missing description"


def test_missing_base_url_fails_cleanly() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env.pop("WALLABAG_BASE_URL", None)
    proc = subprocess.run(
        [sys.executable, "-m", "wallabag_mcp"],
        cwd=ROOT,
        input="",
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    assert proc.returncode == 1
    assert "WALLABAG_BASE_URL is required" in proc.stderr
