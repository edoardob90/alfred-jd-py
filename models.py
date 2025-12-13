"""
Core module defining all the models to implement a Johnny Decimal system.

Defines dataclasses for:
    - An ID (`JDId`)
    - A Category (`JDCategory`)
    - An Area (`JDArea`)
    - The whole index (`JDex`)
"""

import json
from dataclasses import dataclass, field
from functools import cached_property
from itertools import chain
from typing import Iterator


@dataclass
class JDId:
    """
    Represents a Johnny Decimal ID (e.g., 11.01).

    The atomic unit of the JD system - a single folder.
    """

    code: str  # e.g., "11.01"
    name: str  # e.g., "11.01 Inbox"
    section: bool = False

    # Private parent reference - excluded from equality/repr
    _category: "JDCategory | None" = field(
        default=None, repr=False, compare=False, hash=False
    )

    @property
    def category(self) -> "JDCategory | None":
        """Parent category (read-only)."""
        return self._category

    @property
    def category_code(self) -> str:
        """Extract category code from ID code."""
        return self.code.split(".")[0]

    @property
    def id_number(self) -> int:
        """Extract numeric ID portion (0-99)."""
        return int(self.code.split(".")[1])

    @property
    def decade(self) -> int:
        """Get the decade (0, 10, 20, ..., 90) this ID belongs to."""
        return (self.id_number // 10) * 10

    @property
    def is_section_header(self) -> bool:
        """Alias for section flag."""
        return self.section

    @property
    def section_header(self) -> "JDId | None":
        """Get the section header for this ID, if any."""
        if self._category is None or self.decade == 0:
            return None
        section_code = f"{self.category_code}.{self.decade:02d}"
        section = self._category.get_id(section_code)
        return section if section and section.section else None

    @property
    def section_name(self) -> str | None:
        """Get the section header name, cleaned of markers."""
        header = self.section_header
        if header:
            return header.name.replace("■ ", "")
        return None

    def matches(self, query: str) -> bool:
        """Check if this ID matches a search query."""
        query_lower = query.lower()
        return query_lower in self.name.lower() or query_lower in self.code

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        d: dict = {"name": self.name}
        if self.section:
            d["section"] = True
        return d


@dataclass
class JDCategory:
    """
    Represents a Johnny Decimal Category (e.g., 11 Finance).

    Contains 0-100 IDs organized by decade sections.
    """

    code: str  # e.g., "11"
    name: str  # e.g., "11 Finance"

    _ids: dict[str, JDId] = field(default_factory=dict, repr=False)
    _area: "JDArea | None" = field(default=None, repr=False, compare=False, hash=False)

    @property
    def area(self) -> "JDArea | None":
        """Parent area (read-only)."""
        return self._area

    @property
    def area_code(self) -> str | None:
        """Get parent area code if available."""
        return self._area.code if self._area else None

    @property
    def ids(self) -> dict[str, JDId]:
        """All IDs in this category (read-only view)."""
        return self._ids

    def __iter__(self) -> Iterator[JDId]:
        """Iterate over IDs in sorted order."""
        for code in sorted(self._ids.keys()):
            yield self._ids[code]

    def __len__(self) -> int:
        return len(self._ids)

    def get_id(self, code: str) -> JDId | None:
        """Get ID by code."""
        return self._ids.get(code)

    def add_id(self, jd_id: JDId) -> None:
        """Add an ID to this category, setting parent reference."""
        jd_id._category = self
        self._ids[jd_id.code] = jd_id

    def remove_id(self, code: str) -> JDId | None:
        """Remove and return an ID by code."""
        jd_id = self._ids.pop(code, None)
        if jd_id:
            jd_id._category = None
        return jd_id

    @property
    def regular_ids(self) -> list[JDId]:
        """Non-section IDs only."""
        return [jd_id for jd_id in self if not jd_id.section]

    @property
    def section_ids(self) -> list[JDId]:
        """Section header IDs only."""
        return [jd_id for jd_id in self if jd_id.section]

    @property
    def section_decades(self) -> set[int]:
        """Decades that have section headers (10, 20, etc.)."""
        return {jd_id.decade for jd_id in self.section_ids}

    @property
    def used_slots(self) -> set[int]:
        """All used ID numbers (0-99)."""
        return {jd_id.id_number for jd_id in self}

    def get_next_available_id(self) -> str | None:
        """
        Calculate the next available ID slot.

        Skips section positions and finds first gap.
        Returns None if category is full.
        """
        used = self.used_slots
        for num in range(100):
            if num not in used:
                return f"{self.code}.{num:02d}"
        return None

    def get_available_id_slots(self, limit: int = 3) -> list[str]:
        """
        Get smart list of available ID slots.

        Returns first `limit` available in 00-09 range,
        plus first available after each section decade.
        """
        used = self.used_slots
        sections = self.section_decades
        available: list[str] = []
        count_initial = 0
        decades_covered: set[int] = set()

        for num in range(100):
            if num in used:
                continue

            decade = (num // 10) * 10

            # First N available in 00-09 range
            if decade == 0 and count_initial < limit:
                available.append(f"{self.code}.{num:02d}")
                count_initial += 1
            # First available after each section
            elif decade in sections and decade not in decades_covered:
                available.append(f"{self.code}.{num:02d}")
                decades_covered.add(decade)

        return sorted(available)

    def matches(self, query: str) -> bool:
        """Check if this category matches a search query."""
        query_lower = query.lower()
        return query_lower in self.name.lower() or query_lower in self.code

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "name": self.name,
            "ids": {code: jd_id.to_dict() for code, jd_id in sorted(self._ids.items())},
        }


@dataclass
class JDArea:
    """
    Represents a Johnny Decimal Area (e.g., 10-19 Life Admin).

    Contains up to 10 categories (X0-X9).
    """

    code: str  # e.g., "10-19"
    name: str  # e.g., "10-19 Life Admin"

    _categories: dict[str, JDCategory] = field(default_factory=dict, repr=False)
    _index: "JDex | None" = field(default=None, repr=False, compare=False, hash=False)

    @property
    def index(self) -> "JDex | None":
        """Parent index (read-only)."""
        return self._index

    @property
    def categories(self) -> dict[str, JDCategory]:
        """All categories in this area (read-only view)."""
        return self._categories

    @property
    def decade(self) -> int:
        """The decade this area covers (10, 20, ..., 90)."""
        return int(self.code.split("-")[0])

    def __iter__(self) -> Iterator[JDCategory]:
        """Iterate over categories in sorted order."""
        for code in sorted(self._categories.keys()):
            yield self._categories[code]

    def __len__(self) -> int:
        return len(self._categories)

    def get_category(self, code: str) -> JDCategory | None:
        """Get category by code."""
        return self._categories.get(code)

    def add_category(self, category: JDCategory) -> None:
        """Add a category, setting parent reference."""
        category._area = self
        self._categories[category.code] = category

    def remove_category(self, code: str) -> JDCategory | None:
        """Remove and return a category by code."""
        cat = self._categories.pop(code, None)
        if cat:
            cat._area = None
        return cat

    def contains_category(self, code: str) -> bool:
        """Check if this area contains a category code."""
        return code in self._categories

    @property
    def id_count(self) -> int:
        """Total IDs across all categories."""
        return sum(len(cat) for cat in self)

    def matches(self, query: str) -> bool:
        """Check if this area matches a search query."""
        query_lower = query.lower()
        return query_lower in self.name.lower() or query_lower in self.code

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "name": self.name,
            "categories": {
                code: cat.to_dict() for code, cat in sorted(self._categories.items())
            },
        }


