# Design Document — dashboard-charts-filters

## Overview

This feature enhances the IT Asset Management Flask application in two complementary areas:

1. **Status Bar Chart on Dashboard** — formally specify and guarantee the correct rendering of a Chart.js bar chart showing asset distribution by status (Active, Maintenance, Inactive), with data sourced from PostgreSQL via the existing `/dashboard` Flask route.

2. **Dynamic Filtering on the Assets Table** — consolidate and complete the client-side filtering mechanism on `/assets`, adding category filtering, a result counter, and a "no results" message, while keeping all filtering purely client-side (no page reload, no new dependencies).

The implementation touches two files: `app.py` (minor route additions) and `templates/assets.html` (filter bar enhancements). The `templates/dashboard.html` already has the chart canvas and the Chart.js script; only small corrections/confirmations are needed.

No new Python packages or JavaScript libraries are introduced. Chart.js is already loaded via CDN in `dashboard.html`.

---

## Architecture

The feature follows the existing MVC-like structure of the application:

```
┌─────────────┐   HTTP GET /dashboard   ┌──────────────────────┐
│   Browser   │ ─────────────────────► │  Flask: dashboard()   │
│             │ ◄───────────────────── │  4 COUNT(*) queries   │
│  Chart.js   │   rendered HTML with   └──────────┬───────────┘
│  (CDN)      │   Jinja2 variables                │ psycopg2
└─────────────┘                         ┌─────────▼───────────┐
                                        │   PostgreSQL         │
                                        │   assets table       │
                                        └─────────────────────┘

┌─────────────┐   HTTP GET /assets      ┌──────────────────────┐
│   Browser   │ ─────────────────────► │  Flask: assets()      │
│             │ ◄───────────────────── │  JOIN assets+categories│
│  plain JS   │   full asset list      └──────────┬───────────┘
│  filterTable│   with data-* attrs               │ psycopg2
└─────────────┘                         ┌─────────▼───────────┐
                                        │   PostgreSQL         │
                                        │   assets + categories│
                                        └─────────────────────┘
```

Key design decisions:
- **No server-side filtering for the assets table.** All assets are loaded once and filtering is done in the browser. This is appropriate given the expected dataset size (hundreds of assets, not millions) and avoids additional route complexity.
- **No new API endpoint for chart data.** The dashboard route already collects all four count variables needed; Chart.js consumes them as Jinja2-interpolated JS literals. Adding a JSON endpoint would add complexity without benefit.
- **Dynamic dropdown population in JS.** Category and brand dropdowns are built from the rendered `data-category` / `data-brand` attributes in the table rather than from a separate server-side list. This keeps the route simple and ensures the dropdowns only show values that actually appear in the current result set.

---

## Components and Interfaces

### 1. Flask Route — `dashboard()` in `app.py`

**Current state:** The route already runs four `COUNT(*)` queries and passes `active_assets`, `maintenance_assets`, `inactive_assets`, and `total_assets` as template variables. This satisfies Requirement 1.1.

**Changes required:** None to the Python logic. The route is correct as-is.

**Interface (template variables passed to `dashboard.html`):**

| Variable | Type | Description |
|---|---|---|
| `total_assets` | `int` | Total number of assets |
| `active_assets` | `int` | Assets with `status = 'Active'` |
| `maintenance_assets` | `int` | Assets with `status = 'Maintenance'` |
| `inactive_assets` | `int` | Assets with `status = 'Inactive'` |
| `total_interventions` | `int` | Open interventions |
| `completed_interventions` | `int` | Completed interventions |

### 2. Jinja2 Template — `templates/dashboard.html`

**Current state:** The template already has:
- A `<canvas id="statusChart">` element inside a `.card-box`
- A `<script src="https://cdn.jsdelivr.net/npm/chart.js">` CDN tag
- A Chart.js bar chart initialization that uses `{{ active_assets }}`, `{{ maintenance_assets }}`, `{{ inactive_assets }}`
- Colors: `backgroundColor: ['#d1fae5', '#fef3c7', '#fee2e2']` (light fills) and `borderColor: ['#1cc88a', '#f6c23e', '#e74a3b']` (solid borders)

**Changes required:**

The requirements specify solid background colors (`#1cc88a`, `#f6c23e`, `#e74a3b`) for the bars (Requirement 1.3). The current template uses light pastel fills with solid borders. The `backgroundColor` array must be updated to match the specified colors:

