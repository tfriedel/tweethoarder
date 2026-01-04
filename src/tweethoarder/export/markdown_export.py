"""Markdown export functionality for TweetHoarder."""

from datetime import UTC, datetime
from typing import Any

COLLECTION_TITLES = {
    "likes": "Liked Tweets",
    "bookmarks": "Bookmarked Tweets",
    "tweets": "My Tweets",
    "reposts": "Reposted Tweets",
}


def export_tweets_to_markdown(
    tweets: list[dict[str, Any]],
    collection: str | None = None,
) -> str:
    """Export tweets to Markdown format."""
    lines: list[str] = []

    if collection:
        title = COLLECTION_TITLES.get(collection, f"{collection.title()} Tweets")
        lines.append(f"# {title}")

    lines.append("")
    lines.append(f"Exported: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    lines.append(f"Total: {len(tweets):,} tweets")

    for tweet in tweets:
        lines.append("")
        lines.append("---")
        lines.append("")
        username = tweet.get("author_username", "unknown")
        created_at = tweet.get("created_at", "")
        # Parse ISO date to YYYY-MM-DD HH:MM format
        if created_at:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        else:
            date_str = ""
        lines.append(f"## @{username} - {date_str}")
        lines.append("")
        lines.append(tweet.get("text", ""))
        lines.append("")
        tweet_id = tweet.get("id", "")
        lines.append(f"[View on Twitter](https://twitter.com/{username}/status/{tweet_id})")

    return "\n".join(lines)
