"""
Unit and property-based tests for pagination math — task 4.3.

Covers the three pure-math functions used by the /assets route:
  - offset  = (page - 1) * per_page
  - total_pages = max(1, ceil(total_count / per_page))
  - page (clamped) = min(max(1, page), total_pages)

Tests are organized by requirement:
  - Requirements 2.2 : offset formula
  - Requirements 2.3 : total_pages boundaries
  - Requirements 2.4 : page clamping (out-of-range page → valid page)
"""

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Pure-math helpers matching the /assets route implementation exactly
# (design.md § Feature 2, Route GET /assets)
# ---------------------------------------------------------------------------

PER_PAGE = 20


def compute_total_pages(total_count: int, per_page: int = PER_PAGE) -> int:
    """total_pages = max(1, ceil(total_count / per_page))"""
    return max(1, math.ceil(total_count / per_page))


def clamp_page(page: int, total_pages: int) -> int:
    """page = min(max(1, page), total_pages)"""
    return min(max(1, page), total_pages)


def compute_offset(page: int, per_page: int = PER_PAGE) -> int:
    """offset = (page - 1) * per_page  — assumes page is already clamped ≥ 1"""
    return (page - 1) * per_page


# ---------------------------------------------------------------------------
# Example-based unit tests
# ---------------------------------------------------------------------------

# ── Requirement 2.2 : offset formula ────────────────────────────────────────

class TestOffsetFormula:
    """Validates: Requirements 2.2"""

    def test_page_1_offset_is_zero(self):
        """Page 1 must always start at offset 0."""
        assert compute_offset(1) == 0

    def test_page_2_offset_is_20(self):
        """Page 2 → skip 20 rows (one full page)."""
        assert compute_offset(2) == 20

    def test_page_3_offset_is_40(self):
        """Page 3 → skip 40 rows (two full pages)."""
        assert compute_offset(3) == 40

    def test_offset_scales_linearly_with_page(self):
        """Offset must equal (page - 1) * PER_PAGE for a range of pages."""
        for page in range(1, 11):
            assert compute_offset(page) == (page - 1) * PER_PAGE


# ── Requirement 2.3 : total_pages boundaries ────────────────────────────────

class TestTotalPagesBoundaries:
    """Validates: Requirements 2.3"""

    def test_zero_rows_gives_one_page(self):
        """0 rows → at least 1 page (empty state still shows page 1)."""
        assert compute_total_pages(0) == 1

    def test_one_row_gives_one_page(self):
        """1 row → 1 page (ceil(1/20) = 1)."""
        assert compute_total_pages(1) == 1

    def test_exactly_per_page_rows_gives_one_page(self):
        """20 rows → exactly 1 page (no overflow)."""
        assert compute_total_pages(20) == 1

    def test_one_over_per_page_rows_gives_two_pages(self):
        """21 rows → 2 pages (one full page + 1 row on a second page)."""
        assert compute_total_pages(21) == 2

    def test_40_rows_gives_two_pages(self):
        """40 rows → exactly 2 pages."""
        assert compute_total_pages(40) == 2

    def test_41_rows_gives_three_pages(self):
        """41 rows → 3 pages."""
        assert compute_total_pages(41) == 3

    def test_19_rows_gives_one_page(self):
        """19 rows → 1 page (does not spill over)."""
        assert compute_total_pages(19) == 1

    def test_large_count(self):
        """1000 rows with per_page=20 → 50 pages."""
        assert compute_total_pages(1000) == 50

    def test_custom_per_page(self):
        """Verify formula works with a per_page other than 20."""
        assert compute_total_pages(total_count=10, per_page=3) == 4  # ceil(10/3)=4


# ── Requirement 2.4 : page clamping ─────────────────────────────────────────

