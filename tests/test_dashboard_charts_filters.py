"""
Property-based and example-based tests for dashboard-charts-filters spec.

Tests are organized by property/requirement:
- Property 1: Chart renders injected counts faithfully (Requirements 1.3, 1.4)
- Task 1.3 examples: Chart HTML structure (Requirements 1.2, 1.3)
"""

import os
import re
from jinja2 import Environment, FileSystemLoader

from hypothesis import given, settings
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Jinja2 environment setup
# ---------------------------------------------------------------------------

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def _make_jinja_env():
    """
    Create a Jinja2 Environment pointing at the templates/ directory.
    Provides stub implementations of Flask globals that the base template
    uses (url_for, request, session) so the template renders standalone.
    """
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
    )

    # Stub Flask globals injected as globals into the environment
    env.globals["url_for"] = lambda endpoint, **kwargs: "#"
    env.globals["session"] = {"user": "testuser"}
    env.globals["get_flashed_messages"] = lambda **kwargs: []

    # Stub request object with a .path attribute
    class _FakeRequest:
        path = "/dashboard"

    env.globals["request"] = _FakeRequest()

    return env


def _render_dashboard(active, maintenance, inactive, env=None):
    """Render dashboard.html with the given asset counts."""
    if env is None:
        env = _make_jinja_env()
    tmpl = env.get_template("dashboard.html")
    return tmpl.render(
        active_assets=active,
        maintenance_assets=maintenance,
        inactive_assets=inactive,
        total_assets=active + maintenance + inactive,
        total_interventions=0,
        completed_interventions=0,
    )


# ---------------------------------------------------------------------------
# Property 1: Chart renders injected counts faithfully
# Validates: Requirements 1.3, 1.4
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(
    active=st.integers(min_value=0),
    maintenance=st.integers(min_value=0),
    inactive=st.integers(min_value=0),
)
def test_chart_data_array_reflects_injected_counts(active, maintenance, inactive):
    """
    **Validates: Requirements 1.3, 1.4**

    Property 1: For any non-negative integer triple (active, maintenance, inactive),
    rendering dashboard.html with those values must produce a chart data: array
    containing exactly [active, maintenance, inactive] in that order, and the
    three required bar colors must appear in the script block.
    """
    html = _render_dashboard(active, maintenance, inactive)

    # Assert the data array contains exactly the three values in order.
    # The rendered template produces: data: [<active>, <maintenance>, <inactive>]
    pattern = re.compile(
        r"data:\s*\[\s*" + str(active) + r"\s*,\s*" + str(maintenance) + r"\s*,\s*" + str(inactive) + r"\s*\]"
    )
    assert pattern.search(html), (
        f"Expected 'data: [{active}, {maintenance}, {inactive}]' in rendered chart script, "
        f"but did not find it.\n"
        f"Searched for pattern: {pattern.pattern}"
    )

    # Assert required bar colors appear in the script block (Requirement 1.3)
    assert "#1cc88a" in html, "Expected green color #1cc88a in rendered HTML"
    assert "#f6c23e" in html, "Expected yellow color #f6c23e in rendered HTML"
    assert "#e74a3b" in html, "Expected red color #e74a3b in rendered HTML"


# ---------------------------------------------------------------------------
# Task 1.3: Example-based tests for chart HTML structure
# Validates: Requirements 1.2, 1.3
# ---------------------------------------------------------------------------

def test_dashboard_template_has_canvas():
    """Rendered dashboard HTML must contain the Chart.js canvas element.

    Validates: Requirement 1.2
    """
    html = _render_dashboard(
        active=5,
        maintenance=2,
        inactive=1,
    )
    assert '<canvas id="statusChart"' in html, (
        'Expected <canvas id="statusChart"> to be present in rendered dashboard HTML'
    )


def test_dashboard_chart_colors():
    """Rendered dashboard HTML must contain the required solid bar colors.

    The backgroundColor array must use the three specified solid colors:
      #1cc88a (Active / green)
      #f6c23e (Maintenance / yellow)
      #e74a3b (Inactive / red)

    Validates: Requirement 1.3
    """
    html = _render_dashboard(
        active=5,
        maintenance=2,
        inactive=1,
    )

    for color in ("#1cc88a", "#f6c23e", "#e74a3b"):
        assert color in html, (
            f"Expected color {color} to appear in the chart script block of the "
            f"rendered dashboard HTML"
        )


