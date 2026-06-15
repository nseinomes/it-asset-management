# Implementation Plan: dashboard-charts-filters

## Overview

This plan implements two complementary improvements to the IT Asset Management application:

1. Fix the dashboard Status Bar Chart to use solid background colors (`#1cc88a`, `#f6c23e`, `#e74a3b`) as required by Requirement 1.3.
2. Complete the assets table filtering mechanism by adding category filtering, a result counter, and a "no results" message, with AND logic across all four filter dimensions.

All changes are confined to `templates/dashboard.html` and `templates/assets.html`. No changes to `app.py` are needed.

---

## Tasks

- [x] 1. Fix dashboard chart background colors
  - [x] 1.1 Update `backgroundColor` array in `dashboard.html` chart script
    - In the Chart.js initialization block inside `templates/dashboard.html`, change `backgroundColor` from `['#d1fae5', '#fef3c7', '#fee2e2']` to `['#1cc88a', '#f6c23e', '#e74a3b']`
    - Keep `borderColor` as-is (already correct)
    - The `borderWidth` and `borderRadius` properties must remain unchanged
    - _Requirements: 1.3_

  - [x] 1.2 Write property test for chart color injection (Property 1)
    - **Property 1: Chart renders injected counts faithfully**
    - Use Hypothesis with `st.integers(min_value=0)` to generate `(active, maintenance, inactive)` triples
    - Render `dashboard.html` via Jinja2 with those values and assert the chart `data:` array contains exactly those three integers in order
    - Also assert `#1cc88a`, `#f6c23e`, `#e74a3b` appear in the rendered script block
    - Place test in `tests/test_dashboard_charts_filters.py`
    - **Validates: Requirements 1.3, 1.4**

  - [x] 1.3 Write example-based test for chart HTML structure
    - `test_dashboard_template_has_canvas`: assert rendered HTML contains `<canvas id="statusChart">`
    - `test_dashboard_chart_colors`: assert rendered HTML contains `#1cc88a`, `#f6c23e`, `#e74a3b` in the chart script
    - Place test in `tests/test_dashboard_charts_filters.py`
    - _Requirements: 1.2, 1.3_

- [x] 2. Checkpoint — Verify dashboard chart tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Add `data-category` attribute to asset table rows
  - [x] 3.1 Update each `<tr>` in `assets.html` to include `data-category`
    - In `templates/assets.html`, locate the `{% for asset in assets %}` loop and add `data-category="{{ asset.category_name or '' }}"` to the `<tr>` element alongside the existing `data-status` and `data-brand` attributes
    - When `asset.category_name` is `None` the attribute must render as an empty string, not the literal `"None"`
    - _Requirements: 3.4_

  - [x] 3.2 Write property test for template row data attributes (Property 2)
    - **Property 2: Template row data attributes match asset fields**
    - Use Hypothesis to generate lists of asset-like dicts with `status` ∈ `{'Active', 'Maintenance', 'Inactive'}`, `brand` as random text or `None`, `category_name` as random text or `None`
    - Render `assets.html` via Jinja2 and parse the resulting HTML with `html.parser`
    - For each `<tr>` assert: `data-status == asset.status`, `data-brand == (asset.brand or '')`, `data-category == (asset.category_name or '')`
    - Place test in `tests/test_dashboard_charts_filters.py`
    - **Validates: Requirements 2.4, 3.4, 4.4**

- [x] 4. Add category filter select and UI feedback elements to the filter bar
  - [x] 4.1 Insert `<select id="categoryFilter">` into the `.table-toolbar` in `assets.html`
    - Add `<select id="categoryFilter" onchange="filterTable()"><option value="">All Categories</option></select>` to the toolbar, between the status filter and the brand filter
    - _Requirements: 3.1_

  - [x] 4.2 Insert `<span id="resultCount">` into the `.table-toolbar`
    - Add `<span id="resultCount" style="...">` after the brand filter select; initial text can be empty (it will be populated by `filterTable()` on first interaction)
    - _Requirements: 6.2_

  - [x] 4.3 Insert `<div id="noResults">` below the `<table>` element
    - Add `<div id="noResults" style="display:none; text-align:center; padding:40px 20px; color:#9ca3af;">No assets match the current filters.</div>` immediately after the closing `</table>` tag and before the `{% else %}` branch
    - _Requirements: 6.5_

  - [x] 4.4 Write example-based tests for filter bar HTML structure
    - `test_assets_page_has_category_filter`: assert `<select id="categoryFilter">` exists in rendered HTML
    - `test_assets_page_has_search_input`: assert `<input id="searchInput">` with placeholder exists
    - `test_no_results_message_hidden_by_default`: assert `#noResults` has `display:none` on initial render
    - Place test in `tests/test_dashboard_charts_filters.py`
    - _Requirements: 3.1, 5.1, 6.5_

