# Design Document

## IT Asset Management Enhancements

---

## Overview

This design covers nine incremental enhancements to the existing Flask / Jinja2 / MySQL IT Asset Management application. Each enhancement is self-contained but shares the same application shell (`app.py`, `database.py`, `base.html`). The goal is to improve data retention, usability, security, and reporting without restructuring the existing architecture.

The current stack is:

- **Backend:** Python 3, Flask, `mysql-connector-python`
- **Frontend:** Jinja2 server-rendered templates, Bootstrap 5.3, custom CSS
- **Database:** MySQL — tables `users`, `categories`, `assets`, `technicians`, `interventions`
- **Auth:** Flask `session` (server-side, cookie-based)

No new frameworks are introduced. Each enhancement uses patterns already present in the codebase.

---

## Architecture

The application follows a single-file route/controller pattern (`app.py`) with no service layer. Database access is done inline via `mysql-connector-python`. Templates inherit from `base.html`.

```
Browser
  │
  ▼
Flask (app.py)          ← route handlers, session checks, business logic
  │
  ├── database.py       ← get_connection() helper
  │     └── MySQL
  │
  └── templates/        ← Jinja2 HTML, extends base.html
        └── static/     ← images, future JS/CSS assets
```

The enhancements fit into this architecture as follows:

| Enhancement | Touch points |
|---|---|
| 1 – Intervention History Preservation | `interventions` table (new column), `app.py` routes, `interventions.html` |
| 2 – Asset Detail Page | New route + template `asset_detail.html` |
| 3 – Technician Management | New route + template `technicians.html`, `base.html` sidebar |
| 4 – Intervention Status Badges | `base.html` CSS, `interventions.html`, `asset_detail.html` |
| 5 – Custom 404 Page | `app.py` error handler, new template `404.html` |
| 6 – Password Hashing | `app.py` login, new migration script `migrate_passwords.py` |
| 7 – Session Timeout | `app.py` `before_request` hook, `app.config` |
| 8 – Dashboard Bar Chart | `dashboard.html`, `app.py` dashboard route |
| 9 – Asset Table Client-Side Filters | `assets.html` JavaScript |

---

## Components and Interfaces

### 1. Intervention History Preservation

**Database change:** Add a `status` column to `interventions`:

```sql
ALTER TABLE interventions
ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'Pending';
```

**Route changes in `app.py`:**

- `POST /interventions/add` — inserts with `status = 'Pending'` (default handles this automatically, but the INSERT should be explicit).
- `GET /interventions/complete/<id>` — changed from DELETE to `UPDATE interventions SET status='Completed'`; also sets `assets.status = 'Active'`. Does **not** delete the record.
- `GET /interventions/delete/<id>` — kept but requires the request to include a `confirm=yes` query parameter as the secondary confirmation token; without it, redirects back with an error flash message.
- `GET /interventions` — queries split into two result sets: `WHERE status='Pending'` for the active table and `WHERE status='Completed'` for the history table.

**Template `interventions.html`:**

- Active table shows only Pending rows with the ✅ Done and Delete actions.
- History table below (or collapsible) shows Completed rows (read-only).

### 2. Asset Detail Page

**New route:** `GET /assets/<int:id>` in `app.py`.

The route:
1. Checks `session['user']`.
2. Queries `assets JOIN categories` for the asset; returns 404 if not found.
3. Queries `interventions JOIN technicians WHERE asset_id = <id> ORDER BY intervention_date DESC`.
4. Renders `asset_detail.html`.

**New template `templates/asset_detail.html`** extends `base.html`. Displays two sections:

- **Asset info card** — all fields; uses Jinja2 `or '—'` filter for null/empty values.
- **Intervention history table** — all interventions for the asset; empty-state message if none.

**Link from assets list:** In `assets.html`, the asset name `<td>` becomes a link:

```html
<a href="/assets/{{ asset.id }}">{{ asset.name }}</a>
```

### 3. Technician Management

**New route `GET/POST /technicians`** in `app.py`:

- `GET` — queries all technicians, renders `technicians.html`.
- `POST` (add) — validates name (strip + length check), inserts, redirects.
- `POST /technicians/edit/<int:id>` — validates, updates name, redirects.
- `GET /technicians/delete/<int:id>` — checks for associated interventions; if any exist, redirects with error flash; otherwise deletes and redirects.

**Validation logic (shared helper):**

```python
def validate_technician_name(name: str) -> str | None:
    """Returns stripped name or None if invalid."""
    stripped = name.strip()
    if not stripped or len(stripped) > 100:
        return None
    return stripped
```

**New template `templates/technicians.html`** extends `base.html`. Contains:

- Add-technician form (inline or modal).
- Table of all technicians with Edit and Delete actions.
- Edit form pre-populated via a secondary route or inline modal with current name.

**Sidebar link:** Add to `base.html` under the "Operations" `<nav-section>`:

```html
<a href="/technicians" class="{% if request.path == '/technicians' %}active{% endif %}">
    <span class="icon">👷</span> Technicians
</a>
```

### 4. Intervention Status Badges

**CSS additions to `base.html` `<style>` block** (same block as existing `badge-active`, etc.):

```css
.badge-pending    { background: #fff3cd; color: #856404; }
.badge-completed  { background: #d1fae5; color: #065f46; }
.badge-neutral    { background: #f3f4f6; color: #6b7280; }
```

**Template macro (inline in `interventions.html` and `asset_detail.html`):**

```html
{% if i.status == 'Pending' %}
    <span class="badge-status badge-pending">Pending</span>
{% elif i.status == 'Completed' %}
    <span class="badge-status badge-completed">Completed</span>
{% else %}
    <span class="badge-status badge-neutral">{{ i.status }}</span>
{% endif %}
```

A "Status" column is added to both the active and history intervention tables.

### 5. Custom 404 Error Page

**`app.py` error handler:**

```python
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404
```

**New template `templates/404.html`** extends `base.html`:

- `{% block title %}404 – Page Not Found{% endblock %}`
- Visible heading containing "404" and "not found"
- Link `<a href="/dashboard">Return to Dashboard</a>`

### 6. Password Hashing

**Dependency:** `flask-bcrypt` (wraps `bcrypt`). Add to project requirements:

```
flask-bcrypt==1.0.1
```

**`app.py` changes:**

```python
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt(app)
```

Login route replaces plaintext comparison with:

```python
if user and bcrypt.check_password_hash(user['password'], password):
    session['user'] = user['username']
    return redirect('/dashboard')
```

**Migration script `migrate_passwords.py`** (one-time, idempotent):

```python
# Reads every user row.
# Detects bcrypt hash by checking if value starts with '$2b$' or '$2a$'.
# If plain-text: replaces with bcrypt.generate_password_hash(plain).decode('utf-8').
# Safe to re-run: already-hashed values are skipped.
```

The `password` column is already `VARCHAR(255)` in the schema — no schema change needed.

### 7. Session Timeout

**`app.py` configuration:**

```python
import os
from datetime import timedelta

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.permanent_session_lifetime = timedelta(
    minutes=int(os.environ.get('SESSION_TIMEOUT_MINUTES', 30))
)
```

**`before_request` hook:**

```python
from datetime import datetime, timezone

@app.before_request
def check_session_timeout():
    if 'user' not in session:
        return  # unauthenticated, handled by individual route guards
    last_active = session.get('last_active')
    timeout = app.permanent_session_lifetime.total_seconds()
    if last_active:
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last_active)).total_seconds()
        if elapsed > timeout:
            session.clear()
            return redirect('/login?expired=1')
    session['last_active'] = datetime.now(timezone.utc).isoformat()
    session.permanent = True
```

The login template checks `request.args.get('expired')` to display the "Session expired" message.

### 8. Dashboard Bar Chart

**`app.py` dashboard route** — passes the three existing count variables already present (`active_assets`, `maintenance_assets`, `inactive_assets`) to the template. No new queries needed.

**`dashboard.html`** additions:

```html
<canvas id="statusChart" height="120"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
(function() {
    var ctx = document.getElementById('statusChart');
    if (!ctx) return;
    try {
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Active', 'Maintenance', 'Inactive'],
                datasets: [{
                    data: [{{ active_assets }}, {{ maintenance_assets }}, {{ inactive_assets }}],
                    backgroundColor: ['#28a745', '#ffc107', '#dc3545']
                }]
            },
            options: { plugins: { legend: { display: false } } }
        });
    } catch (e) { /* graceful degradation */ }
})();
</script>
```

The try/catch ensures that if Chart.js fails to load (CDN outage, CSP block) no unhandled error surfaces.

### 9. Asset Table Client-Side Filters

**`assets.html`** additions — three `<select>` dropdowns rendered above the table, populated via JavaScript from the table data:

```html
<select id="filterStatus">…</select>
<select id="filterCategory">…</select>
<select id="filterBrand">…</select>
```

The JavaScript function `applyFilters()` is called on every `change` event on any dropdown and on `keyup` of the search input. It reads the current value of each filter; a row is shown only if it satisfies **all** active constraints simultaneously (logical AND). When no rows remain visible, a `<tr id="noResults">` row is toggled visible.

Dropdown options are built on page load by scanning the rendered `<tbody>` rows to extract distinct non-null category and brand values — no additional HTTP requests.

---

## Data Models

### Schema Changes

**`interventions` table — add `status` column:**

```sql
ALTER TABLE interventions
ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'Pending';
```

No other schema changes are required. All other enhancements are handled in application code.

### Updated `interventions` Table

| Column | Type | Notes |
|---|---|---|
| id | INT AUTO_INCREMENT PK | |
| asset_id | INT FK → assets.id | |
| technician_id | INT FK → technicians.id | |
| description | TEXT | |
| intervention_date | DATE | |
| **status** | VARCHAR(20) NOT NULL DEFAULT 'Pending' | **New** — 'Pending' or 'Completed' |

### `users` Table (unchanged schema)

| Column | Type | Notes |
|---|---|---|
| id | INT | |
| username | VARCHAR(50) UNIQUE | |
| name | VARCHAR(100) | |
| email | VARCHAR(100) | |
| password | VARCHAR(255) | Must store bcrypt hash after migration |
| role | VARCHAR(50) | |

### `technicians` Table (existing, no change)

| Column | Type |
|---|---|
| id | INT AUTO_INCREMENT PK |
| name | VARCHAR(100) NOT NULL |
| email | VARCHAR(100) |
| phone | VARCHAR(50) |

### `assets` Table (existing, no change)

| Column | Type |
|---|---|
| id | INT AUTO_INCREMENT PK |
| asset_tag | VARCHAR(50) UNIQUE |
| name | VARCHAR(100) |
| brand | VARCHAR(100) |
| model | VARCHAR(100) |
| serial_number | VARCHAR(100) |
| category_id | INT FK → categories.id |
| status | VARCHAR(50) DEFAULT 'Active' |
| location | VARCHAR(100) |
| purchase_date | DATE |
| warranty_expiration | DATE |
| notes | TEXT |

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: New interventions default to Pending status

*For any* valid combination of asset_id, technician_id, description, and intervention_date used to create a new intervention, the resulting record's `status` field SHALL equal `"Pending"`.

**Validates: Requirements 1.1**

---

### Property 2: Completing an intervention preserves the record and updates both statuses

*For any* intervention in `Pending` status and its linked asset, after calling the complete operation the intervention record SHALL still exist in the database with `status = "Completed"` AND the linked asset's `status` SHALL equal `"Active"`.

**Validates: Requirements 1.2, 1.3**

---

### Property 3: Intervention page displays correct status partitioning

*For any* set of intervention records with a mix of `Pending` and `Completed` statuses, the interventions page SHALL display each `Pending` intervention in the active table and each `Completed` intervention exclusively in the history table — with no row appearing in both tables.

**Validates: Requirements 1.4, 1.5**

---

### Property 4: Asset detail page renders null/empty fields with placeholder

*For any* asset record where one or more optional fields (`brand`, `model`, `serial_number`, `category`, `location`, `purchase_date`, `warranty_expiration`, `notes`) are NULL or empty string, the rendered Asset Detail Page SHALL display `"N/A"` or `"—"` for each such field rather than an empty cell.

**Validates: Requirements 2.1**

---

