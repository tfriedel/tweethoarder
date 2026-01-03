"""Cookie resolution flow with fallbacks."""

import os
import tomllib
from pathlib import Path

from tweethoarder.auth.firefox import extract_firefox_cookies, find_firefox_cookies_db
from tweethoarder.config import get_config_dir


class CookieError(Exception):
    """Raised when cookie resolution fails."""


def resolve_cookies(home_dir: Path | None = None) -> dict[str, str]:
    """Resolve cookies using priority-based fallback chain."""
    auth_token = os.environ.get("TWITTER_AUTH_TOKEN")
    ct0 = os.environ.get("TWITTER_CT0")

    if auth_token and ct0:
        return {"auth_token": auth_token, "ct0": ct0}

    config_path = get_config_dir() / "config.toml"
    if config_path.exists():
        with config_path.open("rb") as f:
            data = tomllib.load(f)
        auth_data = data.get("auth", {})
        auth_token = auth_data.get("auth_token")
        ct0 = auth_data.get("ct0")
        if auth_token and ct0:
            return {"auth_token": auth_token, "ct0": ct0}

    if home_dir is None:
        home_dir = Path.home()
    firefox_db = find_firefox_cookies_db(home_dir)
    if firefox_db:
        cookies = extract_firefox_cookies(firefox_db)
        auth_token = cookies.get("auth_token")
        ct0 = cookies.get("ct0")
        if auth_token and ct0:
            result = {"auth_token": auth_token, "ct0": ct0}
            if "twid" in cookies:
                result["twid"] = cookies["twid"]
            return result

    raise CookieError("No Twitter cookies found")
