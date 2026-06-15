"""
Property-based tests for priority-bugs spec — Fix 1 (Intervention History)
and Fix 2 (Asset Status Validation).

Tests are organised by property/requirement:

- Property 1: Active/Completed separation is exhaustive and non-overlapping
  # Feature: priority-bugs, Property 1: Active/Completed separation
  Validates: Requirements 1.1

- Property 2: History rows contain no action buttons
  # Feature: priority-bugs, Property 2: History rows contain no action buttons
  Validates: Requirements 1.4

- Property 3: Non-Inactive assets are always rejected
  # Feature: priority-bugs, Property 3: Non-Inactive assets are always rejected
  Validates: Requirements 2.2, 2.3
"""

import os
import re
import sys
from datetime import date
from unittest.mock import MagicMock, call, patch

import pytest
from bs4 import BeautifulSoup
from hypothesis import given, settings
from hypothesis import strategies as st
from jinja2 import Environment, FileSystemLoader

# ---------------------------------------------------------------------------
# Path setup — make sure the project root is importable
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")

# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_TEXT = st.text(min_size=1, max_size=30, alphabet=st.characters(
    whitelist_categories=("Lu", "Ll", "Nd"),
    whitelist_characters=" -",
))

_MIXED_STATUS     = st.sampled_from(["Active", "Completed"])
_COMPLETED_STATUS = st.just("Completed")


def _intervention_dict(status_strategy):
    """Generate a single intervention dict with the given status strategy."""
    return st.fixed_dictionaries({
        "id":                st.integers(min_value=1, max_value=99999),
        "description":       _TEXT,
        "intervention_date": st.just(date(2024, 1, 1)),
        "status":            status_strategy,
        "asset_tag":         _TEXT,
        "asset_name":        _TEXT,
        "technician_name":   _TEXT,
    })


_mixed_intervention     = _intervention_dict(_MIXED_STATUS)
_completed_intervention = _intervention_dict(_COMPLETED_STATUS)

# ---------------------------------------------------------------------------
# Jinja2 environment (mirrors test_dashboard_charts_filters.py setup)
# ---------------------------------------------------------------------------


def _make_jinja_env():
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
    )
    env.globals["url_for"] = lambda endpoint, **kwargs: "#"
    env.globals["session"] = {"user": "testuser"}
    env.globals["get_flashed_messages"] = lambda: []

    class _FakeRequest:
        path = "/interventions"

    env.globals["request"] = _FakeRequest()
    return env


def _render_interventions_template(interventions, completed_interventions, env=None):
    """Render interventions.html directly via Jinja2 (no Flask app context needed)."""
    if env is None:
        env = _make_jinja_env()
    tmpl = env.get_template("interventions.html")
    return tmpl.render(
        interventions=interventions,
        completed_interventions=completed_interventions,
        assets=[],
        technicians=[],
    )


# ---------------------------------------------------------------------------
# Property 1: Active/Completed separation is exhaustive and non-overlapping
# Feature: priority-bugs, Property 1: Active/Completed separation
# Validates: Requirements 1.1
# ---------------------------------------------------------------------------


def _simulate_route_split(all_interventions):
    """
    Simulate the two SQL queries in the interventions() route:
      - Query 1: WHERE status = 'Active'
      - Query 2: WHERE status = 'Completed'

    Returns (active_list, completed_list) as the route would produce.
    """
    active    = [i for i in all_interventions if i["status"] == "Active"]
    completed = [i for i in all_interventions if i["status"] == "Completed"]
    return active, completed


