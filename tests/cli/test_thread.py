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
    result = runner.invoke(app, ["thread", "--help"])
    assert result.exit_code == 0
    assert "--depth" in result.output
