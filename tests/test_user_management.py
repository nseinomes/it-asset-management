"""
Unit and property-based tests for user management validation — task 2.7.

Covers pure validation logic matching the /users routes in app.py:
  - validate_username(username) → (bool, str|None)
  - validate_password(password) → (bool, str|None)
  - is_duplicate_username(candidate, existing_usernames) → bool
  - is_self_delete(target_username, session_username) → bool

Tests are organised by requirement:
  - Requirements 1.2, 1.4 : username length (1–50 chars after strip)
  - Requirements 1.2, 1.4 : password length (≥ 8 chars)
  - Requirements 1.3      : duplicate username detection (case-insensitive)
  - Requirements 1.7, 1.8 : self-delete guard
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Pure validation helpers — mirror the logic in app.py create_user / delete_user
# (design.md § Feature 1 — Route POST /users/create, Route GET /users/delete/<id>)
# ---------------------------------------------------------------------------

def validate_username(username: str) -> tuple[bool, str | None]:
    """
    Returns (True, None) when valid; (False, error_message) when invalid.
    Rule: non-empty, between 1 and 50 characters after stripping whitespace.
    """
    stripped = username.strip()
    if not stripped:
        return False, "Username must be between 1 and 50 characters."
    if len(stripped) > 50:
        return False, "Username must be between 1 and 50 characters."
    return True, None


def validate_password(password: str) -> tuple[bool, str | None]:
    """
    Returns (True, None) when valid; (False, error_message) when invalid.
    Rule: at least 8 characters.
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    return True, None


def is_duplicate_username(candidate: str, existing_usernames: list[str]) -> bool:
    """
    Returns True if candidate matches any name in existing_usernames
    using a case-insensitive comparison (mirrors LOWER(username) = LOWER(%s)).
    """
    candidate_lower = candidate.lower()
    return any(name.lower() == candidate_lower for name in existing_usernames)


def is_self_delete(target_username: str, session_username: str) -> bool:
    """
    Returns True when target_username matches the session user (case-insensitive),
    meaning the delete should be rejected.
    """
    return target_username.lower() == session_username.lower()


# ---------------------------------------------------------------------------
# Example-based unit tests
# ---------------------------------------------------------------------------

# ── Requirements 1.2, 1.4 : username length boundaries ──────────────────────

class TestUsernameValidation:
    """Validates: Requirements 1.2, 1.4"""

    def test_empty_username_is_invalid(self):
        """Empty string must be rejected."""
        valid, error = validate_username("")
        assert valid is False
        assert error is not None

    def test_whitespace_only_username_is_invalid(self):
        """A username of only spaces is empty after strip — must be rejected."""
        valid, error = validate_username("   ")
        assert valid is False
        assert error is not None

    def test_single_char_username_is_valid(self):
        """1 character is the minimum valid length."""
        valid, error = validate_username("a")
        assert valid is True
        assert error is None

    def test_50_char_username_is_valid(self):
        """50 characters is exactly the maximum — must be accepted."""
        valid, error = validate_username("a" * 50)
        assert valid is True
        assert error is None

    def test_51_char_username_is_invalid(self):
        """51 characters exceeds the maximum — must be rejected."""
        valid, error = validate_username("a" * 51)
        assert valid is False
        assert error is not None

    def test_typical_username_is_valid(self):
        """A realistic username like 'admin' must be valid."""
        valid, error = validate_username("admin")
        assert valid is True
        assert error is None

    def test_leading_trailing_spaces_trimmed(self):
        """Username with surrounding spaces must be valid if stripped length ≥ 1."""
        valid, error = validate_username("  alice  ")
        assert valid is True
        assert error is None

    def test_username_of_49_chars_is_valid(self):
        """49 characters is within the allowed range."""
        valid, error = validate_username("b" * 49)
        assert valid is True
        assert error is None

    def test_username_of_52_chars_is_invalid(self):
        """52 characters must also be rejected."""
        valid, error = validate_username("c" * 52)
        assert valid is False
        assert error is not None


# ── Requirements 1.2, 1.4 : password length boundary ───────────────────────

class TestPasswordValidation:
    """Validates: Requirements 1.2, 1.4"""

    def test_empty_password_is_invalid(self):
        """Empty password (0 chars) must be rejected."""
        valid, error = validate_password("")
        assert valid is False
        assert error is not None

    def test_seven_char_password_is_invalid(self):
        """7 characters is one below the minimum — must be rejected."""
        valid, error = validate_password("a" * 7)
        assert valid is False
        assert error is not None

    def test_eight_char_password_is_valid(self):
        """8 characters is the minimum — must be accepted."""
        valid, error = validate_password("a" * 8)
        assert valid is True
        assert error is None

    def test_nine_char_password_is_valid(self):
        """9 characters is safely above the minimum."""
        valid, error = validate_password("a" * 9)
        assert valid is True
        assert error is None

    def test_long_password_is_valid(self):
        """A long password (100 chars) must always be accepted."""
        valid, error = validate_password("x" * 100)
        assert valid is True
        assert error is None

    def test_typical_password_is_valid(self):
        """A realistic password must be accepted."""
        valid, error = validate_password("Secur3P@ss")
        assert valid is True
        assert error is None

    def test_one_char_password_is_invalid(self):
        """1 character is well below the minimum."""
        valid, error = validate_password("z")
        assert valid is False
        assert error is not None


# ── Requirement 1.3 : duplicate username detection (case-insensitive) ────────

