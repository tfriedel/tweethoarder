"""Chrome cookie extraction for TweetHoarder."""

import sqlite3
from pathlib import Path


def extract_chrome_cookies(db_path: Path) -> dict[str, str]:
    """Extract auth_token, ct0, and twid cookies from Chrome Cookies DB."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT name, value FROM cookies WHERE name IN ('auth_token', 'ct0', 'twid')"
        )
        cookies = {row[0]: row[1] for row in cursor.fetchall()}
    return cookies


def decrypt_chrome_cookie(encrypted_value: bytes, key: bytes) -> str:
    """Decrypt a Chrome cookie value using AES-128-CBC."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    if encrypted_value[:3] != b"v10":
        return ""

    ciphertext = encrypted_value[3:]
    iv = b" " * 16  # Chrome uses space padding for IV

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    # Remove PKCS7 padding
    padding_length = padded_plaintext[-1]
    plaintext = padded_plaintext[:-padding_length]

    return plaintext.decode("utf-8")


def get_chrome_encryption_key() -> bytes | None:
    """Get Chrome encryption key from GNOME keyring."""
    import secretstorage
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    connection = secretstorage.dbus_init()
    collection = secretstorage.get_default_collection(connection)

    # Search for Chrome Safe Storage item
    items = list(collection.search_items({"application": "chrome"}))
    if not items:
        return None

    password = items[0].get_secret()

    # Derive key using PBKDF2 with Chrome's parameters
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA1(),
        length=16,
        salt=b"saltysalt",
        iterations=1,
    )
    return kdf.derive(password)


def find_chrome_cookies_db(home_dir: Path, profile: str | None = None) -> Path | None:
    """Find the Chrome Cookies database file."""
    profile_name = profile or "Default"
    cookies_path = home_dir / ".config" / "google-chrome" / profile_name / "Cookies"
    if cookies_path.exists():
        return cookies_path
    return None
