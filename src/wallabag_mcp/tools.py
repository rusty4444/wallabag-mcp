"""MCP tools for wallabag."""

from __future__ import annotations

import json
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from . import client as api

EntryId = Annotated[int, Field(description="wallabag entry/article id")]


def register_tools(mcp: MCPServer) -> None:
    """Register wallabag MCP tools."""

    @mcp.tool()
    async def wallabag_health_check() -> str:
        """Verify wallabag API connectivity and authentication with a tiny read-only request."""
        try:
            return _json(api.health_check())
        except Exception as exc:
            return f"Error checking wallabag health: {exc}"

    @mcp.tool()
    async def wallabag_list_entries(
        page: Annotated[int, Field(description="Page number to fetch from wallabag, starting at 1")] = 1,
        per_page: Annotated[int, Field(description="Entries per page, usually 1-100")] = 30,
        sort: Annotated[str, Field(description="Sort field supported by wallabag, commonly created, updated, archived, starred, reading_time, domain_name")] = "created",
        order: Annotated[str, Field(description="Sort order: asc or desc")] = "desc",
        archived: Annotated[bool | None, Field(description="Filter archived entries; true archived, false not archived, null no filter")] = None,
        starred: Annotated[bool | None, Field(description="Filter starred entries; true starred, false unstarred, null no filter")] = None,
        unread: Annotated[bool | None, Field(description="Filter unread entries; true unread, false read, null no filter")] = None,
        domain_name: Annotated[str | None, Field(description="Optional domain_name filter, for example example.com")] = None,
        tags: Annotated[str | None, Field(description="Optional comma-separated tag filter")]= None,
    ) -> str:
        """List wallabag entries/articles with filters and pagination."""
        try:
            data = api.list_entries(
                page=max(1, page),
                per_page=max(1, min(per_page, 100)),
                sort=sort,
                order=order,
                archive=_bool_int(archived),
                starred=_bool_int(starred),
                unread=_bool_int(unread),
                domain_name=domain_name,
                tags=tags,
            )
            return _format_entry_list(data["items"], data.get("pagination", {}))
        except Exception as exc:
            return f"Error listing wallabag entries: {exc}"

    @mcp.tool()
    async def wallabag_get_entry(
        entry_id: EntryId,
        include_content: Annotated[bool, Field(description="Include extracted HTML content in the output; false returns metadata only")] = False,
    ) -> str:
        """Get a wallabag entry/article by id."""
        try:
            entry = api.get_entry(entry_id)
            return _format_entry_detail(entry, include_content=include_content)
        except Exception as exc:
            return f"Error getting wallabag entry {entry_id}: {exc}"

    @mcp.tool()
    async def wallabag_add_entry(
        url: Annotated[str, Field(description="URL to save into wallabag")],
        title: Annotated[str | None, Field(description="Optional title override")]= None,
        tags: Annotated[str | None, Field(description="Optional comma-separated tags to assign")]= None,
        archive: Annotated[bool | None, Field(description="Set archived state after creation")]= None,
        starred: Annotated[bool | None, Field(description="Set starred/favourite state after creation")]= None,
    ) -> str:
        """Save a URL as a wallabag entry."""
        try:
            entry = api.create_entry(url, title=title, tags=tags, archive=_bool_int(archive), starred=_bool_int(starred))
            return _format_entry_detail(entry, include_content=False)
        except Exception as exc:
            return f"Error adding wallabag entry: {exc}"

    @mcp.tool()
    async def wallabag_update_entry(
        entry_id: EntryId,
        title: Annotated[str | None, Field(description="Optional new title")]= None,
        url: Annotated[str | None, Field(description="Optional new URL")]= None,
        archived: Annotated[bool | None, Field(description="Set archived/read-later state")]= None,
        starred: Annotated[bool | None, Field(description="Set starred/favourite state")]= None,
        tags: Annotated[str | None, Field(description="Optional comma-separated tag list to set/add depending on wallabag version")]= None,
    ) -> str:
        """Update metadata/state for a wallabag entry."""
        try:
            entry = api.update_entry(entry_id, title=title, url=url, archive=_bool_int(archived), starred=_bool_int(starred), tags=tags)
            return _format_entry_detail(entry, include_content=False)
        except Exception as exc:
            return f"Error updating wallabag entry {entry_id}: {exc}"

    @mcp.tool()
    async def wallabag_archive_entry(entry_id: EntryId) -> str:
        """Mark a wallabag entry as archived/read."""
        try:
            return _format_entry_detail(api.update_entry(entry_id, archive=1), include_content=False)
        except Exception as exc:
            return f"Error archiving wallabag entry {entry_id}: {exc}"

    @mcp.tool()
    async def wallabag_unarchive_entry(entry_id: EntryId) -> str:
        """Mark a wallabag entry as unarchived/unread."""
        try:
            return _format_entry_detail(api.update_entry(entry_id, archive=0), include_content=False)
        except Exception as exc:
            return f"Error unarchiving wallabag entry {entry_id}: {exc}"

    @mcp.tool()
    async def wallabag_star_entry(entry_id: EntryId) -> str:
        """Mark a wallabag entry as starred/favourite."""
        try:
            return _format_entry_detail(api.update_entry(entry_id, starred=1), include_content=False)
        except Exception as exc:
            return f"Error starring wallabag entry {entry_id}: {exc}"

    @mcp.tool()
    async def wallabag_unstar_entry(entry_id: EntryId) -> str:
        """Remove starred/favourite state from a wallabag entry."""
        try:
            return _format_entry_detail(api.update_entry(entry_id, starred=0), include_content=False)
        except Exception as exc:
            return f"Error unstarring wallabag entry {entry_id}: {exc}"

    @mcp.tool()
    async def wallabag_reload_entry(entry_id: EntryId) -> str:
        """Ask wallabag to refetch/reparse the original article URL."""
        try:
            return _format_entry_detail(api.reload_entry(entry_id), include_content=False)
        except Exception as exc:
            return f"Error reloading wallabag entry {entry_id}: {exc}"

    @mcp.tool()
    async def wallabag_delete_entry(entry_id: EntryId) -> str:
        """Delete a wallabag entry."""
        try:
            return _json(api.delete_entry(entry_id))
        except Exception as exc:
            return f"Error deleting wallabag entry {entry_id}: {exc}"

    @mcp.tool()
    async def wallabag_list_tags() -> str:
        """List tags known to the wallabag account."""
        try:
            return _format_tags(api.list_tags())
        except Exception as exc:
            return f"Error listing wallabag tags: {exc}"

    @mcp.tool()
    async def wallabag_add_tags_to_entry(
        entry_id: EntryId,
        tags: Annotated[str, Field(description="Comma-separated tags to add to the entry")],
    ) -> str:
        """Add one or more tags to a wallabag entry."""
        try:
            return _format_entry_detail(api.add_tag(entry_id, tags), include_content=False)
        except Exception as exc:
            return f"Error adding tags to wallabag entry {entry_id}: {exc}"

    @mcp.tool()
    async def wallabag_delete_tag(
        tag_id: Annotated[int, Field(description="wallabag tag id to delete globally")],
    ) -> str:
        """Delete a wallabag tag globally."""
        try:
            return _json(api.delete_tag(tag_id))
        except Exception as exc:
            return f"Error deleting wallabag tag {tag_id}: {exc}"

    @mcp.tool()
    async def wallabag_list_annotations(entry_id: EntryId) -> str:
        """List annotations for a wallabag entry."""
        try:
            return _json(api.list_annotations(entry_id))
        except Exception as exc:
            return f"Error listing annotations for wallabag entry {entry_id}: {exc}"

    @mcp.tool()
    async def wallabag_create_annotation(
        entry_id: EntryId,
        text: Annotated[str, Field(description="Annotation text/comment")],
        quote: Annotated[str, Field(description="Exact quoted article text being annotated")],
        ranges_json: Annotated[str | None, Field(description="Optional JSON array of wallabag annotation range objects, for example [{\"start\":\"/p[1]\",\"startOffset\":0,\"end\":\"/p[1]\",\"endOffset\":12}]")]= None,
    ) -> str:
        """Create an annotation on a wallabag entry."""
        try:
            ranges = json.loads(ranges_json) if ranges_json else None
            if ranges is not None and not isinstance(ranges, list):
                raise ValueError("ranges_json must decode to a JSON array")
            return _json(api.create_annotation(entry_id, text=text, quote=quote, ranges=ranges))
        except Exception as exc:
            return f"Error creating annotation for wallabag entry {entry_id}: {exc}"

    @mcp.tool()
    async def wallabag_delete_annotation(
        annotation_id: Annotated[int, Field(description="wallabag annotation id to delete")],
    ) -> str:
        """Delete a wallabag annotation."""
        try:
            return _json(api.delete_annotation(annotation_id))
        except Exception as exc:
            return f"Error deleting wallabag annotation {annotation_id}: {exc}"