class TestPageClamping:
    """Validates: Requirements 2.4"""

    # ── below-range inputs ──────────────────────────────────────────────────

    def test_page_zero_clamped_to_1(self):
        """page=0 → 1 (floor clamped to 1)."""
        total_pages = compute_total_pages(100)
        assert clamp_page(0, total_pages) == 1

    def test_page_negative_five_clamped_to_1(self):
        """page=-5 → 1."""
        total_pages = compute_total_pages(100)
        assert clamp_page(-5, total_pages) == 1

    def test_page_large_negative_clamped_to_1(self):
        """page=-999 → 1."""
        total_pages = compute_total_pages(100)
        assert clamp_page(-999, total_pages) == 1

    # ── above-range inputs ──────────────────────────────────────────────────

    def test_page_beyond_total_clamped_to_total(self):
        """page > total_pages → total_pages."""
        total_pages = compute_total_pages(100)  # 5 pages
        assert clamp_page(100, total_pages) == total_pages

    def test_page_one_over_total_clamped_to_total(self):
        """page = total_pages + 1 → total_pages."""
        total_pages = compute_total_pages(100)  # 5
        assert clamp_page(total_pages + 1, total_pages) == total_pages

    # ── valid in-range inputs ────────────────────────────────────────────────

    def test_page_1_stays_1(self):
        """page=1 is always valid and must not change."""
        total_pages = compute_total_pages(100)
        assert clamp_page(1, total_pages) == 1

    def test_page_equal_to_total_stays(self):
        """page == total_pages must not be clamped."""
        total_pages = compute_total_pages(100)
        assert clamp_page(total_pages, total_pages) == total_pages

    def test_page_in_middle_stays(self):
        """A valid mid-range page must not change."""
        total_pages = compute_total_pages(200)  # 10 pages
        assert clamp_page(5, total_pages) == 5

    # ── edge case: single page ──────────────────────────────────────────────

    def test_clamping_when_only_one_page(self):
        """When there is only 1 page, any page value must clamp to 1."""
        total_pages = compute_total_pages(0)  # always 1
        assert clamp_page(0, total_pages) == 1
        assert clamp_page(-10, total_pages) == 1
        assert clamp_page(1, total_pages) == 1
        assert clamp_page(50, total_pages) == 1


# ── End-to-end: offset after clamping ───────────────────────────────────────

class TestOffsetAfterClamping:
    """Validates: Requirements 2.2, 2.4 together.

    Ensures that computing offset after clamping page always yields a
    non-negative offset that is consistent with total_count.
    """

    def test_negative_page_yields_zero_offset(self):
        """A negative page clamps to 1 → offset 0."""
        total_pages = compute_total_pages(100)
        page = clamp_page(-3, total_pages)
        assert compute_offset(page) == 0

    def test_over_page_yields_last_page_offset(self):
        """page > total_pages → offset points to the last page."""
        total_count = 95  # 5 pages
        total_pages = compute_total_pages(total_count)  # 5
        page = clamp_page(999, total_pages)
        offset = compute_offset(page)
        assert page == 5
        assert offset == 80  # (5-1)*20

    def test_offset_always_within_total_count(self):
        """After clamping, offset must be < total_count (or 0 when empty)."""
        for total_count in [0, 1, 19, 20, 21, 40, 41, 100, 1000]:
            total_pages = compute_total_pages(total_count)
            for raw_page in [-1, 0, 1, total_pages, total_pages + 1, 9999]:
                page = clamp_page(raw_page, total_pages)
                offset = compute_offset(page)
                # offset must be non-negative
                assert offset >= 0, (
                    f"Negative offset {offset} for total_count={total_count}, "
                    f"raw_page={raw_page}"
                )
                # offset must be < total_count (unless count is 0: page 1 offset 0 is fine)
                if total_count > 0:
                    assert offset < total_count, (
                        f"offset {offset} >= total_count {total_count} for "
                        f"raw_page={raw_page} → clamped page={page}"
                    )


# ---------------------------------------------------------------------------
# Property-based tests (Hypothesis)
# ---------------------------------------------------------------------------

# ── Property 1: offset is always non-negative and a multiple of per_page ────

