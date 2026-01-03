"""Tests for thread command."""

from typer.testing import CliRunner

from tweethoarder.cli.main import app

runner = CliRunner()


def test_thread_command_exists() -> None:
    """Thread command should be available."""
    result = runner.invoke(app, ["thread", "--help"])
    assert result.exit_code == 0
    assert "tweet_id" in result.output.lower() or "TWEET_ID" in result.output


def test_thread_command_has_depth_option() -> None:
    """Thread command should have --depth option."""
    import re

    result = runner.invoke(app, ["thread", "--help"])
    assert result.exit_code == 0
    # Strip ANSI escape codes for reliable matching
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--depth" in clean_output


def test_thread_command_displays_tweet_id() -> None:
    """Thread command should display the tweet ID being fetched."""
    result = runner.invoke(app, ["thread", "1234567890"])
    assert result.exit_code == 0
    assert "1234567890" in result.output
