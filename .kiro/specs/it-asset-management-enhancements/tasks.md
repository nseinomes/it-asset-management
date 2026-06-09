# Implementation Plan: IT Asset Management Enhancements

## Overview

Nine incremental enhancements to the existing Flask / Jinja2 / MySQL application. All changes fit the existing single-file route pattern (`app.py`), `database.py` helper, and Jinja2 templates that extend `base.html`. No new frameworks are introduced.

The implementation order moves from foundational database and security changes (schema migration, password hashing, session timeout) through new pages and UI features (asset detail, technician management, intervention history, badges, 404 page) to purely client-side additions (dashboard chart, asset filters).

---

## Tasks

- [ ] 1. Database schema migration — add `status` column to `interventions`
  - [ ] 1.1 Write and run the SQL migration to add the `status` column
    - Execute `ALTER TABLE interventions ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'Pending';` against the `it_asset_management` database
    - Verify the column is present with `DESCRIBE interventions;`
    - _Requirements: 1.1_

  - [ ]* 1.2 Write a property test for new intervention default status (Property 1)
    - **Property 1: New interventions default to Pending status**
    - Use `@given` with valid `asset_id`, `technician_id`, `st.text(min_size=1)` description, and `st.dates()` for date
    - Assert the inserted row's `status == "Pending"` for every generated combination
    - **Validates: Requirements 1.1**

- [ ] 2. Intervention history preservation — backend changes
  - [ ] 2.1 Update `complete_intervention` route in `app.py` to preserve the record
    - Change the `DELETE FROM interventions` statement to `UPDATE interventions SET status='Completed' WHERE id=%s`
    - Keep the existing `UPDATE assets SET status='Active'` statement
    - _Requirements: 1.2, 1.3_

  - [ ]* 2.2 Write a property test for completing an intervention (Property 2)
    - **Property 2: Completing an intervention preserves the record and updates both statuses**
    - Seed a Pending intervention; call the complete route; assert record still exists with `status='Completed'` and linked asset has `status='Active'`
    - **Validates: Requirements 1.2, 1.3**

  - [ ] 2.3 Update `delete_intervention` route to require `confirm=yes` query parameter
    - Add a check: if `request.args.get('confirm') != 'yes'`, flash an error and redirect back without deleting
    - Only proceed with `DELETE` if the confirmation token is present
    - _Requirements: 1.6_

  - [ ]* 2.4 Write a unit test for delete-intervention confirmation guard
    - Test that `GET /interventions/delete/<id>` without `?confirm=yes` does not remove the row
    - Test that `GET /interventions/delete/<id>?confirm=yes` does remove the row
    - _Requirements: 1.6_

  - [ ] 2.5 Update `/interventions` GET route to split results into Pending and Completed sets
    - Replace the single `SELECT` with two queries: one `WHERE status='Pending'` (for active table) and one `WHERE status='Completed'` (for history table)
    - Pass both result sets to the template as `pending_interventions` and `completed_interventions`
    - _Requirements: 1.4, 1.5_

  - [ ] 2.6 Update `add_intervention` route to explicitly set `status='Pending'` in the INSERT
    - Modify the `INSERT INTO interventions` statement to include the `status` column with value `'Pending'`
    - _Requirements: 1.1_

- [ ] 3. Intervention history preservation — template changes
  - [ ] 3.1 Update `interventions.html` to render two separate tables
    - Replace the single interventions loop with a Pending table (with ✅ Done and Delete actions — delete link must append `?confirm=yes`) and a Completed history table (read-only, below or collapsible)
    - _Requirements: 1.4, 1.5, 1.6_

  - [ ]* 3.2 Write a property test for status partitioning on the interventions page (Property 3)
    - **Property 3: Intervention page displays correct status partitioning**
    - For a generated mix of Pending/Completed rows, assert each Pending row appears only in the active table and each Completed row appears only in the history table
    - **Validates: Requirements 1.4, 1.5**

