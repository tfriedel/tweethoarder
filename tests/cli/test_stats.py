"""Tests for the stats CLI command."""

import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tweethoarder.cli.main import app
from tweethoarder.storage.database import init_database

runner = CliRunner()


@pytest.fixture
def stats_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path]:
    """Create an initialized database and patch get_database_path to use it."""
    db_path = tmp_path / "tweethoarder.db"
    init_database(db_path)
    monkeypatch.setattr("tweethoarder.cli.stats.get_database_path", lambda: db_path)
    yield db_path


def test_stats_command_exists() -> None:
    """The stats command should be available."""
    result = runner.invoke(app, ["stats", "--help"])
    assert result.exit_code == 0
    assert "stats" in result.output.lower()


def test_stats_shows_total_tweets(stats_db: Path) -> None:
    """Stats command should show total tweet count."""
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "Total Tweets" in result.output


def test_stats_shows_actual_tweet_count(stats_db: Path) -> None:
    """Stats command should show actual count of tweets in database."""
    # Insert some test tweets
    with sqlite3.connect(stats_db) as conn:
        conn.execute(
            """INSERT INTO tweets (id, text, author_id, author_username, created_at,
               first_seen_at, last_updated_at)
               VALUES ('1', 'test tweet 1', 'user1', 'testuser', '2025-01-01T00:00:00Z',
               '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO tweets (id, text, author_id, author_username, created_at,
               first_seen_at, last_updated_at)
               VALUES ('2', 'test tweet 2', 'user1', 'testuser', '2025-01-01T00:00:00Z',
               '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"""
        )
        conn.commit()

    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "2" in result.output


def test_stats_shows_collection_counts(stats_db: Path) -> None:
    """Stats command should show count for each collection type."""
    # Insert test tweets and collections
    with sqlite3.connect(stats_db) as conn:
        for i in range(5):
            conn.execute(
                """INSERT INTO tweets (id, text, author_id, author_username, created_at,
                   first_seen_at, last_updated_at)
                   VALUES (?, 'test tweet', 'user1', 'testuser', '2025-01-01T00:00:00Z',
                   '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')""",
                (str(i),),
            )
        # Add to collections: 3 likes, 2 bookmarks
        conn.execute(
            """INSERT INTO collections (tweet_id, collection_type, added_at, synced_at)
               VALUES ('0', 'like', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO collections (tweet_id, collection_type, added_at, synced_at)
               VALUES ('1', 'like', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO collections (tweet_id, collection_type, added_at, synced_at)
               VALUES ('2', 'like', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO collections (tweet_id, collection_type, added_at, synced_at)
               VALUES ('3', 'bookmark', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO collections (tweet_id, collection_type, added_at, synced_at)
               VALUES ('4', 'bookmark', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"""
        )
        conn.commit()

    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "Likes" in result.output
    assert "3" in result.output
    assert "Bookmarks" in result.output


def test_stats_shows_last_sync_times(stats_db: Path) -> None:
    """Stats command should show last sync time for each collection."""
    # Insert sync progress
    with sqlite3.connect(stats_db) as conn:
        conn.execute(
            """INSERT INTO sync_progress (collection_type, total_synced, completed_at, status)
               VALUES ('likes', 100, '2025-01-02T10:30:00Z', 'completed')"""
        )
        conn.commit()

    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "last:" in result.output.lower() or "2025-01-02" in result.output


def test_stats_shows_database_size(stats_db: Path) -> None:
    """Stats command should show database file size."""
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "Database" in result.output


def test_stats_uses_rich_panel(stats_db: Path) -> None:
    """Stats command should use rich panel for formatted output."""
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    # Rich panel should have border characters
    assert "TweetHoarder Stats" in result.output or "─" in result.output


def test_stats_handles_missing_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stats command should handle case when database doesn't exist."""
    db_path = tmp_path / "nonexistent.db"

    monkeypatch.setattr("tweethoarder.cli.stats.get_database_path", lambda: db_path)

    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "Total Tweets: 0" in result.output


def test_stats_shows_bookmark_folder_breakdown(stats_db: Path) -> None:
    """Stats command should show breakdown of bookmarks by folder."""
    with sqlite3.connect(stats_db) as conn:
        # Insert test tweets
        for i in range(3):
            conn.execute(
                """INSERT INTO tweets (id, text, author_id, author_username, created_at,
                   first_seen_at, last_updated_at)
                   VALUES (?, 'test tweet', 'user1', 'testuser', '2025-01-01T00:00:00Z',
                   '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')""",
                (str(i),),
            )
        # Add bookmarks with different folders
        conn.execute(
            """INSERT INTO collections (tweet_id, collection_type, bookmark_folder_name,
               added_at, synced_at)
               VALUES ('0', 'bookmark', 'Work', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO collections (tweet_id, collection_type, bookmark_folder_name,
               added_at, synced_at)
               VALUES ('1', 'bookmark', 'Work', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"""
        )
        conn.execute(
            """INSERT INTO collections (tweet_id, collection_type, bookmark_folder_name,
               added_at, synced_at)
               VALUES ('2', 'bookmark', 'Personal', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"""  # noqa: E501
        )
        conn.commit()

    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    # Should show folder breakdown with correct counts
    assert "- Work: 2" in result.output
    assert "- Personal: 1" in result.output
