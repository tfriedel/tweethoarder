"""Tests for user tweets sync functionality."""

import inspect
from pathlib import Path

import pytest


def test_sync_tweets_async_function_exists() -> None:
    """sync_tweets_async function should be importable."""
    from tweethoarder.cli.sync import sync_tweets_async

    assert callable(sync_tweets_async)


def test_build_user_tweets_url_includes_query_id() -> None:
    """build_user_tweets_url should include the query ID in the path."""
    from tweethoarder.client.timelines import build_user_tweets_url

    url = build_user_tweets_url(query_id="ABC123", user_id="12345")

    assert "ABC123" in url
    assert "/graphql/" in url


def test_build_user_tweets_url_includes_user_id() -> None:
    """build_user_tweets_url should include user_id in variables."""
    from tweethoarder.client.timelines import build_user_tweets_url

    url = build_user_tweets_url(query_id="ABC123", user_id="12345")

    assert "userId" in url
    assert "12345" in url


def test_build_user_tweets_url_includes_cursor() -> None:
    """build_user_tweets_url should include cursor when provided."""
    from tweethoarder.client.timelines import build_user_tweets_url

    url = build_user_tweets_url(query_id="ABC123", user_id="12345", cursor="cursor_xyz")

    assert "cursor_xyz" in url


def test_fetch_user_tweets_page_exists() -> None:
    """fetch_user_tweets_page function should be importable."""
    from tweethoarder.client.timelines import fetch_user_tweets_page

    assert callable(fetch_user_tweets_page)


@pytest.mark.asyncio
async def test_fetch_user_tweets_page_returns_dict() -> None:
    """fetch_user_tweets_page should return parsed JSON response."""
    from unittest.mock import AsyncMock, MagicMock

    from tweethoarder.client.timelines import fetch_user_tweets_page

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"user": {"result": {}}}}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    result = await fetch_user_tweets_page(
        client=mock_client,
        query_id="ABC123",
        user_id="12345",
    )

    assert isinstance(result, dict)
    assert "data" in result


@pytest.mark.asyncio
async def test_fetch_user_tweets_page_calls_client_get() -> None:
    """fetch_user_tweets_page should call client.get with the URL."""
    from unittest.mock import AsyncMock, MagicMock

    from tweethoarder.client.timelines import fetch_user_tweets_page

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {}}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    await fetch_user_tweets_page(
        client=mock_client,
        query_id="ABC123",
        user_id="12345",
    )

    mock_client.get.assert_called_once()
    call_url = mock_client.get.call_args[0][0]
    assert "ABC123" in call_url
    assert "12345" in call_url


@pytest.mark.asyncio
async def test_fetch_user_tweets_page_retries_on_429() -> None:
    """fetch_user_tweets_page should retry on 429 rate limit with exponential backoff."""
    from unittest.mock import AsyncMock, MagicMock

    from tweethoarder.client.timelines import fetch_user_tweets_page

    rate_limit_response = MagicMock()
    rate_limit_response.status_code = 429

    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = {"data": {"user": {"result": {}}}}
    success_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.side_effect = [rate_limit_response, success_response]

    result = await fetch_user_tweets_page(
        client=mock_client,
        query_id="ABC123",
        user_id="12345",
        max_retries=5,
        base_delay=0.01,
    )

    assert mock_client.get.call_count == 2
    assert "data" in result


def test_parse_user_tweets_response_exists() -> None:
    """parse_user_tweets_response function should be importable."""
    from tweethoarder.client.timelines import parse_user_tweets_response

    assert callable(parse_user_tweets_response)


def test_parse_user_tweets_response_extracts_tweets_with_sort_index() -> None:
    """parse_user_tweets_response should extract tweets with sort_index from response."""
    from tweethoarder.client.timelines import parse_user_tweets_response

    response = {
        "data": {
            "user": {
                "result": {
                    "timeline_v2": {
                        "timeline": {
                            "instructions": [
                                {
                                    "type": "TimelineAddEntries",
                                    "entries": [
                                        {
                                            "entryId": "tweet-123",
                                            "sortIndex": "1234567890",
                                            "content": {
                                                "itemContent": {
                                                    "tweet_results": {"result": {"rest_id": "123"}}
                                                }
                                            },
                                        }
                                    ],
                                }
                            ]
                        }
                    }
                }
            }
        }
    }

    entries, _cursor = parse_user_tweets_response(response)

    assert len(entries) == 1
    assert entries[0]["tweet"]["rest_id"] == "123"
    assert entries[0]["sort_index"] == "1234567890"


