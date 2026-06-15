# Implementation Plan: priority-bugs

## Overview

Four targeted bug fixes to the IT Asset Management Flask application. All changes are confined to `app.py`, `templates/interventions.html`, `templates/assets.html`, and a new `.env.example` file. No new dependencies, no database migrations.

---

## Tasks

- [x] 1. Fix 1 — Add completed-intervention history to the interventions route and template
  - [x] 1.1 Add completed-interventions query in `interventions()` route in `app.py`
    - Below the existing `cursor.execute(... WHERE i.status = 'Active' ...)` block, add a second query that fetches all interventions where `status = 'Completed'` ordered by `intervention_date DESC`, storing the result as `completed_interventions`
    - Update the `render_template('interventions.html', ...)` call to pass `completed_interventions=completed_interventions`
    - _Requirements: 1.1_

  - [x] 1.2 Add flash message block to `templates/interventions.html`
    - Immediately after `{% block content %}`, before the `.interventions-header` div, insert a `{% for msg in get_flashed_messages() %}` block that renders each message as a Bootstrap `alert alert-danger alert-dismissible` div
    - _Requirements: 2.5_

  - [x] 1.3 Add collapsible History section to `templates/interventions.html`
    - After the closing `</div>` of the existing `.table-card` div, append a Bootstrap collapse section with a toggle button showing `📋 History ({{ completed_interventions|length }})`
    - The collapsed `#historyCollapse` section contains a read-only table with columns: Asset, Technician, Description, Date, Status — no action buttons in any history row
    - When `completed_interventions` is empty, render an empty-state placeholder paragraph inside the collapsed section
    - _Requirements: 1.2, 1.3, 1.4_

  - [x]* 1.4 Write property tests for Fix 1
    - **Property 1: Active/Completed separation is exhaustive and non-overlapping**
    - **Validates: Requirements 1.1**
    - Use `hypothesis` with `@given(st.lists(...))` to generate mixed-status intervention dicts; simulate the route's split logic; assert the two lists are disjoint and their union equals all interventions; also render `interventions.html` and confirm each group lands in the correct HTML section
    - **Property 2: History rows contain no action buttons**
    - **Validates: Requirements 1.4**
    - Use `hypothesis` with `@given(st.lists(..., min_size=1))` to generate completed intervention dicts; render `interventions.html`; parse response HTML and assert `#historyCollapse` contains no `href` with `/complete/` and no element with class `btn-delete`
    - Tag each test: `# Feature: priority-bugs, Property 1: Active/Completed separation` and `# Feature: priority-bugs, Property 2: History rows contain no action buttons`
    - Test file: `tests/test_priority_bugs.py`
    - _Requirements: 1.1, 1.2, 1.4_

- [x] 2. Fix 2 — Add server-side asset status validation in `add_intervention`
  - [x] 2.1 Add `flash` to the Flask import line in `app.py`
    - Update the `from flask import ...` line to include `flash` alongside the existing imports
    - _Requirements: 2.5_

  - [x] 2.2 Insert validation block in `add_intervention()` in `app.py`
    - After reading `asset_id`, `technician_id`, `description` from the form and opening the DB connection, insert a validation block before the `INSERT` statement:
      - Query `SELECT status FROM assets WHERE id=%s` for the submitted `asset_id`
      - If the asset does not exist: close cursor/conn, flash `"Asset not found."`, return `redirect('/interventions'), 404`
      - If `asset['status'] != 'Inactive'`: close cursor/conn, flash `"Asset is not available for intervention."`, return `redirect('/interventions'), 400`
    - The existing `INSERT` and `UPDATE assets SET status='Maintenance'` lines remain unchanged after the guard
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x]* 2.3 Write property test for Fix 2
    - **Property 3: Non-Inactive assets are always rejected**
    - **Validates: Requirements 2.3**
    - Use `hypothesis` with `@given(st.sampled_from(['Active', 'Maintenance']))` for the asset status; mock `get_connection()` so the SELECT returns an asset with that status; POST to `/interventions/add`; assert the response redirects to `/interventions`, no `INSERT` was executed, and the flash message equals `"Asset is not available for intervention."`
    - Include an edge-case unit test: posting with an `asset_id` that does not exist returns 404 and flashes `"Asset not found."`
    - Tag: `# Feature: priority-bugs, Property 3: Non-Inactive assets are always rejected`
    - Test file: `tests/test_priority_bugs.py`
    - _Requirements: 2.2, 2.3_

- [x] 3. Checkpoint — Ensure all tests pass before continuing
  - Run `pytest tests/test_priority_bugs.py` and confirm all tests pass. If any failures arise, resolve them before proceeding.

