# Implementation Plan: app-improvements

## Overview

Four targeted improvements to the existing Flask + PyMySQL + Jinja2 IT Asset Management application: user management CRUD, server-side pagination for the assets table, audit logging wired to all mutating routes, and category management CRUD. All changes are additive — new routes and templates are added, and existing routes are extended without breaking current behaviour.

## Tasks

- [x] 1. Prepare shared infrastructure for all features
  - [x] 1.1 Add `session['user_id']` to the login route
    - In `app.py` `login()`, after setting `session['user']`, also store `session['user_id'] = user['id']`
    - This is required by audit logging in all subsequent mutating routes
    - Add `from app_utils import log_action` import at the top of `app.py`
    - Add `import bcrypt` import at the top of `app.py`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [x] 2. User Management routes
  - [x] 2.1 Implement `GET /users` — list all users
    - Add route to `app.py`: query `SELECT u.id, u.username, r.name as role_name FROM users u LEFT JOIN roles r ON u.role_id = r.id ORDER BY u.username`
    - Also query all roles for the create form dropdown
    - Render `users.html` with `users` and `roles` context
    - Guard with `if 'user' not in session`
    - _Requirements: 1.1_

  - [x] 2.2 Implement `POST /users/create` — create new user
    - Validate: `username` 1–50 chars, `password` ≥ 8 chars, `role_id` exists in `roles`; re-render with `error` on failure
    - Check duplicate username case-insensitively: `SELECT id FROM users WHERE LOWER(username) = LOWER(%s)`; re-render with error if found
    - Hash password with `bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()`
    - INSERT into `users`; capture `cursor.lastrowid`
    - Wrap `log_action(session['user_id'], 'CREATE', 'user', new_id, new_value={'username': username, 'role_id': role_id})` in try/except; on failure call `app.logger.error(...)`
    - Redirect to `/users` on success
    - _Requirements: 1.2, 1.3, 1.4_

  - [x] 2.3 Implement `GET /users/edit/<id>` and `POST /users/edit/<id>` — edit user
    - GET: fetch user by id (404-flash-redirect if not found), fetch all roles, render `edit_user.html`
    - POST: validate `role_id` exists; if password field non-empty validate ≥ 8 chars then hash with bcrypt and include in UPDATE; call `log_action` with `old_value={'role_id': old_role_id}` and `new_value={'role_id': new_role_id}`; redirect to `/users`
    - _Requirements: 1.5, 1.6, 1.9_

  - [x] 2.4 Implement `GET /users/delete/<id>` — delete user
    - Fetch user by id; flash error and redirect if not found
    - Guard: if `user['username'] == session['user']`, flash "Cannot delete your own account" and redirect
    - DELETE from `users`; call `log_action` with `old_value={'username': username}`
    - Redirect to `/users`
    - _Requirements: 1.7, 1.8, 1.9_

  - [x] 2.5 Create `templates/users.html`
    - Extend `base.html`; table listing `id`, `username`, `role_name` with edit and delete buttons per row
    - Inline create form with username, password, and role dropdown
    - Display `error` flash/context message when present
    - _Requirements: 1.1, 1.10_

  - [x] 2.6 Create `templates/edit_user.html`
    - Extend `base.html`; form with role dropdown pre-selected; optional new password field
    - Display `error` context variable when present
    - _Requirements: 1.5, 1.6_

  - [x] 2.7 Write unit tests for user management validation
    - Test username length boundaries (empty, 1 char, 50 chars, 51 chars)
    - Test password length boundary (7 chars rejected, 8 chars accepted)
    - Test duplicate username detection (case-insensitive)
    - Test self-delete guard
    - _Requirements: 1.2, 1.3, 1.4, 1.7, 1.8_

