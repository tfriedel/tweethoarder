"""Shared test fixtures and utilities."""

import os
from typing import Any

import pytest

# Disable Rich color output for consistent test output across environments
os.environ["NO_COLOR"] = "1"


def _make_tweet(
    tweet_id: str = "123",
    text: str = "Hello world",
    author_id: str = "456",
    author_username: str = "testuser",
    author_display_name: str = "Test User",
    created_at: str = "2025-01-01T12:00:00Z",
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a test tweet with sensible defaults.

    Args:
        tweet_id: The tweet's unique identifier.
        text: The tweet content.
        author_id: The author's unique identifier.
        author_username: The author's username.
        author_display_name: The author's display name.
        created_at: ISO 8601 timestamp of tweet creation.
        **kwargs: Additional tweet fields to include.

    Returns:
        A dictionary representing a tweet with the specified fields.
    """
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


@pytest.fixture
def make_tweet() -> Any:
    """Fixture that provides the make_tweet factory function."""
    return _make_tweet
