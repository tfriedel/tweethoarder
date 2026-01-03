"""Tests for the sync CLI commands."""

from conftest import strip_ansi
from typer.testing import CliRunner

from tweethoarder.cli.main import app

runner = CliRunner()


def test_sync_likes_command_exists() -> None:
    """The sync likes command should be available."""
    result = runner.invoke(app, ["sync", "likes", "--help"])
    assert result.exit_code == 0
    assert "likes" in result.output.lower()


def test_sync_bookmarks_command_exists() -> None:
    """The sync bookmarks command should be available."""
    result = runner.invoke(app, ["sync", "bookmarks", "--help"])
    assert result.exit_code == 0
    assert "bookmarks" in result.output.lower()


def test_sync_tweets_command_exists() -> None:
    """The sync tweets command should be available."""
    result = runner.invoke(app, ["sync", "tweets", "--help"])
    assert result.exit_code == 0
    assert "tweets" in result.output.lower()


def test_sync_reposts_command_exists() -> None:
    """The sync reposts command should be available."""
    result = runner.invoke(app, ["sync", "reposts", "--help"])
    assert result.exit_code == 0
    assert "reposts" in result.output.lower()


def test_sync_likes_accepts_count_option() -> None:
    """The sync likes command should accept a --count option."""
    result = runner.invoke(app, ["sync", "likes", "--help"])
    assert result.exit_code == 0
    assert "--count" in strip_ansi(result.output)


def test_sync_likes_accepts_all_flag() -> None:
    """The sync likes command should accept an --all flag for unlimited sync."""
    result = runner.invoke(app, ["sync", "likes", "--help"])
    assert result.exit_code == 0
    assert "--all" in strip_ansi(result.output)
