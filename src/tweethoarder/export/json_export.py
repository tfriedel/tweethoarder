"""JSON export functionality for TweetHoarder."""

import json
from datetime import UTC, datetime
from typing import Any


def _format_tweet(
    tweet: dict[str, Any],
    quoted_tweets: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Format a tweet for export with nested author object."""
    formatted: dict[str, Any] = {
        "id": tweet["id"],
        "text": tweet["text"],
        "created_at": tweet["created_at"],
        "author": {
            "id": tweet["author_id"],
            "username": tweet["author_username"],
            "display_name": tweet["author_display_name"],
        },
    }
    if "reply_count" in tweet:
        formatted["metrics"] = {
            "reply_count": tweet["reply_count"],
            "retweet_count": tweet["retweet_count"],
            "like_count": tweet["like_count"],
        }
    if tweet.get("media_json"):
        formatted["media"] = json.loads(tweet["media_json"])
    quoted_id = tweet.get("quoted_tweet_id")
    if quoted_id and quoted_tweets and quoted_id in quoted_tweets:
        formatted["quoted_tweet"] = _format_tweet(quoted_tweets[quoted_id])
    return formatted


def export_tweets_to_json(
    tweets: list[dict[str, Any]],
    collection: str | None = None,
    quoted_tweets: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Export tweets to a JSON-serializable dictionary."""
    result: dict[str, Any] = {
        "exported_at": datetime.now(UTC).isoformat(),
        "count": len(tweets),
        "tweets": [_format_tweet(t, quoted_tweets) for t in tweets],
    }
    if collection is not None:
        result["collection"] = collection
    return result
