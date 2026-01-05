"""Markdown export functionality for TweetHoarder."""

import json
import re
from datetime import UTC, datetime
from typing import Any

COLLECTION_TITLES = {
    "likes": "Liked Tweets",
    "bookmarks": "Bookmarked Tweets",
    "tweets": "My Tweets",
    "reposts": "Reposted Tweets",
}


def _linkify_mentions(text: str) -> str:
    """Convert @mentions to markdown links."""
    return re.sub(r"@(\w+)", r"[@\1](https://x.com/\1)", text)


def _expand_urls(text: str, urls_json: str | None) -> str:
    """Expand t.co URLs to their full URLs and strip media t.co URLs."""
    if urls_json:
        try:
            urls = json.loads(urls_json)
            for url_info in urls:
                short_url = url_info.get("url", "")
                expanded_url = url_info.get("expanded_url", "")
                if short_url and expanded_url:
                    text = text.replace(short_url, expanded_url)
        except (json.JSONDecodeError, TypeError):
            pass
    # Strip remaining t.co URLs (media URLs not in urls_json)
    text = re.sub(r"\s*https://t\.co/\w+", "", text)
    return text


def export_tweets_to_markdown(
    tweets: list[dict[str, Any]],
    collection: str | None = None,
    thread_context: dict[str, list[dict[str, Any]]] | None = None,
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

        # Check if tweet has thread context (thread = same author's tweets only)
        conversation_id = tweet.get("conversation_id")
        author_id = tweet.get("author_id")
        thread_tweets: list[dict[str, Any]] = []
        if thread_context and conversation_id and author_id:
            all_conv_tweets = thread_context.get(conversation_id, [])
            # Filter to same author's tweets that are NOT replies to other users
            # (replies to others start with @username and are not part of the thread)
            for t in all_conv_tweets:
                if t.get("author_id") != author_id:
                    continue
                text = t.get("text", "")
                # Include if: root tweet OR doesn't start with @ (not a reply to someone)
                if t.get("id") == conversation_id or not text.startswith("@"):
                    thread_tweets.append(t)

        if len(thread_tweets) > 1:
            lines.append(f"## 🧵 Thread by @{username} - {date_str}")
            lines.append("")
            liked_tweet_id = tweet.get("id", "")
            sorted_tweets = sorted(thread_tweets, key=lambda t: t.get("created_at", ""))
            for t in sorted_tweets:
                text = _linkify_mentions(_expand_urls(t.get("text", ""), t.get("urls_json")))
                if t.get("id") == liked_tweet_id:
                    lines.append(f"⭐ {text}")
                else:
                    lines.append(text)
                lines.append("")
        else:
            lines.append(f"## @{username} - {date_str}")
            lines.append("")
            text = _linkify_mentions(_expand_urls(tweet.get("text", ""), tweet.get("urls_json")))
            lines.append(text)
            lines.append("")
        tweet_id = tweet.get("id", "")
        lines.append(f"[View on Twitter](https://twitter.com/{username}/status/{tweet_id})")

    return "\n".join(lines)
