"""Cookie resolution flow with fallbacks."""

import os
import tomllib
from pathlib import Path

from tweethoarder.auth.chrome import extract_chrome_cookies, find_chrome_cookies_db
from tweethoarder.auth.firefox import extract_firefox_cookies, find_firefox_cookies_db
from tweethoarder.config import DEFAULT_COOKIE_SOURCES, get_config_dir


class CookieError(Exception):
    """Raised when cookie resolution fails."""


def resolve_cookies(home_dir: Path | None = None) -> dict[str, str]:
    """Resolve cookies using priority-based fallback chain."""
    auth_token = os.environ.get("TWITTER_AUTH_TOKEN")
    ct0 = os.environ.get("TWITTER_CT0")
    twid = os.environ.get("TWITTER_TWID")

    if auth_token and ct0:
        result = {"auth_token": auth_token, "ct0": ct0}
        if twid:
            result["twid"] = twid
        return result

    config_path = get_config_dir() / "config.toml"
    auth_data = {}
    if config_path.exists():
        with config_path.open("rb") as f:
            data = tomllib.load(f)
        auth_data = data.get("auth", {})
        auth_token = auth_data.get("auth_token")
        ct0 = auth_data.get("ct0")
        twid = auth_data.get("twid")
        if auth_token and ct0:
            result = {"auth_token": auth_token, "ct0": ct0}
            if twid:
                result["twid"] = twid
            return result

    if home_dir is None:
        home_dir = Path.home()
    cookie_sources = auth_data.get("cookie_sources", DEFAULT_COOKIE_SOURCES)
    for source in cookie_sources:
        if source == "firefox":
            cookies_db = find_firefox_cookies_db(home_dir)
            if not cookies_db:
                continue
            cookies = extract_firefox_cookies(cookies_db)
        elif source in ("brave", "chrome", "chromium"):
            cookies_db = find_chrome_cookies_db(home_dir, browser=source)
            if not cookies_db:
                continue
            cookies = extract_chrome_cookies(cookies_db, browser=source)
        else:
            continue

        auth_token = cookies.get("auth_token")
        ct0 = cookies.get("ct0")
        if auth_token and ct0:
            result = {"auth_token": auth_token, "ct0": ct0}
            if cookies.get("twid"):
                result["twid"] = cookies["twid"]
            return result

    raise CookieError("No Twitter cookies found")
