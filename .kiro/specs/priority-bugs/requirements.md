# Requirements Document

## Introduction

This document covers four priority bug fixes for the IT Asset Management Flask application. The fixes address: a missing intervention history display, absent server-side validation when creating interventions, unguarded asset deletion that can orphan intervention records, and a hardcoded Flask secret key that poses a security risk. All changes are confined to the existing Flask/MySQL/Jinja2/Bootstrap 5 stack — no new frameworks are introduced.

---

## Glossary

- **Application**: The Flask IT Asset Management web application.
- **Intervention**: A maintenance record in the `interventions` table linking an asset to a technician, with a status of `'Active'` or `'Completed'`.
- **Active_Intervention**: An intervention whose `status` column equals `'Active'`.
- **Completed_Intervention**: An intervention whose `status` column equals `'Completed'`.
- **Asset**: A row in the `assets` table with a `status` of `'Active'`, `'Inactive'`, or `'Maintenance'`.
- **Inactive_Asset**: An asset whose `status` column equals `'Inactive'`.
- **History_Section**: A read-only HTML section on the `/interventions` page that lists Completed_Interventions below the active interventions table.
- **Validator**: The server-side Python logic inside the `add_intervention` route that checks asset eligibility before inserting a row.
- **Secret_Key**: The value assigned to `app.secret_key` used by Flask to sign session cookies.
- **Environment_Variable**: An OS-level variable resolved at runtime, separate from source code.
- **env_example_file**: A file named `.env.example` in the project root documenting required Environment_Variables without containing real secret values.

---

## Requirements

### Requirement 1: Display Completed Interventions in a History Section

**User Story:** As an IT manager, I want to see completed interventions on the interventions page, so that I have a full maintenance history without navigating away.

#### Acceptance Criteria

1. WHEN a user navigates to `/interventions`, THE Application SHALL query all interventions whose `status` equals `'Completed'` and pass them to the template as a separate list distinct from the active interventions list.

2. WHEN the `/interventions` page renders and at least one Completed_Intervention exists, THE Application SHALL display a "History" section below the active interventions table containing a read-only HTML table with columns: Asset, Technician, Description, Date, and Status.

3. WHEN the `/interventions` page renders and no Completed_Interventions exist, THE Application SHALL display a placeholder message inside the History_Section indicating that no completed interventions are recorded.

4. WHILE a user views the History_Section, THE Application SHALL render each Completed_Intervention row without action buttons (no "Complete" link and no "Delete" button).

5. WHEN an intervention is marked complete via `/interventions/complete/<id>`, THE Application SHALL set `status = 'Completed'` in the database and redirect to `/interventions`, where that intervention immediately appears in the History_Section on the next page load.

---

### Requirement 2: Server-Side Validation of Asset Status on Intervention Creation

**User Story:** As a system administrator, I want the server to validate the asset's status before creating an intervention, so that the data integrity of the system is preserved even when requests are made outside the UI.

#### Acceptance Criteria

1. WHEN a POST request is received at `/interventions/add`, THE Validator SHALL query the `assets` table for a row matching the submitted `asset_id` before executing any `INSERT` statement.

2. IF the submitted `asset_id` does not correspond to an existing row in the `assets` table, THEN THE Validator SHALL abort the insert, flash an error message reading "Asset not found.", return an HTTP 404 status code, and redirect the request to `/interventions`.

3. IF the asset corresponding to the submitted `asset_id` has a `status` that is not `'Inactive'` (including assets with `status = 'Maintenance'`), THEN THE Validator SHALL abort the insert, flash an error message reading "Asset is not available for intervention.", return an HTTP 400 status code, and redirect the request to `/interventions`.

4. WHEN the asset validation passes (asset exists and `status = 'Inactive'`), THE Application SHALL proceed to insert the intervention record and update the asset's `status` to `'Maintenance'` as before.

5. WHEN a flash error message is set by THE Validator, THE Application SHALL display that message on the `/interventions` page using the existing Bootstrap alert pattern in the template.

---

### Requirement 3: Guard Asset Deletion When Intervention Records Exist

**User Story:** As an IT manager, I want the system to prevent me from deleting an asset that has intervention history, so that I do not accidentally lose maintenance records.

#### Acceptance Criteria

1. WHEN a GET request is received at `/delete-asset/<id>`, THE Application SHALL query the `interventions` table for any rows where `asset_id` equals the given `id` before executing any `DELETE` statement.

2. IF one or more intervention records exist for the asset being deleted, THEN THE Application SHALL abort the delete operation, flash an error message reading "Cannot delete asset: intervention records exist. Delete the interventions first.", and redirect to `/assets`.

3. WHEN no intervention records exist for the asset being deleted, THE Application SHALL execute `DELETE FROM assets WHERE id = %s` as before and redirect to `/assets`.

4. WHEN the deletion is blocked by THE Application, THE Application SHALL display the flash error message on the `/assets` page using the existing Bootstrap alert pattern in the template. THE Application SHALL NOT display any flash message when an asset is deleted successfully.

---

### Requirement 4: Load Flask Secret Key from Environment Variable

**User Story:** As a developer, I want the Flask secret key to be loaded from an environment variable, so that the production secret is never committed to source control.

#### Acceptance Criteria

1. THE Application SHALL read the Secret_Key from the `SECRET_KEY` Environment_Variable at startup using `os.environ.get('SECRET_KEY')`.

2. IF the `SECRET_KEY` Environment_Variable is not set, THEN THE Application SHALL fall back to a hardcoded development default value and SHALL NOT raise an exception during startup.

3. THE Application SHALL assign the resolved Secret_Key to `app.secret_key` before any request is handled, replacing the current hardcoded string `"evolve_secret_key"`.

4. THE Application SHALL include `import os` (or use `os.environ`) at the top of `app.py` to resolve the Environment_Variable.

5. THE Application SHALL include an env_example_file at the project root containing at minimum the entry `SECRET_KEY=your-secret-key-here` with no real secret values.

6. WHERE the env_example_file is present, THE Application SHALL NOT include the env_example_file in `.gitignore`, but any real `.env` file containing actual secret values SHALL be listed in `.gitignore`.
