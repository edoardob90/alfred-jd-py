"""
Alfred-specific JSON output formatting.

Generates Script Filter JSON with proper structure for items,
modifier keys, and variables.
"""

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
    """Create a single Alfred result item."""
    item: dict[str, Any] = {
        k: v
        for k, v in {
            "title": title,
            "subtitle": subtitle,
            "arg": arg,
            "uid": uid,
            "autocomplete": autocomplete,
            "type": item_type,
            "match": match,
            "mods": mods,
            "variables": variables,
            "quicklookurl": quicklookurl,
            "text": text,
        }.items()
        if v
    }

    if not valid:
        item["valid"] = False
    if icon:
        item["icon"] = {"type": icon_type, "path": icon} if icon_type else {"path": icon}

    return item


def create_mod(
    subtitle: str | None = None,
    arg: str | None = None,
    valid: bool = True,
    icon: str | None = None,
    variables: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create a modifier key behavior (cmd, alt, ctrl, shift, fn)."""
    mod: dict[str, Any] = {
        k: v
        for k, v in {"subtitle": subtitle, "arg": arg, "variables": variables}.items()
        if v is not None
    }

    if not valid:
        mod["valid"] = False
    if icon:
        mod["icon"] = {"path": icon}

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