class TestDuplicateUsernameDetection:
    """Validates: Requirements 1.3"""

    def test_exact_match_is_duplicate(self):
        """Exact case match must be detected as a duplicate."""
        assert is_duplicate_username("alice", ["alice", "bob"]) is True

    def test_uppercase_candidate_matches_lowercase_existing(self):
        """'ALICE' must match 'alice' (case-insensitive)."""
        assert is_duplicate_username("ALICE", ["alice", "bob"]) is True

    def test_lowercase_candidate_matches_uppercase_existing(self):
        """'alice' must match 'ALICE' in the DB."""
        assert is_duplicate_username("alice", ["ALICE", "bob"]) is True

    def test_mixed_case_candidate_matches_mixed_case_existing(self):
        """'Alice' must match 'aLiCe'."""
        assert is_duplicate_username("Alice", ["aLiCe", "bob"]) is True

    def test_no_duplicate_in_empty_list(self):
        """No existing users → never a duplicate."""
        assert is_duplicate_username("alice", []) is False

    def test_different_username_is_not_duplicate(self):
        """A truly different username must not be flagged as duplicate."""
        assert is_duplicate_username("charlie", ["alice", "bob"]) is False

    def test_prefix_is_not_duplicate(self):
        """'ali' must not match 'alice'."""
        assert is_duplicate_username("ali", ["alice"]) is False

    def test_superstring_is_not_duplicate(self):
        """'alice2' must not match 'alice'."""
        assert is_duplicate_username("alice2", ["alice"]) is False

    def test_whitespace_difference_is_not_duplicate(self):
        """'alice ' (trailing space) must not match 'alice'."""
        assert is_duplicate_username("alice ", ["alice"]) is False


# ── Requirements 1.7, 1.8 : self-delete guard ───────────────────────────────

class TestSelfDeleteGuard:
    """Validates: Requirements 1.7, 1.8"""

    def test_same_username_exact_match_blocked(self):
        """Deleting your own account (exact case) must be blocked."""
        assert is_self_delete("admin", "admin") is True

    def test_same_username_uppercase_target_blocked(self):
        """'ADMIN' target == 'admin' session → must be blocked."""
        assert is_self_delete("ADMIN", "admin") is True

    def test_same_username_uppercase_session_blocked(self):
        """'admin' target == 'ADMIN' session → must be blocked."""
        assert is_self_delete("admin", "ADMIN") is True

    def test_different_username_allowed(self):
        """Different target and session usernames must allow deletion."""
        assert is_self_delete("alice", "admin") is False

    def test_prefix_not_blocked(self):
        """'adm' target and 'admin' session are different — must not block."""
        assert is_self_delete("adm", "admin") is False

    def test_empty_target_and_nonempty_session_allowed(self):
        """Empty target vs non-empty session must not be treated as self."""
        assert is_self_delete("", "admin") is False

    def test_different_case_different_user_allowed(self):
        """'Bob' target and 'alice' session — must allow deletion."""
        assert is_self_delete("Bob", "alice") is False


# ---------------------------------------------------------------------------
# Property-based tests (Hypothesis)
# ---------------------------------------------------------------------------

# ── Property 1: username validation — valid length ──────────────────────────

@settings(max_examples=300, deadline=None)
@given(
    username=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=1,
        max_size=50,
    ).filter(lambda u: len(u.strip()) >= 1)
)
def test_property_username_valid_length_always_passes(username):
    """
    **Validates: Requirements 1.2, 1.4**

    Property 1: For any username whose stripped length is between 1 and 50
    characters (inclusive), validate_username must return True.
    """
    valid, error = validate_username(username)
    assert valid is True, (
        f"Expected valid=True for username of stripped length "
        f"{len(username.strip())!r}, got valid=False (error={error!r})"
    )


@settings(max_examples=200, deadline=None)
@given(
    username=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=51,
        max_size=200,
    )
)
def test_property_username_over_50_always_fails(username):
    """
    **Validates: Requirements 1.2, 1.4**

    Property 2: For any username longer than 50 characters (before strip),
    validate_username must return False. Stripping cannot increase length,
    so a raw string of length > 50 that has no leading/trailing whitespace
    is definitely too long.
    """
    # Generate only strings that are still too long after stripping
    stripped = username.strip()
    if len(stripped) > 50:
        valid, error = validate_username(username)
        assert valid is False, (
            f"Expected valid=False for stripped length {len(stripped)}, "
            f"got valid=True"
        )


# ── Property 2: password validation — length boundary ───────────────────────

@settings(max_examples=300, deadline=None)
@given(
    password=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=8,
        max_size=200,
    )
)
def test_property_password_at_least_8_always_passes(password):
    """
    **Validates: Requirements 1.2, 1.4**

    Property 3: For any password of length ≥ 8, validate_password must
    return True.
    """
    valid, error = validate_password(password)
    assert valid is True, (
        f"Expected valid=True for password of length {len(password)}, "
        f"got valid=False (error={error!r})"
    )


@settings(max_examples=200, deadline=None)
@given(
    password=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=0,
        max_size=7,
    )
)
def test_property_password_under_8_always_fails(password):
    """
    **Validates: Requirements 1.2, 1.4**

    Property 4: For any password of length < 8, validate_password must
    return False.
    """
    valid, error = validate_password(password)
    assert valid is False, (
        f"Expected valid=False for password of length {len(password)}, "
        f"got valid=True"
    )
