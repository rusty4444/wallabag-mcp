"""Unit tests for wallabag API client."""

from __future__ import annotations

import httpx
import pytest
import respx

from wallabag_mcp import client


@pytest.fixture(autouse=True)
def configure_client() -> None:
    client.configure(
        base_url="https://wallabag.example",
        client_id="client-id",
        client_secret="client-secret",
        username="user",
        password="pass",
        timeout=5,
    )


@respx.mock
def test_oauth_token_requested_and_used() -> None:
    token_route = respx.post("https://wallabag.example/oauth/v2/token").mock(
        return_value=httpx.Response(200, json={"access_token": "token-123", "expires_in": 3600})
    )
    entries_route = respx.get("https://wallabag.example/api/entries.json").mock(
        return_value=httpx.Response(200, json={"_embedded": {"items": []}, "page": 1, "pages": 1, "limit": 30, "total": 0})
    )

    data = client.list_entries()

    assert data == {"items": [], "pagination": {"page": 1, "pages": 1, "limit": 30, "total": 0}}
    assert "grant_type=password" in token_route.calls[0].request.content.decode()
    assert entries_route.calls[0].request.headers["Authorization"] == "Bearer token-123"


@respx.mock
def test_access_token_skips_password_grant() -> None:
    client.configure(base_url="https://wallabag.example", access_token="already-have-token")
    entries_route = respx.get("https://wallabag.example/api/entries.json").mock(
        return_value=httpx.Response(200, json={"_embedded": {"items": [{"id": 1}]}})
    )

    data = client.list_entries(per_page=5, archive=0, starred=1)

    assert data["items"] == [{"id": 1}]
    assert entries_route.calls[0].request.headers["Authorization"] == "Bearer already-have-token"
    assert "perPage=5" in str(entries_route.calls[0].request.url)
    assert "archive=0" in str(entries_route.calls[0].request.url)
    assert "starred=1" in str(entries_route.calls[0].request.url)


@respx.mock
def test_create_and_update_entry_payloads() -> None:
    client.configure(base_url="https://wallabag.example", access_token="token")
    create_route = respx.post("https://wallabag.example/api/entries.json").mock(
        return_value=httpx.Response(200, json={"id": 7, "url": "https://example.com", "title": "Example"})
    )
    update_route = respx.patch("https://wallabag.example/api/entries/7.json").mock(
        return_value=httpx.Response(200, json={"id": 7, "is_archived": 1})
    )

    assert client.create_entry("https://example.com", title="Example")["id"] == 7
    assert client.update_entry(7, archive=1)["is_archived"] == 1
    assert create_route.calls[0].request.content == b'{"url":"https://example.com","title":"Example"}'
    assert update_route.calls[0].request.content == b'{"archive":1}'


@respx.mock
def test_update_entry_refetches_empty_response() -> None:
    client.configure(base_url="https://wallabag.example", access_token="token")
    respx.patch("https://wallabag.example/api/entries/7.json").mock(return_value=httpx.Response(204))
    respx.get("https://wallabag.example/api/entries/7.json").mock(
        return_value=httpx.Response(200, json={"id": 7, "title": "Refetched"})
    )

    assert client.update_entry(7, starred=1) == {"id": 7, "title": "Refetched"}


@respx.mock
def test_tags_and_annotations() -> None:
    client.configure(base_url="https://wallabag.example", access_token="token")
    respx.get("https://wallabag.example/api/tags.json").mock(return_value=httpx.Response(200, json=[{"id": 2, "label": "ai"}]))
    add_tag_route = respx.post("https://wallabag.example/api/entries/7/tags.json").mock(
        return_value=httpx.Response(200, json={"id": 7, "tags": [{"label": "ai"}]})
    )
    respx.get("https://wallabag.example/api/entries/7/annotations.json").mock(
        return_value=httpx.Response(200, json=[{"id": 9, "text": "note"}])
    )

    assert client.list_tags() == [{"id": 2, "label": "ai"}]
    assert client.add_tag(7, "ai")["id"] == 7
    assert add_tag_route.calls[0].request.content == b'{"tags":"ai"}'
    assert client.list_annotations(7) == [{"id": 9, "text": "note"}]


@respx.mock
def test_health_check_uses_tiny_read_only_request() -> None:
    client.configure(base_url="https://wallabag.example", access_token="token")
    route = respx.get("https://wallabag.example/api/entries.json").mock(
        return_value=httpx.Response(200, json={"_embedded": {"items": [{"id": 1}]}, "page": 1, "pages": 1, "limit": 1, "total": 5})
    )

    assert client.health_check() == {"ok": True, "entries_seen": 1, "pagination": {"page": 1, "pages": 1, "limit": 1, "total": 5}}
    assert "perPage=1" in str(route.calls[0].request.url)


@respx.mock
def test_http_errors_are_readable() -> None:
    client.configure(base_url="https://wallabag.example", access_token="token")
    respx.get("https://wallabag.example/api/entries/404.json").mock(return_value=httpx.Response(404, text="Not found"))

    with pytest.raises(client.WallabagError, match="HTTP 404"):
        client.get_entry(404)
