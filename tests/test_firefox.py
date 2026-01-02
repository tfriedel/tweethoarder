"""Tests for Firefox cookie extraction."""

import sqlite3
from pathlib import Path


def _create_test_cookies_db(db_path: Path, cookies: list[tuple[str, str, str]]) -> None:
    """Create a test Firefox cookies database with given cookies."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE moz_cookies (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value TEXT,
            host TEXT,
            path TEXT DEFAULT '/',
            expiry INTEGER DEFAULT 0,
            isSecure INTEGER DEFAULT 1,
            isHttpOnly INTEGER DEFAULT 1,
            sameSite INTEGER DEFAULT 0,
            rawSameSite INTEGER DEFAULT 0,
            schemeMap INTEGER DEFAULT 0
        )
    """)
    for name, value, host in cookies:
        conn.execute(
            "INSERT INTO moz_cookies (name, value, host) VALUES (?, ?, ?)",
            (name, value, host),
        )
    conn.commit()
    conn.close()


def test_extract_firefox_cookies_returns_auth_token_and_ct0(tmp_path: Path) -> None:
    """Should extract auth_token and ct0 cookies from Firefox database."""
    from tweethoarder.auth.firefox import extract_firefox_cookies

    db_path = tmp_path / "cookies.sqlite"
    _create_test_cookies_db(
        db_path,
        [
            ("auth_token", "test_auth_token_value", ".x.com"),
            ("ct0", "test_ct0_value", ".x.com"),
            ("other_cookie", "ignored", ".x.com"),
        ],
    )

    cookies = extract_firefox_cookies(db_path)

    assert cookies["auth_token"] == "test_auth_token_value"
    assert cookies["ct0"] == "test_ct0_value"


def test_find_firefox_cookies_db_returns_most_recent(tmp_path: Path) -> None:
    """Should find the most recently modified cookies.sqlite across locations."""
    from tweethoarder.auth.firefox import find_firefox_cookies_db

    # Create two fake Firefox locations with cookies.sqlite
    old_location = tmp_path / ".mozilla" / "firefox" / "profile1"
    old_location.mkdir(parents=True)
    old_db = old_location / "cookies.sqlite"
    _create_test_cookies_db(old_db, [("old", "old_value", ".x.com")])

    new_location = tmp_path / "snap" / "firefox" / "common" / ".mozilla" / "firefox" / "profile2"
    new_location.mkdir(parents=True)
    new_db = new_location / "cookies.sqlite"
    _create_test_cookies_db(new_db, [("new", "new_value", ".x.com")])

    # Make the snap one newer by touching it
    import time

    time.sleep(0.01)
    new_db.touch()

    result = find_firefox_cookies_db(tmp_path)

    assert result == new_db


def test_find_firefox_cookies_db_returns_none_when_no_firefox(tmp_path: Path) -> None:
    """Should return None when no Firefox cookies database is found."""
    from tweethoarder.auth.firefox import find_firefox_cookies_db

    result = find_firefox_cookies_db(tmp_path)

    assert result is None