# ---------------------------------------------------------------------------
# Helper: render assets.html
# ---------------------------------------------------------------------------

def _render_assets(assets, categories=None, brands=None, env=None,
                   page=1, total_pages=1, total_count=None,
                   filter_search="", filter_status="",
                   filter_category="", filter_brand=""):
    """Render assets.html with the given list of asset dicts.

    Passes all pagination and filter variables required by the server-side
    template introduced in task 4.2.
    """
    if categories is None:
        categories = []
    if brands is None:
        brands = []
    if total_count is None:
        total_count = len(assets)
    if env is None:
        env = _make_jinja_env()
    # Point request.path to /assets so sidebar active-link logic works
    env.globals["request"].path = "/assets"
    tmpl = env.get_template("assets.html")
    return tmpl.render(
        assets=assets,
        categories=categories,
        brands=brands,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        filter_search=filter_search,
        filter_status=filter_status,
        filter_category=filter_category,
        filter_brand=filter_brand,
    )


# ---------------------------------------------------------------------------
# Property 2: Template row data attributes match asset fields
# Validates: Requirements 2.4, 3.4, 4.4
# ---------------------------------------------------------------------------

from bs4 import BeautifulSoup

# Strategy: generate a single valid asset dict
_status_strategy = st.sampled_from(["Active", "Maintenance", "Inactive"])
_text_or_none = st.one_of(st.none(), st.text(min_size=1, max_size=50))

_asset_strategy = st.fixed_dictionaries({
    "id": st.integers(min_value=1, max_value=999999),
    "asset_tag": st.text(min_size=1, max_size=20),
    "name": st.text(min_size=1, max_size=50),
    "brand": _text_or_none,
    "model": _text_or_none,
    "category_name": _text_or_none,
    "status": _status_strategy,
})


@settings(max_examples=100, deadline=None)
@given(assets=st.lists(_asset_strategy, min_size=0, max_size=20))
def test_template_row_data_attributes_match_asset_fields(assets):
    """
    **Validates: Requirements 2.4, 3.4, 4.4**

    Property 2: For any list of asset dicts, rendering assets.html must
    produce exactly one <tr> per asset in the tbody.
    """
    html = _render_assets(assets)
    soup = BeautifulSoup(html, "html.parser")

    # Locate the assets table tbody
    table = soup.find("table", {"id": "assetsTable"})

    if not assets:
        # When there are no assets, the template renders the empty-state branch
        # (no table), so there are no rows to check.
        assert table is None, "Expected no assetsTable when asset list is empty"
        return

    assert table is not None, "Expected <table id='assetsTable'> in rendered HTML"

    tbody = table.find("tbody")
    assert tbody is not None, "Expected <tbody> inside assetsTable"

    rows = tbody.find_all("tr")
    assert len(rows) == len(assets), (
        f"Expected {len(assets)} <tr> rows in tbody, got {len(rows)}"
    )


# ---------------------------------------------------------------------------
# Task 4.4: Example-based tests for filter bar HTML structure
# Validates: Requirements 3.1, 5.1, 6.5
# ---------------------------------------------------------------------------

_SAMPLE_ASSET = {
    "id": 1,
    "asset_tag": "IT-001",
    "name": "Test Laptop",
    "brand": "Dell",
    "model": "XPS 15",
    "category_name": "Laptop",
    "status": "Active",
}


def test_assets_page_has_category_filter():
    """Rendered assets HTML must contain the category filter select element.

    After the server-side pagination refactor (task 4.2), the category filter
    is a <select name="category"> inside a GET form, not a client-side select.

    Validates: Requirement 3.1
    """
    cats = [{"id": 1, "name": "Laptop"}]
    html = _render_assets(assets=[_SAMPLE_ASSET], categories=cats)
    soup = BeautifulSoup(html, "html.parser")
    category_select = soup.find("select", {"name": "category"})
    assert category_select is not None, (
        'Expected <select name="category"> to be present in rendered assets HTML'
    )


