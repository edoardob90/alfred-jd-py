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

from alfred import create_item, create_mod, create_output
from core import (
    JDex,
    JDId,
    get_config,
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


def show_categories(query: str, index: JDex, jd_root: Path) -> list[dict]:
    """Step 1: Show all categories for user to select."""
    items = []
    query_lower = query.lower()

    for area in index:
        for category in area:
            # Filter by query if provided
            if query_lower and query_lower not in category.name.lower():
                continue

            path = resolve_path(category.code, index, jd_root)
            next_id = category.get_next_available_id()

            if not path:
                continue

            items.append(
                create_item(
                    title=category.name,
                    subtitle=f"Next available: {next_id}"
                    if next_id
                    else "Category full",
                    arg="",
                    uid=f"new-cat-{category.code}",
                    icon=str(path),
                    icon_type="fileicon",
                    variables={
                        "jd_category": category.code,
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
    index: JDex,
) -> list[dict]:
    """Step 2: Show available ID slots for user to pick."""
    items = []

    category = index.get_category(category_code)
    if not category or not category.area:
        return [
            create_item(
                title=f"Category {category_code} not found",
                subtitle="Run 'jdb' to rebuild index",
                valid=False,
            )
        ]

    area = category.area
    available = category.get_available_id_slots()

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
        # Build hierarchy subtitle - use temporary JDID to compute section
        temp_id = JDId(code=id_code, name="")
        temp_id._category = category
        section_name = temp_id.section_name

        subtitle = f"{area.name} → {category.name}"
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
    index: JDex,
) -> list[dict]:
    """Step 3: Show name input and create option."""
    items = []

    category = index.get_category(category_code)
    if not category or not category.area:
        return [
            create_item(
                title=f"Category {category_code} not found",
                subtitle="Run 'jdb' to rebuild index",
                valid=False,
            )
        ]

    area = category.area

    # Build hierarchy subtitle - use temporary JDID to compute section
    temp_id = JDId(code=selected_id, name="")
    temp_id._category = category
    section_name = temp_id.section_name

    subtitle = f"{area.name} → {category.name}"
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
