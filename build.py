#!/usr/bin/env python3
"""
Script for `jdb` keyword - Rebuild JD index.

Scans ~/Documents and saves a nested JSON index.
"""

import sys

from core import get_config, save_index, scan_filesystem


def main() -> None:
    jd_root, index_path = get_config()

    index = scan_filesystem(jd_root)

    if len(index) == 0:
        print(f"No JD folders found in {jd_root}")
        sys.exit(1)

    error = save_index(index, index_path)
    if error:
        print(error)
        sys.exit(1)

    areas, categories, ids = index.count()
    print(f"Index rebuilt: {areas} areas, {categories} categories, {ids} IDs")


if __name__ == "__main__":
    main()
