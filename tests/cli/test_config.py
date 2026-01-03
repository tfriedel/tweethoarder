"""Tests for config commands."""

from pathlib import Path

from pytest import MonkeyPatch
from typer.testing import CliRunner

from tweethoarder.cli.main import app

runner = CliRunner()


def test_config_show_command_exists() -> None:
    """Config show subcommand should be available."""
    result = runner.invoke(app, ["config", "show", "--help"])
    assert result.exit_code == 0
    assert "Show current configuration" in result.output


def test_config_set_command_exists() -> None:
    """Config set subcommand should be available."""
    result = runner.invoke(app, ["config", "set", "--help"])
    assert result.exit_code == 0
    assert "Set a configuration value" in result.output


def test_config_show_displays_config_dir(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Config show should display the config directory."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "config_dir" in result.output.lower() or str(tmp_path) in result.output


def test_config_set_writes_value(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Config set should write a value to config file."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = runner.invoke(app, ["config", "set", "sync.default_tweet_count", "200"])

    assert result.exit_code == 0
    config_file = tmp_path / "tweethoarder" / "config.toml"
    assert config_file.exists()
    content = config_file.read_text()
    assert "200" in content