```js
// Before (current)
backgroundColor: ['#d1fae5', '#fef3c7', '#fee2e2'],
borderColor:     ['#1cc88a', '#f6c23e', '#e74a3b'],

// After (conforming to Req 1.3)
backgroundColor: ['#1cc88a', '#f6c23e', '#e74a3b'],
borderColor:     ['#1cc88a', '#f6c23e', '#e74a3b'],
```

### 3. Flask Route — `assets()` in `app.py`

**Current state:** The route executes a LEFT JOIN query returning all asset fields plus `category_name`. It passes `assets` and `categories` to the template. No changes needed to the SQL query.

**Changes required:** None to `app.py`. The query already returns `category_name` for each asset.

### 4. Jinja2 Template — `templates/assets.html`

This is the main implementation surface. The following changes are needed:

#### 4a. Table Row `data-*` attributes

Each `<tr>` must expose three data attributes consumed by `filterTable()`:

```html
<tr data-status="{{ asset.status }}"
    data-brand="{{ asset.brand or '' }}"
    data-category="{{ asset.category_name or '' }}">
```

`data-status` already exists. `data-brand` already exists. **`data-category` is missing** and must be added (Requirement 3.4).

#### 4b. Filter Bar — Category selector

A `<select id="categoryFilter">` must be added to the toolbar alongside the existing status and brand selectors. Its options are populated dynamically by JavaScript from the `data-category` attributes in the table (following the same pattern as the existing brand filter).

#### 4c. Filter Bar — Result counter

A `<span id="resultCount">` element is added to the toolbar to display the count of currently visible rows. It updates on every call to `filterTable()`.

#### 4d. No-results message

A hidden `<div id="noResults">` element (initially `display:none`) is shown when `filterTable()` determines that zero rows are visible.

#### 4e. Updated `filterTable()` function

The function is extended to:
1. Read the value of `#categoryFilter`
2. Apply AND logic across all four criteria (status, category, brand, search text)
3. Count visible rows and update `#resultCount`
4. Toggle `#noResults` visibility based on the count

```
filterTable():
  search   = lowercase(searchInput.value)
  status   = statusFilter.value
  category = categoryFilter.value
  brand    = brandFilter.value
  count    = 0

  for each row in tbody:
    matchSearch   = row.textContent.toLowerCase().includes(search)
    matchStatus   = status === '' OR row.dataset.status === status
    matchCategory = category === '' OR row.dataset.category === category
    matchBrand    = brand === '' OR row.dataset.brand === brand
    visible       = matchSearch AND matchStatus AND matchCategory AND matchBrand
    row.style.display = visible ? '' : 'none'
    if visible: count++

  resultCount.textContent = count + ' asset(s)'
  noResults.style.display = (count === 0) ? '' : 'none'
```

#### 4f. Updated `DOMContentLoaded` initializer

The existing initializer populates the brand dropdown. It must also populate the category dropdown using the same approach:

```js
// Existing — brands
const brands = new Set()
rows.forEach(row => { if (row.dataset.brand) brands.add(row.dataset.brand) })
brands.forEach(brand => brandSelect.appendChild(makeOption(brand)))

// New — categories
const categories = new Set()
rows.forEach(row => { if (row.dataset.category) categories.add(row.dataset.category) })
categories.forEach(cat => categorySelect.appendChild(makeOption(cat)))
```

---

## Data Models

No new database tables or schema changes are required.

### Relevant existing tables

**`assets`** (relevant fields):

| Column | Type | Notes |
|---|---|---|
| `id` | integer PK | |
| `asset_tag` | varchar | Unique identifier shown in table |
| `name` | varchar | Asset name |
| `brand` | varchar | Manufacturer; may be NULL |
| `model` | varchar | Model; may be NULL |
| `category_id` | integer FK → categories | May be NULL |
| `status` | enum/varchar | `'Active'`, `'Maintenance'`, `'Inactive'` |

**`categories`** (relevant fields):

| Column | Type | Notes |
|---|---|---|
| `id` | integer PK | |
| `name` | varchar | Category display name |

### Data flow — Dashboard Chart

