# Requirements Document

## Introduction

This document covers a set of enhancements to the existing IT Asset Management web application built with Flask, Jinja2 templates, and a MySQL database. The application currently supports asset tracking, intervention logging, basic reporting, and user authentication. These enhancements improve data retention, usability, security, and reporting capabilities without replacing the existing system.

## Glossary

- **Application**: The Flask-based IT Asset Management web application.
- **Asset**: A physical or virtual IT item (e.g., computer, monitor) tracked in the `assets` table with an `asset_tag`, `name`, `brand`, `model`, `status`, `purchase_date`, `warranty_expiration`, and `notes`.
- **Intervention**: A maintenance or support event recorded in the `interventions` table, linked to an Asset and a Technician, with a `description`, `intervention_date`, and `status`.
- **Technician**: A person responsible for carrying out Interventions, stored in the `technicians` table with `id` and `name`.
- **User**: An authenticated person who accesses the Application, stored in the `users` table with a hashed `password`.
- **Session**: A Flask server-side session that tracks the authenticated User.
- **Status**: A discrete state of an Asset — one of `Active`, `Inactive`, or `Maintenance`.
- **Intervention_Status**: A discrete state of an Intervention — one of `Pending` or `Completed`.
- **Dashboard**: The `/dashboard` page displaying summary statistics and quick actions.
- **Asset_Detail_Page**: A dedicated page at `/assets/<id>` showing all information for a single Asset.
- **Technician_Management_Page**: A dedicated page at `/technicians` for managing Technician records.
- **Reports_Page**: The `/reports` page showing export options and summary data.

---

## Requirements

### Requirement 1: Intervention History Preservation

**User Story:** As a technician, I want completed interventions to be saved with a "Completed" status rather than deleted, so that I can maintain a full history of what was done to each asset.

#### Acceptance Criteria

1. WHEN a new Intervention is created, THE Application SHALL assign it an `Intervention_Status` of `Pending` by default.
2. WHEN a User clicks "Done" on a Pending intervention, THE Application SHALL set that intervention's `Intervention_Status` to `Completed` and set the linked Asset's `Status` to `Active`.
3. WHEN a User clicks "Done" on a Pending intervention, THE Application SHALL NOT delete the intervention record.
4. WHEN the interventions page is loaded, THE Application SHALL display only `Pending` interventions in the active interventions table.
5. WHEN an Intervention's `Intervention_Status` is `Completed`, THE Application SHALL display that Intervention in a dedicated history table accessible from the interventions page or the Asset Detail Page.
6. IF a User requests deletion of an intervention record, THEN THE Application SHALL permanently remove that record from the database only after the User performs an explicit secondary confirmation step.

---

### Requirement 2: Asset Detail Page

**User Story:** As a user, I want to click on an asset and see all its information in one place, so that I can quickly review its history, warranty, and notes without navigating multiple pages.

#### Acceptance Criteria

1. THE Application SHALL provide an Asset Detail Page at `/assets/<id>` that displays the Asset's `asset_tag`, `name`, `brand`, `model`, `status`, `purchase_date`, `warranty_expiration`, `notes`, and `category`. WHERE any of these fields are null or empty, THE Application SHALL display a placeholder value such as "N/A" or "—" rather than leaving the cell blank.
2. WHEN a User clicks on an asset name or tag in the assets list, THE Application SHALL navigate to the Asset Detail Page for that Asset.
3. WHEN the Asset Detail Page is loaded for a given Asset, THE Application SHALL query the `interventions` table for all rows where `asset_id` matches that Asset's `id` and display the results ordered by `intervention_date` descending, showing each intervention's `description`, `intervention_date`, `technician_name`, and current `Intervention_Status`.
4. WHEN no interventions exist for the Asset, THE Application SHALL display a message such as "No intervention history available" in place of the interventions table.
5. IF the requested asset `id` does not exist in the database, THEN THE Application SHALL render the custom 404 page and return HTTP status 404.
6. IF a User is not authenticated, THEN THE Application SHALL redirect the User to the login page before rendering the Asset Detail Page.

---

### Requirement 3: Technician Management

**User Story:** As an administrator, I want a dedicated page to add, edit, and remove technicians, so that I do not need direct database access to manage technician records.

#### Acceptance Criteria

1. THE Application SHALL provide a Technician_Management_Page at `/technicians` listing all Technicians with their `id` and `name`. IF a User is not authenticated, THEN THE Application SHALL redirect the User to the login page.
2. WHEN a User submits a name that is non-empty after trimming whitespace and is at most 100 characters via the add-technician form, THE Application SHALL insert a new record into the `technicians` table and redirect to the Technician_Management_Page.
3. IF a User submits an empty name or a name that consists only of whitespace in the add-technician form, THEN THE Application SHALL display a validation error message and SHALL NOT insert the record.
4. WHEN a User submits a valid edited name (non-empty after trimming, at most 100 characters) for an existing Technician, THE Application SHALL update that Technician's `name` in the database, and the edit form SHALL be pre-populated with the Technician's current name before submission.
5. WHEN a User confirms deletion of a Technician, THE Application SHALL remove that Technician's record from the `technicians` table and redirect to the Technician_Management_Page.
6. IF a User attempts to delete a Technician who has one or more associated Intervention records, THEN THE Application SHALL display an error message and SHALL NOT delete the Technician record.
7. THE Application SHALL add a link to the Technician_Management_Page in the sidebar navigation under the "Operations" section.

---

### Requirement 4: Intervention Status Badges

**User Story:** As a user, I want status badges on the interventions table, so that I can visually distinguish between pending and completed interventions at a glance.

