"""Markdown export functionality for TweetHoarder."""

import json
import re
from datetime import UTC, datetime
from typing import Any

from tweethoarder.export.richtext import (
    apply_richtext_tags_markdown,
    extract_richtext_tags,
)

COLLECTION_TITLES = {
    "likes": "Liked Tweets",
    "bookmarks": "Bookmarked Tweets",
    "tweets": "My Tweets",
    "reposts": "Reposted Tweets",
    "replies": "My Replies",
    "posts": "My Posts",
}


def _linkify_mentions(text: str) -> str:
    """Convert @mentions to markdown links."""
    return re.sub(r"@(\w+)", r"[@\1](https://x.com/\1)", text)


def _format_tweet_text(tweet: dict[str, Any]) -> str:
    """Format tweet text with URL expansion, mention links, and rich text formatting.

    Args:
        tweet: Tweet dictionary containing text, urls_json, and optionally raw_json.

    Returns:
        Formatted text with expanded URLs, clickable mentions, and bold/italic formatting.
    """
    text = tweet.get("text", "")
    urls_json = tweet.get("urls_json")
    raw_json = tweet.get("raw_json")

    # Extract richtext tags first (before URL expansion changes positions)
    richtext_tags = extract_richtext_tags(raw_json)

    # Apply rich text formatting if available (must be done on original text indices)
    if richtext_tags:
        text = apply_richtext_tags_markdown(text, richtext_tags)

    # Then expand URLs and linkify mentions
    text = _expand_urls(text, urls_json)
    text = _linkify_mentions(text)

    return text


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


def _format_quoted_tweet(quoted_tweet: dict[str, Any]) -> list[str]:
    """Format a quoted tweet as a blockquote."""
    lines: list[str] = []
    qt_username = quoted_tweet.get("author_username", "unknown")
    qt_display = quoted_tweet.get("author_display_name") or qt_username
    qt_text = _format_tweet_text(quoted_tweet)
    qt_id = quoted_tweet.get("id", "")

    lines.append("> **Quote:**")
    lines.append(f"> **{qt_display}** [@{qt_username}](https://x.com/{qt_username})")
    lines.append(">")
    # Indent each line of the quoted tweet text
    for text_line in qt_text.split("\n"):
        lines.append(f"> {text_line}")
    lines.append(">")
    lines.append(f"> [View quoted tweet](https://x.com/{qt_username}/status/{qt_id})")
    return lines


def _format_parent_tweet(parent_tweet: dict[str, Any]) -> list[str]:
    """Format a parent tweet (for replies) as a blockquote."""
    lines: list[str] = []
    pt_username = parent_tweet.get("author_username", "unknown")
    pt_display = parent_tweet.get("author_display_name") or pt_username
    pt_text = _format_tweet_text(parent_tweet)
    pt_id = parent_tweet.get("id", "")

    lines.append(f"> **In reply to @{pt_username}:**")
    lines.append(f"> **{pt_display}** [@{pt_username}](https://x.com/{pt_username})")
    lines.append(">")
    # Indent each line of the parent tweet text
    for text_line in pt_text.split("\n"):
        lines.append(f"> {text_line}")
    lines.append(">")
    lines.append(f"> [View original](https://x.com/{pt_username}/status/{pt_id})")
    return lines


def export_tweets_to_markdown(
    tweets: list[dict[str, Any]],
    collection: str | None = None,
    thread_context: dict[str, list[dict[str, Any]]] | None = None,
    quoted_tweets: dict[str, dict[str, Any]] | None = None,
    parent_tweets: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Export tweets to Markdown format.

    Args:
        tweets: List of tweet dictionaries to export.
        collection: Optional collection name for title.
        thread_context: Optional dict mapping conversation_id to list of thread tweets.
        quoted_tweets: Optional dict mapping tweet_id to quoted tweet data.
        parent_tweets: Optional dict mapping tweet_id to parent tweet data (for replies).

    Returns:
        Markdown formatted string.
    """
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
                text = _format_tweet_text(t)
                if t.get("id") == liked_tweet_id:
                    lines.append(f"⭐ {text}")
                else:
                    lines.append(text)
                lines.append("")
        else:
            lines.append(f"## @{username} - {date_str}")
            lines.append("")

            # For replies, show parent tweet context first
            in_reply_to_id = tweet.get("in_reply_to_tweet_id")
            if in_reply_to_id and parent_tweets:
                parent_tweet = parent_tweets.get(in_reply_to_id)
                if parent_tweet:
                    lines.extend(_format_parent_tweet(parent_tweet))
                    lines.append("")

            text = _format_tweet_text(tweet)
            lines.append(text)
            lines.append("")

        # Render quoted tweet if present
        quoted_tweet_id = tweet.get("quoted_tweet_id")
        if quoted_tweet_id and quoted_tweets:
            quoted_tweet = quoted_tweets.get(quoted_tweet_id)
            if quoted_tweet:
                lines.extend(_format_quoted_tweet(quoted_tweet))
                lines.append("")

        tweet_id = tweet.get("id", "")
        lines.append(f"[View on Twitter](https://twitter.com/{username}/status/{tweet_id})")

    return "\n".join(lines)
