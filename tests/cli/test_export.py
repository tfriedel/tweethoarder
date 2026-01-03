"""Tests for the CLI export module."""

from typer.testing import CliRunner

from tweethoarder.cli.main import app

runner = CliRunner()


def test_export_json_command_exists() -> None:
    """Export json subcommand should be available."""
    result = runner.invoke(app, ["export", "json", "--help"])
    assert result.exit_code == 0
    assert "Export tweets to JSON format" in result.output


def test_export_json_has_collection_option() -> None:
    """Export json command should have collection option."""
    result = runner.invoke(app, ["export", "json", "--help"])
    assert result.exit_code == 0
    assert "--collection" in result.output


def test_export_json_has_output_option() -> None:
    """Export json command should have output path option."""
    result = runner.invoke(app, ["export", "json", "--help"])
    assert result.exit_code == 0
    assert "--output" in result.output
