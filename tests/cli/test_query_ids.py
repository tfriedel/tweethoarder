"""Tests for the refresh-ids CLI command."""

from typer.testing import CliRunner

from tweethoarder.cli.main import app

runner = CliRunner()


def test_refresh_ids_command_exists() -> None:
    """The refresh-ids command should be available."""
    result = runner.invoke(app, ["refresh-ids", "--help"])
    assert result.exit_code == 0
    assert "refresh" in result.output.lower()