- [x] 4. Fix 3 — Guard asset deletion when intervention records exist
  - [x] 4.1 Add intervention-count guard in `delete_asset()` in `app.py`
    - Before the `DELETE FROM assets` statement, add:
      - `SELECT COUNT(*) as cnt FROM interventions WHERE asset_id=%s`
      - If `count > 0`: close cursor/conn, flash `"Cannot delete asset: intervention records exist. Delete the interventions first."`, return `redirect('/assets')`
    - The existing `DELETE FROM assets WHERE id=%s` and `conn.commit()` remain for the count-is-zero path
    - `flash` is already imported after task 2.1
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 4.2 Add flash message block to `templates/assets.html`
    - After `{% block content %}` and before the `<div class="page-header">` div, insert a `{% for msg in get_flashed_messages() %}` block that renders each message as a Bootstrap `alert alert-danger alert-dismissible fade show mt-3` div
    - No flash message is emitted on successful deletion (satisfies Requirement 3.4)
    - _Requirements: 3.4_

  - [x]* 4.3 Write property test for Fix 3
    - **Property 4: Assets with interventions are never deleted**
    - **Validates: Requirements 3.2**
    - Use `hypothesis` with `@given(st.integers(min_value=1, max_value=20))` for the intervention count; mock `get_connection()` so the COUNT query returns that value; GET `/delete-asset/<id>`; assert the response redirects to `/assets`, no `DELETE FROM assets` was executed, and the flash message equals `"Cannot delete asset: intervention records exist. Delete the interventions first."`
    - Include a unit test for the happy path: COUNT returns 0, DELETE executes, redirect to `/assets`, no flash message
    - Tag: `# Feature: priority-bugs, Property 4: Assets with interventions are never deleted`
    - Test file: `tests/test_priority_bugs.py`
    - _Requirements: 3.2, 3.3, 3.4_

- [x] 5. Fix 4 — Load Flask secret key from environment variable
  - [x] 5.1 Add `import os` to `app.py`
    - Add `import os` to the existing import block at the top of `app.py`
    - _Requirements: 4.4_

  - [x] 5.2 Replace hardcoded `app.secret_key` in `app.py`
    - Change `app.secret_key = "evolve_secret_key"` to `app.secret_key = os.environ.get('SECRET_KEY', 'evolve_secret_key_dev')`
    - The fallback `'evolve_secret_key_dev'` makes the dev default visually distinct from any production value
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 5.3 Create `.env.example` at the project root
    - Create `.env.example` at the project root with content: `SECRET_KEY=your-secret-key-here`
    - Do NOT add `.env.example` to `.gitignore` (it contains no secrets and should be committed)
    - Verify `.gitignore` already includes `.env` (no change needed)
    - _Requirements: 4.5, 4.6_

  - [x]* 5.4 Write smoke tests for Fix 4
    - In `tests/test_priority_bugs.py`, add unit/smoke tests (single-execution, not property-based):
      - `import os` is present in `app.py` (verified via AST parse)
      - `.env.example` exists at the project root and contains the line `SECRET_KEY=your-secret-key-here`
      - `.gitignore` contains `.env` as a standalone entry and does NOT contain `.env.example`
      - When `SECRET_KEY` env var is unset, `app.secret_key` equals `'evolve_secret_key_dev'`
      - When `SECRET_KEY` env var is set to a custom value, `app.secret_key` equals that value
    - _Requirements: 4.1, 4.2, 4.4, 4.5, 4.6_

- [x] 6. Final checkpoint — Ensure all tests pass
  - Run `pytest tests/test_priority_bugs.py` and confirm all tests pass. Ask the user if any failures arise.

---

## Notes

- Tasks marked with `*` are optional test tasks that can be skipped for a faster MVP
- Fix 2 (task 2.1) must be completed before Fix 3 (task 4.1) because both depend on `flash` being imported
- The flash block in `interventions.html` (task 1.2) is shared between Fix 1 and Fix 2 — it is written once and serves both
- All property tests use [Hypothesis](https://hypothesis.readthedocs.io/) (already present at `.hypothesis/`)
- Property tests use `@settings(max_examples=100, deadline=None)` for reliable CI behaviour

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "5.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "2.1", "5.2", "5.3"] },
    { "id": 2, "tasks": ["2.2", "4.1", "4.2"] },
    { "id": 3, "tasks": ["1.4", "2.3", "4.3", "5.4"] },
    { "id": 4, "tasks": ["3", "6"] }
  ]
}
```
