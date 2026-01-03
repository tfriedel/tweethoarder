"""Tests for JSON export functionality."""

from typing import Any

from tweethoarder.export.json_export import export_tweets_to_json


def test_export_tweets_to_json_returns_dict() -> None:
    """Export function returns a dictionary."""
    result = export_tweets_to_json(tweets=[])
    assert isinstance(result, dict)


def test_export_includes_exported_at_timestamp() -> None:
    """Export includes exported_at timestamp in ISO format."""
    result = export_tweets_to_json(tweets=[])
    assert "exported_at" in result
    # ISO 8601 format check (simple validation)
    assert "T" in result["exported_at"]


def test_export_includes_collection_name() -> None:
    """Export includes collection name when specified."""
    result = export_tweets_to_json(tweets=[], collection="likes")
    assert result["collection"] == "likes"


def test_export_includes_tweet_count(make_tweet: Any) -> None:
    """Export includes count of tweets."""
    tweets = [make_tweet(tweet_id="1"), make_tweet(tweet_id="2"), make_tweet(tweet_id="3")]
    result = export_tweets_to_json(tweets=tweets)
    assert result["count"] == 3


def test_export_includes_tweets_array(make_tweet: Any) -> None:
    """Export includes tweets array with basic tweet data."""
    tweets = [make_tweet()]
    result = export_tweets_to_json(tweets=tweets)
    assert "tweets" in result
    assert len(result["tweets"]) == 1
    assert result["tweets"][0]["id"] == "123"
    assert result["tweets"][0]["text"] == "Hello world"
    assert result["tweets"][0]["created_at"] == "2025-01-01T12:00:00Z"


def test_export_formats_author_as_nested_object(make_tweet: Any) -> None:
    """Export formats author fields as nested object."""
    tweets = [make_tweet()]
    result = export_tweets_to_json(tweets=tweets)
    author = result["tweets"][0]["author"]
    assert author["id"] == "456"
    assert author["username"] == "testuser"
    assert author["display_name"] == "Test User"


def test_export_includes_metrics(make_tweet: Any) -> None:
    """Export includes tweet metrics as nested object."""
    tweets = [make_tweet(reply_count=10, retweet_count=50, like_count=200, quote_count=5)]
    result = export_tweets_to_json(tweets=tweets)
    metrics = result["tweets"][0]["metrics"]
    assert metrics["reply_count"] == 10
    assert metrics["retweet_count"] == 50
    assert metrics["like_count"] == 200


def test_export_includes_media(make_tweet: Any) -> None:
    """Export includes media from JSON field."""
    media_json = '[{"type": "photo", "url": "https://pbs.twimg.com/media/xxx.jpg"}]'
    tweets = [make_tweet(media_json=media_json)]
    result = export_tweets_to_json(tweets=tweets)
    media = result["tweets"][0]["media"]
    assert len(media) == 1
    assert media[0]["type"] == "photo"
    assert media[0]["url"] == "https://pbs.twimg.com/media/xxx.jpg"


def test_export_includes_quoted_tweet(make_tweet: Any) -> None:
    """Export includes quoted tweet when present."""
    quoted_tweet = make_tweet(
        tweet_id="999", text="Original tweet", author_username="original_user"
    )
    tweets = [make_tweet(quoted_tweet_id="999")]
    result = export_tweets_to_json(tweets=tweets, quoted_tweets={quoted_tweet["id"]: quoted_tweet})
    assert result["tweets"][0]["quoted_tweet"]["id"] == "999"
    assert result["tweets"][0]["quoted_tweet"]["text"] == "Original tweet"