- [x] 3. Checkpoint — user management
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Asset Table Pagination
  - [x] 4.1 Refactor `GET /assets` route to support server-side pagination and filtering
    - Parse and sanitise query params: `page` (clamp to ≥ 1), `search`, `status`, `category`, `brand`
    - Build parameterised WHERE clause; run COUNT query for `total_count`
    - Compute `total_pages = max(1, ceil(total_count / 20))`; clamp `page` to `[1, total_pages]`
    - Run data query with `LIMIT 20 OFFSET (page-1)*20 ORDER BY id DESC`
    - Remove the existing single-query `fetchall()` for the full assets list
    - Fetch distinct brands for filter dropdown
    - Pass to template: `assets`, `categories`, `brands`, `page`, `total_pages`, `total_count`, `filter_search`, `filter_status`, `filter_category`, `filter_brand`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.7, 2.8_

  - [x] 4.2 Update `templates/assets.html` — replace client-side filter with server-side form and pagination bar
    - Replace any client-side JS filtering with a server-side filter form (`GET` to `/assets`); include hidden `page` reset to 1 on filter submit (no explicit hidden field needed — form action without `page` defaults to 1)
    - Add `Pagination_Bar`: previous link (disabled on page 1), page number links (current ± 1), next link (disabled on last page); preserve all active filter params in every pagination link
    - _Requirements: 2.1, 2.6, 2.7, 2.8_

  - [x] 4.3 Write unit tests for pagination math
    - Test offset calculation: `(page-1) * 20`
    - Test `total_pages` from `total_count` (boundaries: 0 rows, 1 row, 20 rows, 21 rows)
    - Test page clamping: `page=0` → 1, `page=-5` → 1, `page > total_pages` → `total_pages`
    - _Requirements: 2.2, 2.3, 2.4_

- [x] 5. Checkpoint — pagination
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Audit Logging — wire `log_action()` to all mutating routes
  - [x] 6.1 Instrument asset routes (`add_asset`, `edit_asset`, `delete_asset`)
    - `add_asset` POST: after `conn.commit()`, call `log_action(session['user_id'], 'CREATE', 'asset', cursor.lastrowid, new_value={...non-null asset fields...})`; wrap in try/except → `app.logger.error` on failure
    - `edit_asset` POST: before UPDATE, fetch old asset row; after `conn.commit()`, call `log_action(..., 'UPDATE', 'asset', id, old_value=old_dict, new_value=new_dict)`
    - `delete_asset` GET: before DELETE, fetch asset row; after `conn.commit()`, call `log_action(..., 'DELETE', 'asset', id, old_value=old_dict)`
    - _Requirements: 3.1, 3.2, 3.3, 3.9_

  - [x] 6.2 Instrument intervention routes (`add_intervention`, `complete_intervention`, `delete_intervention`)
    - `add_intervention` POST: after commit, `log_action(..., 'CREATE', 'intervention', cursor.lastrowid, new_value={...})`
    - `complete_intervention` GET: after commit, `log_action(..., 'UPDATE', 'intervention', id, old_value={'status':'Active'}, new_value={'status':'Completed'})`
    - `delete_intervention` GET: fetch row before DELETE; after commit, `log_action(..., 'DELETE', 'intervention', id, old_value={...})`
    - _Requirements: 3.4, 3.5, 3.6, 3.9_

  - [x] 6.3 Instrument technician routes (`add_technician`, `delete_technician`)
    - `add_technician` POST: after commit, `log_action(..., 'CREATE', 'technician', cursor.lastrowid, new_value={name, email, phone})`
    - `delete_technician` GET: fetch row before DELETE; after commit, `log_action(..., 'DELETE', 'technician', id, old_value={...})`
    - _Requirements: 3.7, 3.8, 3.9_

  - [x] 6.4 Implement `GET /audit-log` route and `templates/audit_log.html`
    - Route: guard session; query `SELECT al.id, al.timestamp, u.username, al.action, al.entity_type, al.entity_id, al.old_value, al.new_value FROM audit_log al JOIN users u ON al.user_id = u.id ORDER BY al.timestamp DESC LIMIT 500`
    - Render `audit_log.html` with `entries`
    - Template: extend `base.html`; table with columns `timestamp`, `username`, `action`, `entity_type`, `entity_id`, `old_value`, `new_value`
    - _Requirements: 3.10_

  - [x] 6.5 Write unit tests for audit logging wrapper behaviour
    - Test that `log_action()` failure does not raise an exception in the route (primary operation must still complete)
    - Test `_serialize_value()` with dict, list, None, int, and string inputs
    - _Requirements: 3.9_