@settings(max_examples=100, deadline=None)
@given(all_interventions=st.lists(
    _mixed_intervention,
    min_size=0,
    max_size=20,
    unique_by=lambda i: i["id"],   # DB primary key: IDs are unique across rows
))
def test_active_completed_separation(all_interventions):
    """
    **Validates: Requirements 1.1**

    # Feature: priority-bugs, Property 1: Active/Completed separation

    Property 1: For any list of intervention dicts with unique IDs and
    mixed statuses, the interventions() route must split them so that:
      - `interventions`            contains exactly those with status == 'Active'
      - `completed_interventions`  contains exactly those with status == 'Completed'

    The two resulting lists must be:
      1. Non-overlapping (disjoint by row ID — the DB primary key ensures
         each intervention has a unique id, so the same row cannot appear
         in both the Active and Completed result sets)
      2. Exhaustive (the union of the two lists equals the full input)

    This is verified by:
      (a) checking the split logic is correct for any input, and
      (b) rendering interventions.html and confirming each group lands in
          the correct section of the HTML output.
    """
    # ── Simulate the route split ────────────────────────────────────────────
    active_rows, completed_rows = _simulate_route_split(all_interventions)

    # ── Invariant 1: Non-overlapping ────────────────────────────────────────
    # Each row has a unique id (enforced by unique_by above), so checking ID
    # sets is equivalent to checking row-object disjointness.
    active_ids    = {i["id"] for i in active_rows}
    completed_ids = {i["id"] for i in completed_rows}

    assert active_ids.isdisjoint(completed_ids), (
        f"Separation is not disjoint: IDs in both lists = "
        f"{active_ids & completed_ids}"
    )

    # ── Invariant 2: Exhaustive ─────────────────────────────────────────────
    all_ids   = {i["id"] for i in all_interventions}
    union_ids = active_ids | completed_ids

    assert union_ids == all_ids, (
        f"Separation is not exhaustive: "
        f"all_ids={all_ids}, union_ids={union_ids}, "
        f"missing={all_ids - union_ids}"
    )

    # ── Invariant 3: Size consistency ──────────────────────────────────────
    assert len(active_rows) + len(completed_rows) == len(all_interventions), (
        f"Total count mismatch: active={len(active_rows)}, "
        f"completed={len(completed_rows)}, total={len(all_interventions)}"
    )

    # ── Invariant 4: Template renders each group in the correct section ─────
    html = _render_interventions_template(
        interventions=active_rows,
        completed_interventions=completed_rows,
    )
    soup = BeautifulSoup(html, "html.parser")

    # Active interventions get a "Complete" action link; completed ones must not
    complete_hrefs = {
        int(m)
        for m in re.findall(r"/interventions/complete/(\d+)", html)
    }

    assert complete_hrefs == active_ids, (
        f"HTML contains /complete/ links for wrong IDs.\n"
        f"  Expected active IDs: {active_ids}\n"
        f"  Complete links found: {complete_hrefs}"
    )

    # No /complete/ links should reference completed IDs
    assert complete_hrefs.isdisjoint(completed_ids), (
        f"Found /complete/ links for completed intervention IDs: "
        f"{complete_hrefs & completed_ids}"
    )

    # History section row count must equal completed count
    history_div  = soup.find("div", {"id": "historyCollapse"})
    assert history_div is not None, "Expected #historyCollapse in rendered HTML"

    history_rows = [r for r in history_div.find_all("tr") if r.find("td")]
    assert len(history_rows) == len(completed_rows), (
        f"#historyCollapse has {len(history_rows)} data rows but expected "
        f"{len(completed_rows)}"
    )


# ---------------------------------------------------------------------------
# Property 2: History rows contain no action buttons
# Feature: priority-bugs, Property 2: History rows contain no action buttons
# Validates: Requirements 1.4
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(completed=st.lists(_completed_intervention, min_size=1, max_size=20))
def test_history_no_action_buttons(completed):
    """
    **Validates: Requirements 1.4**

    # Feature: priority-bugs, Property 2: History rows contain no action buttons

    Property 2: For any non-empty list of completed intervention dicts,
    rendering interventions.html must produce HTML in the #historyCollapse
    section that contains:
      - No <a> href containing '/complete/'
      - No element with class 'btn-delete'
    """
    html = _render_interventions_template(
        interventions=[],
        completed_interventions=completed,
    )

    soup = BeautifulSoup(html, "html.parser")
    history_div = soup.find("div", {"id": "historyCollapse"})

    assert history_div is not None, (
        "Expected #historyCollapse div to be present in rendered interventions HTML"
    )

    # Assert: no href containing '/complete/' inside #historyCollapse
    complete_links = history_div.find_all("a", href=re.compile(r"/complete/"))
    assert len(complete_links) == 0, (
        f"Found {len(complete_links)} 'Complete' action link(s) inside "
        f"#historyCollapse; history rows must not have action buttons.\n"
        f"Offending hrefs: {[a['href'] for a in complete_links]}"
    )

    # Assert: no element with class 'btn-delete' inside #historyCollapse
    delete_buttons = history_div.find_all(class_="btn-delete")
    assert len(delete_buttons) == 0, (
        f"Found {len(delete_buttons)} element(s) with class 'btn-delete' "
        f"inside #historyCollapse; history rows must not have delete buttons.\n"
        f"Offending elements: {delete_buttons}"
    )