### Property 5: Asset interventions displayed in descending date order

*For any* asset with two or more associated intervention records having distinct `intervention_date` values, the Asset Detail Page SHALL render those interventions ordered so that for every adjacent pair of displayed rows (row i, row i+1), `row_i.intervention_date >= row_{i+1}.intervention_date`.

**Validates: Requirements 2.3**

---

### Property 6: Unauthenticated requests to protected routes redirect to login

*For any* route that requires authentication (`/dashboard`, `/assets`, `/assets/<id>`, `/add-asset`, `/edit-asset/<id>`, `/delete-asset/<id>`, `/interventions`, `/technicians`, `/reports`) and *for any* request made without a valid authenticated session, the application SHALL respond with a redirect to `/login`.

**Validates: Requirements 2.6, 3.1**

---

### Property 7: Valid technician names are accepted and stored after trimming

*For any* non-empty string of at most 100 characters (after stripping leading/trailing whitespace) submitted as a technician name, the application SHALL insert a new `technicians` record whose stored `name` equals the trimmed value.

**Validates: Requirements 3.2**

---

### Property 8: Whitespace-only technician names are rejected without insertion

*For any* string composed entirely of whitespace characters (including the empty string), submitting it as a technician name SHALL result in no new row being inserted into the `technicians` table and SHALL cause an error message to be displayed.

**Validates: Requirements 3.3**

---

### Property 9: Technicians with associated interventions cannot be deleted

*For any* technician who has one or more rows in the `interventions` table referencing their `id`, a deletion request SHALL be rejected: the technician record SHALL remain in the database and an error message SHALL be shown to the user.

**Validates: Requirements 3.6**

---

### Property 10: Intervention status badges match status value

*For any* intervention record displayed in a table row, the badge rendered in that row SHALL use CSS class `badge-pending` with label `"Pending"` when `status = "Pending"`, class `badge-completed` with label `"Completed"` when `status = "Completed"`, and class `badge-neutral` with the raw status value as label for any other status string.

**Validates: Requirements 4.1, 4.2, 4.4**

---

### Property 11: Stored passwords are non-plaintext and verifiable

*For any* plaintext password string submitted during registration or migration, the value stored in `users.password` SHALL NOT equal the plaintext string AND SHALL be verifiable as correct by `bcrypt.check_password_hash(stored, plaintext)`.

**Validates: Requirements 6.1**

---

### Property 12: Login succeeds if and only if password matches hash

*For any* username present in the `users` table and *for any* submitted password string, the login endpoint SHALL grant access (set `session['user']`) if and only if `bcrypt.check_password_hash(stored_hash, submitted_password)` returns `True`.

**Validates: Requirements 6.2**

---

### Property 13: Password migration script is idempotent

*For any* `users` table containing a mix of already-hashed and plaintext passwords, running the migration script twice SHALL produce the same final state as running it once: all passwords stored as bcrypt hashes, no plaintext values remaining.

**Validates: Requirements 6.3**

---

### Property 14: Session activity timestamp is updated on every authenticated request

*For any* authenticated request to a protected route, `session['last_active']` SHALL be set to a timestamp that is within a few seconds of the current UTC time after the request completes.

**Validates: Requirements 7.2**

---

### Property 15: Requests after timeout clear the session and redirect to login

*For any* configured timeout duration `T` (in seconds) and *for any* authenticated session whose `last_active` timestamp is more than `T` seconds in the past, the next request to any protected route SHALL clear the session and redirect the user to `/login`.

**Validates: Requirements 7.3**

---

### Property 16: Dashboard chart data matches actual asset status counts

*For any* state of the `assets` table, the counts passed to the dashboard template for `active_assets`, `maintenance_assets`, and `inactive_assets` SHALL equal the actual counts returned by `SELECT COUNT(*) FROM assets WHERE status = '<status>'` for each respective status value.

**Validates: Requirements 8.2**

---

### Property 17: Active filter constraints reduce visible rows consistently

*For any* combination of active filter values (status, category, brand) and search text, every visible table row SHALL satisfy all active constraints simultaneously (logical AND), and every hidden row SHALL fail at least one active constraint.

**Validates: Requirements 9.2, 9.3, 9.4**