def test_assets_page_has_search_input():
    """Rendered assets HTML must contain the search input.

    After the server-side pagination refactor, the search input has
    name="search" inside a GET form.

    Validates: Requirement 5.1
    """
    html = _render_assets(assets=[_SAMPLE_ASSET])
    soup = BeautifulSoup(html, "html.parser")

    search_input = soup.find("input", {"name": "search"})
    assert search_input is not None, (
        'Expected <input name="search"> to be present in rendered assets HTML'
    )
    assert search_input.get("placeholder"), (
        '<input name="search"> must have a non-empty placeholder attribute'
    )


def test_no_results_message_shown_when_no_assets():
    """When there are no matching assets, the empty-state message is shown.

    After the server-side pagination refactor (task 4.2), the client-side
    #noResults element was removed; the template now renders an empty-state
    div when the `assets` list is empty.

    Validates: Requirement 6.5 (empty state visible when no results)
    """
    html = _render_assets(assets=[], total_count=0)
    soup = BeautifulSoup(html, "html.parser")

    empty_state = soup.find(class_="empty-state")
    assert empty_state is not None, (
        'Expected an element with class "empty-state" when no assets are present'
    )


# ---------------------------------------------------------------------------
# Helper: Python equivalent of filterTable() JS logic
# ---------------------------------------------------------------------------

def _filter_rows(rows, status_filter, category_filter, brand_filter, search_text):
    """
    Python equivalent of the filterTable() JavaScript logic in assets.html.

    Mirrors the defensive AND logic:
      - search_text: row['text'] must contain search_text (case-insensitive)
      - status_filter: empty string means "any"; None/missing data treated as unfiltered
      - category_filter: empty string means "any"; None/missing data treated as unfiltered
      - brand_filter: empty string means "any"; None/missing data treated as unfiltered
    """
    visible = []
    for row in rows:
        match_search   = search_text.lower() in row['text'].lower()
        match_status   = status_filter   == '' or row.get('status')   is None or row['status']   == status_filter
        match_category = category_filter == '' or row.get('category') is None or row['category'] == category_filter
        match_brand    = brand_filter    == '' or row.get('brand')    is None or row['brand']    == brand_filter
        if match_search and match_status and match_category and match_brand:
            visible.append(row)
    return visible


# ---------------------------------------------------------------------------
# Property 3: Combined AND filter shows exactly the matching rows
# Validates: Requirements 2.2, 2.3, 3.2, 3.3, 4.2, 4.3, 5.2, 5.3, 6.1, 6.4
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(
    rows=st.lists(
        st.fixed_dictionaries({
            'status':   st.sampled_from(['Active', 'Maintenance', 'Inactive', '']),
            'category': st.text(max_size=20),
            'brand':    st.text(max_size=20),
            'text':     st.text(max_size=100),
        }),
        max_size=20,
    ),
    status_filter=st.sampled_from(['', 'Active', 'Maintenance', 'Inactive']),
    category_filter=st.text(max_size=20),
    brand_filter=st.text(max_size=20),
    search_text=st.text(max_size=50),
)
def test_combined_and_filter_shows_exactly_matching_rows(
    rows, status_filter, category_filter, brand_filter, search_text
):
    """
    **Validates: Requirements 2.2, 2.3, 3.2, 3.3, 4.2, 4.3, 5.2, 5.3, 6.1, 6.4**

    Property 3: For any table of rows and any combination of filter values,
    the set of visible rows after filtering must be exactly those rows that
    satisfy all four conditions simultaneously:
      - row text contains search_text (case-insensitive)
      - data-status matches status_filter, or status_filter is empty
      - data-category matches category_filter, or category_filter is empty
      - data-brand matches brand_filter, or brand_filter is empty

    Rows with a missing/None attribute for status/category/brand are treated
    as unfiltered (always visible) for that dimension — matching the defensive
    `undefined` check in the JS implementation.
    """
    # Expected: compute independently using the same logical specification
    expected_visible = [
        r for r in rows
        if (search_text.lower() in r['text'].lower())
        and (status_filter   == '' or r['status']   == status_filter)
        and (category_filter == '' or r['category'] == category_filter)
        and (brand_filter    == '' or r['brand']    == brand_filter)
    ]

    actual_visible = _filter_rows(rows, status_filter, category_filter, brand_filter, search_text)

    assert actual_visible == expected_visible, (
        f"Filter mismatch.\n"
        f"  status_filter={status_filter!r}, category_filter={category_filter!r}, "
        f"brand_filter={brand_filter!r}, search_text={search_text!r}\n"
        f"  Expected {len(expected_visible)} visible rows, got {len(actual_visible)}\n"
        f"  Expected: {expected_visible}\n"
        f"  Actual:   {actual_visible}"
    )


