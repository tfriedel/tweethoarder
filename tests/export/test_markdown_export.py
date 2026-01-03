"""Tests for Markdown export functionality."""

from typing import Any

from tweethoarder.export.markdown_export import export_tweets_to_markdown


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


def test_export_tweets_to_markdown_returns_string() -> None:
    """Export function returns a string."""
    result = export_tweets_to_markdown(tweets=[])
    assert isinstance(result, str)


def test_export_includes_collection_title() -> None:
    """Export includes collection name as title."""
    result = export_tweets_to_markdown(tweets=[], collection="likes")
    assert "# Liked Tweets" in result


def test_export_includes_exported_timestamp() -> None:
    """Export includes exported timestamp."""
    result = export_tweets_to_markdown(tweets=[], collection="likes")
    assert "Exported:" in result


def test_export_includes_total_count() -> None:
    """Export includes total count of tweets."""
    result = export_tweets_to_markdown(tweets=[{}, {}, {}], collection="likes")
    assert "Total: 3 tweets" in result


def test_export_formats_tweet_with_author() -> None:
    """Export formats tweet with author username header."""
    tweet = make_tweet(author_username="example_user", created_at="2025-01-01T12:00:00Z")
    result = export_tweets_to_markdown(tweets=[tweet], collection="likes")
    assert "## @example_user" in result


def test_export_includes_tweet_date() -> None:
    """Export includes formatted date from tweet."""
    tweet = make_tweet(created_at="2025-01-15T12:00:00Z")
    result = export_tweets_to_markdown(tweets=[tweet], collection="likes")
    assert "Jan 15, 2025" in result


def test_export_includes_tweet_text() -> None:
    """Export includes the tweet text content."""
    tweet = make_tweet(text="This is my tweet content")
    result = export_tweets_to_markdown(tweets=[tweet], collection="likes")
    assert "This is my tweet content" in result


def test_export_includes_twitter_link() -> None:
    """Export includes link to view tweet on Twitter."""
    tweet = make_tweet(tweet_id="1234567890", author_username="example_user")
    result = export_tweets_to_markdown(tweets=[tweet], collection="likes")
    assert "[View on Twitter](https://twitter.com/example_user/status/1234567890)" in result