- [ ] 4. Intervention status badges — CSS and template macro
  - [ ] 4.1 Add badge CSS classes to `base.html`
    - Add `.badge-pending`, `.badge-completed`, `.badge-neutral` rules to the `<style>` block alongside the existing badge classes
    - _Requirements: 4.3_

  - [ ]* 4.2 Write a unit test for badge CSS presence
    - Assert that `base.html` source contains `.badge-pending` and `.badge-completed` class definitions
    - _Requirements: 4.3_

  - [ ] 4.3 Add a "Status" column with badge macro to `interventions.html`
    - Insert a "Status" `<th>` and a Jinja2 `{% if %}` block that renders `badge-pending`, `badge-completed`, or `badge-neutral` based on `i.status`
    - _Requirements: 4.1, 4.2, 4.4_

  - [ ]* 4.4 Write a property test for intervention status badge rendering (Property 10)
    - **Property 10: Intervention status badges match status value**
    - For any status string ('Pending', 'Completed', arbitrary), assert the correct CSS class and label appear in the rendered HTML
    - **Validates: Requirements 4.1, 4.2, 4.4**

- [ ] 5. Custom 404 error page
  - [ ] 5.1 Create `templates/404.html`
    - Extend `base.html`; set `{% block title %}404 – Page Not Found{% endblock %}`
    - Include a visible heading with "404" and "not found"
    - Include `<a href="/dashboard">Return to Dashboard</a>`
    - _Requirements: 5.2_

  - [ ] 5.2 Register the 404 error handler in `app.py`
    - Add `@app.errorhandler(404)` handler that calls `render_template('404.html'), 404`
    - _Requirements: 5.1_

  - [ ]* 5.3 Write unit tests for the 404 handler
    - Assert that `GET /nonexistent-url` returns HTTP 404
    - Assert the response body contains "404" and "not found"
    - Assert the response body contains `href="/dashboard"`
    - _Requirements: 5.1, 5.2_

- [ ] 6. Password hashing — dependency and migration
  - [ ] 6.1 Add `flask-bcrypt==1.0.1` to project requirements
    - Create or update `requirements.txt` with `flask-bcrypt==1.0.1`, `hypothesis==6.131.0`, `pytest==8.3.5`
    - _Requirements: 6.1_

  - [ ] 6.2 Initialise `flask-bcrypt` in `app.py` and update the login route
    - Add `from flask_bcrypt import Bcrypt; bcrypt = Bcrypt(app)` after app creation
    - Replace the plaintext `SELECT … WHERE password=%s` login query with a lookup by username only, then verify with `bcrypt.check_password_hash(user['password'], password)`
    - _Requirements: 6.1, 6.2_

  - [ ]* 6.3 Write property tests for password hashing invariants (Properties 11 and 12)
    - **Property 11: Stored passwords are non-plaintext and verifiable**
    - **Property 12: Login succeeds if and only if password matches hash**
    - Use `st.text(min_size=1)` for plaintext passwords; assert stored value differs from plaintext and `bcrypt.check_password_hash` returns True for correct input and False for any other
    - **Validates: Requirements 6.1, 6.2**

  - [ ] 6.4 Write `migrate_passwords.py` migration script
    - Read every row in `users`; skip rows where `password` already starts with `'$2b$'` or `'$2a$'`; replace plaintext values with `bcrypt.generate_password_hash(plain).decode('utf-8')`
    - Include a guard so re-running the script is safe (idempotent)
    - _Requirements: 6.3, 6.4_

  - [ ]* 6.5 Write a property test for migration script idempotency (Property 13)
    - **Property 13: Password migration script is idempotent**
    - Seed a test DB with plaintext and already-hashed passwords; run the script twice; assert the resulting state is identical after both runs and no plaintext remains
    - **Validates: Requirements 6.3**

