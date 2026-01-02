"""Configuration management for TweetHoarder."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


def get_config_dir() -> Path:
    """Get the XDG-compliant configuration directory."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(xdg_config) / "tweethoarder"


def get_data_dir() -> Path:
    """Get the XDG-compliant data directory."""
    xdg_data = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(xdg_data) / "tweethoarder"


@dataclass
class SyncConfig:
    """Sync-related configuration."""

    default_tweet_count: int = 100


@dataclass
class AuthConfig:
    """Authentication-related configuration."""

    cookie_sources: list[str]


@dataclass
class Config:
    """Application configuration."""

    sync: SyncConfig
    auth: AuthConfig


def load_config(path: Path) -> Config:
    """Load configuration from TOML file, with defaults for missing values."""
    default_cookie_sources = ["firefox", "chrome"]

    if not path.exists():
        return Config(
            sync=SyncConfig(),
            auth=AuthConfig(cookie_sources=default_cookie_sources),
        )

    with path.open("rb") as f:
        data = tomllib.load(f)

    sync_data = data.get("sync", {})
    sync_config = SyncConfig(
        default_tweet_count=sync_data.get("default_tweet_count", 100),
    )

    auth_data = data.get("auth", {})
    auth_config = AuthConfig(
        cookie_sources=auth_data.get("cookie_sources", default_cookie_sources),
    )

    return Config(sync=sync_config, auth=auth_config)
