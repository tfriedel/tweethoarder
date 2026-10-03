"""Tests for Chrome cookie extraction."""

import hashlib
import sqlite3
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from pytest import MonkeyPatch


def _encrypt_cookie(value: bytes, key: bytes, version: bytes = b"v11") -> bytes:
    padder = padding.PKCS7(128).padder()
    plaintext = padder.update(hashlib.sha256(b".x.com").digest() + value) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(b" " * 16)).encryptor()
    return version + encryptor.update(plaintext) + encryptor.finalize()


def _create_test_chrome_cookies_db(db_path: Path, cookies: list[tuple[str, str, str]]) -> None:
    """Create a test Chrome cookies database with given cookies (unencrypted)."""
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE meta (key TEXT, value TEXT)")
    conn.execute("INSERT INTO meta VALUES ('version', '24')")
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
    for name, value, host in cookies:
        conn.execute(
            """INSERT INTO cookies (
                creation_utc, host_key, top_frame_site_key, name, value, encrypted_value,
                path, expires_utc, is_secure, is_httponly, last_access_utc, has_expires,
                is_persistent, priority, samesite, source_scheme, source_port,
                last_update_utc, source_type, has_cross_site_ancestor
            ) VALUES (?, ?, '', ?, ?, ?, '/', 0, 1, 1, 0, 1, 1, 1, 0, 2, 443, 0, 0, 0)""",
            (0, host, name, value, b""),
        )
    conn.commit()
    conn.close()


def test_extract_chrome_cookies_is_importable() -> None:
    """extract_chrome_cookies function should be importable."""
    from tweethoarder.auth.chrome import extract_chrome_cookies

    assert callable(extract_chrome_cookies)


def test_find_chrome_cookies_db_is_importable() -> None:
    """find_chrome_cookies_db function should be importable."""
    from tweethoarder.auth.chrome import find_chrome_cookies_db

    assert callable(find_chrome_cookies_db)


@pytest.mark.parametrize(
    ("browser", "data_dir"),
    [
        ("chrome", "google-chrome"),
        ("brave", "BraveSoftware/Brave-Browser"),
        ("chromium", "chromium"),
    ],
)
@pytest.mark.parametrize("database_dir", ["", "Network"])
def test_find_chrome_cookies_db_finds_default_profile(
    tmp_path: Path, browser: str, data_dir: str, database_dir: str
) -> None:
    """Should find Cookies file in Default profile."""
    from tweethoarder.auth.chrome import find_chrome_cookies_db

    chrome_dir = tmp_path / ".config" / data_dir / "Default" / database_dir
    chrome_dir.mkdir(parents=True)
    cookies_file = chrome_dir / "Cookies"
    cookies_file.touch()

    result = find_chrome_cookies_db(tmp_path, browser=browser)

    assert result == cookies_file


def test_find_chrome_cookies_db_finds_named_profile(tmp_path: Path) -> None:
    """Should find Cookies file in named profile when specified."""
    from tweethoarder.auth.chrome import find_chrome_cookies_db

    chrome_dir = tmp_path / ".config" / "google-chrome" / "Profile 2"
    chrome_dir.mkdir(parents=True)
    cookies_file = chrome_dir / "Cookies"
    cookies_file.touch()

    result = find_chrome_cookies_db(tmp_path, profile="Profile 2")

    assert result == cookies_file


def test_extract_chrome_cookies_returns_unencrypted_values(tmp_path: Path) -> None:
    """Should extract cookies when values are unencrypted."""
    from tweethoarder.auth.chrome import extract_chrome_cookies

    db_path = tmp_path / "Cookies"
    _create_test_chrome_cookies_db(
        db_path,
        [
            ("auth_token", "unrelated_auth", ".example.com"),
            ("auth_token", "legacy_auth", ".twitter.com"),
            ("auth_token", "test_auth_token_value", ".x.com"),
            ("ct0", "test_ct0_value", ".x.com"),
            ("twid", "test_twid_value", ".x.com"),
        ],
    )

    cookies = extract_chrome_cookies(db_path)

    assert cookies["auth_token"] == "test_auth_token_value"
    assert cookies["ct0"] == "test_ct0_value"
    assert cookies["twid"] == "test_twid_value"


def test_decrypt_chrome_cookie_is_importable() -> None:
    """decrypt_chrome_cookie function should be importable."""
    from tweethoarder.auth.chrome import decrypt_chrome_cookie

    assert callable(decrypt_chrome_cookie)


def test_decrypt_chrome_cookie_decrypts_v10_value() -> None:
    """Should decrypt v10 encrypted cookie value."""
    from tweethoarder.auth.chrome import decrypt_chrome_cookie

    key = bytes.fromhex("fd621fe5a2b402539dfa147ca9272778")
    encrypted_value = _encrypt_cookie(b"test_cookie_value", key, b"v10")
    result = decrypt_chrome_cookie(encrypted_value, key, host=".x.com")

    assert result == "test_cookie_value"


