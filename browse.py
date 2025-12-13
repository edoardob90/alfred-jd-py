#!/usr/bin/env python3
"""
Script Filter for `jd` keyword - Browse and search JD system.

Usage:
- `jd` -> Show all areas
- `jd 10-19` -> Show categories in area 10-19
- `jd 11` -> Show IDs in category 11
- `jd 11.` -> Show IDs in category 11
- `jd 11.01` -> Show specific ID
- `jd health` -> Search all items containing "health"

With --level filter (search only, no navigation):
- `jd -l id health` -> Search IDs only
- `jd -l category docs` -> Search categories only
- `jd -l area life` -> Search areas only
"""

import argparse
import re
from pathlib import Path

from alfred import create_error_item, create_item, create_jd_item, create_output
from core import JDex, get_config, load_index, resolve_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Browse and search JD system")
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument(
        "--level",
        "-l",
        choices=["id", "category", "area"],
        help="Filter results by level (search only, no navigation)",
    )
    args = parser.parse_args()

    query = args.query.strip()
    filter_level = args.level  # None, "id", "category", or "area"

    jd_root, index_path = get_config()
    index, error = load_index(index_path)

    if error or index is None:
        items = [
            create_error_item("Index unavailable", error or "Unknown error"),
            create_item(
                title="Rebuild Index",
                subtitle="Use 'jdb' command to scan ~/Documents",
                valid=False,
                icon="icons/build.png",
            ),
        ]
        print(create_output(items))
        return

    items = get_items_for_query(query, index, jd_root, filter_level)
    print(create_output(items))


def get_items_for_query(
    query: str,
    index: JDex,
    jd_root: Path,
    filter_level: str | None = None,
) -> list[dict]:
    """
    Determine items to display based on query pattern.

    If filter_level is set, skip navigation patterns and go directly to filtered search.

    Patterns (without filter):
    1. Empty query: Show all areas
    2. Area pattern (XX-YY): Show categories in that area
    3. Category pattern (XX): Show IDs in that category
    4. Partial ID pattern (XX.): Show IDs in that category
    5. ID pattern (XX.YY): Show that specific ID
    6. Text query: Search all items by name
    """
    # When filter is set, go directly to search (no navigation)
    if filter_level:
        if not query:
            level_names = {"id": "IDs", "category": "categories", "area": "areas"}
            return [
                create_item(
                    title=f"Search {level_names[filter_level]}...",
                    subtitle="Start typing to search",
                    valid=False,
                )
            ]
        return search_items(query, index, jd_root, filter_level)

    # Standard navigation patterns (no filter)
    area_pattern = re.compile(r"^(\d0-\d9)\s*$")  # e.g., "10-19"
    category_pattern = re.compile(r"^(\d{2})\s*$")  # e.g., "11"
    partial_id_pattern = re.compile(r"^(\d{2})\.\s*$")  # e.g., "11."
    id_pattern = re.compile(r"^(\d{2}\.\d{2})\s*$")  # e.g., "11.01"

    if not query:
        return show_areas(index, jd_root)

    if area_match := area_pattern.match(query):
        return show_categories_in_area(area_match.group(1), index, jd_root)

    if cat_match := category_pattern.match(query):
        return show_ids_in_category(cat_match.group(1), index, jd_root)

    if partial_match := partial_id_pattern.match(query):
        return show_ids_in_category(partial_match.group(1), index, jd_root)

    if id_match := id_pattern.match(query):
        return show_specific_id(id_match.group(1), index, jd_root)

    # Text search (all levels)
    return search_items(query, index, jd_root)


def show_areas(index: JDex, jd_root: Path) -> list[dict]:
    """Show all JD areas."""
    items = []

    for area in index:  # Iterates in sorted order
        path = resolve_path(area.code, index, jd_root)
        cat_count = len(area.categories)

        items.append(
            create_jd_item(
                title=area.name,
                code=area.code,
                path=path,
                level="area",
                subtitle=f"{cat_count} categories",
                autocomplete=f"{area.code} ",
            )
        )

    if not items:
        items.append(create_error_item("No areas found", "Run 'jdb' to rebuild index"))

    return items


def show_categories_in_area(area_code: str, index: JDex, jd_root: Path) -> list[dict]:
    """Show categories within a specific area."""
    area = index.get_area(area_code)

    if not area:
        return [create_error_item(f"Area {area_code} not found")]

    items = []

    # Add "back" item to show all areas
    items.append(
        create_item(
            title=".. Back to all areas",
            subtitle=f"Currently in {area.name}",
            autocomplete="",
            valid=False,
            icon="icons/area.png",
        )
    )

    for category in area:  # Iterates in sorted order
        path = resolve_path(category.code, index, jd_root)
        id_count = len(category.ids)

        items.append(
            create_jd_item(
                title=category.name,
                code=category.code,
                path=path,
                level="category",
                subtitle=f"{id_count} items",
                autocomplete=f"{category.code} ",
            )
        )

    return items


