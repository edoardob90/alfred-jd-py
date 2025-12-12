#!/usr/bin/env python3
"""
Script Filter for `jdn` keyword - Create new JD folder.

Three-step flow:
1. `jdn` -> Show all categories (user picks one)
2. `jdn` with jd_category set -> Show available ID slots (user picks one)
3. `jdn <name>` with jd_category and jd_selected_id set -> Show create option

State passing via variables:
- jd_category: Selected category code
- jd_category_path: Full path to category folder
- jd_selected_id: Chosen ID slot
"""

import os
import sys
from pathlib import Path

from jd_alfred import create_item, create_mod, create_output
from jd_core import (
    JDIndex,
    get_available_ids,
    get_config,
    get_next_id,
    get_section_name,
    load_index,
    resolve_path,
)


def main() -> None:
    query = sys.argv[1].strip() if len(sys.argv) > 1 else ""

    # Check state from previous steps
    category_code = os.environ.get("jd_category", "")
    category_path = os.environ.get("jd_category_path", "")
    selected_id = os.environ.get("jd_selected_id", "")

    jd_root, index_path = get_config()
    index, error = load_index(index_path)

    if error or index is None:
        items = [
            create_item(
                title="Index unavailable",
                subtitle=error or "Unknown error",
                valid=False,
            )
        ]
        print(create_output(items))
        return

    if not category_code:
        # Step 1: Show categories to choose from
        items = show_categories(query, index, jd_root)
    elif not selected_id:
        # Step 2: Show available ID slots
        items = show_available_ids(category_code, category_path, query, index)
    else:
        # Step 3: User has selected ID, show name input
        items = show_name_input(category_code, category_path, selected_id, query, index)

    print(create_output(items))


def show_categories(query: str, index: JDIndex, jd_root) -> list[dict]:
    """Step 1: Show all categories for user to select."""
    items = []
    query_lower = query.lower()

    for area_code, area in sorted(index.get("areas", {}).items()):
        for cat_code, cat in sorted(area.get("categories", {}).items()):
            # Filter by query if provided
            if query_lower and query_lower not in cat["name"].lower():
                continue

            path = resolve_path(cat_code, index, jd_root)
            next_id = get_next_id(cat_code, index)

            if not path:
                continue

            items.append(
                create_item(
                    title=cat["name"],
                    subtitle=f"Next available: {next_id}"
                    if next_id
                    else "Category full",
                    arg="",
                    uid=f"new-cat-{cat_code}",
                    icon=str(path),
                    icon_type="fileicon",
                    variables={
                        "jd_category": cat_code,
                        "jd_category_path": str(path),
                    },
                )
            )

    if not items:
        if query:
            items.append(
                create_item(
                    title=f'No categories matching "{query}"',
                    subtitle="Try a different search term",
                    valid=False,
                )
            )
        else:
            items.append(
                create_item(
                    title="No categories found",
                    subtitle="Run 'jdb' to rebuild index",
                    valid=False,
                )
            )

    return items


def show_available_ids(
    category_code: str,
    category_path: str,
    query: str,
    index: JDIndex,
) -> list[dict]:
    """Step 2: Show available ID slots for user to pick."""
    items = []

    # Get category info for hierarchy display
    area_name = ""
    category_name = f"Category {category_code}"
    ids: dict = {}

    for area_code, area in index.get("areas", {}).items():
        cat = area.get("categories", {}).get(category_code)
        if cat:
            area_name = area["name"]
            category_name = cat["name"]
            ids = cat.get("ids", {})
            break

    available = get_available_ids(category_code, index)

    if not available:
        return [
            create_item(
                title=f"Category {category_code} is full",
                subtitle="All 100 IDs are in use",
                valid=False,
            )
        ]

    # Filter by query if provided (user can type a number)
    if query:
        available = [a for a in available if query in a]

    for id_code in available:
        # Build hierarchy subtitle
        section_name = get_section_name(id_code, ids)
        subtitle = f"{area_name} → {category_name}"
        if section_name:
            subtitle += f" → {section_name}"

        items.append(
            create_item(
                title=id_code,
                subtitle=subtitle,
                arg="",
                uid=f"new-id-{id_code}",
                icon="icons/id.png",
                variables={
                    "jd_category": category_code,
                    "jd_category_path": category_path,
                    "jd_selected_id": id_code,
                },
            )
        )

    if not items:
        items.append(
            create_item(
                title=f'No available IDs matching "{query}"',
                subtitle="Try a different number",
                valid=False,
            )
        )

    return items


def show_name_input(
    category_code: str,
    category_path: str,
    selected_id: str,
    name_query: str,
    index: JDIndex,
) -> list[dict]:
    """Step 3: Show name input and create option."""
    items = []

    # Get category info for hierarchy display
    area_name = ""
    category_name = f"Category {category_code}"
    ids: dict = {}

    for area_code, area in index.get("areas", {}).items():
        cat = area.get("categories", {}).get(category_code)
        if cat:
            area_name = area["name"]
            category_name = cat["name"]
            ids = cat.get("ids", {})
            break

    # Build hierarchy subtitle
    section_name = get_section_name(selected_id, ids)
    subtitle = f"{area_name} → {category_name}"
    if section_name:
        subtitle += f" → {section_name}"

    if not name_query:
        # No name entered yet, show prompt
        items.append(
            create_item(
                title=f"Type a name for {selected_id}",
                subtitle=subtitle,
                valid=False,
                icon="icons/id.png",
            )
        )
    else:
        # Name entered, show create option
        folder_name = f"{selected_id} {name_query}"
        full_path = Path(category_path) / folder_name

        items.append(
            create_item(
                title=f"Create: {folder_name}",
                subtitle=subtitle,
                arg=str(full_path),
                uid=f"create-{selected_id}",
                icon="icons/id.png",
                variables={
                    "action": "create",
                    "jd_open_after": "false",
                },
                mods={
                    "alt": create_mod(
                        subtitle="Create and open in Finder",
                        arg=str(full_path),
                        variables={
                            "action": "create",
                            "jd_open_after": "true",
                        },
                    ),
                },
            )
        )

        # Show preview of what will be created
        items.append(
            create_item(
                title=f"Path: {full_path}",
                subtitle="Alt+Enter to create and open",
                valid=False,
                icon=category_path,
                icon_type="fileicon",
            )
        )

    return items


if __name__ == "__main__":
    main()
