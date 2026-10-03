"""Chromium-family cookie extraction for TweetHoarder."""

import hashlib
import sqlite3
from pathlib import Path


def extract_chrome_cookies(db_path: Path, browser: str = "chrome") -> dict[str, str]:
    """Extract X session cookies from a Chromium-family Cookies database."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT host_key, name, value, encrypted_value
            FROM cookies
            WHERE name IN ('auth_token', 'ct0', 'twid')
              AND host_key IN ('x.com', '.x.com', 'twitter.com', '.twitter.com')
            ORDER BY CASE WHEN host_key IN ('x.com', '.x.com') THEN 0 ELSE 1 END
            """
        )
        rows = cursor.fetchall()
        if any(row[3] for row in rows):
            _check_cookie_schema(conn, browser)

    cookies: dict[str, str] = {}
    encryption_keys: dict[bytes, bytes | None] = {b"v10": _derive_encryption_key(b"peanuts")}
    for host, name, value, encrypted_value in rows:
        if name in cookies:
            continue
        if encrypted_value:
            version = encrypted_value[:3]
            if version == b"v11" and version not in encryption_keys:
                encryption_keys[version] = get_chrome_encryption_key(browser)
            value = decrypt_chrome_cookie(
                encrypted_value,
                encryption_keys.get(version),
                host=host,
            )
        if value:
            cookies[name] = value
    return cookies


def _check_cookie_schema(conn: sqlite3.Connection, browser: str) -> None:
    """Require schema 24 or later for encrypted cookies."""
    try:
        schema_version = int(
            conn.execute("SELECT value FROM meta WHERE key='version'").fetchone()[0]
        )
    except (sqlite3.OperationalError, TypeError, ValueError):
        schema_version = 0
    if schema_version < 24:
        raise ValueError(
            f"Cannot read {browser.capitalize()}'s encrypted cookies. "
            "Your cookie database schema might be out of date. "
            f"Update {browser.capitalize()}, reopen this browser profile, and retry."
        )


def decrypt_chrome_cookie(
    encrypted_value: bytes,
    key: bytes | None,
    *,
    host: str,
) -> str:
    """Decrypt a Linux Chromium cookie using its v10 or v11 key."""
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    version = encrypted_value[:3]
    if version not in (b"v10", b"v11") or key is None:
        return ""

    ciphertext = encrypted_value[3:]
    if not ciphertext or len(ciphertext) % 16:
        return ""
    iv = b" " * 16

    try:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
        domain_hash = hashlib.sha256(host.encode("utf-8")).digest()
        if not plaintext.startswith(domain_hash):
            return ""
        return plaintext[len(domain_hash) :].decode("utf-8")
    except ValueError:
        return ""


def _derive_encryption_key(password: bytes) -> bytes:
    """Derive Chromium's Linux AES-128 key from its keyring password."""
    return hashlib.pbkdf2_hmac("sha1", password, b"saltysalt", 1, dklen=16)


def get_chrome_encryption_key(browser: str = "chrome") -> bytes | None:
    """Get a browser's v11 encryption key from an existing Secret Service item."""
    import secretstorage
    from secretstorage.exceptions import SecretStorageException

    try:
        connection = secretstorage.dbus_init()
        item = next(secretstorage.search_items(connection, {"application": browser}), None)
        if item is None:
            return None
        return _derive_encryption_key(item.get_secret())
    except SecretStorageException:
        return None


def find_chrome_cookies_db(
    home_dir: Path, profile: str | None = None, browser: str = "chrome"
) -> Path | None:
    """Find a Chromium-family Cookies database file."""
    profile_name = profile or "Default"
    user_data_dirs = {
        "brave": home_dir / ".config" / "BraveSoftware" / "Brave-Browser",
        "chrome": home_dir / ".config" / "google-chrome",
        "chromium": home_dir / ".config" / "chromium",
    }
    user_data_dir = user_data_dirs.get(browser)
    if user_data_dir is None:
        return None

    profile_dir = user_data_dir / profile_name
    for cookies_path in (profile_dir / "Network" / "Cookies", profile_dir / "Cookies"):
        if cookies_path.exists():
            return cookies_path
    return None
