"""Tests for Markdown export functionality."""

from typing import Any

from tweethoarder.export.markdown_export import export_tweets_to_markdown


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


def test_export_formats_tweet_with_author(make_tweet: Any) -> None:
    """Export formats tweet with author username header."""
    tweet = make_tweet(author_username="example_user", created_at="2025-01-01T12:00:00Z")
    result = export_tweets_to_markdown(tweets=[tweet], collection="likes")
    assert "## @example_user" in result


def test_export_includes_tweet_date_in_iso_format(make_tweet: Any) -> None:
    """Export includes formatted date in YYYY-MM-DD HH:MM format."""
    tweet = make_tweet(created_at="2025-01-15T12:00:00Z")
    result = export_tweets_to_markdown(tweets=[tweet], collection="likes")
    assert "2025-01-15 12:00" in result


def test_export_includes_tweet_text(make_tweet: Any) -> None:
    """Export includes the tweet text content."""
    tweet = make_tweet(text="This is my tweet content")
    result = export_tweets_to_markdown(tweets=[tweet], collection="likes")
    assert "This is my tweet content" in result


def test_export_includes_twitter_link(make_tweet: Any) -> None:
    """Export includes link to view tweet on Twitter."""
    tweet = make_tweet(tweet_id="1234567890", author_username="example_user")
    result = export_tweets_to_markdown(tweets=[tweet], collection="likes")
    assert "[View on Twitter](https://twitter.com/example_user/status/1234567890)" in result


def test_export_preserves_input_order(make_tweet: Any) -> None:
    """Export preserves input order (database already sorts by added_at)."""
    first_tweet = make_tweet(
        tweet_id="1", author_username="first", created_at="2025-01-01T10:00:00Z"
    )
    second_tweet = make_tweet(
        tweet_id="2", author_username="second", created_at="2025-01-15T10:00:00Z"
    )
    # Input order should be preserved regardless of created_at
    result = export_tweets_to_markdown(tweets=[first_tweet, second_tweet], collection="likes")
    first_pos = result.find("@first")
    second_pos = result.find("@second")
    assert first_pos < second_pos, "Input order should be preserved"


def test_export_expands_tco_urls() -> None:
    """Export should expand t.co URLs to full URLs."""
    import json

    from tweethoarder.export.markdown_export import export_tweets_to_markdown

    tweet = {
        "id": "123",
        "text": "Check this out https://t.co/abc123",
        "author_username": "user",
        "author_id": "456",
        "created_at": "2025-01-01T12:00:00Z",
        "urls_json": json.dumps(
            [{"url": "https://t.co/abc123", "expanded_url": "https://example.com/full-url"}]
        ),
    }

    result = export_tweets_to_markdown([tweet], collection="likes")

    assert "https://example.com/full-url" in result
    assert "https://t.co/abc123" not in result


def test_export_strips_media_tco_urls() -> None:
    """Export should strip t.co URLs not in urls_json (media URLs)."""
    import json

    from tweethoarder.export.markdown_export import export_tweets_to_markdown

    tweet = {
        "id": "123",
        "text": "Check this https://t.co/link and image https://t.co/media123",
        "author_username": "user",
        "author_id": "456",
        "created_at": "2025-01-01T12:00:00Z",
        "urls_json": json.dumps(
            [{"url": "https://t.co/link", "expanded_url": "https://example.com"}]
        ),
    }

    result = export_tweets_to_markdown([tweet], collection="likes")

    assert "https://example.com" in result
    assert "https://t.co/media123" not in result