- [ ] 7. Session timeout — configuration and before_request hook
  - [ ] 7.1 Configure session security settings and timeout in `app.py`
    - Add `import os` and `from datetime import timedelta, datetime, timezone`
    - Set `app.config['SESSION_COOKIE_HTTPONLY'] = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`
    - Set `app.permanent_session_lifetime = timedelta(minutes=int(os.environ.get('SESSION_TIMEOUT_MINUTES', 30)))`
    - _Requirements: 7.1, 7.4_

  - [ ] 7.2 Implement the `before_request` session timeout hook in `app.py`
    - Add `@app.before_request` function `check_session_timeout()` that reads `session['last_active']`, computes elapsed seconds against `app.permanent_session_lifetime.total_seconds()`, clears the session and redirects to `/login?expired=1` if elapsed, otherwise updates `session['last_active']` and sets `session.permanent = True`
    - _Requirements: 7.2, 7.3_

  - [ ] 7.3 Update `login.html` to display a session-expired message
    - Check `request.args.get('expired')` in the template; if truthy, display a message such as "Your session has expired. Please log in again."
    - _Requirements: 7.3_

  - [ ]* 7.4 Write property tests for session timeout (Properties 14 and 15)
    - **Property 14: Session activity timestamp is updated on every authenticated request**
    - **Property 15: Requests after timeout clear the session and redirect to login**
    - Use `st.integers(min_value=1, max_value=120)` for timeout minutes; `st.floats(min_value=0.0)` for elapsed seconds
    - **Validates: Requirements 7.2, 7.3**

  - [ ]* 7.5 Write unit tests for session configuration
    - Assert `app.config['SESSION_COOKIE_HTTPONLY'] == True` and `SESSION_COOKIE_SAMESITE == 'Lax'`
    - Assert default timeout is 30 minutes when `SESSION_TIMEOUT_MINUTES` env var is unset
    - _Requirements: 7.1, 7.4_

- [ ] 8. Checkpoint — core backend and security complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Asset detail page — backend route
  - [ ] 9.1 Add `GET /assets/<int:id>` route to `app.py`
    - Check `session['user']`; query `assets JOIN categories WHERE assets.id = <id>`; abort with 404 if not found
    - Query `interventions JOIN technicians WHERE asset_id = <id> ORDER BY intervention_date DESC`
    - Render `asset_detail.html` with asset and interventions data
    - _Requirements: 2.1, 2.3, 2.5, 2.6_

  - [ ]* 9.2 Write a property test for asset detail null-field placeholders (Property 4)
    - **Property 4: Asset detail page renders null/empty fields with placeholder**
    - Use `st.one_of(st.none(), st.just(''))` for optional fields; assert the rendered HTML contains `'N/A'` or `'—'` for each null/empty field
    - **Validates: Requirements 2.1**

  - [ ]* 9.3 Write a property test for intervention date ordering (Property 5)
    - **Property 5: Asset interventions displayed in descending date order**
    - For any generated set of intervention dates, assert adjacent rendered rows satisfy `row_i.date >= row_{i+1}.date`
    - **Validates: Requirements 2.3**

  - [ ]* 9.4 Write a property test for unauthenticated redirect (Property 6)
    - **Property 6: Unauthenticated requests to protected routes redirect to login**
    - For routes `/dashboard`, `/assets`, `/assets/<id>`, `/add-asset`, `/edit-asset/<id>`, `/delete-asset/<id>`, `/interventions`, `/technicians`, `/reports`, assert unauthenticated requests return a redirect to `/login`
    - **Validates: Requirements 2.6, 3.1**

  - [ ]* 9.5 Write unit tests for asset detail page edge cases
    - Assert `GET /assets/99999` returns 404 and uses the custom template
    - Assert asset detail with no interventions shows "No intervention history available"
    - Assert assets list `<td>` contains `<a href="/assets/<id>">` for each asset
    - _Requirements: 2.2, 2.4, 2.5_

- [ ] 10. Asset detail page — template
  - [ ] 10.1 Create `templates/asset_detail.html`
    - Extend `base.html`; add an asset info card that displays all fields (`asset_tag`, `name`, `brand`, `model`, `status`, `purchase_date`, `warranty_expiration`, `notes`, `category`) using `{{ asset.field or '—' }}` for optional fields
    - Add an intervention history table with columns for description, date, technician, and status badge; show empty-state message when list is empty
    - _Requirements: 2.1, 2.3, 2.4_

  - [ ] 10.2 Update `assets.html` to link asset name to the detail page
    - Wrap the asset name `<td>` content with `<a href="/assets/{{ asset.id }}">{{ asset.name }}</a>`
    - _Requirements: 2.2_