def show_ids_in_category(category_code: str, index: JDex, jd_root: Path) -> list[dict]:
    """Show IDs within a specific category."""
    category = index.get_category(category_code)
    if not category or not category.area:
        return [create_error_item(f"Category {category_code} not found")]

    area = category.area
    items = []

    # Back navigation to parent area
    items.append(
        create_item(
            title=f".. Back to {area.name}",
            subtitle=f"Currently in {category.name}",
            autocomplete=f"{area.code} ",
            valid=False,
            icon="icons/category.png",
        )
    )

    for jd_id in category:  # Iterates in sorted order
        path = resolve_path(jd_id.code, index, jd_root) if not jd_id.section else None

        items.append(
            create_jd_item(
                title=jd_id.name,
                code=jd_id.code,
                path=path,
                level="id",
                is_section=jd_id.section,
            )
        )

    return items


def show_specific_id(id_code: str, index: JDex, jd_root: Path) -> list[dict]:
    """Show a specific ID item."""
    jd_id = index.get_id(id_code)

    if not jd_id or not jd_id.category:
        return [create_error_item(f"ID {id_code} not found")]

    category = jd_id.category
    path = resolve_path(id_code, index, jd_root)

    items = [
        create_item(
            title=f".. Back to {category.name}",
            subtitle=f"Currently viewing {jd_id.name}",
            autocomplete=f"{category.code} ",
            valid=False,
            icon="icons/id.png",
        ),
        create_jd_item(
            title=jd_id.name,
            code=jd_id.code,
            path=path,
            level="id",
            is_section=jd_id.section,
        ),
    ]

    return items


def search_items(
    query: str,
    index: JDex,
    jd_root: Path,
    filter_level: str | None = None,
) -> list[dict]:
    """Search items by text query, optionally filtered by level."""
    query_lower = query.lower()
    query_words = query_lower.split()
    # (code, name, path, score, level, subtitle)
    results: list[tuple[str, str, Path | None, int, str, str]] = []

    for area in index:
        # Search areas (if not filtered or filter is "area")
        if not filter_level or filter_level == "area":
            if _matches_query(area.name, query_words):
                path = resolve_path(area.code, index, jd_root)
                score = _score_match(area.name, query_lower)
                results.append((area.code, area.name, path, score, "area", ""))

        # Search categories (if not filtered or filter is "category")
        for category in area:
            if not filter_level or filter_level == "category":
                if _matches_query(category.name, query_words):
                    path = resolve_path(category.code, index, jd_root)
                    score = _score_match(category.name, query_lower)
                    results.append(
                        (
                            category.code,
                            category.name,
                            path,
                            score,
                            "category",
                            area.name,
                        )
                    )

            # Search IDs (if not filtered or filter is "id")
            if not filter_level or filter_level == "id":
                for jd_id in category:
                    # Skip sections from search results
                    if jd_id.section:
                        continue

                    if _matches_query(jd_id.name, query_words):
                        path = resolve_path(jd_id.code, index, jd_root)
                        score = _score_match(jd_id.name, query_lower)
                        subtitle = f"{area.name} → {category.name}"
                        if jd_id.section_name:
                            subtitle += f" → {jd_id.section_name}"
                        results.append(
                            (jd_id.code, jd_id.name, path, score, "id", subtitle)
                        )

    # Sort by score (higher is better), then by code
    results.sort(key=lambda x: (-x[3], x[0]))

    items = []
    for code, name, path, _, level, subtitle in results[:50]:  # Limit to 50 results
        items.append(
            create_jd_item(
                title=name,
                code=code,
                path=path,
                level=level,
                subtitle=subtitle or None,
            )
        )

    if not items:
        level_hint = f" in {filter_level}s" if filter_level else ""
        items.append(
            create_item(
                title=f'No results for "{query}"{level_hint}',
                subtitle="Try a different search term",
                valid=False,
            )
        )

    return items


def _matches_query(name: str, query_words: list[str]) -> bool:
    """Check if all query words appear in the name."""
    name_lower = name.lower()
    return all(word in name_lower for word in query_words)


def _score_match(name: str, query: str) -> int:
    """Score a match - prefer exact matches and shorter names."""
    name_lower = name.lower()
    if query in name_lower:
        return 100 - len(name)  # Exact substring match, prefer shorter
    return -len(name)  # Just word matches, prefer shorter


if __name__ == "__main__":
    main()
