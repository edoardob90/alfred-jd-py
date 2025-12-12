# Claude Code Context

## Project Overview

Alfred workflow for navigating a Johnny Decimal organizational system. Pure Python 3.10+ with no external dependencies.

## Architecture

- **`jd_core.py`** - Core logic: index loading/saving, path resolution, ID calculations
- **`jd_alfred.py`** - Alfred JSON output helpers (`create_item`, `create_output`, etc.)
- **`jd_browse.py`** - Main browse/search script (supports `--level` filter via argparse)
- **`jd_new.py`** - Three-step folder creation flow (category → ID slot → name)
- **`jd_build.py`** - Filesystem scanner, rebuilds index
- **`info.plist`** - Alfred workflow manifest (connections, objects, uidata)

## Key Patterns

### Alfred Script Filters
Scripts output JSON with `items` array. Each item can have:
- `title`, `subtitle`, `arg`, `uid`
- `valid` (boolean)
- `icon` (path or `{"type": "fileicon", "path": "..."}`)
- `variables` (passed to next step)
- `mods` (modifier key overrides)

### State Passing
Multi-step flows use environment variables:
```python
category_code = os.environ.get("jd_category", "")
```
Set via `variables` dict in item output.

### Index Structure
Nested JSON at `~/.config/jd/index.json`:
```json
{
  "areas": {
    "10-19": {
      "name": "10-19 Area Name",
      "categories": {
        "11": {
          "name": "11 Category",
          "ids": {
            "11.01": {"name": "11.01 Folder Name"},
            "11.10": {"name": "11.10 ■ Section", "section": true}
          }
        }
      }
    }
  }
}
```

## Conventions

- Type hints: Use `X | None` (not `Optional[X]`)
- Imports: `from __future__ import annotations` at top
- No external dependencies - stdlib only
- Config via env vars: `JD_ROOT`, `JD_INDEX`

## Testing

```bash
# Browse/search
python3 jd_browse.py "query"
python3 jd_browse.py -l id "query"

# Rebuild index
python3 jd_build.py

# Check argparse
python3 jd_browse.py --help
```

## info.plist Structure

When editing `info.plist`:
1. **objects** array - workflow nodes (Script Filters, actions, etc.)
2. **connections** dict - node-to-node links with modifier keys
3. **uidata** dict - x/y positions for workflow canvas

Each object needs a unique `uid` referenced in connections.
