"""Tests for configuration management."""

from pathlib import Path

import pytest

from tweethoarder.config import get_config_dir, get_data_dir


def test_get_config_dir_returns_xdg_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config directory should follow XDG spec."""
    monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/test-config")
    result = get_config_dir()
    assert result == Path("/tmp/test-config/tweethoarder")


def test_get_config_dir_uses_home_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config directory should fall back to ~/.config when XDG not set."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", "/tmp/test-home")
    result = get_config_dir()
    assert result == Path("/tmp/test-home/.config/tweethoarder")


def test_get_data_dir_returns_xdg_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Data directory should follow XDG spec."""
    monkeypatch.setenv("XDG_DATA_HOME", "/tmp/test-data")
    result = get_data_dir()
    assert result == Path("/tmp/test-data/tweethoarder")


def test_load_config_returns_defaults_when_no_file(tmp_path: Path) -> None:
    """Load config should return defaults when config file doesn't exist."""
    from tweethoarder.config import load_config

    config = load_config(tmp_path / "nonexistent.toml")
    assert config.sync.default_tweet_count == 100


def test_load_config_reads_toml_file(tmp_path: Path) -> None:
    """Load config should read values from TOML file."""
    from tweethoarder.config import load_config

    config_file = tmp_path / "config.toml"
    config_file.write_text("[sync]\ndefault_tweet_count = 500\n")
    config = load_config(config_file)
    assert config.sync.default_tweet_count == 500


def test_load_config_has_auth_section(tmp_path: Path) -> None:
    """Load config should have auth section with cookie sources."""
    from tweethoarder.config import load_config

    config = load_config(tmp_path / "nonexistent.toml")
    assert config.auth.cookie_sources == ["firefox", "chrome"]


def test_load_config_reads_auth_from_toml(tmp_path: Path) -> None:
    """Load config should read auth settings from TOML file."""
    from tweethoarder.config import load_config

    config_file = tmp_path / "config.toml"
    config_file.write_text('[auth]\ncookie_sources = ["chrome"]\n')
    config = load_config(config_file)
    assert config.auth.cookie_sources == ["chrome"]
