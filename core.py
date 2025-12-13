"""
Core module for Johnny Decimal system operations.

Handles index loading/saving, path resolution, and ID calculation.
Uses compositional dataclasses for type-safe, ergonomic access.
"""

import json
import os
import re
from pathlib import Path

from models import JDArea, JDCategory, JDex, JDId

# Regex patterns for JD codes
AREA_PATTERN = re.compile(r"^(\d0-\d9)\s+(.*)$")
CATEGORY_PATTERN = re.compile(r"^(\d{2})\s+(.*)$")
ID_PATTERN = re.compile(r"^(\d{2}\.\d{2})\s+(.*)$")


def load_index(index_path: Path) -> tuple[JDex | None, str | None]:
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
        return JDex.from_json(content), None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in index file: {e}"
    except (OSError, PermissionError) as e:
        return None, f"Cannot read index file: {e}"


def save_index(index: JDex, index_path: Path) -> str | None:
    """
    Save the index to a JSON file.

    Returns error message if failed, None if successful.
    """
    try:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(index.to_json() + "\n", encoding="utf-8")
        return None
    except (OSError, PermissionError) as e:
        return f"Cannot write index file: {e}"


def scan_filesystem(jd_root: Path) -> JDex:
    """
    Scan JD root and build a JDex index.

    Walks the filesystem looking for JD-formatted folders:
    - Areas: XX-YY Name (e.g., "10-19 Life admin")
    - Categories: XX Name (e.g., "11 Finance")
    - IDs: XX.YY Name (e.g., "11.01 Inbox")
    """
    index = JDex()

    if not jd_root.exists():
        return index

    for area_dir in sorted(jd_root.iterdir()):
        if not area_dir.is_dir():
            continue

        match = AREA_PATTERN.match(area_dir.name)
        if not match:
            continue

        area_code = match.group(1)
        area = JDArea(code=area_code, name=area_dir.name)

        for cat_dir in sorted(area_dir.iterdir()):
            if not cat_dir.is_dir():
                continue

            match = CATEGORY_PATTERN.match(cat_dir.name)
            if not match:
                continue

            cat_code = match.group(1)
            category = JDCategory(code=cat_code, name=cat_dir.name)

            for id_dir in sorted(cat_dir.iterdir()):
                if not id_dir.is_dir():
                    continue

                match = ID_PATTERN.match(id_dir.name)
                if not match:
                    continue

                id_code = match.group(1)
                is_section = "■" in id_dir.name
                jd_id = JDId(code=id_code, name=id_dir.name, section=is_section)
                category.add_id(jd_id)

            area.add_category(category)

        index.add_area(area)

    return index


def resolve_path(
    code: str,
    index: JDex,
    jd_root: Path,
) -> Path | None:
    """
    Find the actual filesystem path for a JD code.

    Handles area codes (10-19), category codes (11), and ID codes (11.01).
    """
    item = index.find_by_code(code)
    if item is None:
        return None

    # Area code (e.g., "10-19")
    if "-" in code:
        return _find_folder_by_code(jd_root, code)

    # ID code (e.g., "11.01")
    if "." in code:
        cat_code = code.split(".")[0]
        category = index.get_category(cat_code)
        if not category or not category.area:
            return None
        area_path = _find_folder_by_code(jd_root, category.area.code)
        if not area_path:
            return None
        cat_path = _find_folder_by_code(area_path, cat_code)
        if not cat_path:
            return None
        return _find_folder_by_code(cat_path, code)

    # Category code (e.g., "11")
    category = index.get_category(code)
    if not category or not category.area:
        return None
    area_path = _find_folder_by_code(jd_root, category.area.code)
    if not area_path:
        return None
    return _find_folder_by_code(area_path, code)


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


def get_config() -> tuple[Path, Path]:
    """Get JD root and index paths from environment or defaults."""
    jd_root = Path(os.path.expanduser(os.environ.get("JD_ROOT", "~/Documents")))
    index_path = Path(
        os.path.expanduser(os.environ.get("JD_INDEX", "~/.config/jd/index.json"))
    )
    return jd_root, index_path
