"""Tests for the stats CLI command."""

from typer.testing import CliRunner

from tweethoarder.cli.main import app

runner = CliRunner()


def test_stats_command_exists() -> None:
    """The stats command should be available."""
    result = runner.invoke(app, ["stats", "--help"])
    assert result.exit_code == 0
    assert "stats" in result.output.lower()
