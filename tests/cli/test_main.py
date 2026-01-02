"""Tests for the CLI main module."""

from typer.testing import CliRunner

from tweethoarder.cli.main import app

runner = CliRunner()


def test_app_exists() -> None:
    """The CLI app should be importable."""
    assert app is not None


def test_help_shows_description() -> None:
    """Running --help should show the app description."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Archive your Twitter/X data" in result.output
