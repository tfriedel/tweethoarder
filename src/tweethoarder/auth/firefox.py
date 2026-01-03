"""Firefox cookie extraction for TweetHoarder."""

import sqlite3
from pathlib import Path


def extract_firefox_cookies(db_path: Path) -> dict[str, str]:
    """Extract auth_token, ct0, and twid cookies from Firefox cookies.sqlite."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT name, value FROM moz_cookies WHERE name IN ('auth_token', 'ct0', 'twid')"
        )
        cookies = {row[0]: row[1] for row in cursor.fetchall()}
    return cookies


FIREFOX_COOKIE_PATHS = [
    ".mozilla/firefox",
    "snap/firefox/common/.mozilla/firefox",
]


def find_firefox_cookies_db(home_dir: Path) -> Path | None:
    """Find the most recently modified Firefox cookies.sqlite file."""
    candidates: list[Path] = []

    for base_path in FIREFOX_COOKIE_PATHS:
        firefox_dir = home_dir / base_path
        if firefox_dir.exists():
            candidates.extend(firefox_dir.glob("*/cookies.sqlite"))

    if not candidates:
        return None

    return max(candidates, key=lambda p: p.stat().st_mtime)