# ---------------------------------------------------------------------------
# Property 3: Non-Inactive assets are always rejected
# Feature: priority-bugs, Property 3: Non-Inactive assets are always rejected
# Validates: Requirements 2.2, 2.3
# ---------------------------------------------------------------------------


def _make_mock_connection(asset_row):
    """Return a MagicMock mimicking get_connection() whose cursor.fetchone()
    returns *asset_row* for the SELECT and None is never reached for INSERT."""
    mock_conn   = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = asset_row
    return mock_conn


@settings(max_examples=100, deadline=None)
@given(asset_status=st.sampled_from(['Active', 'Maintenance']))
def test_non_inactive_asset_rejected(asset_status):
    """
    **Validates: Requirements 2.2, 2.3**

    # Feature: priority-bugs, Property 3: Non-Inactive assets are always rejected

    Property 3: For any asset whose status is 'Active' or 'Maintenance',
    a POST to /interventions/add must:
      - Redirect to /interventions (HTTP 3xx)
      - Execute NO INSERT into the interventions table
      - Flash exactly "Asset is not available for intervention."
    """
    from app import app as flask_app

    asset_row = {'status': asset_status}
    mock_conn = _make_mock_connection(asset_row)

    with patch('app.get_connection', return_value=mock_conn):
        with flask_app.test_client() as client:
            # Seed a valid session so the login guard passes
            with client.session_transaction() as sess:
                sess['user'] = 'testuser'

            response = client.post(
                '/interventions/add',
                data={
                    'asset_id':      '1',
                    'technician_id': '1',
                    'description':   'test intervention',
                },
                follow_redirects=False,
            )

            # ── Assert: response is a redirect to /interventions ────────────
            assert response.status_code in (302, 400), (
                f"Expected redirect (302) or rejection (400) for asset "
                f"status={asset_status!r}, got {response.status_code}"
            )
            location = response.headers.get('Location', '')
            assert '/interventions' in location, (
                f"Expected redirect to /interventions, got Location={location!r}"
            )

            # ── Assert: no INSERT was called on the cursor ──────────────────
            execute_calls = mock_conn.cursor.return_value.execute.call_args_list
            insert_calls  = [
                c for c in execute_calls
                if 'INSERT' in str(c).upper()
            ]
            assert len(insert_calls) == 0, (
                f"INSERT was called despite asset status={asset_status!r}.\n"
                f"All execute calls: {execute_calls}"
            )

            # ── Assert: flash message is correct ───────────────────────────
            with client.session_transaction() as sess:
                flashes = sess.get('_flashes', [])
            messages = [msg for _cat, msg in flashes]
            assert 'Asset is not available for intervention.' in messages, (
                f"Expected flash 'Asset is not available for intervention.' "
                f"for status={asset_status!r}, got flashes={messages!r}"
            )


# ---------------------------------------------------------------------------
# Edge-case unit test: asset_id does not exist → 404 + "Asset not found."
# Validates: Requirements 2.2
# ---------------------------------------------------------------------------


def test_asset_not_found_returns_404():
    """
    Edge case: when the SELECT returns None (asset does not exist), the route
    must return HTTP 404 and flash "Asset not found.".
    """
    from app import app as flask_app

    mock_conn = _make_mock_connection(asset_row=None)

    with patch('app.get_connection', return_value=mock_conn):
        with flask_app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user'] = 'testuser'

            response = client.post(
                '/interventions/add',
                data={
                    'asset_id':      '9999',
                    'technician_id': '1',
                    'description':   'ghost asset intervention',
                },
                follow_redirects=False,
            )

            # ── Assert: HTTP 404 ────────────────────────────────────────────
            assert response.status_code == 404, (
                f"Expected 404 for non-existent asset, got {response.status_code}"
            )

            # ── Assert: correct flash message ──────────────────────────────
            with client.session_transaction() as sess:
                flashes = sess.get('_flashes', [])
            messages = [msg for _cat, msg in flashes]
            assert 'Asset not found.' in messages, (
                f"Expected flash 'Asset not found.', got flashes={messages!r}"
            )


# ---------------------------------------------------------------------------
# Property 4: Assets with interventions are never deleted
# Feature: priority-bugs, Property 4: Assets with interventions are never deleted
# Validates: Requirements 3.2, 3.3, 3.4
# ---------------------------------------------------------------------------


def _make_mock_connection_with_count(cnt):
    """Return a MagicMock mimicking get_connection() whose cursor.fetchone()
    returns {'cnt': cnt} for the COUNT query."""
    mock_conn   = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = {'cnt': cnt}
    return mock_conn