def test_export_groups_thread_tweets_when_context_provided(make_tweet: Any) -> None:
    """Export groups tweets with thread context, marking the liked tweet."""
    # The liked tweet (part of a thread)
    liked_tweet = make_tweet(
        tweet_id="456",
        author_username="bcherny",
        text="2/ This is the second tweet",
        created_at="2025-01-01T12:01:00Z",
        conversation_id="123",
    )

    # Thread context: tweets in the same conversation
    thread_tweets = [
        make_tweet(
            tweet_id="123",
            author_username="bcherny",
            text="1/ Starting a thread",
            created_at="2025-01-01T12:00:00Z",
            conversation_id="123",
        ),
        make_tweet(
            tweet_id="456",
            author_username="bcherny",
            text="2/ This is the second tweet",
            created_at="2025-01-01T12:01:00Z",
            conversation_id="123",
        ),
        make_tweet(
            tweet_id="789",
            author_username="bcherny",
            text="3/ Final tweet",
            created_at="2025-01-01T12:02:00Z",
            conversation_id="123",
        ),
    ]

    # thread_context maps conversation_id to list of tweets
    thread_context = {"123": thread_tweets}

    result = export_tweets_to_markdown(
        tweets=[liked_tweet], collection="likes", thread_context=thread_context
    )

    # Should show thread indicator
    assert "🧵" in result or "Thread by" in result
    # Should show all 3 tweets from the thread
    assert "1/ Starting a thread" in result
    assert "2/ This is the second tweet" in result
    assert "3/ Final tweet" in result
    # Should mark the liked tweet
    assert "⭐" in result


def test_export_does_not_show_conversation_with_multiple_authors_as_thread(
    make_tweet: Any,
) -> None:
    """Conversation with multiple authors should not be shown as a thread."""
    # The liked tweet
    liked_tweet = make_tweet(
        tweet_id="1",
        author_id="user1",
        author_username="adocomplete",
        text="Advent of Claude Day 31",
        created_at="2025-12-31T16:18:00Z",
        conversation_id="1",
    )

    # Conversation includes replies from other users (not a thread!)
    conversation_tweets = [
        make_tweet(
            tweet_id="1",
            author_id="user1",
            author_username="adocomplete",
            text="Advent of Claude Day 31",
            created_at="2025-12-31T16:18:00Z",
            conversation_id="1",
        ),
        make_tweet(
            tweet_id="2",
            author_id="user2",
            author_username="soholev",
            text="What about the primitives?",
            created_at="2025-12-31T16:20:00Z",
            conversation_id="1",
        ),
        make_tweet(
            tweet_id="3",
            author_id="user1",
            author_username="adocomplete",
            text="@soholev All the primitives are there",  # Reply to soholev
            created_at="2025-12-31T16:22:00Z",
            conversation_id="1",
        ),
    ]

    thread_context = {"1": conversation_tweets}

    result = export_tweets_to_markdown(
        tweets=[liked_tweet], collection="likes", thread_context=thread_context
    )

    # Should NOT show as a thread since there's only one non-reply tweet
    assert "🧵" not in result
    assert "Thread by" not in result
    # Should only show the single liked tweet
    assert "Advent of Claude Day 31" in result
    # Should NOT show other people's replies or replies to others
    assert "What about the primitives?" not in result


def test_export_does_not_show_replies_to_others_as_thread(make_tweet: Any) -> None:
    """Replies to other users are not a thread even if all from same author."""
    # The liked tweet
    liked_tweet = make_tweet(
        tweet_id="1",
        author_id="user1",
        author_username="adocomplete",
        text="Advent of Claude Day 31",
        created_at="2025-12-31T16:18:00Z",
        conversation_id="1",
    )

    # All tweets from same author, but some are replies to OTHER users
    conversation_tweets = [
        make_tweet(
            tweet_id="1",
            author_id="user1",
            author_username="adocomplete",
            text="Advent of Claude Day 31",
            created_at="2025-12-31T16:18:00Z",
            conversation_id="1",
        ),
        make_tweet(
            tweet_id="2",
            author_id="user1",
            author_username="adocomplete",
            text="@soholev All the primitives are there",  # Reply to someone else
            created_at="2025-12-31T16:20:00Z",
            conversation_id="1",
        ),
    ]

    thread_context = {"1": conversation_tweets}

    result = export_tweets_to_markdown(
        tweets=[liked_tweet], collection="likes", thread_context=thread_context
    )

    # Should NOT show as thread - replies to others are not a thread
    assert "🧵" not in result
    assert "Thread by" not in result