@pytest.mark.asyncio
async def test_sync_tweets_async_syncs_tweets(tmp_path: Path) -> None:
    """sync_tweets_async should sync tweets to database."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_tweets_async

    db_path = tmp_path / "test.db"

    mock_response = {
        "data": {
            "user": {
                "result": {
                    "timeline_v2": {
                        "timeline": {
                            "instructions": [
                                {
                                    "type": "TimelineAddEntries",
                                    "entries": [
                                        {
                                            "entryId": "tweet-123",
                                            "content": {
                                                "itemContent": {
                                                    "tweet_results": {
                                                        "result": {
                                                            "rest_id": "123",
                                                            "legacy": {
                                                                "full_text": "Hello world",
                                                                "created_at": "Wed Jan 01 12:00:00 +0000 2025",  # noqa: E501
                                                                "conversation_id_str": "123",
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
                                                                            "screen_name": "testuser",  # noqa: E501
                                                                            "name": "Test User",
                                                                        },
                                                                    }
                                                                }
                                                            },
                                                        }
                                                    }
                                                }
                                            },
                                        }
                                    ],
                                }
                            ]
                        }
                    }
                }
            }
        }
    }

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

        result = await sync_tweets_async(db_path, count=10)

        assert result["synced_count"] == 1


def test_tweets_command_accepts_count_option() -> None:
    """Tweets command should accept a --count option."""
    from typer.testing import CliRunner

    from tweethoarder.cli.sync import app

    runner = CliRunner()
    result = runner.invoke(app, ["tweets", "--help"])

    assert "--count" in result.output or "-c" in result.output


def test_tweets_command_accepts_all_flag() -> None:
    """Tweets command should accept an --all flag."""
    import re

    from typer.testing import CliRunner

    from tweethoarder.cli.sync import app

    runner = CliRunner()
    result = runner.invoke(app, ["tweets", "--help"])

    # Strip ANSI escape codes for reliable matching
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--all" in clean_output


def test_tweets_command_calls_sync_tweets_async() -> None:
    """Tweets command should call sync_tweets_async."""
    from unittest.mock import AsyncMock, patch

    from typer.testing import CliRunner

    from tweethoarder.cli.sync import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_tweets_async", new_callable=AsyncMock) as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        result = runner.invoke(app, ["tweets", "--count", "10"])

        mock_sync.assert_called_once()
        assert "5" in result.output


def test_sync_tweets_async_accepts_with_threads_parameter() -> None:
    """sync_tweets_async should accept with_threads parameter."""
    from tweethoarder.cli.sync import sync_tweets_async

    sig = inspect.signature(sync_tweets_async)
    params = list(sig.parameters.keys())

    assert "with_threads" in params


def test_sync_tweets_async_accepts_thread_mode_parameter() -> None:
    """sync_tweets_async should accept thread_mode parameter."""
    from tweethoarder.cli.sync import sync_tweets_async

    sig = inspect.signature(sync_tweets_async)
    params = list(sig.parameters.keys())

    assert "thread_mode" in params


def test_tweets_command_passes_with_threads_to_async() -> None:
    """The tweets CLI command should pass with_threads to sync_tweets_async."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from tweethoarder.cli.main import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_tweets_async") as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        runner.invoke(app, ["sync", "tweets", "--with-threads"])

        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs.get("with_threads") is True


def test_tweets_command_passes_thread_mode_to_async() -> None:
    """The tweets CLI command should pass thread_mode to sync_tweets_async."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from tweethoarder.cli.main import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_tweets_async") as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        runner.invoke(app, ["sync", "tweets", "--thread-mode", "conversation"])

        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs.get("thread_mode") == "conversation"


def _make_tweet_entry(tweet_id: str, text: str = "Hello") -> dict:
    """Create a mock tweet entry for testing."""
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


def _make_tweets_response(entries: list) -> dict:
    """Create a mock user tweets API response."""
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


def test_sync_tweets_async_accepts_store_raw_parameter() -> None:
    """sync_tweets_async should accept store_raw parameter."""
    from tweethoarder.cli.sync import sync_tweets_async

    sig = inspect.signature(sync_tweets_async)
    params = list(sig.parameters.keys())

    assert "store_raw" in params


def test_tweets_command_passes_store_raw_to_async() -> None:
    """The tweets CLI command should pass store_raw to sync_tweets_async."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from tweethoarder.cli.main import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_tweets_async") as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        runner.invoke(app, ["sync", "tweets", "--store-raw"])

        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs.get("store_raw") is True