@dataclass
class JDex:
    """
    Root container for the Johnny Decimal index.

    Provides flattened access to all areas, categories, and IDs
    with bidirectional navigation and search capabilities.
    """

    _areas: dict[str, JDArea] = field(default_factory=dict, repr=False)

    # --- Area Access ---

    @property
    def areas(self) -> dict[str, JDArea]:
        """All areas by code."""
        return self._areas

    def __iter__(self) -> Iterator[JDArea]:
        """Iterate over areas in sorted order."""
        for code in sorted(self._areas.keys()):
            yield self._areas[code]

    def __len__(self) -> int:
        return len(self._areas)

    def get_area(self, code: str) -> JDArea | None:
        """Get area by code (e.g., '10-19')."""
        return self._areas.get(code)

    def add_area(self, area: JDArea) -> None:
        """Add an area, setting parent reference."""
        area._index = self
        self._areas[area.code] = area

    # --- Flattened Category Access ---

    @cached_property
    def categories(self) -> dict[str, JDCategory]:
        """
        All categories flattened across areas.

        Cached for performance; call invalidate_cache() after mutations.
        """
        return {cat.code: cat for cat in chain.from_iterable(self)}

    def get_category(self, code: str) -> JDCategory | None:
        """Get category by code from any area."""
        return self.categories.get(code)

    def get_area_for_category(self, cat_code: str) -> JDArea | None:
        """Find which area contains a category code."""
        cat = self.get_category(cat_code)
        return cat.area if cat else None

    # --- Flattened ID Access ---

    @cached_property
    def ids(self) -> dict[str, JDId]:
        """
        All IDs flattened across all categories.

        Cached for performance; call invalidate_cache() after mutations.
        """
        return {jd_id.code: jd_id for jd_id in chain.from_iterable(self.categories.values())}

    def get_id(self, code: str) -> JDId | None:
        """Get ID by code from any category."""
        return self.ids.get(code)

    # --- Search Methods ---

    def search(
        self,
        query: str,
        level: str | None = None,
        include_sections: bool = False,
    ) -> list[JDArea | JDCategory | JDId]:
        """
        Search all items by name.

        Args:
            query: Search string (case-insensitive, all words must match)
            level: Filter to "area", "category", or "id" (None = all)
            include_sections: Whether to include section headers in ID results

        Returns:
            List of matching items, sorted by relevance.
        """
        query_words = query.lower().split()
        results: list[tuple[int, str, JDArea | JDCategory | JDId]] = []

        if level is None or level == "area":
            for area in self:
                if self._matches_all_words(area.name, query_words):
                    score = self._score_match(area.name, query)
                    results.append((score, area.code, area))

        if level is None or level == "category":
            for cat in self.categories.values():
                if self._matches_all_words(cat.name, query_words):
                    score = self._score_match(cat.name, query)
                    results.append((score, cat.code, cat))

        if level is None or level == "id":
            for jd_id in self.ids.values():
                if jd_id.section and not include_sections:
                    continue
                if self._matches_all_words(jd_id.name, query_words):
                    score = self._score_match(jd_id.name, query)
                    results.append((score, jd_id.code, jd_id))

        # Sort by score (desc) then code (asc)
        results.sort(key=lambda x: (-x[0], x[1]))
        return [item for _, _, item in results]

    def find_by_code(self, code: str) -> JDArea | JDCategory | JDId | None:
        """
        Find any item by its code.

        Automatically detects type based on code format:
        - "10-19" -> Area
        - "11" -> Category
        - "11.01" -> ID
        """
        if "-" in code:
            return self.get_area(code)
        elif "." in code:
            return self.get_id(code)
        else:
            return self.get_category(code)

    @staticmethod
    def _matches_all_words(name: str, words: list[str]) -> bool:
        name_lower = name.lower()
        return all(word in name_lower for word in words)

    @staticmethod
    def _score_match(name: str, query: str) -> int:
        """Score match - prefer exact substrings and shorter names."""
        name_lower = name.lower()
        query_lower = query.lower()
        if query_lower in name_lower:
            return 100 - len(name)
        return -len(name)

    # --- Statistics ---

    def count(self) -> tuple[int, int, int]:
        """Return (area_count, category_count, id_count)."""
        area_count = len(self._areas)
        cat_count = len(self.categories)
        id_count = len(self.ids)
        return area_count, cat_count, id_count

    # --- Cache Management ---

    def invalidate_cache(self) -> None:
        """Clear cached properties after mutations."""
        for attr in ("categories", "ids"):
            try:
                delattr(self, attr)
            except AttributeError:
                pass

    # --- Serialization ---

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict (existing format)."""
        return {
            "areas": {
                code: area.to_dict() for code, area in sorted(self._areas.items())
            }
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "JDex":
        """Deserialize from dict (existing format)."""
        index = cls()

        for area_code, area_data in data.get("areas", {}).items():
            area = JDArea(code=area_code, name=area_data["name"])

            for cat_code, cat_data in area_data.get("categories", {}).items():
                category = JDCategory(code=cat_code, name=cat_data["name"])

                for id_code, id_data in cat_data.get("ids", {}).items():
                    jd_id = JDId(
                        code=id_code,
                        name=id_data["name"],
                        section=id_data.get("section", False),
                    )
                    category.add_id(jd_id)

                area.add_category(category)

            index.add_area(area)

        return index

    @classmethod
    def from_json(cls, json_str: str) -> "JDex":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))
