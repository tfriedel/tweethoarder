"""Tests for the stats CLI command."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from tweethoarder.cli.main import app
from tweethoarder.storage.database import init_database

runner = CliRunner()


def test_stats_command_exists() -> None:
    """The stats command should be available."""
    result = runner.invoke(app, ["stats", "--help"])
    assert result.exit_code == 0
    assert "stats" in result.output.lower()


def test_stats_shows_total_tweets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stats command should show total tweet count."""
    db_path = tmp_path / "tweethoarder.db"
    init_database(db_path)

    monkeypatch.setattr("tweethoarder.cli.stats.get_database_path", lambda: db_path)

    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "Total Tweets" in result.output


def test_stats_shows_actual_tweet_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stats command should show actual count of tweets in database."""
    import sqlite3

    db_path = tmp_path / "tweethoarder.db"
    init_database(db_path)

    # Insert some test tweets
    conn = sqlite3.connect(db_path)
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
    conn.close()

    monkeypatch.setattr("tweethoarder.cli.stats.get_database_path", lambda: db_path)

    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "2" in result.output


def test_stats_shows_collection_counts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stats command should show count for each collection type."""
    import sqlite3

    db_path = tmp_path / "tweethoarder.db"
    init_database(db_path)

    # Insert test tweets and collections
    conn = sqlite3.connect(db_path)
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
    conn.close()

    monkeypatch.setattr("tweethoarder.cli.stats.get_database_path", lambda: db_path)

    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "Likes" in result.output
    assert "3" in result.output
    assert "Bookmarks" in result.output


def test_stats_shows_last_sync_times(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stats command should show last sync time for each collection."""
    import sqlite3

    db_path = tmp_path / "tweethoarder.db"
    init_database(db_path)

    # Insert sync progress
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO sync_progress (collection_type, total_synced, completed_at, status)
           VALUES ('likes', 100, '2025-01-02T10:30:00Z', 'completed')"""
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr("tweethoarder.cli.stats.get_database_path", lambda: db_path)

    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "last:" in result.output.lower() or "2025-01-02" in result.output


def test_stats_shows_database_size(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stats command should show database file size."""
    db_path = tmp_path / "tweethoarder.db"
    init_database(db_path)

    monkeypatch.setattr("tweethoarder.cli.stats.get_database_path", lambda: db_path)

    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "Database" in result.output


def test_stats_uses_rich_panel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stats command should use rich panel for formatted output."""
    db_path = tmp_path / "tweethoarder.db"
    init_database(db_path)

    monkeypatch.setattr("tweethoarder.cli.stats.get_database_path", lambda: db_path)

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