- [x] 7. Checkpoint — audit logging
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Category Management routes
  - [x] 8.1 Implement `GET /categories` — list all categories
    - Query: `SELECT c.id, c.name, COUNT(a.id) AS asset_count FROM categories c LEFT JOIN assets a ON a.category_id = c.id GROUP BY c.id, c.name ORDER BY c.name`
    - Render `categories.html` with `categories` list and `roles` is not needed here
    - Guard with `if 'user' not in session`
    - _Requirements: 4.1_

  - [x] 8.2 Implement `POST /categories/create` — create new category
    - Trim `name`; validate non-empty and ≤ 100 chars; re-render with `error` on failure
    - Duplicate check case-insensitively (excluding none); re-render with error if found
    - INSERT into `categories`; wrap `log_action(..., 'CREATE', 'category', cursor.lastrowid, new_value={'name': name})` in try/except
    - Redirect to `/categories`
    - _Requirements: 4.2, 4.3, 4.4, 4.5_

  - [x] 8.3 Implement `GET /categories/edit/<id>` and `POST /categories/edit/<id>` — edit category
    - GET: fetch category by id (flash + redirect if not found), render `edit_category.html`
    - POST: trim and validate name (non-empty, ≤ 100 chars); duplicate check excluding self: `WHERE LOWER(name)=LOWER(%s) AND id != %s`; UPDATE; `log_action(..., 'UPDATE', 'category', id, old_value={'name': old_name}, new_value={'name': new_name})`; redirect
    - _Requirements: 4.6, 4.7, 4.8, 4.11_

  - [x] 8.4 Implement `GET /categories/delete/<id>` — delete category with asset-count guard
    - Fetch category (flash + redirect if not found)
    - Count assets: `SELECT COUNT(*) FROM assets WHERE category_id = %s`; if count > 0, flash `f"Cannot delete: {count} asset(s) use this category."` and redirect
    - DELETE; `log_action(..., 'DELETE', 'category', id, old_value={'name': name})`; redirect
    - _Requirements: 4.9, 4.10, 4.11_

  - [x] 8.5 Create `templates/categories.html`
    - Extend `base.html`; table with `id`, `name`, `asset_count` and edit/delete buttons per row
    - Inline create form with name field
    - Display `error` flash/context message when present
    - _Requirements: 4.1, 4.12_

  - [x] 8.6 Create `templates/edit_category.html`
    - Extend `base.html`; form with name field pre-filled; display `error` when present
    - _Requirements: 4.6, 4.7, 4.8_

  - [x] 8.7 Write unit tests for category management validation
    - Test name trimming (spaces-only → invalid, leading/trailing spaces trimmed)
    - Test length boundary (100 chars valid, 101 chars invalid)
    - Test duplicate detection (case-insensitive, excluding self in edit)
    - Test asset-count guard (0 assets → allow delete, 1+ assets → reject)
    - _Requirements: 4.3, 4.4, 4.5, 4.7, 4.8, 4.9, 4.10_

- [x] 9. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- `session['user_id']` (task 1.1) is a prerequisite for all audit log calls — it must be implemented first
- The audit log calls in tasks 6.1–6.3 also apply to the new user and category routes created in tasks 2 and 8 — those route implementations already include the `log_action` calls
- All SQL uses parameterised queries (PyMySQL `%s` placeholders) — no string interpolation
- `bcrypt` is used for password hashing in user management; the existing Werkzeug `check_password_hash` in `login()` stays unchanged for backward compatibility with existing accounts
- The `generate_password_hash` import in `app.py` is currently unused and can be removed during task 2 cleanup

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "4.1", "6.4", "8.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "4.2", "6.1", "6.2", "6.3", "8.2", "8.3", "8.4"] },
    { "id": 3, "tasks": ["2.5", "2.6", "4.3", "6.5", "8.5", "8.6"] },
    { "id": 4, "tasks": ["2.7", "8.7"] }
  ]
}
```
