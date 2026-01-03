"""Tests for CSV export functionality."""

from typing import Any

from tweethoarder.export.csv_export import export_tweets_to_csv


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


def test_export_includes_tweet_data(make_tweet: Any) -> None:
    """Export includes tweet data rows."""
    tweet = make_tweet(tweet_id="999", text="Hello CSV", author_username="csvuser")
    result = export_tweets_to_csv(tweets=[tweet])
    assert "999" in result
    assert "Hello CSV" in result
    assert "csvuser" in result
