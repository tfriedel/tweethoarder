"""Tests for the CLI export module."""

from pathlib import Path

from typer.testing import CliRunner

from tweethoarder.cli.main import app

runner = CliRunner()


def _setup_test_db(tmp_path: Path) -> Path:
    """Set up a test database with sample data in XDG structure."""
    from tweethoarder.storage.database import (
        add_to_collection,
        init_database,
        save_tweet,
    )

    data_dir = tmp_path / "tweethoarder"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "tweethoarder.db"
    init_database(db_path)
    save_tweet(
        db_path,
        {
            "id": "123",
            "text": "Test tweet",
            "author_id": "456",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    add_to_collection(db_path, "123", "like")
    return db_path


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


def test_export_markdown_command_exists() -> None:
    """Export markdown subcommand should be available."""
    result = runner.invoke(app, ["export", "markdown", "--help"])
    assert result.exit_code == 0
    assert "Export tweets to Markdown format" in result.output


def test_export_markdown_has_collection_option() -> None:
    """Export markdown command should have collection option."""
    result = runner.invoke(app, ["export", "markdown", "--help"])
    assert result.exit_code == 0
    assert "--collection" in result.output


def test_export_markdown_writes_file(tmp_path: Path, monkeypatch: object) -> None:
    """Export markdown command should write to file."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.md"
    result = runner.invoke(
        app, ["export", "markdown", "--collection", "likes", "--output", str(output_path)]
    )

    assert result.exit_code == 0
    assert output_path.exists()
    content = output_path.read_text()
    assert "# Liked Tweets" in content
    assert "@testuser" in content


def test_export_markdown_uses_default_output_path(tmp_path: Path, monkeypatch: object) -> None:
    """Export markdown command should write to default path when --output not specified."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    result = runner.invoke(app, ["export", "markdown", "--collection", "likes"])

    assert result.exit_code == 0
    # Check that file was created in exports directory
    exports_dir = tmp_path / "tweethoarder" / "exports"
    assert exports_dir.exists()
    md_files = list(exports_dir.glob("likes_*.md"))
    assert len(md_files) == 1
    content = md_files[0].read_text()
    assert "# Liked Tweets" in content


def test_export_markdown_exports_all_tweets_when_no_collection(
    tmp_path: Path, monkeypatch: object
) -> None:
    """Export markdown without --collection should export all tweets."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "all.md"
    result = runner.invoke(app, ["export", "markdown", "--output", str(output_path)])

    assert result.exit_code == 0
    content = output_path.read_text()
    assert "@testuser" in content
    assert "Test tweet" in content


def test_export_csv_command_exists() -> None:
    """Export csv subcommand should be available."""
    result = runner.invoke(app, ["export", "csv", "--help"])
    assert result.exit_code == 0
    assert "Export tweets to CSV format" in result.output


def test_export_csv_has_collection_option() -> None:
    """Export csv command should have collection option."""
    result = runner.invoke(app, ["export", "csv", "--help"])
    assert result.exit_code == 0
    assert "--collection" in result.output


def test_export_csv_writes_file(tmp_path: Path, monkeypatch: object) -> None:
    """Export csv command should write to file."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.csv"
    result = runner.invoke(
        app, ["export", "csv", "--collection", "likes", "--output", str(output_path)]
    )

    assert result.exit_code == 0
    assert output_path.exists()
    content = output_path.read_text()
    assert "id" in content
    assert "testuser" in content
