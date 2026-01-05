"""Tests for user replies sync functionality."""

from pathlib import Path

import pytest


def test_sync_replies_async_function_exists() -> None:
    """sync_replies_async function should be importable."""
    from tweethoarder.cli.sync import sync_replies_async

    assert callable(sync_replies_async)


def _make_reply_entry(tweet_id: str, in_reply_to_id: str, text: str = "Reply") -> dict:
    """Create a mock reply tweet entry for testing."""
    return {
        "entryId": f"tweet-{tweet_id}",
        "content": {
            "itemContent": {
                "tweet_results": {
                    "result": {
                        "rest_id": tweet_id,
                        "legacy": {
                            "full_text": text,
                            "created_at": "Wed Jan 01 12:00:00 +0000 2025",
                            "conversation_id_str": in_reply_to_id,
                            "in_reply_to_status_id_str": in_reply_to_id,
                            "reply_count": 0,
                            "retweet_count": 0,
                            "favorite_count": 0,
                            "quote_count": 0,
                        },
                        "core": {
                            "user_results": {
                                "result": {
                                    "rest_id": "456",
                                    "core": {
                                        "screen_name": "testuser",
                                        "name": "Test User",
                                    },
                                }
                            }
                        },
                    }
                }
            },
        },
    }


def _make_regular_tweet_entry(tweet_id: str, text: str = "Hello") -> dict:
    """Create a mock regular tweet entry for testing."""
    return {
        "entryId": f"tweet-{tweet_id}",
        "content": {
            "itemContent": {
                "tweet_results": {
                    "result": {
                        "rest_id": tweet_id,
                        "legacy": {
                            "full_text": text,
                            "created_at": "Wed Jan 01 12:00:00 +0000 2025",
                            "conversation_id_str": tweet_id,
                            "reply_count": 0,
                            "retweet_count": 0,
                            "favorite_count": 0,
                            "quote_count": 0,
                        },
                        "core": {
                            "user_results": {
                                "result": {
                                    "rest_id": "456",
                                    "core": {
                                        "screen_name": "testuser",
                                        "name": "Test User",
                                    },
                                }
                            }
                        },
                    }
                }
            },
        },
    }


def _make_replies_response(entries: list) -> dict:
    """Create a mock user tweets and replies API response."""
    return {
        "data": {
            "user": {
                "result": {
                    "timeline_v2": {
                        "timeline": {
                            "instructions": [{"type": "TimelineAddEntries", "entries": entries}]
                        }
                    }
                }
            }
        }
    }


@pytest.mark.asyncio
async def test_sync_replies_async_syncs_only_replies(tmp_path: Path) -> None:
    """sync_replies_async should sync only replies, not regular tweets."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_replies_async

    db_path = tmp_path / "test.db"

    # Response with one regular tweet and one reply
    mock_response = _make_replies_response(
        [
            _make_regular_tweet_entry("123", "Regular tweet"),
            _make_reply_entry("456", "999", "This is a reply"),
        ]
    )

    with (
        patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies,
        patch("tweethoarder.cli.sync.TwitterClient") as mock_client_class,
        patch("tweethoarder.cli.sync.get_config_dir") as mock_config_dir,
        patch("tweethoarder.cli.sync.get_query_id_with_fallback") as mock_get_query_id,
        patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_async_client,
    ):
        mock_cookies.return_value = {"twid": "u%3D789"}
        mock_client_class.return_value.get_base_headers.return_value = {}
        mock_config_dir.return_value = tmp_path
        mock_get_query_id.return_value = "ABC123"

        mock_http = AsyncMock()
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_http_response
        mock_async_client.return_value.__aenter__.return_value = mock_http

        result = await sync_replies_async(db_path, count=10)

        # Should only sync the reply, not the regular tweet
        assert result["synced_count"] == 1


def test_replies_command_exists() -> None:
    """Replies command should be available in sync CLI."""
    from typer.testing import CliRunner

    from tweethoarder.cli.sync import app

    runner = CliRunner()
    result = runner.invoke(app, ["replies", "--help"])

    assert result.exit_code == 0


def test_posts_command_exists() -> None:
    """Posts command should be available in sync CLI."""
    from typer.testing import CliRunner

    from tweethoarder.cli.sync import app

    runner = CliRunner()
    result = runner.invoke(app, ["posts", "--help"])

    assert result.exit_code == 0
    assert "tweets" in result.output.lower() or "replies" in result.output.lower()


def _make_parent_tweet_response(tweet_id: str, text: str) -> dict:
    """Create a mock TweetDetail response for a parent tweet."""
    return {
        "data": {
            "tweetResult": {
                "result": {
                    "rest_id": tweet_id,
                    "legacy": {
                        "full_text": text,
                        "created_at": "Wed Jan 01 10:00:00 +0000 2025",
                        "conversation_id_str": tweet_id,
                        "reply_count": 1,
                        "retweet_count": 0,
                        "favorite_count": 5,
                        "quote_count": 0,
                    },
                    "core": {
                        "user_results": {
                            "result": {
                                "rest_id": "111",
                                "legacy": {
                                    "screen_name": "parentauthor",
                                    "name": "Parent Author",
                                },
                            }
                        }
                    },
                }
            }
        }
    }


@pytest.mark.asyncio
async def test_sync_replies_async_fetches_parent_tweets(tmp_path: Path) -> None:
    """sync_replies_async should fetch and save parent tweets for replies."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_replies_async
    from tweethoarder.storage.database import get_tweets_by_ids, init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    # Response with two replies to different parent tweets
    mock_replies_response = _make_replies_response(
        [
            _make_reply_entry("reply1", "parent1", "Reply to parent1"),
            _make_reply_entry("reply2", "parent2", "Reply to parent2"),
        ]
    )

    # Mock parent tweet responses
    parent1_response = _make_parent_tweet_response("parent1", "Original tweet 1")
    parent2_response = _make_parent_tweet_response("parent2", "Original tweet 2")

    with (
        patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies,
        patch("tweethoarder.cli.sync.TwitterClient") as mock_client_class,
        patch("tweethoarder.cli.sync.get_config_dir") as mock_config_dir,
        patch("tweethoarder.cli.sync.get_query_id_with_fallback") as mock_get_query_id,
        patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_async_client,
    ):
        mock_cookies.return_value = {"twid": "u%3D789"}
        mock_client_class.return_value.get_base_headers.return_value = {}
        mock_config_dir.return_value = tmp_path
        # Return different query IDs for different endpoints
        mock_get_query_id.side_effect = lambda store, name: f"QID_{name}"

        mock_http = AsyncMock()

        # Set up get() to return different responses for different URLs
        def mock_get(url: str) -> MagicMock:
            response = MagicMock()
            response.raise_for_status = MagicMock()
            if "UserTweets" in url:
                response.json.return_value = mock_replies_response
            elif "parent1" in url:
                response.json.return_value = parent1_response
            elif "parent2" in url:
                response.json.return_value = parent2_response
            return response

        mock_http.get.side_effect = mock_get
        mock_async_client.return_value.__aenter__.return_value = mock_http

        result = await sync_replies_async(db_path, count=10)

        assert result["synced_count"] == 2

        # Verify parent tweets were saved
        parents = get_tweets_by_ids(db_path, ["parent1", "parent2"])
        assert len(parents) == 2
        parent_ids = {p["id"] for p in parents}
        assert parent_ids == {"parent1", "parent2"}
