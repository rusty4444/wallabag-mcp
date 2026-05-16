"""Thin wallabag REST API client."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

_BASE_URL: str | None = None
_CLIENT_ID: str | None = None
_CLIENT_SECRET: str | None = None
_USERNAME: str | None = None
_PASSWORD: str | None = None
_ACCESS_TOKEN: str | None = None
_REFRESH_TOKEN: str | None = None
_TOKEN_EXPIRES_AT = 0.0
_TIMEOUT = 20.0


class WallabagError(RuntimeError):
    """Raised when the wallabag API returns an error."""


def configure(
    base_url: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    username: str | None = None,
    password: str | None = None,
    access_token: str | None = None,
    refresh_token: str | None = None,
    timeout: float | None = None,
) -> None:
    """Configure the wallabag API client."""
    global _BASE_URL, _CLIENT_ID, _CLIENT_SECRET, _USERNAME, _PASSWORD, _ACCESS_TOKEN, _REFRESH_TOKEN, _TIMEOUT
    if base_url is not None:
        _BASE_URL = base_url.rstrip("/")
    if client_id is not None:
        _CLIENT_ID = client_id
    if client_secret is not None:
        _CLIENT_SECRET = client_secret
    if username is not None:
        _USERNAME = username
    if password is not None:
        _PASSWORD = password
    if access_token is not None:
        _ACCESS_TOKEN = access_token
    if refresh_token is not None:
        _REFRESH_TOKEN = refresh_token
    if timeout is not None:
        _TIMEOUT = timeout


def _base_url() -> str:
    base = (_BASE_URL or os.environ.get("WALLABAG_BASE_URL") or "").rstrip("/")
    if not base:
        raise WallabagError("WALLABAG_BASE_URL is required")
    return base


def _api_path(path: str, fmt: bool = True) -> str:
    suffix = ".json" if fmt and not path.endswith(".json") else ""
    return f"/api{path}{suffix}"


def _credentials() -> tuple[str | None, str | None, str | None, str | None]:
    return (
        _CLIENT_ID or os.environ.get("WALLABAG_CLIENT_ID"),
        _CLIENT_SECRET or os.environ.get("WALLABAG_CLIENT_SECRET"),
        _USERNAME or os.environ.get("WALLABAG_USERNAME"),
        _PASSWORD or os.environ.get("WALLABAG_PASSWORD"),
    )


def _token() -> str:
    global _ACCESS_TOKEN, _REFRESH_TOKEN, _TOKEN_EXPIRES_AT
    token = _ACCESS_TOKEN or os.environ.get("WALLABAG_ACCESS_TOKEN")
    if token and time.time() < _TOKEN_EXPIRES_AT - 30:
        return token
    if token and not _TOKEN_EXPIRES_AT:
        return token

    client_id, client_secret, username, password = _credentials()
    if not (client_id and client_secret and username and password):
        raise WallabagError(
            "Authentication requires WALLABAG_ACCESS_TOKEN or WALLABAG_CLIENT_ID, WALLABAG_CLIENT_SECRET, WALLABAG_USERNAME, and WALLABAG_PASSWORD"
        )
    data = {
        "grant_type": "password",
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password,
    }
    try:
        response = httpx.post(f"{_base_url()}/oauth/v2/token", data=data, timeout=_TIMEOUT)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise WallabagError(f"OAuth token request failed: HTTP {exc.response.status_code}: {exc.response.text[:500]}") from exc
    except httpx.HTTPError as exc:
        raise WallabagError(f"OAuth token request failed: {exc}") from exc
    payload = response.json()
    _ACCESS_TOKEN = str(payload["access_token"])
    _REFRESH_TOKEN = payload.get("refresh_token")
    _TOKEN_EXPIRES_AT = time.time() + int(payload.get("expires_in") or 3600)
    return _ACCESS_TOKEN


def _request(method: str, path: str, *, params: dict[str, Any] | None = None, json_body: dict[str, Any] | None = None) -> Any:
    url = f"{_base_url()}{path}"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {_token()}"}
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    try:
        response = httpx.request(method, url, headers=headers, params=_drop_none(params or {}), json=json_body, timeout=_TIMEOUT)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise WallabagError(f"{method} {path} failed: HTTP {exc.response.status_code}: {exc.response.text[:500]}") from exc
    except httpx.HTTPError as exc:
        raise WallabagError(f"{method} {path} failed: {exc}") from exc
    if response.status_code == 204 or not response.content:
        return {"ok": True}
    ctype = response.headers.get("content-type", "")
    if "json" in ctype:
        return response.json()
    text = response.text.strip()
    return {"ok": True, "text": text} if text else {"ok": True}


def _drop_none(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if v is not None}


def _items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        embedded = data.get("_embedded")
        if isinstance(embedded, dict) and isinstance(embedded.get("items"), list):
            return embedded["items"]
        if isinstance(data.get("items"), list):
            return data["items"]
    if isinstance(data, list):
        return data
    return []


def pagination(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    return {k: data.get(k) for k in ("page", "pages", "limit", "total") if k in data}


def health_check() -> dict[str, Any]:
    """Verify authentication and basic API connectivity with a tiny read-only request."""
    data = list_entries(page=1, per_page=1)
    return {"ok": True, "entries_seen": len(data.get("items", [])), "pagination": data.get("pagination", {})}


def list_entries(
    *,
    page: int = 1,
    per_page: int = 30,
    sort: str = "created",
    order: str = "desc",
    archive: int | None = None,
    starred: int | None = None,
    unread: int | None = None,
    domain_name: str | None = None,
    since: int | None = None,
    tags: str | None = None,
) -> dict[str, Any]:
    params = {
        "page": page,
        "perPage": per_page,
        "sort": sort,
        "order": order,
        "archive": archive,
        "starred": starred,
        "unread": unread,
        "domain_name": domain_name,
        "since": since,
        "tags": tags,
    }
    data = _request("GET", _api_path("/entries"), params=params)
    return {"items": _items(data), "pagination": pagination(data)}


def get_entry(entry_id: int) -> dict[str, Any]:
    data = _request("GET", _api_path(f"/entries/{entry_id}"))
    if not isinstance(data, dict):
        raise WallabagError(f"Expected entry object for {entry_id}, got {type(data).__name__}")
    return data


def create_entry(url: str, **kwargs: Any) -> dict[str, Any]:
    data = _request("POST", _api_path("/entries"), json_body=_drop_none({"url": url, **kwargs}))
    if not isinstance(data, dict):
        raise WallabagError(f"Expected entry object after create, got {type(data).__name__}")
    return data


def update_entry(entry_id: int, **kwargs: Any) -> dict[str, Any]:
    data = _request("PATCH", _api_path(f"/entries/{entry_id}"), json_body=_drop_none(kwargs))
    if isinstance(data, dict) and data.get("ok") and len(data) <= 2:
        return get_entry(entry_id)
    if not isinstance(data, dict):
        return get_entry(entry_id)
    return data


def delete_entry(entry_id: int) -> dict[str, Any]:
    data = _request("DELETE", _api_path(f"/entries/{entry_id}"))
    return data if isinstance(data, dict) else {"deleted": True, "id": entry_id}


def reload_entry(entry_id: int) -> dict[str, Any]:
    data = _request("PATCH", _api_path(f"/entries/{entry_id}/reload"))
    return data if isinstance(data, dict) else get_entry(entry_id)


def list_tags() -> list[dict[str, Any]]:
    data = _request("GET", _api_path("/tags"))
    return _items(data) or (data if isinstance(data, list) else [])


def add_tag(entry_id: int, tags: str) -> dict[str, Any]:
    data = _request("POST", _api_path(f"/entries/{entry_id}/tags"), json_body={"tags": tags})
    return data if isinstance(data, dict) else get_entry(entry_id)


def delete_tag(tag_id: int) -> dict[str, Any]:
    data = _request("DELETE", _api_path(f"/tags/{tag_id}"))
    return data if isinstance(data, dict) else {"deleted": True, "id": tag_id}


def list_annotations(entry_id: int) -> list[dict[str, Any]]:
    data = _request("GET", _api_path(f"/entries/{entry_id}/annotations"))
    return _items(data) or (data if isinstance(data, list) else [])


def create_annotation(entry_id: int, text: str, quote: str, ranges: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    data = _request(
        "POST",
        _api_path(f"/entries/{entry_id}/annotations"),
        json_body=_drop_none({"text": text, "quote": quote, "ranges": ranges}),
    )
    if not isinstance(data, dict):
        raise WallabagError(f"Expected annotation object after create, got {type(data).__name__}")
    return data


def delete_annotation(annotation_id: int) -> dict[str, Any]:
    data = _request("DELETE", _api_path(f"/annotations/{annotation_id}"))
    return data if isinstance(data, dict) else {"deleted": True, "id": annotation_id}