def _bool_int(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, default=str)


def _strip_html(value: str | None, limit: int = 1200) -> str:
    if not value:
        return ""
    text = value.replace("<p>", "\n").replace("</p>", "\n").replace("<br>", "\n").replace("<br />", "\n")
    out = []
    in_tag = False
    for char in text:
        if char == "<":
            in_tag = True
            continue
        if char == ">":
            in_tag = False
            continue
        if not in_tag:
            out.append(char)
    cleaned = "".join(out)
    cleaned = " ".join(cleaned.split())
    return cleaned[:limit] + ("…" if len(cleaned) > limit else "")


def _format_entry_list(entries: list[dict[str, Any]], pagination: dict[str, Any]) -> str:
    if not entries:
        return f"No wallabag entries found. Pagination: {_json(pagination)}"
    lines = [f"wallabag entries ({len(entries)} shown, pagination={pagination}):"]
    for entry in entries:
        tags = ",".join(t.get("label") or t.get("slug") or str(t) for t in entry.get("tags", []) if isinstance(t, dict))
        lines.append(
            f"- #{entry.get('id')} {entry.get('title') or '(untitled)'} | domain={entry.get('domain_name')} "
            f"| archived={entry.get('is_archived')} starred={entry.get('is_starred')} reading_time={entry.get('reading_time')} | tags={tags} | url={entry.get('url')}"
        )
    return "\n".join(lines)


def _format_entry_detail(entry: dict[str, Any], *, include_content: bool) -> str:
    payload = {k: v for k, v in entry.items() if include_content or k != "content"}
    if include_content and entry.get("content"):
        payload["content_text_preview"] = _strip_html(str(entry.get("content")))
    return _json(payload)


def _format_tags(tags: list[dict[str, Any]]) -> str:
    if not tags:
        return "No wallabag tags found."
    lines = [f"wallabag tags ({len(tags)}):"]
    for tag in tags:
        lines.append(f"- #{tag.get('id')} {tag.get('label') or tag.get('slug')} slug={tag.get('slug')}")
    return "\n".join(lines)