```
PostgreSQL                    Flask (app.py)              dashboard.html
──────────                    ──────────────              ──────────────
SELECT COUNT(*) WHERE status='Active'
  → active_assets ─────────────────────────────────────► {{ active_assets }}
SELECT COUNT(*) WHERE status='Maintenance'
  → maintenance_assets ────────────────────────────────► {{ maintenance_assets }}
SELECT COUNT(*) WHERE status='Inactive'
  → inactive_assets ───────────────────────────────────► {{ inactive_assets }}
                                                         ↓
                                                  Chart.js data: [a, m, i]
```

### Data flow — Assets Table Filtering

```
PostgreSQL                    Flask (app.py)              assets.html (JS)
──────────                    ──────────────              ────────────────
SELECT a.*, c.name            assets() route              <tr data-status="..."
FROM assets a                 → assets list  ───────────►     data-brand="..."
LEFT JOIN categories c                                        data-category="...">
                                                         ↓
                                                  filterTable() reads
                                                  data-* attributes
                                                  client-side only
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Chart renders injected counts faithfully

*For any* non-negative integer triple `(active, maintenance, inactive)`, when the dashboard template is rendered with those values, the rendered HTML's chart data array SHALL contain exactly those three values in order `[active, maintenance, inactive]`.

**Validates: Requirements 1.4**

### Property 2: Template row data attributes match asset fields

*For any* list of asset objects (each with `status`, `brand`, and `category_name` fields, where `brand` and `category_name` may be `None`), rendering the assets template SHALL produce one `<tr>` per asset where `data-status` equals `asset.status`, `data-brand` equals `asset.brand` or empty string when `None`, and `data-category` equals `asset.category_name` or empty string when `None`.

**Validates: Requirements 2.4, 3.4, 4.4**

### Property 3: Combined AND filter shows exactly the matching rows

*For any* table of rows (each with `data-status`, `data-category`, `data-brand`, and text content) and any combination of filter values `(status_filter, category_filter, brand_filter, search_text)`, after calling `filterTable()`, the set of visible rows SHALL be exactly those rows satisfying all four conditions simultaneously — `data-status` matches or filter is empty, `data-category` matches or filter is empty, `data-brand` matches or filter is empty, and row text contains the search string case-insensitively.

**Validates: Requirements 2.2, 2.3, 3.2, 3.3, 4.2, 4.3, 5.2, 5.3, 6.1, 6.4**

### Property 4: Result counter equals visible row count

*For any* filter state applied via `filterTable()`, the text content of `#resultCount` SHALL reflect a number equal to the count of `<tr>` elements in the table body whose `display` style is not `'none'`.

**Validates: Requirements 6.2, 6.3**

### Property 5: Dynamic dropdowns contain exactly the unique non-empty values from table rows

*For any* set of table rows with `data-brand` and `data-category` attributes, after the `DOMContentLoaded` initializer runs, the `#brandFilter` select SHALL contain options for exactly the unique non-empty brand values present in those rows, and the `#categoryFilter` select SHALL contain options for exactly the unique non-empty category values present in those rows (each preceded by their respective "All" option).

**Validates: Requirements 3.1, 4.1**

---

## Error Handling

### Dashboard route — zero counts

If no assets exist for a given status, the `COUNT(*)` query returns `0`. Jinja2 renders `0` into the chart data array. Chart.js renders a zero-height bar without error. No special handling is needed (Requirement 1.6).

### Dashboard route — concurrent DB modifications

The route runs four independent `COUNT(*)` queries in a single request. In the unlikely event of concurrent asset mutations between queries, the counts may not sum exactly to `total_assets`. Per Requirement 1.5, this is acceptable: the route displays the values returned by the queries without blocking or retrying. No transaction isolation beyond the default is applied.

### Assets table — missing `data-*` attributes

Per Requirement 2.4: if a row is missing `data-status`, `filterTable()` should treat the row as unfiltered (always visible when a status filter is active). The JavaScript implementation handles this by treating `undefined` dataset values as non-matching only when the filter is non-empty:

```js
const matchStatus = status === '' || row.dataset.status === status;
```

When `row.dataset.status` is `undefined` and `status` is non-empty, `matchStatus` is `false` — the row is hidden. However, Requirement 2.4 states "IF a row does not contain data-status, THEN treat it as unfiltered." To comply strictly, the condition should be:

```js
const matchStatus = status === '' || row.dataset.status === undefined || row.dataset.status === status;
```