@pytest.mark.asyncio
async def test_sync_tweets_async_stores_raw_json_when_store_raw_enabled(tmp_path: Path) -> None:
    """sync_tweets_async should store raw_json in database when store_raw=True."""
    import sqlite3
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_tweets_async

    db_path = tmp_path / "test.db"
    mock_response = _make_tweets_response([_make_tweet_entry("123", "Hello")])

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

        await sync_tweets_async(db_path, count=10, store_raw=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT raw_json FROM tweets WHERE id = ?", ("123",))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] is not None


@pytest.mark.asyncio
async def test_sync_tweets_async_fetches_threads_for_all_synced_tweets(tmp_path: Path) -> None:
    """sync_tweets_async should fetch threads for ALL synced tweets, not just the last one."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_tweets_async

    db_path = tmp_path / "test.db"

    # Create response with 3 tweets
    mock_response = _make_tweets_response(
        [
            _make_tweet_entry("111", "First"),
            _make_tweet_entry("222", "Second"),
            _make_tweet_entry("333", "Third"),
        ]
    )

    with (
        patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies,
        patch("tweethoarder.cli.sync.TwitterClient") as mock_client_class,
        patch("tweethoarder.cli.sync.get_config_dir") as mock_config_dir,
        patch("tweethoarder.cli.sync.get_query_id_with_fallback") as mock_get_query_id,
        patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_async_client,
        patch("tweethoarder.cli.thread.fetch_thread_async") as mock_fetch_thread,
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

        mock_fetch_thread.return_value = {"tweet_count": 5}

        await sync_tweets_async(db_path, count=10, with_threads=True)

        # Should be called 3 times - once for each synced tweet
        assert mock_fetch_thread.call_count == 3
        # Verify each tweet ID was passed
        call_tweet_ids = [call[1]["tweet_id"] for call in mock_fetch_thread.call_args_list]
        assert set(call_tweet_ids) == {"111", "222", "333"}


@pytest.mark.asyncio
async def test_sync_tweets_async_excludes_replies(tmp_path: Path) -> None:
    """sync_tweets_async should NOT sync tweets that are replies."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_tweets_async

    db_path = tmp_path / "test.db"

    # Response with one regular tweet and one reply
    mock_response = _make_tweets_response(
        [
            _make_tweet_entry("123", "Regular tweet"),
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

        result = await sync_tweets_async(db_path, count=10)

        # Should only sync the regular tweet, not the reply
        assert result["synced_count"] == 1


def test_sync_tweets_async_accepts_full_parameter() -> None:
    """sync_tweets_async should accept full parameter for forcing complete resync."""
    import inspect

    from tweethoarder.cli.sync import sync_tweets_async

    sig = inspect.signature(sync_tweets_async)
    params = list(sig.parameters.keys())

    assert "full" in params


@pytest.mark.asyncio
async def test_sync_tweets_async_stops_on_duplicate(tmp_path: Path) -> None:
    """sync_tweets_async should stop when encountering an existing tweet in the collection."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_tweets_async
    from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

    db_path = tmp_path / "test.db"
    init_database(db_path)

    # Pre-populate with an existing tweet
    save_tweet(
        db_path,
        {
            "id": "existing",
            "text": "Already synced",
            "author_id": "456",
            "author_username": "user",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    add_to_collection(db_path, "existing", "tweet")

    # API returns: new_tweet, then existing_tweet
    mock_response = _make_tweets_response(
        [
            _make_tweet_entry("new_tweet", "New tweet"),
            _make_tweet_entry("existing", "Already synced"),
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

        result = await sync_tweets_async(db_path, count=100)

    # Should only sync the new tweet, not the existing one
    assert result["synced_count"] == 1


@pytest.mark.asyncio
async def test_sync_tweets_async_stops_immediately_when_first_is_duplicate(
    tmp_path: Path,
) -> None:
    """sync_tweets_async should stop immediately when the first tweet is already synced."""
    from typing import Any
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_tweets_async
    from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

    db_path = tmp_path / "test.db"
    init_database(db_path)

    # Pre-populate - ALL tweets are already synced
    save_tweet(
        db_path,
        {
            "id": "already_synced_1",
            "text": "Already synced 1",
            "author_id": "456",
            "author_username": "user",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    add_to_collection(db_path, "already_synced_1", "tweet")

    # API returns only already-synced tweets (with cursor for more pages)
    page1_response = {
        "data": {
            "user": {
                "result": {
                    "timeline_v2": {
                        "timeline": {
                            "instructions": [
                                {
                                    "type": "TimelineAddEntries",
                                    "entries": [
                                        _make_tweet_entry("already_synced_1", "Already synced 1"),
                                        {
                                            "entryId": "cursor-bottom-0",
                                            "content": {
                                                "cursorType": "Bottom",
                                                "value": "next_cursor_value",
                                            },
                                        },
                                    ],
                                },
                            ]
                        }
                    }
                }
            }
        }
    }

    call_count = [0]

    def mock_get(*args: Any, **kwargs: Any) -> MagicMock:
        call_count[0] += 1
        if call_count[0] > 1:
            raise AssertionError(
                f"sync_tweets_async made {call_count[0]} API calls but should stop "
                "after first page when hitting duplicate."
            )
        response = MagicMock()
        response.json.return_value = page1_response
        response.raise_for_status = MagicMock()
        return response

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
        mock_http.get.side_effect = mock_get
        mock_async_client.return_value.__aenter__.return_value = mock_http

        result = await sync_tweets_async(db_path, count=100)

        # Should only make ONE API call, not keep fetching pages
        assert call_count[0] == 1

    # Should sync 0 tweets (all were duplicates)
    assert result["synced_count"] == 0


def test_tweets_command_accepts_full_flag() -> None:
    """Tweets CLI command should accept --full flag."""
    import re

    from typer.testing import CliRunner

    from tweethoarder.cli.sync import app

    runner = CliRunner()
    result = runner.invoke(app, ["tweets", "--help"])

    # Strip ANSI escape codes for reliable matching
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--full" in clean_output