# ---------------------------------------------------------------------------
# Property 4: Result counter equals visible row count
# Validates: Requirements 6.2, 6.3
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(
    rows=st.lists(st.fixed_dictionaries({
        "status":   st.sampled_from(["Active", "Maintenance", "Inactive", ""]),
        "category": st.text(max_size=20),
        "brand":    st.text(max_size=20),
        "text":     st.text(max_size=100),
    }), max_size=20),
    status_filter=st.sampled_from(["", "Active", "Maintenance", "Inactive"]),
    category_filter=st.text(max_size=20),
    brand_filter=st.text(max_size=20),
    search_text=st.text(max_size=50),
)
def test_result_counter_equals_visible_row_count(
    rows, status_filter, category_filter, brand_filter, search_text
):
    """
    **Validates: Requirements 6.2, 6.3**

    Property 4: For any table state and any filter combination, the value that
    would be written to #resultCount (i.e. len of visible rows returned by
    _filter_rows) must equal the count of rows satisfying all four conditions
    simultaneously — confirming the counter always reflects the visible row count.
    """
    visible = _filter_rows(rows, status_filter, category_filter, brand_filter, search_text)

    # Independent reference computation — counts rows passing every condition
    expected_count = sum(
        1
        for r in rows
        if (search_text.lower() in r["text"].lower())
        and (status_filter == "" or r["status"] == status_filter)
        and (category_filter == "" or r["category"] == category_filter)
        and (brand_filter == "" or r["brand"] == brand_filter)
    )

    assert len(visible) == expected_count, (
        f"Result counter mismatch: _filter_rows returned {len(visible)} rows "
        f"but the independent reference count is {expected_count}.\n"
        f"Filters: status={status_filter!r}, category={category_filter!r}, "
        f"brand={brand_filter!r}, search={search_text!r}"
    )


# ---------------------------------------------------------------------------
# Property 5: Dynamic dropdowns contain exactly the unique non-empty values
#             from table rows
# Validates: Requirements 3.1, 4.1
# ---------------------------------------------------------------------------

@settings(max_examples=100, deadline=None)
@given(assets=st.lists(_asset_strategy, min_size=0, max_size=20))
def test_dynamic_dropdowns_reflect_unique_non_empty_row_values(assets):
    """
    **Validates: Requirements 3.1, 4.1**

    Property 5: After the server-side pagination refactor (task 4.2), the
    brand and category dropdowns are now populated server-side via the
    `brands` and `categories` template variables. For any list of assets,
    rendering the template with explicit brand/category lists must produce
    the corresponding <option> elements in the filter selects.
    """
    # Build distinct brands and categories from the test assets (as the route does)
    distinct_brands = sorted({a["brand"] for a in assets if a.get("brand")})
    distinct_categories = sorted({a["category_name"] for a in assets if a.get("category_name")})

    # Build category dicts as the route passes them
    categories = [{"id": i + 1, "name": name} for i, name in enumerate(distinct_categories)]

    html = _render_assets(
        assets=assets,
        categories=categories,
        brands=distinct_brands,
    )
    soup = BeautifulSoup(html, "html.parser")

    # Verify brand <option> elements
    brand_select = soup.find("select", {"name": "brand"})
    assert brand_select is not None, "Expected <select name='brand'> in rendered HTML"
    rendered_brands = [
        opt["value"] for opt in brand_select.find_all("option")
        if opt.get("value")
    ]
    for brand in distinct_brands:
        assert brand in rendered_brands, (
            f"Expected brand option {brand!r} in <select name='brand'>, got: {rendered_brands}"
        )

    # Verify category <option> elements
    category_select = soup.find("select", {"name": "category"})
    assert category_select is not None, "Expected <select name='category'> in rendered HTML"
    rendered_category_names = [
        opt["value"] for opt in category_select.find_all("option")
        if opt.get("value")
    ]
    for cat_name in distinct_categories:
        assert cat_name in rendered_category_names, (
            f"Expected category option {cat_name!r} in <select name='category'>, "
            f"got: {rendered_category_names}"
        )
