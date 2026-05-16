---
name: wallabag
description: Use the wallabag MCP server for read-it-later article capture, reading queue management, tags, and annotations.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [wallabag, mcp, read-it-later, bookmarks, articles]
---

# wallabag MCP Skill

Use this skill when the user asks Hermes to connect to or automate wallabag.

## Setup

Configure the MCP server with:

```json
{
  "mcpServers": {
    "wallabag": {
      "command": "wallabag-mcp",
      "env": {
        "WALLABAG_BASE_URL": "https://wallabag.example.com",
        "WALLABAG_CLIENT_ID": "your-client-id",
        "WALLABAG_CLIENT_SECRET": "your-client-secret",
        "WALLABAG_USERNAME": "your-username",
        "WALLABAG_PASSWORD": "your-password"
      }
    }
  }
}
```

Alternatively provide `WALLABAG_ACCESS_TOKEN` to skip password-grant token acquisition.

## Tool selection

- Health/auth: `wallabag_health_check`
- Reading queue: `wallabag_list_entries`, `wallabag_get_entry`
- Capture: `wallabag_add_entry`
- State changes: `wallabag_archive_entry`, `wallabag_unarchive_entry`, `wallabag_star_entry`, `wallabag_unstar_entry`, `wallabag_update_entry`, `wallabag_reload_entry`
- Cleanup: `wallabag_delete_entry`
- Tags: `wallabag_list_tags`, `wallabag_add_tags_to_entry`, `wallabag_delete_tag`
- Annotations: `wallabag_list_annotations`, `wallabag_create_annotation`, `wallabag_delete_annotation`

## Pitfalls

- wallabag's API needs OAuth credentials. Use the wallabag developer client page to create `client_id` and `client_secret`.
- `wallabag_get_entry(include_content=true)` may return large extracted HTML. Prefer the default metadata-only mode unless the user asks to read the article.
- Tag input is comma-separated for wallabag APIs.