The same defensive pattern applies to `data-brand` and `data-category`.

### Assets table — empty result set

When `filterTable()` yields zero visible rows, the `#noResults` element is shown with a message such as "No assets match the current filters." The table structure remains intact; only the visibility of the tbody rows and the no-results div changes (Requirement 6.5).

### Template rendering — `None` values from DB

Assets without a brand or category return `None` from psycopg2. Jinja2's `asset.brand or ''` expression converts `None` to an empty string before writing it into the `data-brand` attribute, preventing `"None"` string literals from appearing in the DOM and being treated as a brand name.

---

## Testing Strategy

This feature is well-suited for property-based testing on the pure JavaScript filter logic and the Python template rendering, and for example-based tests on the Flask route context and static HTML structure.

### Property-Based Testing

**Target library:** [Hypothesis](https://hypothesis.readthedocs.io/en/latest/) for Python (template rendering properties) and [fast-check](https://fast-check.dev/) for JavaScript (client-side filter logic).

Minimum 100 iterations per property test. Each property test references the design property it validates via a comment tag.

**Feature: dashboard-charts-filters, Property 1: Chart renders injected counts faithfully**
- Generator: triples `(active, maintenance, inactive)` of non-negative integers (`st.integers(min_value=0)`)
- Assert: rendered HTML contains `data: [active, maintenance, inactive]` in the chart script block

**Feature: dashboard-charts-filters, Property 2: Template row data attributes match asset fields**
- Generator: lists of asset-like dicts with `status` ∈ {`'Active'`, `'Maintenance'`, `'Inactive'`}, `brand` ∈ random strings | `None`, `category_name` ∈ random strings | `None`
- Assert: for each row, `data-status`, `data-brand`, `data-category` match expected values

**Feature: dashboard-charts-filters, Property 3: Combined AND filter shows exactly the matching rows**
- Generator: lists of row objects `{status, category, brand, text}` plus filter tuples `(status_filter, category_filter, brand_filter, search_text)`
- Assert: visible rows after filtering = rows satisfying all four conditions

**Feature: dashboard-charts-filters, Property 4: Result counter equals visible row count**
- Generator: same as Property 3
- Assert: counter value == count of visible rows after `filterTable()`

**Feature: dashboard-charts-filters, Property 5: Dynamic dropdowns contain exactly the unique non-empty values**
- Generator: lists of rows with random `data-brand` and `data-category` attribute values (including empty strings and `None`)
- Assert: `#brandFilter` options == unique non-empty brands; `#categoryFilter` options == unique non-empty categories

### Unit / Example-Based Tests

These tests cover specific structural requirements that are not meaningfully parameterised:

| Test | What it checks | Requirement |
|---|---|---|
| `test_dashboard_template_has_canvas` | Rendered HTML contains `<canvas id="statusChart">` | 1.2 |
| `test_dashboard_chart_colors` | HTML contains `#1cc88a`, `#f6c23e`, `#e74a3b` in chart script | 1.3 |
| `test_dashboard_route_variables` | `dashboard()` passes all four count keys to render_template | 1.1 |
| `test_assets_page_has_status_filter` | Rendered HTML has `<select id="statusFilter">` with four options | 2.1 |
| `test_assets_page_has_search_input` | Rendered HTML has `<input id="searchInput">` with placeholder | 5.1 |
| `test_assets_page_has_category_filter` | Rendered HTML has `<select id="categoryFilter">` | 3.1 |
| `test_no_results_message_hidden_by_default` | `#noResults` has `display:none` on initial load | 6.5 |

### Integration Tests

These tests require a running database and are not candidates for property-based testing:

| Test | What it checks | Requirement |
|---|---|---|
| `test_dashboard_counts_match_db` | After seeding DB with known counts, route returns matching values | 1.7 |
| `test_dashboard_totals_consistency` | `active + maintenance + inactive == total_assets` on a clean DB | 1.5 |

### Test Configuration

```
# pytest.ini / pyproject.toml (Hypothesis settings)
[tool.pytest.ini_options]
addopts = "--hypothesis-seed=0"

# Hypothesis profile for CI
settings(max_examples=100, deadline=None)
```

For JavaScript property tests (fast-check), run via the project's test runner with `--run` flag to avoid watch mode:
```bash
npx fast-check --run
```
