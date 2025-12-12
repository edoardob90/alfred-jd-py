"""
Alfred-specific JSON output formatting.

Generates Script Filter JSON with proper structure for items,
modifier keys, and variables.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def create_item(
    title: str,
    subtitle: str = "",
    arg: str = "",
    uid: str | None = None,
    icon: str | None = None,
    icon_type: str | None = None,
    autocomplete: str | None = None,
    valid: bool = True,
    item_type: str | None = None,
    match: str | None = None,
    mods: dict[str, dict[str, Any]] | None = None,
    variables: dict[str, str] | None = None,
    quicklookurl: str | None = None,
    text: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Create a single Alfred result item.

    Args:
        title: Main display text
        subtitle: Secondary text
        arg: Argument passed to subsequent actions
        uid: Unique identifier for sorting/caching
        icon: Path to icon file
        icon_type: "fileicon" to use file's icon, "filetype" for UTI
        autocomplete: Text for tab-completion
        valid: Whether item is actionable
        item_type: "file" or "file:skipcheck" for file results
        match: Custom string for Alfred's filtering
        mods: Modifier key behaviors (cmd, alt, ctrl, shift)
        variables: Variables to pass through workflow
        quicklookurl: URL/path for Quick Look preview
        text: Object with "copy" and/or "largetype" keys
    """
    item: dict[str, Any] = {"title": title}

    if subtitle:
        item["subtitle"] = subtitle
    if arg:
        item["arg"] = arg
    if uid:
        item["uid"] = uid
    if not valid:
        item["valid"] = False
    if autocomplete is not None:
        item["autocomplete"] = autocomplete
    if item_type:
        item["type"] = item_type
    if match:
        item["match"] = match
    if mods:
        item["mods"] = mods
    if variables:
        item["variables"] = variables
    if quicklookurl:
        item["quicklookurl"] = quicklookurl
    if text:
        item["text"] = text

    # Handle icon
    if icon:
        if icon_type:
            item["icon"] = {"type": icon_type, "path": icon}
        else:
            item["icon"] = {"path": icon}

    return item


def create_mod(
    subtitle: str | None = None,
    arg: str | None = None,
    valid: bool = True,
    icon: str | None = None,
    variables: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Create a modifier key behavior.

    Used in the 'mods' dict with keys: cmd, alt, ctrl, shift, fn
    """
    mod: dict[str, Any] = {}

    if subtitle is not None:
        mod["subtitle"] = subtitle
    if arg is not None:
        mod["arg"] = arg
    if not valid:
        mod["valid"] = False
    if icon:
        mod["icon"] = {"path": icon}
    if variables:
        mod["variables"] = variables

    return mod


def create_output(
    items: list[dict[str, Any]],
    variables: dict[str, str] | None = None,
    rerun: float | None = None,
) -> str:
    """
    Generate complete Alfred JSON output.

    Args:
        items: List of result items
        variables: Workflow-level variables
        rerun: Seconds before auto-rerunning (0.1-5.0)
    """
    output: dict[str, Any] = {"items": items}

    if variables:
        output["variables"] = variables
    if rerun is not None:
        output["rerun"] = rerun

    return json.dumps(output, ensure_ascii=False)


def create_error_item(title: str, subtitle: str = "") -> dict[str, Any]:
    """Create an error/warning item that's not actionable."""
    return create_item(
        title=title,
        subtitle=subtitle,
        valid=False,
        icon="icons/error.png",
    )


def create_folder_item(
    title: str,
    path: Path,
    subtitle: str | None = None,
    uid: str | None = None,
    icon: str | None = None,
    autocomplete: str | None = None,
) -> dict[str, Any]:
    """
    Create an Alfred item for a folder with standard modifier actions.

    Default: Open in Finder
    Cmd: Browse in Alfred
    Alt: Copy path
    Ctrl: Open in Terminal
    """
    path_str = str(path)

    return create_item(
        title=title,
        subtitle=subtitle or path_str,
        arg=path_str,
        uid=uid,
        icon=icon or path_str,
        icon_type="fileicon" if not icon else None,
        item_type="file",
        autocomplete=autocomplete,
        quicklookurl=path_str,
        text={"copy": path_str, "largetype": title},
        mods={
            "cmd": create_mod(
                subtitle="Browse in Alfred",
                arg=path_str,
                variables={"action": "browse"},
            ),
            "alt": create_mod(
                subtitle="Copy path to clipboard",
                arg=path_str,
                variables={"action": "copy"},
            ),
            "ctrl": create_mod(
                subtitle="Open in Terminal",
                arg=path_str,
                variables={"action": "terminal"},
            ),
        },
    )


def create_jd_item(
    title: str,
    code: str,
    path: Path | None,
    level: str,
    subtitle: str | None = None,
    autocomplete: str | None = None,
    is_section: bool = False,
) -> dict[str, Any]:
    """
    Create an Alfred item for a JD entry.

    Handles sections (non-actionable) and regular folders differently.
    """
    if is_section:
        # Section headers are visual dividers, not actionable
        return create_item(
            title=title,
            subtitle="Section header",
            uid=f"section-{code}",
            valid=False,
            icon="icons/section.png",
        )

    if path and path.exists():
        # Use file's actual icon
        icon = str(path)
        icon_type = "fileicon"
    else:
        # Fallback to level-based icon
        icon = f"icons/{level}.png"
        icon_type = None

    item = create_item(
        title=title,
        subtitle=subtitle or (str(path) if path else f"JD {level}"),
        arg=str(path) if path else "",
        uid=f"{level}-{code}",
        icon=icon,
        icon_type=icon_type,
        item_type="file" if path else None,
        autocomplete=autocomplete,
        match=_create_match_string(title, code),
        quicklookurl=str(path) if path else None,
        text={"copy": str(path), "largetype": title} if path else None,
    )

    # Add modifier actions only for actual folders
    if path:
        item["mods"] = {
            "cmd": create_mod(
                subtitle="Browse in Alfred",
                arg=str(path),
                variables={"action": "browse"},
            ),
            "alt": create_mod(
                subtitle="Copy path to clipboard",
                arg=str(path),
                variables={"action": "copy"},
            ),
            "ctrl": create_mod(
                subtitle="Open in Terminal",
                arg=str(path),
                variables={"action": "terminal"},
            ),
        }

    return item


def _create_match_string(title: str, code: str) -> str:
    """
    Create a match string for Alfred's filtering.

    Includes the code and words from the title for better search.
    """
    # Remove emojis and special characters, keep alphanumeric and spaces
    words = []
    for char in title:
        if char.isalnum() or char.isspace() or char in ".-":
            words.append(char)

    clean_title = "".join(words)
    return f"{code} {clean_title}".lower()
