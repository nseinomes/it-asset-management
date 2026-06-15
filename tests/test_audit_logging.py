"""
Unit and property-based tests for audit logging wrapper behaviour.

Tests cover:
- log_action() failure isolation: a DB error returns False and does not raise
- _serialize_value() correctness across all supported input types
- Property: for any dict with string keys and mixed values, _serialize_value
  always returns a JSON-parseable string

Validates: Requirements 3.9
"""

import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

# Ensure project root is on sys.path so app_utils can be imported directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app_utils import log_action, _serialize_value


# ---------------------------------------------------------------------------
# Unit tests: _serialize_value
# ---------------------------------------------------------------------------

class TestSerializeValue(unittest.TestCase):
    """Example-based tests for _serialize_value with each supported type."""

    def test_none_returns_none(self):
        """None input must return None (not the string 'null')."""
        result = _serialize_value(None)
        assert result is None, f"Expected None, got {result!r}"

    def test_dict_returns_json_string(self):
        """A dict must be serialized to a JSON string."""
        value = {"name": "Laptop", "status": "Active"}
        result = _serialize_value(value)
        assert isinstance(result, str), f"Expected str, got {type(result)}"
        parsed = json.loads(result)
        assert parsed == value, f"Parsed JSON {parsed!r} != original {value!r}"

    def test_list_returns_json_string(self):
        """A list must be serialized to a JSON string."""
        value = [1, "two", {"three": 3}]
        result = _serialize_value(value)
        assert isinstance(result, str), f"Expected str, got {type(result)}"
        parsed = json.loads(result)
        assert parsed == value, f"Parsed JSON {parsed!r} != original {value!r}"

    def test_int_returns_string(self):
        """An int must return its string representation."""
        result = _serialize_value(42)
        assert result == "42", f"Expected '42', got {result!r}"

    def test_int_zero_returns_string(self):
        """Zero must return the string '0'."""
        result = _serialize_value(0)
        assert result == "0", f"Expected '0', got {result!r}"

    def test_string_returns_string_unchanged(self):
        """A string must be returned as-is (str(value) of a str is the same str)."""
        value = "hello world"
        result = _serialize_value(value)
        assert result == value, f"Expected {value!r}, got {result!r}"

    def test_empty_dict_returns_json_string(self):
        """An empty dict must be serialized to '{}'."""
        result = _serialize_value({})
        assert result == "{}", f"Expected '{{}}', got {result!r}"

    def test_empty_list_returns_json_string(self):
        """An empty list must be serialized to '[]'."""
        result = _serialize_value([])
        assert result == "[]", f"Expected '[]', got {result!r}"

    def test_empty_string_returns_empty_string(self):
        """An empty string must return an empty string."""
        result = _serialize_value("")
        assert result == "", f"Expected '', got {result!r}"


# ---------------------------------------------------------------------------
# Unit tests: log_action() failure isolation (Requirement 3.9)
# ---------------------------------------------------------------------------

class TestLogActionFailureIsolation(unittest.TestCase):
    """
    Verify that log_action() absorbs all internal errors and never propagates
    an exception to the caller, so the primary operation is never disrupted.

    Validates: Requirement 3.9
    """

    def test_db_connection_failure_returns_false(self):
        """When get_connection() raises, log_action must return False, not raise."""
        with patch("app_utils.get_connection", side_effect=Exception("DB unavailable")):
            result = log_action(1, "CREATE", "asset", 99, new_value={"name": "X"})
        assert result is False, (
            f"Expected False when DB connection fails, got {result!r}"
        )

    def test_db_execute_failure_returns_false(self):
        """When cursor.execute() raises, log_action must return False, not raise."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Query error")

        with patch("app_utils.get_connection", return_value=mock_conn):
            result = log_action(1, "UPDATE", "asset", 5,
                                old_value={"status": "Active"},
                                new_value={"status": "Inactive"})
        assert result is False, (
            f"Expected False when cursor.execute() fails, got {result!r}"
        )

    def test_db_commit_failure_returns_false(self):
        """When conn.commit() raises, log_action must return False, not raise."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.commit.side_effect = Exception("Commit failed")

        with patch("app_utils.get_connection", return_value=mock_conn):
            result = log_action(2, "DELETE", "intervention", 7,
                                old_value={"id": 7})
        assert result is False, (
            f"Expected False when conn.commit() fails, got {result!r}"
        )

    def test_failure_does_not_raise_any_exception(self):
        """log_action must never raise, regardless of the internal error type."""
        errors = [
            RuntimeError("runtime"),
            ValueError("value"),
            OSError("os"),
            MemoryError("oom"),
        ]
        for exc in errors:
            with patch("app_utils.get_connection", side_effect=exc):
                try:
                    log_action(1, "CREATE", "user", 1)
                except Exception as raised:
                    self.fail(
                        f"log_action raised {type(raised).__name__} "
                        f"for internal {type(exc).__name__}: {raised}"
                    )

    def test_success_returns_true(self):
        """When everything works, log_action must return True."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("app_utils.get_connection", return_value=mock_conn):
            result = log_action(1, "CREATE", "asset", 10, new_value={"name": "Laptop"})
        assert result is True, f"Expected True on success, got {result!r}"


# ---------------------------------------------------------------------------
# Property-based test: _serialize_value on dicts
# Validates: Requirements 3.9 (audit serialisation property from design.md)
# ---------------------------------------------------------------------------

# Build a strategy for mixed-value dicts with string keys
_mixed_value = st.one_of(
    st.none(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.booleans(),
    st.text(max_size=50),
    st.lists(st.integers(), max_size=5),
)

_string_keyed_dict = st.dictionaries(
    keys=st.text(min_size=1, max_size=30),
    values=_mixed_value,
    max_size=10,
)


@settings(max_examples=200, deadline=None)
@given(d=_string_keyed_dict)
def test_serialize_value_dict_always_json_parseable(d):
    """
    **Validates: Requirements 3.9**

    Property: For any dict with string keys and mixed values,
    _serialize_value(d) always returns a JSON-parseable string.
    This ensures audit log storage is always valid JSON for dict values.
    """
    result = _serialize_value(d)

    assert isinstance(result, str), (
        f"_serialize_value({d!r}) returned {type(result).__name__}, expected str"
    )

    try:
        parsed = json.loads(result)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"_serialize_value({d!r}) returned non-JSON string {result!r}: {e}"
        )

    # The parsed result should be a dict (not some other JSON type)
    assert isinstance(parsed, dict), (
        f"_serialize_value({d!r}) parsed to {type(parsed).__name__}, expected dict"
    )


if __name__ == "__main__":
    unittest.main()