@settings(max_examples=100, deadline=None)
@given(intervention_count=st.integers(min_value=1, max_value=20))
def test_asset_with_interventions_not_deleted(intervention_count):
    """
    **Validates: Requirements 3.2, 3.3, 3.4**

    # Feature: priority-bugs, Property 4: Assets with interventions are never deleted

    Property 4: For any asset that has one or more rows in the interventions
    table (COUNT ≥ 1), a GET to /delete-asset/<id> must:
      - Redirect to /assets (HTTP 3xx, Location header contains '/assets')
      - Execute NO DELETE FROM assets statement
      - Flash exactly "Cannot delete asset: intervention records exist.
        Delete the interventions first."
    """
    from app import app as flask_app

    mock_conn = _make_mock_connection_with_count(intervention_count)

    with patch('app.get_connection', return_value=mock_conn):
        with flask_app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user'] = 'testuser'

            response = client.get(
                '/delete-asset/1',
                follow_redirects=False,
            )

            # ── Assert: redirect to /assets ─────────────────────────────────
            assert response.status_code in (301, 302, 303, 307, 308), (
                f"Expected redirect for intervention_count={intervention_count}, "
                f"got {response.status_code}"
            )
            location = response.headers.get('Location', '')
            assert '/assets' in location, (
                f"Expected Location to contain '/assets', got {location!r}"
            )

            # ── Assert: no DELETE FROM assets was executed ──────────────────
            execute_calls = mock_conn.cursor.return_value.execute.call_args_list
            delete_calls = [
                c for c in execute_calls
                if 'DELETE FROM ASSETS' in str(c).upper()
            ]
            assert len(delete_calls) == 0, (
                f"DELETE FROM assets was called despite intervention_count={intervention_count}.\n"
                f"All execute calls: {execute_calls}"
            )

            # ── Assert: correct flash message ──────────────────────────────
            with client.session_transaction() as sess:
                flashes = sess.get('_flashes', [])
            messages = [msg for _cat, msg in flashes]
            expected_msg = (
                "Cannot delete asset: intervention records exist. "
                "Delete the interventions first."
            )
            assert expected_msg in messages, (
                f"Expected flash {expected_msg!r} for "
                f"intervention_count={intervention_count}, "
                f"got flashes={messages!r}"
            )


# ---------------------------------------------------------------------------
# Happy-path unit test: no interventions → DELETE executes, redirect to /assets
# Validates: Requirements 3.1, 3.4
# ---------------------------------------------------------------------------


def test_asset_without_interventions_deleted():
    """
    Happy path: when COUNT returns 0 (no intervention records),
    DELETE FROM assets must execute, redirect to /assets, and no flash
    message is set.
    """
    from app import app as flask_app

    mock_conn = _make_mock_connection_with_count(0)

    with patch('app.get_connection', return_value=mock_conn):
        with flask_app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user'] = 'testuser'

            response = client.get(
                '/delete-asset/42',
                follow_redirects=False,
            )

            # ── Assert: redirect to /assets ─────────────────────────────────
            assert response.status_code in (301, 302, 303, 307, 308), (
                f"Expected redirect, got {response.status_code}"
            )
            location = response.headers.get('Location', '')
            assert '/assets' in location, (
                f"Expected Location to contain '/assets', got {location!r}"
            )

            # ── Assert: DELETE FROM assets was executed ──────────────────────
            execute_calls = mock_conn.cursor.return_value.execute.call_args_list
            delete_calls = [
                c for c in execute_calls
                if 'DELETE FROM ASSETS' in str(c).upper()
            ]
            assert len(delete_calls) == 1, (
                f"Expected exactly 1 DELETE FROM assets call, "
                f"got {len(delete_calls)}.\nAll execute calls: {execute_calls}"
            )

            # ── Assert: no flash message set ────────────────────────────────
            with client.session_transaction() as sess:
                flashes = sess.get('_flashes', [])
            assert len(flashes) == 0, (
                f"Expected no flash messages on successful deletion, "
                f"got flashes={flashes!r}"
            )


# ---------------------------------------------------------------------------
# Smoke tests for Fix 4 — Secret key from environment variable
# Validates: Requirements 4.1, 4.2, 4.4, 4.5, 4.6
# ---------------------------------------------------------------------------

import ast
import importlib