#### Acceptance Criteria

1. WHEN an intervention with `Intervention_Status` equal to `Pending` is displayed in a table row, THE Application SHALL render a badge using CSS classes `badge-status badge-pending` with the label "Pending".
2. WHEN an intervention with `Intervention_Status` equal to `Completed` is displayed in a table row, THE Application SHALL render a badge using CSS classes `badge-status badge-completed` with the label "Completed".
3. THE Application SHALL define `badge-pending` with a yellow background color and `badge-completed` with a green background color in the same stylesheet that defines `badge-active`, `badge-inactive`, and `badge-maintenance`, and the interventions table SHALL include a "Status" column to display these badges.
4. WHEN an intervention's `Intervention_Status` value is neither `Pending` nor `Completed`, THE Application SHALL render a neutral grey badge with the raw status value as its label.

---

### Requirement 5: Custom 404 Error Page

**User Story:** As a user, I want a styled 404 page, so that I see a consistent, branded error message instead of Flask's default error page when I navigate to a non-existent URL.

#### Acceptance Criteria

1. WHEN a request is made to a URL that does not match any registered route, THE Application SHALL respond with HTTP status 404 and render a custom `404.html` template.
2. THE custom 404 page SHALL extend `base.html`, SHALL display a page title of "404 – Page Not Found", SHALL include a visible message containing both the text "404" and "not found", and SHALL include a link with `href="/dashboard"` to return to the Dashboard.

---

### Requirement 6: Password Hashing

**User Story:** As a system administrator, I want passwords stored as hashes, so that plain-text credentials are not exposed if the database is compromised.

#### Acceptance Criteria

1. THE Application SHALL store User passwords as irreversible salted hashes in the `users` table, and the `password` column SHALL be at least 255 characters to accommodate the hash output.
2. WHEN a User attempts to log in, THE Application SHALL verify the submitted password against the stored hash using a constant-time comparison function; IF the submitted password does not match the stored hash, THEN THE Application SHALL reject the login, keep the Session unauthenticated, re-display the login form, and show an error message.
3. THE Application SHALL provide a one-time migration script that reads each row in the `users` table, checks whether the password value is already a recognizable hash, and if not, replaces the plain-text value with its hashed equivalent — ensuring the script is idempotent and safe to re-run.
4. THE migration script SHALL hash the existing `admin123` seed credential (or any other plain-text value present) so that no plain-text passwords remain in the `users` table after migration.

---

### Requirement 7: Session Timeout

**User Story:** As a security administrator, I want the application to automatically log out inactive users, so that unattended sessions cannot be exploited.

#### Acceptance Criteria

1. THE Application SHALL support a configurable session timeout duration, defaulting to 30 minutes, readable from an environment variable or application config key.
2. WHEN a User makes a request while authenticated, THE Application SHALL record the current timestamp as the User's last-activity time in the Session.
3. WHEN a User makes a request while authenticated and the elapsed time since the last-activity timestamp exceeds the configured timeout duration, THE Application SHALL clear the Session, and redirect the User to the login page with a message indicating the session expired.
4. THE Application SHALL mark the session as permanent and set `SESSION_COOKIE_HTTPONLY=True` and `SESSION_COOKIE_SAMESITE='Lax'` in the application configuration.

---

### Requirement 8: Dashboard Bar Chart

**User Story:** As a manager, I want a bar chart on the dashboard showing assets by status, so that I can visually assess the current state of the asset fleet at a glance.

#### Acceptance Criteria

1. WHEN the Dashboard page is loaded, THE Application SHALL render a bar chart with exactly three bars labeled `Active`, `Maintenance`, and `Inactive`, where each bar's height represents the count of Assets with that `Status`.
2. WHEN the Dashboard is loaded, THE Application SHALL query the database for the count of Assets per `Status` value and pass those counts to the template so the chart data is server-rendered and accurate at page load time.
3. THE bar chart SHALL color the `Active` bar with hex `#28a745`, the `Maintenance` bar with hex `#ffc107`, and the `Inactive` bar with hex `#dc3545`, matching the colors already used for Asset status badges in the application.
4. THE Application SHALL render the chart inside a `<canvas>` element and load the Chart.js library to produce the chart; IF Chart.js fails to load, the `<canvas>` element SHALL remain visible without throwing unhandled JavaScript errors.

---

### Requirement 9: Asset Table Client-Side Filters

**User Story:** As a user, I want to filter the assets table by status, category, or brand without reloading the page, so that I can quickly narrow down results during my workflow.

#### Acceptance Criteria

1. THE Application SHALL render a `status` dropdown filter, a `category` dropdown filter, and a `brand` dropdown filter above the assets table, each with a default option of "All".
2. WHEN a User selects a non-"All" value in any filter dropdown, THE Application SHALL immediately hide all table rows whose corresponding column value does not match the selected value, without issuing a new HTTP request.
3. WHEN a User resets a filter dropdown to "All", THE Application SHALL restore visibility for rows previously hidden by that filter alone, while rows hidden by other still-active filters or the search term remain hidden.
4. WHEN two or more filters or the search term are active simultaneously, THE Application SHALL display only rows that satisfy every active condition — the combined filter is a logical AND of all active constraints.
5. THE Application SHALL populate the `category` dropdown with the distinct category names present in the loaded assets data, and the `brand` dropdown with the distinct non-null brand values present in the loaded assets data, deriving both lists from the rendered table rows rather than issuing additional server requests.
6. WHEN all active filters and the search term together match no table rows, THE Application SHALL display a visible "no results" message in the table body in place of the hidden rows.