@settings(max_examples=200, deadline=None)
@given(
    total_count=st.integers(min_value=0, max_value=100_000),
    per_page=st.integers(min_value=1, max_value=200),
    raw_page=st.integers(min_value=-1_000, max_value=10_000),
)
def test_property_offset_nonnegative_and_aligned(total_count, per_page, raw_page):
    """
    **Validates: Requirements 2.2**

    Property 1: For any (total_count ≥ 0, per_page ≥ 1, raw_page),
    the final offset computed after clamping is:
      - always ≥ 0
      - always a multiple of per_page
    """
    total_pages = compute_total_pages(total_count, per_page)
    page = clamp_page(raw_page, total_pages)
    offset = compute_offset(page, per_page)

    assert offset >= 0, f"Negative offset: {offset}"
    assert offset % per_page == 0, (
        f"Offset {offset} is not a multiple of per_page={per_page}"
    )


# ── Property 2: total_pages is always ≥ 1 ───────────────────────────────────

@settings(max_examples=200, deadline=None)
@given(
    total_count=st.integers(min_value=0, max_value=100_000),
    per_page=st.integers(min_value=1, max_value=200),
)
def test_property_total_pages_always_at_least_one(total_count, per_page):
    """
    **Validates: Requirements 2.3**

    Property 2: For any (total_count ≥ 0, per_page ≥ 1),
    total_pages must always be ≥ 1 — even when total_count is 0.
    """
    total_pages = compute_total_pages(total_count, per_page)
    assert total_pages >= 1, (
        f"total_pages={total_pages} < 1 for total_count={total_count}, "
        f"per_page={per_page}"
    )


# ── Property 3: clamped page is always in [1, total_pages] ──────────────────

@settings(max_examples=200, deadline=None)
@given(
    total_count=st.integers(min_value=0, max_value=100_000),
    per_page=st.integers(min_value=1, max_value=200),
    raw_page=st.integers(min_value=-1_000, max_value=10_000),
)
def test_property_clamped_page_in_valid_range(total_count, per_page, raw_page):
    """
    **Validates: Requirements 2.4**

    Property 3: For any (total_count, per_page, raw_page),
    the clamped page must always be in the closed interval [1, total_pages].
    """
    total_pages = compute_total_pages(total_count, per_page)
    page = clamp_page(raw_page, total_pages)

    assert 1 <= page <= total_pages, (
        f"Clamped page {page} is outside [1, {total_pages}] "
        f"(raw_page={raw_page}, total_count={total_count}, per_page={per_page})"
    )


# ── Property 4: ceil relationship — total_pages * per_page ≥ total_count ────

@settings(max_examples=200, deadline=None)
@given(
    total_count=st.integers(min_value=0, max_value=100_000),
    per_page=st.integers(min_value=1, max_value=200),
)
def test_property_total_pages_covers_all_rows(total_count, per_page):
    """
    **Validates: Requirements 2.3**

    Property 4: For any (total_count ≥ 0, per_page ≥ 1),
    total_pages * per_page must be ≥ total_count — i.e. there are enough
    pages to hold every row.
    """
    total_pages = compute_total_pages(total_count, per_page)
    assert total_pages * per_page >= total_count, (
        f"Pages cannot hold all rows: total_pages={total_pages}, "
        f"per_page={per_page}, product={total_pages * per_page} < "
        f"total_count={total_count}"
    )


# ── Property 5: offset is strictly less than total_count (when count > 0) ───

@settings(max_examples=200, deadline=None)
@given(
    total_count=st.integers(min_value=1, max_value=100_000),
    per_page=st.integers(min_value=1, max_value=200),
    raw_page=st.integers(min_value=-1_000, max_value=10_000),
)
def test_property_offset_less_than_total_count(total_count, per_page, raw_page):
    """
    **Validates: Requirements 2.2, 2.4**

    Property 5: For any (total_count ≥ 1, per_page ≥ 1, raw_page),
    the computed offset after clamping must be strictly less than
    total_count — we never skip past all rows.
    """
    total_pages = compute_total_pages(total_count, per_page)
    page = clamp_page(raw_page, total_pages)
    offset = compute_offset(page, per_page)

    assert offset < total_count, (
        f"Offset {offset} >= total_count {total_count} "
        f"(raw_page={raw_page} → clamped={page}, per_page={per_page})"
    )