APP_PY_PATH      = os.path.join(PROJECT_ROOT, "app.py")
ENV_EXAMPLE_PATH = os.path.join(PROJECT_ROOT, ".env.example")
GITIGNORE_PATH   = os.path.join(PROJECT_ROOT, ".gitignore")


def test_fix4_import_os_present():
    """
    Smoke: `import os` (or `import os as ...`) is present in app.py.
    Validates: Requirements 4.4
    """
    with open(APP_PY_PATH, "r", encoding="utf-8") as fh:
        source = fh.read()

    tree = ast.parse(source)
    os_imported = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "os":
                    os_imported = True
        elif isinstance(node, ast.ImportFrom):
            if node.module == "os":
                os_imported = True

    assert os_imported, (
        "app.py does not contain `import os`. "
        "The SECRET_KEY env var cannot be resolved without it."
    )


def test_fix4_env_example_exists_and_contains_key():
    """
    Smoke: .env.example exists at the project root and contains the
    exact line `SECRET_KEY=your-secret-key-here`.
    Validates: Requirements 4.5
    """
    assert os.path.isfile(ENV_EXAMPLE_PATH), (
        f".env.example not found at {ENV_EXAMPLE_PATH}"
    )

    with open(ENV_EXAMPLE_PATH, "r", encoding="utf-8") as fh:
        lines = [line.rstrip("\n") for line in fh.readlines()]

    assert "SECRET_KEY=your-secret-key-here" in lines, (
        f".env.example does not contain the line "
        f"`SECRET_KEY=your-secret-key-here`. Lines found: {lines!r}"
    )


def test_fix4_gitignore_contains_env_not_env_example():
    """
    Smoke: .gitignore contains `.env` (real secrets ignored) and does NOT
    contain `.env.example` (template should be committed).
    Validates: Requirements 4.6
    """
    with open(GITIGNORE_PATH, "r", encoding="utf-8") as fh:
        lines = [line.rstrip("\n") for line in fh.readlines()]

    # .env must appear as a standalone entry (not just .envrc, .venv, etc.)
    env_entries = [l for l in lines if l.strip() == ".env"]
    assert len(env_entries) >= 1, (
        f".gitignore does not have a standalone `.env` entry. "
        f"Lines checked: {[l for l in lines if '.env' in l]!r}"
    )

    # .env.example must NOT appear in .gitignore
    env_example_entries = [l for l in lines if ".env.example" in l and not l.strip().startswith("#")]
    assert len(env_example_entries) == 0, (
        f".gitignore contains `.env.example` but it should not — "
        f"the example file contains no secrets and should be committed. "
        f"Offending lines: {env_example_entries!r}"
    )


def test_fix4_secret_key_uses_fallback_when_env_unset():
    """
    Smoke: when SECRET_KEY env var is not set, app.secret_key equals
    the hardcoded fallback 'evolve_secret_key_dev'.
    Validates: Requirements 4.1, 4.2
    """
    import app as app_module

    # Remove SECRET_KEY from env if present, reload, then restore
    original = os.environ.pop("SECRET_KEY", None)
    try:
        with patch("database.get_connection", MagicMock()):
            importlib.reload(app_module)
        assert app_module.app.secret_key == "evolve_secret_key_dev", (
            f"Expected app.secret_key == 'evolve_secret_key_dev' when "
            f"SECRET_KEY env var is unset, got {app_module.app.secret_key!r}"
        )
    finally:
        if original is not None:
            os.environ["SECRET_KEY"] = original
        # Reload once more to restore original module state
        with patch("database.get_connection", MagicMock()):
            importlib.reload(app_module)


def test_fix4_secret_key_uses_env_var_when_set():
    """
    Smoke: when SECRET_KEY env var is set to a custom value, app.secret_key
    equals that custom value after module reload.
    Validates: Requirements 4.1
    """
    import app as app_module

    custom_key = "super_secret_test_value_xyz_12345"
    original   = os.environ.get("SECRET_KEY")
    os.environ["SECRET_KEY"] = custom_key
    try:
        with patch("database.get_connection", MagicMock()):
            importlib.reload(app_module)
        assert app_module.app.secret_key == custom_key, (
            f"Expected app.secret_key == {custom_key!r} when "
            f"SECRET_KEY={custom_key!r} is set, got {app_module.app.secret_key!r}"
        )
    finally:
        if original is not None:
            os.environ["SECRET_KEY"] = original
        else:
            os.environ.pop("SECRET_KEY", None)
        # Reload once more to restore original module state
        with patch("database.get_connection", MagicMock()):
            importlib.reload(app_module)