- [ ] 11. Technician management — backend routes
  - [ ] 11.1 Add `validate_technician_name` helper and `GET/POST /technicians` route to `app.py`
    - Implement `validate_technician_name(name: str) -> str | None` that strips whitespace and returns `None` if empty or longer than 100 characters
    - `GET /technicians`: query all technicians, render `technicians.html`
    - `POST /technicians`: validate name; on failure flash error and redirect; on success insert and redirect
    - Protect with `session['user']` check
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 11.2 Write property tests for technician name validation (Properties 7 and 8)
    - **Property 7: Valid technician names are accepted and stored after trimming**
    - **Property 8: Whitespace-only technician names are rejected without insertion**
    - Use `st.text(min_size=1, max_size=100)` for valid names; `st.text(alphabet=st.characters(whitelist_categories=('Zs',)))` for whitespace-only inputs
    - **Validates: Requirements 3.2, 3.3**

  - [ ] 11.3 Add `POST /technicians/edit/<int:id>` route to `app.py`
    - Validate name using `validate_technician_name`; on failure flash error; on success `UPDATE technicians SET name=%s WHERE id=%s` and redirect
    - _Requirements: 3.4_

  - [ ] 11.4 Add `GET /technicians/delete/<int:id>` route to `app.py`
    - Query `SELECT COUNT(*) FROM interventions WHERE technician_id=%s`; if count > 0, flash error and redirect without deleting
    - Otherwise `DELETE FROM technicians WHERE id=%s` and redirect
    - _Requirements: 3.5, 3.6_

  - [ ]* 11.5 Write a property test for delete-technician with interventions (Property 9)
    - **Property 9: Technicians with associated interventions cannot be deleted**
    - For any technician with one or more linked interventions, assert a delete request leaves the record intact and shows an error
    - **Validates: Requirements 3.6**

  - [ ]* 11.6 Write unit tests for technician deletion success
    - Assert that a technician with no linked interventions is removed from the DB on delete
    - Assert sidebar HTML in `base.html` contains `href="/technicians"`
    - _Requirements: 3.5, 3.7_

- [ ] 12. Technician management — template and sidebar
  - [ ] 12.1 Create `templates/technicians.html`
    - Extend `base.html`; add an inline modal or form for adding a technician (name field); render a table of all technicians with Edit and Delete action buttons; include an edit form pre-populated with the current technician name
    - Display flashed error messages for validation failures and deletion blocks
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ] 12.2 Add Technicians link to `base.html` sidebar
    - Insert `<a href="/technicians" class="{% if request.path == '/technicians' %}active{% endif %}"><span class="icon">👷</span> Technicians</a>` under the "Operations" `<nav-section>`
    - _Requirements: 3.7_

- [ ] 13. Dashboard bar chart
  - [ ] 13.1 Add Chart.js bar chart to `dashboard.html`
    - Add `<canvas id="statusChart" height="120"></canvas>` below the stats grid
    - Add a `<script>` tag loading Chart.js from `https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js`
    - Implement the inline chart config using `{{ active_assets }}`, `{{ maintenance_assets }}`, `{{ inactive_assets }}` as data values, with colors `#28a745`, `#ffc107`, `#dc3545`; wrap in `try/catch` for graceful degradation
    - _Requirements: 8.1, 8.3, 8.4_

  - [ ]* 13.2 Write a property test for dashboard chart data accuracy (Property 16)
    - **Property 16: Dashboard chart data matches actual asset status counts**
    - For any seeded state of the `assets` table, assert `active_assets`, `maintenance_assets`, `inactive_assets` passed to the template equal the `SELECT COUNT(*)` values for each status
    - **Validates: Requirements 8.2**

  - [ ]* 13.3 Write unit tests for dashboard chart markup
    - Assert `dashboard.html` rendered output contains `<canvas id="statusChart">`
    - Assert the template includes the Chart.js `<script>` tag
    - Assert the chart config contains hex values `#28a745`, `#ffc107`, `#dc3545`
    - _Requirements: 8.1, 8.3_

