#!/usr/bin/env python3
"""Validate public wallabag API documentation endpoints without account credentials."""

from __future__ import annotations

import httpx

URLS = [
    "https://doc.wallabag.org/developer/api/",
    "https://doc.wallabag.org/developer/api/oauth/",
    "https://doc.wallabag.org/developer/api/methods/",
    "https://app.wallabag.it/api/doc",
]

EXPECTED = [
    "wallabag API",
    "oauth/v2/token",
    "/api/entries",
    "wallabag API documentation",
]


def main() -> int:
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for url, expected in zip(URLS, EXPECTED, strict=True):
            response = client.get(url)
            print(f"{response.status_code} {url}")
            response.raise_for_status()
            if expected.lower() not in response.text.lower():
                raise AssertionError(f"{url} did not contain expected text: {expected!r}")
    print(f"{len(URLS)}/{len(URLS)} public wallabag documentation checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
