"""
Core module for Johnny Decimal system operations.

Handles index loading/saving, path resolution, and ID calculation.
Uses a nested JSON structure for clarity and simplicity.
"""

import json
import os
import re
from pathlib import Path
from typing import Any

# Type alias for the index structure
JDIndex = dict[str, Any]

# Regex patterns for JD codes
AREA_PATTERN = re.compile(r"^(\d0-\d9)\s+(.*)$")
CATEGORY_PATTERN = re.compile(r"^(\d{2})\s+(.*)$")
ID_PATTERN = re.compile(r"^(\d{2}\.\d{2})\s+(.*)$")


def load_index(index_path: Path) -> tuple[JDIndex | None, str | None]:
    """
    Load the JSON index file.

    Returns (index, error) tuple. If successful, error is None.
    """
    if not index_path.exists():
        return None, f"Index file not found: {index_path}"

    try:
        content = index_path.read_text(encoding="utf-8")
        if not content.strip():
            return None, "Index file is empty. Run 'jdb' to rebuild."
        return json.loads(content), None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in index file: {e}"
    except (OSError, PermissionError) as e:
        return None, f"Cannot read index file: {e}"


def save_index(index: JDIndex, index_path: Path) -> str | None:
    """
    Save the index to a JSON file.

    Returns error message if failed, None if successful.
    """
    try:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return None
    except (OSError, PermissionError) as e:
        return f"Cannot write index file: {e}"


def scan_filesystem(jd_root: Path) -> JDIndex:
    """
    Scan JD root and build a nested index structure.

    Structure:
    {
      "areas": {
        "10-19": {
          "name": "10-19 Life admin",
          "categories": {
            "11": {
              "name": "11 🙋 Me",
              "ids": {
                "11.01": {"name": "11.01 Inbox 📥"},
                "11.10": {"name": "...", "section": true}
              }
            }
          }
        }
      }
    }
    """
    index: JDIndex = {"areas": {}}

    if not jd_root.exists():
        return index

    for area_dir in sorted(jd_root.iterdir()):
        if not area_dir.is_dir():
            continue
        match = AREA_PATTERN.match(area_dir.name)
        if not match:
            continue

        area_code = match.group(1)
        area_data: dict[str, Any] = {"name": area_dir.name, "categories": {}}

        for cat_dir in sorted(area_dir.iterdir()):
            if not cat_dir.is_dir():
                continue
            match = CATEGORY_PATTERN.match(cat_dir.name)
            if not match:
                continue

            cat_code = match.group(1)
            cat_data: dict[str, Any] = {"name": cat_dir.name, "ids": {}}

            for id_dir in sorted(cat_dir.iterdir()):
                if not id_dir.is_dir():
                    continue
                match = ID_PATTERN.match(id_dir.name)
                if not match:
                    continue

                id_code = match.group(1)
                id_data: dict[str, Any] = {"name": id_dir.name}
                if "■" in id_dir.name:
                    id_data["section"] = True

                cat_data["ids"][id_code] = id_data

            area_data["categories"][cat_code] = cat_data

        index["areas"][area_code] = area_data

    return index


def resolve_path(
    code: str,
    index: JDIndex,
    jd_root: Path,
) -> Path | None:
    """
    Find the actual filesystem path for a JD code.

    Handles area codes (10-19), category codes (11), and ID codes (11.01).
    """
    areas = index.get("areas", {})

    # Area code (e.g., "10-19")
    if "-" in code:
        area = areas.get(code)
        if not area:
            return None
        return _find_folder_by_code(jd_root, code)

    # ID code (e.g., "11.01")
    if "." in code:
        cat_code = code.split(".")[0]
        # Find which area contains this category
        for area_code, area_data in areas.items():
            if cat_code in area_data.get("categories", {}):
                area_path = _find_folder_by_code(jd_root, area_code)
                if not area_path:
                    return None
                cat_path = _find_folder_by_code(area_path, cat_code)
                if not cat_path:
                    return None
                return _find_folder_by_code(cat_path, code)
        return None

    # Category code (e.g., "11")
    for area_code, area_data in areas.items():
        if code in area_data.get("categories", {}):
            area_path = _find_folder_by_code(jd_root, area_code)
            if not area_path:
                return None
            return _find_folder_by_code(area_path, code)

    return None


