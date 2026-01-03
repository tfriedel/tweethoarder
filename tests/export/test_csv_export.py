"""Tests for CSV export functionality."""

from typing import Any

from tweethoarder.export.csv_export import export_tweets_to_csv


def make_tweet(
    tweet_id: str = "123",
    text: str = "Hello world",
    author_id: str = "456",
    author_username: str = "testuser",
    author_display_name: str = "Test User",
    created_at: str = "2025-01-01T12:00:00Z",
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a test tweet with sensible defaults."""
    tweet = {
        "id": tweet_id,
        "text": text,
        "author_id": author_id,
        "author_username": author_username,
        "author_display_name": author_display_name,
        "created_at": created_at,
    }
    tweet.update(kwargs)
    return tweet


def test_export_tweets_to_csv_returns_string() -> None:
    """Export function returns a string."""
    result = export_tweets_to_csv(tweets=[])
    assert isinstance(result, str)


def test_export_includes_header_row() -> None:
    """Export includes CSV header row."""
    result = export_tweets_to_csv(tweets=[])
    first_line = result.split("\n")[0]
    assert "id" in first_line
    assert "text" in first_line
    assert "author_username" in first_line
    assert "created_at" in first_line


def test_export_includes_tweet_data() -> None:
    """Export includes tweet data rows."""
    tweet = make_tweet(tweet_id="999", text="Hello CSV", author_username="csvuser")
    result = export_tweets_to_csv(tweets=[tweet])
    assert "999" in result
    assert "Hello CSV" in result
    assert "csvuser" in result