- [ ] 14. Asset table client-side filters
  - [ ] 14.1 Update `/assets` route in `app.py` to include category name in asset data
    - Modify the `SELECT` to `JOIN categories ON assets.category_id = categories.id` so `category_name` is available in every row for the filters and detail page
    - _Requirements: 9.1, 9.5_

  - [ ] 14.2 Add filter dropdowns and updated `applyFilters` JavaScript to `assets.html`
    - Add three `<select>` dropdowns (`filterStatus`, `filterCategory`, `filterBrand`) with a default `<option value="">All</option>` above the table
    - Populate category and brand options dynamically on page load by scanning `<tbody>` rows for distinct non-null values
    - Rewrite `filterTable()` / add `applyFilters()` that applies all three dropdowns AND the existing search input as a logical AND; bind `applyFilters` to `change` events on each dropdown and `keyup` on the search input
    - Add a `<tr id="noResults">` row that is shown only when all other rows are hidden
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [ ]* 14.3 Write property tests for client-side filter constraints (Properties 17 and 18)
    - **Property 17: Active filter constraints reduce visible rows consistently**
    - **Property 18: Filter dropdown options match distinct values in loaded data**
    - Use `st.sampled_from()` to pick filter values from actual table data; assert every visible row satisfies all active constraints (AND), and every hidden row fails at least one; assert dropdown options match distinct non-null values in rendered rows
    - **Validates: Requirements 9.2, 9.3, 9.4, 9.5**

  - [ ]* 14.4 Write unit tests for filter UI structure
    - Assert `assets.html` renders three `<select>` dropdowns
    - Assert the no-results row is present in the DOM and is initially hidden
    - _Requirements: 9.1, 9.6_

- [ ] 15. Set up pytest and hypothesis test infrastructure
  - [ ] 15.1 Create `tests/conftest.py` with Flask test client and test database fixtures
    - Define a `app_client` fixture that creates a Flask test client using a test database connection (separate from production DB)
    - Define a `seed_db` fixture that inserts known rows into `users`, `assets`, `categories`, `technicians`, `interventions` before each test and tears down after
    - _Requirements: 6.1 (testing infrastructure)_

  - [ ]* 15.2 Write a smoke test to verify the test infrastructure works
    - Assert `GET /` returns HTTP 200
    - Assert `GET /login` returns HTTP 200
    - _Requirements: all (infrastructure validation)_

- [ ] 16. Final checkpoint — all enhancements wired together
  - Ensure all tests pass, ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- The design document specifies **18 correctness properties** — each one has a corresponding property test sub-task referencing it by number
- Schema migration (task 1.1) must be applied before running the app or any tests that touch the `interventions` table
- `migrate_passwords.py` (task 6.4) must be run once against the production DB before deploying the bcrypt login change (task 6.2)
- The `/assets` route update (task 14.1) also benefits the asset detail page (task 9.1) since both need `category_name`; implement 14.1 before or alongside 9.1
- Session timeout configuration (task 7.1) and the before_request hook (task 7.2) must both be in place before any session-related tests are meaningful
- Test fixtures (task 15.1) should be created before running any property or unit tests

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "6.1", "15.1"] },
    { "id": 1, "tasks": ["1.2", "2.1", "2.3", "2.6", "4.1", "5.1", "5.2", "6.2", "6.4", "7.1", "15.2"] },
    { "id": 2, "tasks": ["2.2", "2.4", "2.5", "3.1", "4.3", "5.3", "6.3", "6.5", "7.2", "7.3", "9.1"] },
    { "id": 3, "tasks": ["3.2", "4.2", "4.4", "7.4", "7.5", "9.2", "9.3", "9.4", "9.5", "10.1", "10.2", "11.1", "14.1"] },
    { "id": 4, "tasks": ["11.2", "11.3", "11.4", "12.1", "12.2", "13.1"] },
    { "id": 5, "tasks": ["11.5", "11.6", "13.2", "13.3", "14.2"] },
    { "id": 6, "tasks": ["14.3", "14.4"] }
  ]
}
```