- [x] 5. Update `filterTable()` with AND logic, result counter, and no-results toggle
  - [x] 5.1 Rewrite `filterTable()` in `assets.html` to include category filter and counters
    - Read `#categoryFilter` value in addition to existing status, brand, and search inputs
    - Apply AND logic: a row is visible only when all four conditions are satisfied simultaneously (`matchSearch AND matchStatus AND matchCategory AND matchBrand`)
    - Defensive handling: treat `row.dataset.status === undefined` as unfiltered (visible) when a status filter is active, and apply the same pattern for brand and category
    - After iterating rows, set `document.getElementById('resultCount').textContent = count + ' asset(s)'`
    - Set `document.getElementById('noResults').style.display = count === 0 ? '' : 'none'`
    - _Requirements: 2.2, 2.3, 3.2, 3.3, 4.2, 4.3, 5.2, 5.3, 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 5.2 Write property test for combined AND filter (Property 3)
    - **Property 3: Combined AND filter shows exactly the matching rows**
    - Use Hypothesis to generate lists of row descriptors `{status, category, brand, text}` and random filter tuples `(status_filter, category_filter, brand_filter, search_text)`
    - Build a minimal DOM (via `html.parser` or a JS test harness) and assert that visible rows == rows satisfying all four conditions simultaneously
    - Place test in `tests/test_dashboard_charts_filters.py`
    - **Validates: Requirements 2.2, 2.3, 3.2, 3.3, 4.2, 4.3, 5.2, 5.3, 6.1, 6.4**

  - [x] 5.3 Write property test for result counter (Property 4)
    - **Property 4: Result counter equals visible row count**
    - Reuse the same generator as Property 3
    - Assert that the numeric value extracted from `#resultCount` equals the count of rows whose `display` is not `'none'`
    - Place test in `tests/test_dashboard_charts_filters.py`
    - **Validates: Requirements 6.2, 6.3**

- [x] 6. Update `DOMContentLoaded` initializer to populate the category dropdown
  - [x] 6.1 Extend the `DOMContentLoaded` handler in `assets.html` to build the category dropdown
    - After the existing brand-population block, add a symmetric block that collects unique non-empty `row.dataset.category` values into a `Set`, sorts them, and appends one `<option>` per category to `#categoryFilter`
    - Refactor the option-creation pattern into a shared helper `makeOption(value)` to avoid duplication
    - _Requirements: 3.1_

  - [x] 6.2 Write property test for dynamic dropdown population (Property 5)
    - **Property 5: Dynamic dropdowns contain exactly the unique non-empty values from table rows**
    - Use Hypothesis to generate lists of rows with random `data-brand` and `data-category` values (including empty strings)
    - Assert `#brandFilter` options (excluding "All Brands") == unique non-empty brands; `#categoryFilter` options (excluding "All Categories") == unique non-empty categories
    - Place test in `tests/test_dashboard_charts_filters.py`
    - **Validates: Requirements 3.1, 4.1**

- [x] 7. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for an MVP delivery.
- The design uses Hypothesis (Python) for property-based tests. Install with `pip install hypothesis pytest` if not already present.
- Tests should be placed in `tests/test_dashboard_charts_filters.py`. Use `pytest` with `--hypothesis-seed=0` for reproducible runs.
- Properties 3 and 4 test pure JavaScript logic; consider using a Python DOM parser (e.g., `html.parser` / `BeautifulSoup`) or a headless JS approach (Playwright/Selenium) depending on your test environment.
- No changes to `app.py` are required — the Flask route already provides `category_name` for each asset via the LEFT JOIN query.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "3.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "3.2", "4.1", "4.2", "4.3"] },
    { "id": 2, "tasks": ["4.4", "5.1"] },
    { "id": 3, "tasks": ["5.2", "5.3", "6.1"] },
    { "id": 4, "tasks": ["6.2"] }
  ]
}
```
