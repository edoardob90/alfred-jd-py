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

from jd_alfred import create_error_item, create_item, create_jd_item, create_output
from jd_core import JDIndex, get_config, get_section_name, load_index, resolve_path


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
    index: JDIndex,
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


def show_areas(index: JDIndex, jd_root: Path) -> list[dict]:
    """Show all JD areas."""
    items = []
    areas = index.get("areas", {})

    for code in sorted(areas.keys()):
        area = areas[code]
        path = resolve_path(code, index, jd_root)
        cat_count = len(area.get("categories", {}))

        items.append(
            create_jd_item(
                title=area["name"],
                code=code,
                path=path,
                level="area",
                subtitle=f"{cat_count} categories",
                autocomplete=f"{code} ",
            )
        )

    if not items:
        items.append(create_error_item("No areas found", "Run 'jdb' to rebuild index"))

    return items


def show_categories_in_area(
    area_code: str, index: JDIndex, jd_root: Path
) -> list[dict]:
    """Show categories within a specific area."""
    areas = index.get("areas", {})
    area = areas.get(area_code)

    if not area:
        return [create_error_item(f"Area {area_code} not found")]

    items = []

    # Add "back" item to show all areas
    items.append(
        create_item(
            title=".. Back to all areas",
            subtitle=f"Currently in {area['name']}",
            autocomplete="",
            valid=False,
            icon="icons/area.png",
        )
    )

    categories = area.get("categories", {})
    for cat_code in sorted(categories.keys()):
        cat = categories[cat_code]
        path = resolve_path(cat_code, index, jd_root)
        id_count = len(cat.get("ids", {}))

        items.append(
            create_jd_item(
                title=cat["name"],
                code=cat_code,
                path=path,
                level="category",
                subtitle=f"{id_count} items",
                autocomplete=f"{cat_code} ",
            )
        )

    return items


def show_ids_in_category(
    category_code: str, index: JDIndex, jd_root: Path
) -> list[dict]:
    """Show IDs within a specific category."""
    # Find the category and its parent area
    area_code = _find_area_for_category(category_code, index)
    if not area_code:
        return [create_error_item(f"Category {category_code} not found")]

    areas = index.get("areas", {})
    area = areas[area_code]
    category = area["categories"][category_code]

    items = []

    # Back navigation to parent area
    items.append(
        create_item(
            title=f".. Back to {area['name']}",
            subtitle=f"Currently in {category['name']}",
            autocomplete=f"{area_code} ",
            valid=False,
            icon="icons/category.png",
        )
    )

    ids = category.get("ids", {})
    for id_code in sorted(ids.keys()):
        id_data = ids[id_code]
        is_section = id_data.get("section", False)
        path = resolve_path(id_code, index, jd_root) if not is_section else None

        items.append(
            create_jd_item(
                title=id_data["name"],
                code=id_code,
                path=path,
                level="id",
                is_section=is_section,
            )
        )

    return items


def show_specific_id(id_code: str, index: JDIndex, jd_root: Path) -> list[dict]:
    """Show a specific ID item."""
    # Find the ID and its parent category/area
    cat_code = id_code.split(".")[0]
    area_code = _find_area_for_category(cat_code, index)

    if not area_code:
        return [create_error_item(f"ID {id_code} not found")]

    areas = index.get("areas", {})
    category = areas[area_code]["categories"].get(cat_code, {})
    id_data = category.get("ids", {}).get(id_code)

    if not id_data:
        return [create_error_item(f"ID {id_code} not found")]

    path = resolve_path(id_code, index, jd_root)

    items = [
        create_item(
            title=f".. Back to {category['name']}",
            subtitle=f"Currently viewing {id_data['name']}",
            autocomplete=f"{cat_code} ",
            valid=False,
            icon="icons/id.png",
        ),
        create_jd_item(
            title=id_data["name"],
            code=id_code,
            path=path,
            level="id",
            is_section=id_data.get("section", False),
        ),
    ]

    return items


def search_items(
    query: str,
    index: JDIndex,
    jd_root: Path,
    filter_level: str | None = None,
) -> list[dict]:
    """Search items by text query, optionally filtered by level."""
    query_lower = query.lower()
    query_words = query_lower.split()
    # (code, name, path, score, level, subtitle)
    results: list[tuple[str, str, Path | None, int, str, str]] = []

    areas = index.get("areas", {})

    for area_code, area in areas.items():
        area_name = area["name"]

        # Search areas (if not filtered or filter is "area")
        if not filter_level or filter_level == "area":
            if _matches_query(area_name, query_words):
                path = resolve_path(area_code, index, jd_root)
                score = _score_match(area_name, query_lower)
                results.append((area_code, area_name, path, score, "area", ""))

        # Search categories (if not filtered or filter is "category")
        for cat_code, cat in area.get("categories", {}).items():
            cat_name = cat["name"]

            if not filter_level or filter_level == "category":
                if _matches_query(cat_name, query_words):
                    path = resolve_path(cat_code, index, jd_root)
                    score = _score_match(cat_name, query_lower)
                    results.append(
                        (cat_code, cat_name, path, score, "category", area_name)
                    )

            # Search IDs (if not filtered or filter is "id")
            if not filter_level or filter_level == "id":
                ids = cat.get("ids", {})
                for id_code, id_data in ids.items():
                    # Skip sections from search results
                    if id_data.get("section"):
                        continue

                    if _matches_query(id_data["name"], query_words):
                        path = resolve_path(id_code, index, jd_root)
                        score = _score_match(id_data["name"], query_lower)
                        section = get_section_name(id_code, ids)
                        subtitle = f"{area_name} → {cat_name}"
                        if section:
                            subtitle += f" → {section}"
                        results.append(
                            (id_code, id_data["name"], path, score, "id", subtitle)
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


def _find_area_for_category(cat_code: str, index: JDIndex) -> str | None:
    """Find which area contains a given category code."""
    for area_code, area in index.get("areas", {}).items():
        if cat_code in area.get("categories", {}):
            return area_code
    return None


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
