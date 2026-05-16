#!/usr/bin/env python3
"""Run lightweight LLM validation against OpenAI-compatible endpoints."""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
PROMPT = (ROOT / "scripts" / "model_validation_prompt.txt").read_text()


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def validate(name: str, base_url: str, model: str, api_key: str = "default") -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a strict but concise software release reviewer."},
            {"role": "user", "content": PROMPT},
        ],
        "temperature": 0,
        "max_tokens": 2000,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=180) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content") or msg.get("reasoning_content") or msg.get("reasoning") or json.dumps(msg, indent=2)
    out = ROOT / f"validation_{name}.txt"
    out.write_text(str(content))
    return str(content)


def main() -> int:
    load_env(Path.home() / ".hermes" / ".env")
    targets = []
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    if deepseek_key:
        targets.append(("deepseek_v4_pro", "https://api.deepseek.com/v1", "deepseek-v4-pro", deepseek_key))
    targets.append(("aeon_ultimate", "http://192.168.68.164:8000/v1", "aeon-ultimate", "default"))

    failures = 0
    for name, base, model, key in targets:
        print(f"=== {name} ({model}) ===")
        try:
            content = validate(name, base, model, key)
            print(content[:2000])
            if "VERDICT: PASS" not in content:
                failures += 1
        except Exception as exc:
            failures += 1
            print(f"ERROR: {exc}")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
