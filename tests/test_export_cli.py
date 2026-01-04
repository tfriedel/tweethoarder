"""Tests for export CLI commands."""

import json
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()

# SQL for inserting into collections with bookmark folder
INSERT_COLLECTION_SQL = """
INSERT INTO collections (
    tweet_id, collection_type, bookmark_folder_name, added_at, synced_at
) VALUES (?, ?, ?, ?, ?)
"""


def test_export_json_with_folder_flag_filters_bookmarks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Export json with --folder flag should filter bookmarks by folder."""
    from tweethoarder.cli.export import app
    from tweethoarder.storage.database import init_database, save_tweet

    # Set up database
    db_path = tmp_path / "tweethoarder.db"
    init_database(db_path)

    # Create tweets
    save_tweet(
        db_path,
        {
            "id": "1",
            "text": "Work tweet",
            "author_id": "100",
            "author_username": "user1",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    save_tweet(
        db_path,
        {
            "id": "2",
            "text": "Personal tweet",
            "author_id": "100",
            "author_username": "user1",
            "created_at": "2025-01-02T12:00:00Z",
        },
    )

    # Add to bookmarks with different folders
    conn = sqlite3.connect(db_path)
    conn.execute(
        INSERT_COLLECTION_SQL,
        ("1", "bookmark", "Work", "2025-01-01T12:00:00Z", "2025-01-01T12:00:00Z"),
    )
    conn.execute(
        INSERT_COLLECTION_SQL,
        ("2", "bookmark", "Personal", "2025-01-02T12:00:00Z", "2025-01-02T12:00:00Z"),
    )
    conn.commit()
    conn.close()

    # Mock get_data_dir to return tmp_path
    monkeypatch.setattr("tweethoarder.config.get_data_dir", lambda: tmp_path)

    output_file = tmp_path / "output.json"
    result = runner.invoke(
        app, ["json", "--collection", "bookmarks", "--folder", "Work", "--output", str(output_file)]
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert output_file.exists()

    data = json.loads(output_file.read_text())
    assert len(data["tweets"]) == 1
    assert data["tweets"][0]["text"] == "Work tweet"


def test_export_markdown_with_folder_flag_filters_bookmarks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Export markdown with --folder flag should filter bookmarks by folder."""
    from tweethoarder.cli.export import app
    from tweethoarder.storage.database import init_database, save_tweet

    db_path = tmp_path / "tweethoarder.db"
    init_database(db_path)

    save_tweet(
        db_path,
        {
            "id": "1",
            "text": "Work tweet",
            "author_id": "100",
            "author_username": "user1",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    save_tweet(
        db_path,
        {
            "id": "2",
            "text": "Personal tweet",
            "author_id": "100",
            "author_username": "user1",
            "created_at": "2025-01-02T12:00:00Z",
        },
    )

    conn = sqlite3.connect(db_path)
    conn.execute(
        INSERT_COLLECTION_SQL,
        ("1", "bookmark", "Work", "2025-01-01T12:00:00Z", "2025-01-01T12:00:00Z"),
    )
    conn.execute(
        INSERT_COLLECTION_SQL,
        ("2", "bookmark", "Personal", "2025-01-02T12:00:00Z", "2025-01-02T12:00:00Z"),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr("tweethoarder.config.get_data_dir", lambda: tmp_path)

    output_file = tmp_path / "output.md"
    result = runner.invoke(
        app,
        ["markdown", "--collection", "bookmarks", "--folder", "Work", "--output", str(output_file)],
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert output_file.exists()

    content = output_file.read_text()
    assert "Work tweet" in content
    assert "Personal tweet" not in content


def test_export_csv_with_folder_flag_filters_bookmarks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Export csv with --folder flag should filter bookmarks by folder."""
    from tweethoarder.cli.export import app
    from tweethoarder.storage.database import init_database, save_tweet

    db_path = tmp_path / "tweethoarder.db"
    init_database(db_path)

    save_tweet(
        db_path,
        {
            "id": "1",
            "text": "Work tweet",
            "author_id": "100",
            "author_username": "user1",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    save_tweet(
        db_path,
        {
            "id": "2",
            "text": "Personal tweet",
            "author_id": "100",
            "author_username": "user1",
            "created_at": "2025-01-02T12:00:00Z",
        },
    )

    conn = sqlite3.connect(db_path)
    conn.execute(
        INSERT_COLLECTION_SQL,
        ("1", "bookmark", "Work", "2025-01-01T12:00:00Z", "2025-01-01T12:00:00Z"),
    )
    conn.execute(
        INSERT_COLLECTION_SQL,
        ("2", "bookmark", "Personal", "2025-01-02T12:00:00Z", "2025-01-02T12:00:00Z"),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr("tweethoarder.config.get_data_dir", lambda: tmp_path)

    output_file = tmp_path / "output.csv"
    result = runner.invoke(
        app, ["csv", "--collection", "bookmarks", "--folder", "Work", "--output", str(output_file)]
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert output_file.exists()

    content = output_file.read_text()
    assert "Work tweet" in content
    assert "Personal tweet" not in content


def test_export_html_with_folder_flag_filters_bookmarks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Export html with --folder flag should filter bookmarks by folder."""
    from tweethoarder.cli.export import app
    from tweethoarder.storage.database import init_database, save_tweet

    db_path = tmp_path / "tweethoarder.db"
    init_database(db_path)

    save_tweet(
        db_path,
        {
            "id": "1",
            "text": "Work tweet",
            "author_id": "100",
            "author_username": "user1",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    save_tweet(
        db_path,
        {
            "id": "2",
            "text": "Personal tweet",
            "author_id": "100",
            "author_username": "user1",
            "created_at": "2025-01-02T12:00:00Z",
        },
    )

    conn = sqlite3.connect(db_path)
    conn.execute(
        INSERT_COLLECTION_SQL,
        ("1", "bookmark", "Work", "2025-01-01T12:00:00Z", "2025-01-01T12:00:00Z"),
    )
    conn.execute(
        INSERT_COLLECTION_SQL,
        ("2", "bookmark", "Personal", "2025-01-02T12:00:00Z", "2025-01-02T12:00:00Z"),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr("tweethoarder.config.get_data_dir", lambda: tmp_path)

    output_file = tmp_path / "output.html"
    result = runner.invoke(
        app, ["html", "--collection", "bookmarks", "--folder", "Work", "--output", str(output_file)]
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert output_file.exists()

    content = output_file.read_text()
    assert "Work tweet" in content
    assert "Personal tweet" not in content