def _find_folder_by_code(parent: Path, code: str) -> Path | None:
    """Find a folder in parent directory that starts with the given code."""
    if not parent.exists():
        return None

    code_escaped = re.escape(code)
    pattern = re.compile(f"^{code_escaped}\\s")

    try:
        for item in parent.iterdir():
            if item.is_dir() and pattern.match(item.name):
                return item
    except (OSError, PermissionError):
        pass

    return None


def get_area_for_category(cat_code: str, index: JDIndex) -> str | None:
    """Find which area contains a given category code."""
    for area_code, area_data in index.get("areas", {}).items():
        if cat_code in area_data.get("categories", {}):
            return area_code
    return None


def get_next_id(cat_code: str, index: JDIndex) -> str | None:
    """
    Calculate the next available ID in a category.

    Skips section positions and finds the first available slot.
    """
    # Find the category
    for area_data in index.get("areas", {}).values():
        categories = area_data.get("categories", {})
        if cat_code not in categories:
            continue

        ids = categories[cat_code].get("ids", {})

        # Collect existing ID numbers and section positions
        existing: set[int] = set()
        sections: set[int] = set()

        for id_code, id_data in ids.items():
            num = int(id_code.split(".")[1])
            if id_data.get("section"):
                sections.add(num)
            else:
                existing.add(num)

        # Find next available
        for num in range(100):
            if num not in existing and num not in sections:
                return f"{cat_code}.{num:02d}"

        return None  # Category full

    return f"{cat_code}.00"  # Category not in index yet


def get_available_ids(cat_code: str, index: JDIndex, limit: int = 3) -> list[str]:
    """
    Get a smart list of available ID slots in a category.

    Returns first `limit` available IDs plus the first available after each section.
    This allows users to choose where to place new items, preserving intentional gaps.
    """
    # Find the category
    for area_data in index.get("areas", {}).values():
        categories = area_data.get("categories", {})
        if cat_code not in categories:
            continue

        ids = categories[cat_code].get("ids", {})

        # Collect existing ID numbers and section positions
        existing: set[int] = set()
        sections: set[int] = set()

        for id_code, id_data in ids.items():
            num = int(id_code.split(".")[1])
            if id_data.get("section"):
                sections.add(num)
            else:
                existing.add(num)

        available: list[str] = []
        count_before_sections = 0

        # Collect available IDs
        for num in range(100):
            if num in existing or num in sections:
                continue

            # Determine which decade this is in
            decade = (num // 10) * 10

            # Always include first `limit` available in the 00-09 range
            if decade == 0 and count_before_sections < limit:
                available.append(f"{cat_code}.{num:02d}")
                count_before_sections += 1
            # Include first available after each section (decade boundary)
            elif decade in sections:
                # Check if we already have one from this decade
                has_from_decade = any(
                    int(a.split(".")[1]) // 10 * 10 == decade for a in available
                )
                if not has_from_decade:
                    available.append(f"{cat_code}.{num:02d}")

        return sorted(available)

    # Category not in index yet - return first few IDs
    return [f"{cat_code}.{num:02d}" for num in range(limit)]


def get_config() -> tuple[Path, Path]:
    """Get JD root and index paths from environment or defaults."""
    jd_root = Path(os.path.expanduser(os.environ.get("JD_ROOT", "~/Documents")))
    index_path = Path(
        os.path.expanduser(os.environ.get("JD_INDEX", "~/.config/jd/index.json"))
    )
    return jd_root, index_path


def get_section_name(id_code: str, ids: dict) -> str | None:
    """Get the section header name for an ID (sections have codes like XX.10, XX.20)."""
    cat_code, id_num = id_code.split(".")
    tens = (int(id_num) // 10) * 10
    if tens == 0:
        return None  # IDs 00-09 have no section
    section_code = f"{cat_code}.{tens:02d}"
    section = ids.get(section_code)
    if section and section.get("section"):
        # Remove the "■" marker from section name for cleaner display
        return section["name"].replace("■ ", "")
    return None


def count_items(index: JDIndex) -> tuple[int, int, int]:
    """Count areas, categories, and IDs in the index."""
    areas = index.get("areas", {})
    area_count = len(areas)
    cat_count = sum(len(a.get("categories", {})) for a in areas.values())
    id_count = sum(
        len(c.get("ids", {}))
        for a in areas.values()
        for c in a.get("categories", {}).values()
    )
    return area_count, cat_count, id_count