def test_get_chrome_encryption_key_is_importable() -> None:
    """get_chrome_encryption_key function should be importable."""
    from tweethoarder.auth.chrome import get_chrome_encryption_key

    assert callable(get_chrome_encryption_key)


def test_get_chrome_encryption_key_returns_derived_key() -> None:
    """Should derive key from GNOME keyring password using PBKDF2."""
    from unittest.mock import MagicMock, patch

    from tweethoarder.auth.chrome import get_chrome_encryption_key

    # Mock secretstorage to return a known password
    mock_item = MagicMock()
    mock_item.get_secret.return_value = b"test_password"

    mock_connection = MagicMock()

    with (
        patch("secretstorage.dbus_init", return_value=mock_connection),
        patch("secretstorage.search_items", return_value=iter([mock_item])) as search,
        patch("secretstorage.get_default_collection") as default_collection,
    ):
        key = get_chrome_encryption_key("brave")

    # PBKDF2-HMAC-SHA1 reference value from OpenSSL.
    assert key == bytes.fromhex("53cc885e9ec5859cc0aace46ddd6c0e1")
    search.assert_called_once_with(mock_connection, {"application": "brave"})
    default_collection.assert_not_called()


def test_extract_cookies_uses_separate_v10_and_v11_keys(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    from tweethoarder.auth.chrome import extract_chrome_cookies

    db_path = tmp_path / "Cookies"
    _create_test_chrome_cookies_db(db_path, [("auth_token", "", ".x.com"), ("ct0", "", ".x.com")])
    v11_key = b"0" * 16
    # Chromium's published Linux v10 key, independent of production derivation.
    v10_key = bytes.fromhex("fd621fe5a2b402539dfa147ca9272778")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE cookies SET encrypted_value=? WHERE name='auth_token'",
            (_encrypt_cookie(b"brave_auth", v11_key),),
        )
        conn.execute(
            "UPDATE cookies SET encrypted_value=? WHERE name='ct0'",
            (_encrypt_cookie(b"brave_ct0", v10_key, b"v10"),),
        )

    def get_key(browser: str) -> bytes:
        assert browser == "brave"
        return v11_key

    monkeypatch.setattr("tweethoarder.auth.chrome.get_chrome_encryption_key", get_key)
    assert extract_chrome_cookies(db_path, browser="brave") == {
        "auth_token": "brave_auth",
        "ct0": "brave_ct0",
    }


def test_decryption_requires_matching_domain_hash() -> None:
    from tweethoarder.auth.chrome import decrypt_chrome_cookie

    key = b"0" * 16
    encrypted = _encrypt_cookie(b"cookie_value", key)
    assert decrypt_chrome_cookie(encrypted, key, host=".x.com") == "cookie_value"
    assert decrypt_chrome_cookie(encrypted, key, host=".twitter.com") == ""

    encryptor = Cipher(algorithms.AES(key), modes.CBC(b" " * 16)).encryptor()
    hashless_cookie = b"cookie_value" + b"\x04" * 4
    encrypted = b"v11" + encryptor.update(hashless_cookie) + encryptor.finalize()
    assert decrypt_chrome_cookie(encrypted, key, host=".x.com") == ""


@pytest.mark.parametrize(
    ("schema_version", "encrypted", "should_fail"),
    [(23, True, True), (24, True, False), (23, False, False), (None, True, True)],
)
def test_rejects_unsupported_encrypted_cookie_schema(
    tmp_path: Path,
    schema_version: int | None,
    encrypted: bool,
    should_fail: bool,
) -> None:
    from tweethoarder.auth.chrome import extract_chrome_cookies

    db_path = tmp_path / "Cookies"
    _create_test_chrome_cookies_db(
        db_path, [("auth_token", "plain_auth", ".x.com"), ("ct0", "plain_ct0", ".x.com")]
    )
    with sqlite3.connect(db_path) as conn:
        if schema_version is not None:
            conn.execute("UPDATE meta SET value=? WHERE key='version'", (str(schema_version),))
        else:
            conn.execute("DROP TABLE meta")
        if encrypted:
            conn.execute("UPDATE cookies SET value='', encrypted_value=?", (b"v10" + b"\x00" * 16,))

    if should_fail:
        with pytest.raises(
            ValueError, match="Update Brave, reopen this browser profile, and retry"
        ):
            extract_chrome_cookies(db_path, browser="brave")
    else:
        cookies = extract_chrome_cookies(db_path, browser="brave")
        assert cookies == ({} if encrypted else {"auth_token": "plain_auth", "ct0": "plain_ct0"})
