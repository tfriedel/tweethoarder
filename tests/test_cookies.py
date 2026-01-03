"""Tests for cookie resolution flow."""

import sqlite3
from pathlib import Path

from pytest import MonkeyPatch


def test_resolve_cookies_from_env_vars(monkeypatch: MonkeyPatch) -> None:
    """Should resolve cookies from environment variables first."""
    from tweethoarder.auth.cookies import resolve_cookies

    monkeypatch.setenv("TWITTER_AUTH_TOKEN", "env_auth_token")
    monkeypatch.setenv("TWITTER_CT0", "env_ct0")

    cookies = resolve_cookies()

    assert cookies["auth_token"] == "env_auth_token"
    assert cookies["ct0"] == "env_ct0"


def test_resolve_cookies_from_config_file(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Should fall back to config file when env vars are not set."""
    from tweethoarder.auth.cookies import resolve_cookies

    monkeypatch.delenv("TWITTER_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_CT0", raising=False)

    # XDG_CONFIG_HOME points to the base config dir, then tweethoarder is appended
    config_dir = tmp_path / "tweethoarder"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    config_file.write_text("""
[auth]
auth_token = "config_auth_token"
ct0 = "config_ct0"
""")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    cookies = resolve_cookies()

    assert cookies["auth_token"] == "config_auth_token"
    assert cookies["ct0"] == "config_ct0"


def _create_firefox_cookies_db(db_path: Path, cookies: list[tuple[str, str]]) -> None:
    """Create a test Firefox cookies database."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE moz_cookies (
            id INTEGER PRIMARY KEY,
            name TEXT,
            value TEXT,
            host TEXT DEFAULT '.x.com'
        )
    """)
    for name, value in cookies:
        conn.execute("INSERT INTO moz_cookies (name, value) VALUES (?, ?)", (name, value))
    conn.commit()
    conn.close()


def test_resolve_cookies_from_firefox(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Should fall back to Firefox when env vars and config file are not available."""
    from tweethoarder.auth.cookies import resolve_cookies

    monkeypatch.delenv("TWITTER_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_CT0", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty_config"))

    # Create a fake Firefox profile with cookies
    firefox_dir = tmp_path / ".mozilla" / "firefox" / "test_profile"
    firefox_dir.mkdir(parents=True)
    _create_firefox_cookies_db(
        firefox_dir / "cookies.sqlite",
        [("auth_token", "firefox_auth_token"), ("ct0", "firefox_ct0")],
    )

    cookies = resolve_cookies(home_dir=tmp_path)

    assert cookies["auth_token"] == "firefox_auth_token"
    assert cookies["ct0"] == "firefox_ct0"


def test_resolve_cookies_raises_when_no_cookies_found(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Should raise CookieError when no cookies are found from any source."""
    import pytest

    from tweethoarder.auth.cookies import CookieError, resolve_cookies

    monkeypatch.delenv("TWITTER_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_CT0", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty_config"))

    with pytest.raises(CookieError, match="No Twitter cookies found"):
        resolve_cookies(home_dir=tmp_path)


def test_resolve_cookies_includes_twid_from_firefox(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Should include twid cookie when available from Firefox."""
    from tweethoarder.auth.cookies import resolve_cookies

    monkeypatch.delenv("TWITTER_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_CT0", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty_config"))

    firefox_dir = tmp_path / ".mozilla" / "firefox" / "test_profile"
    firefox_dir.mkdir(parents=True)
    _create_firefox_cookies_db(
        firefox_dir / "cookies.sqlite",
        [
            ("auth_token", "firefox_auth_token"),
            ("ct0", "firefox_ct0"),
            ("twid", "u%3D12345"),
        ],
    )

    cookies = resolve_cookies(home_dir=tmp_path)

    assert cookies["twid"] == "u%3D12345"


def test_resolve_cookies_includes_twid_from_env_vars(monkeypatch: MonkeyPatch) -> None:
    """Should include twid cookie when available from environment variables."""
    from tweethoarder.auth.cookies import resolve_cookies

    monkeypatch.setenv("TWITTER_AUTH_TOKEN", "env_auth_token")
    monkeypatch.setenv("TWITTER_CT0", "env_ct0")
    monkeypatch.setenv("TWITTER_TWID", "u%3D67890")

    cookies = resolve_cookies()

    assert cookies["twid"] == "u%3D67890"


def test_resolve_cookies_includes_twid_from_config_file(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Should include twid cookie when available from config file."""
    from tweethoarder.auth.cookies import resolve_cookies

    monkeypatch.delenv("TWITTER_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_CT0", raising=False)
    monkeypatch.delenv("TWITTER_TWID", raising=False)

    config_dir = tmp_path / "tweethoarder"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    config_file.write_text("""
[auth]
auth_token = "config_auth_token"
ct0 = "config_ct0"
twid = "u%3D11111"
""")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    cookies = resolve_cookies()

    assert cookies["twid"] == "u%3D11111"


def _create_chrome_cookies_db(db_path: Path, cookies: list[tuple[str, str]]) -> None:
    """Create a test Chrome cookies database with unencrypted values."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE cookies (
            creation_utc INTEGER NOT NULL,
            host_key TEXT NOT NULL,
            top_frame_site_key TEXT NOT NULL,
            name TEXT NOT NULL,
            value TEXT NOT NULL,
            encrypted_value BLOB NOT NULL,
            path TEXT NOT NULL,
            expires_utc INTEGER NOT NULL,
            is_secure INTEGER NOT NULL,
            is_httponly INTEGER NOT NULL,
            last_access_utc INTEGER NOT NULL,
            has_expires INTEGER NOT NULL,
            is_persistent INTEGER NOT NULL,
            priority INTEGER NOT NULL,
            samesite INTEGER NOT NULL,
            source_scheme INTEGER NOT NULL,
            source_port INTEGER NOT NULL,
            last_update_utc INTEGER NOT NULL,
            source_type INTEGER NOT NULL,
            has_cross_site_ancestor INTEGER NOT NULL
        )
    """)
    for name, value in cookies:
        conn.execute(
            """INSERT INTO cookies (
                creation_utc, host_key, top_frame_site_key, name, value, encrypted_value,
                path, expires_utc, is_secure, is_httponly, last_access_utc, has_expires,
                is_persistent, priority, samesite, source_scheme, source_port,
                last_update_utc, source_type, has_cross_site_ancestor
            ) VALUES (?, ?, '', ?, ?, ?, '/', 0, 1, 1, 0, 1, 1, 1, 0, 2, 443, 0, 0, 0)""",
            (0, ".x.com", name, value, b""),
        )
    conn.commit()
    conn.close()


def test_resolve_cookies_from_chrome_when_firefox_fails(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Should fall back to Chrome when Firefox is not available."""
    from tweethoarder.auth.cookies import resolve_cookies

    monkeypatch.delenv("TWITTER_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_CT0", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty_config"))

    # Create a Chrome profile with cookies (no Firefox)
    chrome_dir = tmp_path / ".config" / "google-chrome" / "Default"
    chrome_dir.mkdir(parents=True)
    _create_chrome_cookies_db(
        chrome_dir / "Cookies",
        [("auth_token", "chrome_auth_token"), ("ct0", "chrome_ct0")],
    )

    cookies = resolve_cookies(home_dir=tmp_path)

    assert cookies["auth_token"] == "chrome_auth_token"
    assert cookies["ct0"] == "chrome_ct0"
