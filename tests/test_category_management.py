"""
Unit and property-based tests for category management validation — task 8.7.

Tests cover pure validation logic (no running DB required):
  - Name trimming (spaces-only → invalid; leading/trailing spaces trimmed)
  - Length boundary  (≤ 100 chars valid, > 100 chars invalid)
  - Duplicate detection (case-insensitive, excluding self for edit)
  - Asset-count guard (0 assets → allow delete, 1+ assets → reject)

Validates: Requirements 4.3, 4.4, 4.5, 4.7, 4.8, 4.9, 4.10
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Pure-logic helpers extracted from app.py category routes
# (mirrors the route logic exactly so tests remain DB-free)
# ---------------------------------------------------------------------------

MAX_NAME_LEN = 100


def validate_category_name(raw_name: str) -> tuple[bool, str]:
    """
    Trim the raw input and apply the two validation rules used by both
    create_category and edit_category.

    Returns (True, trimmed_name) on success, or (False, error_message).
    """
    name = raw_name.strip()

    if not name:
        return False, "Category name cannot be empty."

    if len(name) > MAX_NAME_LEN:
        return False, "Category name must be 100 characters or fewer."

    return True, name


def is_duplicate_create(name: str, existing_names: list[str]) -> bool:
    """
    Return True if *name* (already trimmed) already exists in *existing_names*,
    compared case-insensitively.
    Mirrors: SELECT id FROM categories WHERE LOWER(name) = LOWER(%s)
    """
    lower_name = name.lower()
    return any(n.lower() == lower_name for n in existing_names)


def is_duplicate_edit(name: str, self_id: int,
                      existing: list[tuple[int, str]]) -> bool:
    """
    Return True if *name* (already trimmed) already exists in *existing*,
    compared case-insensitively, but **excluding** the row with *self_id*.
    Mirrors: SELECT id FROM categories WHERE LOWER(name) = LOWER(%s) AND id != %s
    """
    lower_name = name.lower()
    return any(row_name.lower() == lower_name
               for row_id, row_name in existing
               if row_id != self_id)


def can_delete_category(asset_count: int) -> tuple[bool, str]:
    """
    Return (True, '') if the category can be deleted, or
    (False, error_message) if it has associated assets.
    Mirrors the asset-count guard in delete_category.
    """
    if asset_count > 0:
        return False, f"Cannot delete: {asset_count} asset(s) use this category."
    return True, ""


# ---------------------------------------------------------------------------
# Unit tests — name trimming
# Validates: Requirements 4.3 (empty after trim), 4.4 (length), 4.7
# ---------------------------------------------------------------------------

class TestNameTrimming:
    """Validates: Requirements 4.3, 4.7"""

    def test_spaces_only_is_invalid(self):
        """A name made of spaces only strips to '' → validation fails."""
        ok, _ = validate_category_name("   ")
        assert ok is False

    def test_tabs_only_is_invalid(self):
        """Tabs-only input also strips to '' → validation fails."""
        ok, _ = validate_category_name("\t\t")
        assert ok is False

    def test_mixed_whitespace_only_is_invalid(self):
        """Mixed whitespace strips to '' → validation fails."""
        ok, _ = validate_category_name(" \t \n ")
        assert ok is False

    def test_empty_string_is_invalid(self):
        """Completely empty input → validation fails."""
        ok, _ = validate_category_name("")
        assert ok is False

    def test_leading_spaces_are_trimmed(self):
        """Leading spaces are removed; the stored name has no leading space."""
        ok, trimmed = validate_category_name("   Laptop")
        assert ok is True
        assert trimmed == "Laptop"

    def test_trailing_spaces_are_trimmed(self):
        """Trailing spaces are removed; the stored name has no trailing space."""
        ok, trimmed = validate_category_name("Monitor   ")
        assert ok is True
        assert trimmed == "Monitor"

    def test_leading_and_trailing_spaces_are_trimmed(self):
        """Both sides are trimmed, inner content preserved."""
        ok, trimmed = validate_category_name("  Server  ")
        assert ok is True
        assert trimmed == "Server"

    def test_inner_spaces_preserved(self):
        """Spaces inside the name are NOT removed."""
        ok, trimmed = validate_category_name("  Network Switch  ")
        assert ok is True
        assert trimmed == "Network Switch"

    def test_single_non_space_char_is_valid(self):
        """A single non-whitespace character is a valid (minimal) name."""
        ok, trimmed = validate_category_name("A")
        assert ok is True
        assert trimmed == "A"

    def test_single_char_surrounded_by_spaces_is_valid(self):
        """Single char surrounded by spaces trims to that char → valid."""
        ok, trimmed = validate_category_name("  X  ")
        assert ok is True
        assert trimmed == "X"


# ---------------------------------------------------------------------------
# Unit tests — length boundary
# Validates: Requirements 4.4, 4.7
# ---------------------------------------------------------------------------

class TestLengthBoundary:
    """Validates: Requirements 4.4, 4.7"""

    def test_exactly_100_chars_is_valid(self):
        """A name of exactly 100 characters (after trim) is valid."""
        name = "A" * 100
        ok, trimmed = validate_category_name(name)
        assert ok is True
        assert trimmed == name

    def test_101_chars_is_invalid(self):
        """A name of 101 characters (after trim) is rejected."""
        name = "A" * 101
        ok, msg = validate_category_name(name)
        assert ok is False
        assert "100" in msg

    def test_99_chars_is_valid(self):
        """99 characters is well within the limit."""
        name = "B" * 99
        ok, _ = validate_category_name(name)
        assert ok is True

    def test_1_char_is_valid(self):
        """The shortest possible name (1 char after trim) is valid."""
        ok, _ = validate_category_name("Z")
        assert ok is True

    def test_long_name_with_surrounding_spaces_exceeds_100(self):
        """101-char core surrounded by spaces still fails (trim preserves length)."""
        name = " " + "C" * 101 + " "
        ok, _ = validate_category_name(name)
        assert ok is False

    def test_trimmed_to_100_chars_is_valid(self):
        """100-char core surrounded by spaces becomes valid after trim."""
        name = "   " + "D" * 100 + "   "
        ok, trimmed = validate_category_name(name)
        assert ok is True
        assert len(trimmed) == 100

    def test_error_message_mentions_limit(self):
        """Error message for overlong name must reference the 100-char limit."""
        ok, msg = validate_category_name("X" * 101)
        assert ok is False
        assert "100" in msg


# ---------------------------------------------------------------------------
# Unit tests — duplicate detection (create)
# Validates: Requirements 4.5
# ---------------------------------------------------------------------------

class TestDuplicateCreateDetection:
    """Validates: Requirements 4.5"""

    def test_no_existing_names_is_not_duplicate(self):
        """With an empty DB, no name can be a duplicate."""
        assert is_duplicate_create("Laptop", []) is False

    def test_exact_match_is_duplicate(self):
        """An exactly matching name is detected as a duplicate."""
        assert is_duplicate_create("Laptop", ["Desktop", "Laptop", "Server"]) is True

    def test_case_insensitive_upper_is_duplicate(self):
        """'LAPTOP' matches existing 'laptop' → duplicate."""
        assert is_duplicate_create("LAPTOP", ["laptop"]) is True

    def test_case_insensitive_mixed_is_duplicate(self):
        """'LaP tOp' mixed case matches 'lap top' → duplicate."""
        assert is_duplicate_create("LaP tOp", ["lap top"]) is True

    def test_different_name_is_not_duplicate(self):
        """A genuinely different name is not flagged as duplicate."""
        assert is_duplicate_create("Printer", ["Laptop", "Monitor"]) is False

    def test_similar_but_different_name_is_not_duplicate(self):
        """'Laptops' (plural) does not match 'Laptop' (singular)."""
        assert is_duplicate_create("Laptops", ["Laptop"]) is False

    def test_name_with_extra_space_trimmed_before_check(self):
        """
        The route trims *before* the duplicate check, so the caller must
        pass an already-trimmed name. Confirm exact-match logic is correct.
        """
        # Simulate what the route does: trim first, then check
        raw = "  Laptop  "
        trimmed = raw.strip()
        assert is_duplicate_create(trimmed, ["Laptop"]) is True


# ---------------------------------------------------------------------------
# Unit tests — duplicate detection (edit, excluding self)
# Validates: Requirements 4.8
# ---------------------------------------------------------------------------

class TestDuplicateEditDetection:
    """Validates: Requirements 4.8"""

    # existing rows: [(id, name), ...]
    EXISTING = [(1, "Laptop"), (2, "Monitor"), (3, "Server")]

    def test_same_name_same_id_is_not_duplicate(self):
        """Editing a category to keep the same name must not be blocked."""
        assert is_duplicate_edit("Laptop", self_id=1, existing=self.EXISTING) is False

    def test_same_name_case_insensitive_same_id_is_not_duplicate(self):
        """Case-variant of own name must not be flagged as duplicate."""
        assert is_duplicate_edit("LAPTOP", self_id=1, existing=self.EXISTING) is False

    def test_name_used_by_other_row_is_duplicate(self):
        """A name already in use by a different row is a duplicate."""
        assert is_duplicate_edit("Monitor", self_id=1, existing=self.EXISTING) is True

    def test_name_used_by_other_row_case_insensitive_is_duplicate(self):
        """Case-insensitive match against a different row is a duplicate."""
        assert is_duplicate_edit("MONITOR", self_id=1, existing=self.EXISTING) is True

    def test_new_unique_name_is_not_duplicate(self):
        """A name not used by any row (including self) is not a duplicate."""
        assert is_duplicate_edit("Printer", self_id=1, existing=self.EXISTING) is False

    def test_empty_existing_list_is_not_duplicate(self):
        """With only the row being edited (removed from list), nothing matches."""
        assert is_duplicate_edit("Laptop", self_id=1, existing=[(1, "Laptop")]) is False

    def test_duplicate_check_ignores_only_self_id(self):
        """Only the self_id row is excluded; all other rows are checked."""
        existing = [(1, "Laptop"), (2, "laptop")]
        # Both rows have 'laptop', but self_id=1 is excluded — row 2 still matches
        assert is_duplicate_edit("LAPTOP", self_id=1, existing=existing) is True


# ---------------------------------------------------------------------------
# Unit tests — asset-count guard (delete)
# Validates: Requirements 4.9, 4.10
# ---------------------------------------------------------------------------

class TestAssetCountGuard:
    """Validates: Requirements 4.9, 4.10"""

    def test_zero_assets_allows_delete(self):
        """A category with 0 associated assets can be deleted."""
        ok, _ = can_delete_category(0)
        assert ok is True

    def test_one_asset_rejects_delete(self):
        """A category with 1 asset must not be deletable."""
        ok, _ = can_delete_category(1)
        assert ok is False

    def test_many_assets_rejects_delete(self):
        """A category with many assets must not be deletable."""
        ok, _ = can_delete_category(50)
        assert ok is False

    def test_error_message_contains_count(self):
        """The error message must include the exact asset count."""
        _, msg = can_delete_category(7)
        assert "7" in msg

    def test_error_message_mentions_cannot_delete(self):
        """The error message must indicate deletion was blocked."""
        _, msg = can_delete_category(3)
        assert "Cannot delete" in msg or "cannot delete" in msg.lower()

    def test_error_message_singular_asset(self):
        """With exactly 1 asset the message includes '1 asset(s)'."""
        _, msg = can_delete_category(1)
        assert "1" in msg

    def test_no_error_message_on_zero_assets(self):
        """When delete is allowed, the error message should be empty."""
        ok, msg = can_delete_category(0)
        assert ok is True
        assert msg == ""


# ---------------------------------------------------------------------------
# Property-based tests (Hypothesis)
# Validates: Requirements 4.3, 4.4, 4.7
# ---------------------------------------------------------------------------

# ── Property 1: any name of length 1-100 (after trim) passes validation ─────

@settings(max_examples=300, deadline=None)
@given(
    core=st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",),   # exclude surrogates
            blacklist_characters="\x00",    # exclude null bytes
        ),
        min_size=1,
        max_size=100,
    ).filter(lambda s: s.strip() != ""),     # ensure non-empty after trim
    padding=st.text(alphabet=" \t", max_size=10),
)
def test_property_valid_name_1_to_100_chars_passes(core, padding):
    """
    **Validates: Requirements 4.3, 4.4**

    Property 1: For any non-whitespace-only name whose stripped length is
    between 1 and 100 characters (inclusive), validation must pass and the
    returned name must equal the trimmed input.
    """
    raw = padding + core + padding
    trimmed_core = core.strip()
    # Only test when the trimmed core itself is within bounds
    if len(trimmed_core) < 1 or len(trimmed_core) > 100:
        return  # skip out-of-range cores
    ok, result = validate_category_name(raw)
    assert ok is True, (
        f"Expected valid for name {raw!r} (trimmed={trimmed_core!r}, "
        f"len={len(trimmed_core)})"
    )
    assert result == trimmed_core


# ── Property 2: any name longer than 100 chars (after trim) fails ───────────

@settings(max_examples=200, deadline=None)
@given(
    name=st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",),
            blacklist_characters="\x00",
        ),
        min_size=101,
        max_size=300,
    ).filter(lambda s: len(s.strip()) > 100),  # ensure trim doesn't shrink to ≤ 100
)
def test_property_name_over_100_chars_fails(name):
    """
    **Validates: Requirements 4.4**

    Property 2: For any name whose stripped length exceeds 100 characters,
    validation must fail and the error message must mention the limit.
    """
    ok, msg = validate_category_name(name)
    assert ok is False, (
        f"Expected invalid for name of stripped length "
        f"{len(name.strip())} > 100"
    )
    assert "100" in msg


# ── Property 3: whitespace-only names always fail ───────────────────────────

@settings(max_examples=200, deadline=None)
@given(
    name=st.text(alphabet=" \t\n\r", min_size=1, max_size=50),
)
def test_property_whitespace_only_name_always_fails(name):
    """
    **Validates: Requirements 4.3**

    Property 3: Any string composed entirely of whitespace characters must
    fail validation (strips to empty string).
    """
    ok, _ = validate_category_name(name)
    assert ok is False, (
        f"Expected invalid for whitespace-only name {name!r}"
    )


# ── Property 4: delete guard allows iff asset_count == 0 ────────────────────

@settings(max_examples=200, deadline=None)
@given(asset_count=st.integers(min_value=0, max_value=100_000))
def test_property_delete_allowed_iff_zero_assets(asset_count):
    """
    **Validates: Requirements 4.9, 4.10**

    Property 4: can_delete_category(n) must return True iff n == 0,
    and False for all n > 0.
    """
    ok, msg = can_delete_category(asset_count)
    if asset_count == 0:
        assert ok is True, f"Expected delete allowed for asset_count=0"
        assert msg == ""
    else:
        assert ok is False, (
            f"Expected delete rejected for asset_count={asset_count}"
        )
        assert str(asset_count) in msg, (
            f"Error message {msg!r} should contain count {asset_count}"
        )