---

### Property 18: Filter dropdown options match distinct values in loaded data

*For any* loaded assets dataset, the `category` filter dropdown SHALL contain exactly the distinct non-null category name values present in the rendered table rows, and the `brand` filter dropdown SHALL contain exactly the distinct non-null brand values present in the rendered table rows.

**Validates: Requirements 9.5**

---

## Error Handling

| Scenario | Handling |
|---|---|
| Asset `id` not found in `/assets/<id>` | 404 error handler renders `404.html`, returns HTTP 404 |
| Any unregistered URL | 404 error handler (same) |
| Technician name empty / whitespace-only | Server-side validation returns error message; no DB write |
| Delete technician with linked interventions | Query count of linked interventions; if > 0, flash error and redirect |
| Login with wrong password | `bcrypt.check_password_hash` returns False; re-render login with generic error |
| Session expired | `before_request` hook clears session, redirects to `/login?expired=1` |
| Chart.js CDN failure | try/catch in inline script suppresses unhandled errors |
| DB connection failure | Existing pattern (exceptions propagate to Flask 500 handler) — out of scope for these enhancements |

---

## Testing Strategy

### Dual Testing Approach

Unit/example-based tests verify specific concrete behaviors. Property-based tests verify universal invariants across many generated inputs. Both are needed for comprehensive coverage.

### Property-Based Testing Library

**`hypothesis`** (Python) — the standard PBT library for Python projects.

```
hypothesis==6.x
pytest==8.x
```

Each property test runs a minimum of **100 iterations**. Each test is tagged with a comment referencing the design property it validates:

```python
# Feature: it-asset-management-enhancements, Property 1: New interventions default to Pending status
```

### Unit / Example Tests

- **Req 1.6** — Deletion requires `confirm=yes`; without it, no deletion occurs.
- **Req 2.2** — Assets list page contains `<a href="/assets/<id>">` for each asset.
- **Req 2.4** — Asset detail with no interventions shows empty-state message.
- **Req 2.5** — `GET /assets/99999` returns HTTP 404 with custom template.
- **Req 3.5** — Delete technician with no interventions succeeds.
- **Req 3.7** — Sidebar HTML contains `href="/technicians"`.
- **Req 4.3** — CSS in `base.html` defines `.badge-pending` and `.badge-completed`.
- **Req 5.1/5.2** — 404 handler is registered; response is 404; template extends `base.html` with required content.
- **Req 6.4** — Migration script hashes `admin123` so stored value differs from plaintext.
- **Req 7.1** — Default `SESSION_TIMEOUT_MINUTES` is 30 when env var is not set.
- **Req 7.4** — `app.config` contains `SESSION_COOKIE_HTTPONLY=True` and `SESSION_COOKIE_SAMESITE='Lax'`.
- **Req 8.1** — Dashboard template contains `<canvas id="statusChart">` and Chart.js script tag.
- **Req 8.3** — Chart configuration in template contains hex values `#28a745`, `#ffc107`, `#dc3545`.
- **Req 9.1** — Assets page renders three `<select>` dropdowns with default `"All"` option.
- **Req 9.6** — When all filters match no rows, no-results row is displayed.

### Property Tests (Hypothesis)

Each of Properties 1–18 above maps to one `@given`-decorated test function. Key strategies:

- **Interventions** — `st.integers(min_value=1)` for FK ids (DB seeded in test fixtures), `st.text(min_size=1)` for descriptions.
- **Technician names** — `st.text()` for arbitrary strings; `st.text(alphabet=st.characters(whitelist_categories=('Zs',)))` for whitespace-only inputs.
- **Asset fields** — `st.one_of(st.none(), st.text())` for optional fields to test null/empty placeholder rendering.
- **Session timeout** — `st.integers(min_value=1, max_value=120)` for timeout minutes; `st.floats(min_value=0.0)` for elapsed seconds.
- **Filter values** — sampled from the actual rendered table data using `st.sampled_from()`.

### Integration Tests

- Full login → navigate → logout flow with a test DB.
- Migration script against a test DB with known plaintext passwords.
- Session timeout end-to-end with a shortened timeout value.
