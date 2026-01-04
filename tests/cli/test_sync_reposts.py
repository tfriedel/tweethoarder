"""Tests for user reposts sync functionality."""

import inspect
from pathlib import Path

import pytest


def test_sync_reposts_async_function_exists() -> None:
    """sync_reposts_async function should be importable."""
    from tweethoarder.cli.sync import sync_reposts_async

    assert callable(sync_reposts_async)


def test_is_repost_exists() -> None:
    """is_repost function should be importable."""
    from tweethoarder.client.timelines import is_repost

    assert callable(is_repost)


def test_is_repost_detects_retweet() -> None:
    """is_repost should return True for tweets with retweeted_status_result."""
    from tweethoarder.client.timelines import is_repost

    retweet = {"legacy": {"retweeted_status_result": {"result": {"rest_id": "123"}}}}

    assert is_repost(retweet) is True


def test_is_repost_returns_false_for_regular_tweet() -> None:
    """is_repost should return False for regular tweets."""
    from tweethoarder.client.timelines import is_repost

    regular_tweet = {"legacy": {"full_text": "Hello world"}}

    assert is_repost(regular_tweet) is False


@pytest.mark.asyncio
async def test_sync_reposts_async_syncs_reposts(tmp_path: Path) -> None:
    """sync_reposts_async should sync only reposts to database."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_reposts_async

    db_path = tmp_path / "test.db"

    # Response with one regular tweet and one repost
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
                                                                "full_text": "Regular tweet",
                                                                "created_at": "Wed Jan 01 12:00:00 +0000 2025",  # noqa: E501
                                                                "conversation_id_str": "123",
                                                            },
                                                            "core": {
                                                                "user_results": {
                                                                    "result": {
                                                                        "rest_id": "456",
                                                                        "core": {
                                                                            "screen_name": "testuser",  # noqa: E501
                                                                            "name": "Test",
                                                                        },
                                                                    }
                                                                }
                                                            },
                                                        }
                                                    }
                                                }
                                            },
                                        },
                                        {
                                            "entryId": "tweet-456",
                                            "content": {
                                                "itemContent": {
                                                    "tweet_results": {
                                                        "result": {
                                                            "rest_id": "456",
                                                            "legacy": {
                                                                "full_text": "RT @other: Repost",
                                                                "created_at": "Wed Jan 01 12:00:00 +0000 2025",  # noqa: E501
                                                                "conversation_id_str": "456",
                                                                "retweeted_status_result": {
                                                                    "result": {"rest_id": "789"}
                                                                },
                                                            },
                                                            "core": {
                                                                "user_results": {
                                                                    "result": {
                                                                        "rest_id": "456",
                                                                        "core": {
                                                                            "screen_name": "testuser",  # noqa: E501
                                                                            "name": "Test",
                                                                        },
                                                                    }
                                                                }
                                                            },
                                                        }
                                                    }
                                                }
                                            },
                                        },
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

        result = await sync_reposts_async(db_path, count=10)

        # Should only sync the repost, not the regular tweet
        assert result["synced_count"] == 1


def test_reposts_command_accepts_count_option() -> None:
    """Reposts command should accept a --count option."""
    from typer.testing import CliRunner

    from tweethoarder.cli.sync import app

    runner = CliRunner()
    result = runner.invoke(app, ["reposts", "--help"])

    assert "--count" in result.output or "-c" in result.output


def test_reposts_command_accepts_all_flag() -> None:
    """Reposts command should accept an --all flag."""
    import re

    from typer.testing import CliRunner

    from tweethoarder.cli.sync import app

    runner = CliRunner()
    result = runner.invoke(app, ["reposts", "--help"])

    # Strip ANSI escape codes for reliable matching
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--all" in clean_output


def test_reposts_command_calls_sync_reposts_async() -> None:
    """Reposts command should call sync_reposts_async."""
    from unittest.mock import AsyncMock, patch

    from typer.testing import CliRunner

    from tweethoarder.cli.sync import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_reposts_async", new_callable=AsyncMock) as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        result = runner.invoke(app, ["reposts", "--count", "10"])

        mock_sync.assert_called_once()
        assert "5" in result.output


def test_sync_reposts_async_accepts_with_threads_parameter() -> None:
    """sync_reposts_async should accept with_threads parameter."""
    from tweethoarder.cli.sync import sync_reposts_async

    sig = inspect.signature(sync_reposts_async)
    params = list(sig.parameters.keys())

    assert "with_threads" in params


def test_sync_reposts_async_accepts_thread_mode_parameter() -> None:
    """sync_reposts_async should accept thread_mode parameter."""
    from tweethoarder.cli.sync import sync_reposts_async

    sig = inspect.signature(sync_reposts_async)
    params = list(sig.parameters.keys())

    assert "thread_mode" in params


def test_reposts_command_passes_with_threads_to_async() -> None:
    """The reposts CLI command should pass with_threads to sync_reposts_async."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from tweethoarder.cli.main import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_reposts_async") as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        runner.invoke(app, ["sync", "reposts", "--with-threads"])

        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs.get("with_threads") is True


def test_reposts_command_passes_thread_mode_to_async() -> None:
    """The reposts CLI command should pass thread_mode to sync_reposts_async."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from tweethoarder.cli.main import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_reposts_async") as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        runner.invoke(app, ["sync", "reposts", "--thread-mode", "conversation"])

        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs.get("thread_mode") == "conversation"


def _make_repost_entry(tweet_id: str, text: str = "RT @other: Repost") -> dict:
    """Create a mock repost entry for testing."""
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
                            "retweeted_status_result": {"result": {"rest_id": "789"}},
                        },
                        "core": {
                            "user_results": {
                                "result": {
                                    "rest_id": "456",
                                    "core": {"screen_name": "testuser", "name": "Test"},
                                }
                            }
                        },
                    }
                }
            },
        },
    }


def _make_reposts_response(entries: list) -> dict:
    """Create a mock user reposts API response."""
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


def test_sync_reposts_async_accepts_store_raw_parameter() -> None:
    """sync_reposts_async should accept store_raw parameter."""
    from tweethoarder.cli.sync import sync_reposts_async

    sig = inspect.signature(sync_reposts_async)
    params = list(sig.parameters.keys())

    assert "store_raw" in params


def test_reposts_command_passes_store_raw_to_async() -> None:
    """The reposts CLI command should pass store_raw to sync_reposts_async."""
    from unittest.mock import patch

    from typer.testing import CliRunner

    from tweethoarder.cli.main import app

    runner = CliRunner()

    with patch("tweethoarder.cli.sync.sync_reposts_async") as mock_sync:
        mock_sync.return_value = {"synced_count": 5}
        runner.invoke(app, ["sync", "reposts", "--store-raw"])

        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs.get("store_raw") is True


@pytest.mark.asyncio
async def test_sync_reposts_async_stores_raw_json_when_store_raw_enabled(tmp_path: Path) -> None:
    """sync_reposts_async should store raw_json in database when store_raw=True."""
    import sqlite3
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_reposts_async

    db_path = tmp_path / "test.db"
    mock_response = _make_reposts_response([_make_repost_entry("123", "RT @other: Repost")])

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

        await sync_reposts_async(db_path, count=10, store_raw=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT raw_json FROM tweets WHERE id = ?", ("123",))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] is not None


@pytest.mark.asyncio
async def test_sync_reposts_async_fetches_threads_for_all_synced_tweets(tmp_path: Path) -> None:
    """sync_reposts_async should fetch threads for ALL synced reposts, not just the last one."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.sync import sync_reposts_async

    db_path = tmp_path / "test.db"

    # Response with 3 reposts
    mock_response = _make_reposts_response(
        [
            _make_repost_entry("111", "RT @a: First"),
            _make_repost_entry("222", "RT @b: Second"),
            _make_repost_entry("333", "RT @c: Third"),
        ]
    )

    with (
        patch("tweethoarder.cli.sync.resolve_cookies") as mock_cookies,
        patch("tweethoarder.cli.sync.TwitterClient") as mock_client_class,
        patch("tweethoarder.cli.sync.get_config_dir") as mock_config_dir,
        patch("tweethoarder.cli.sync.get_query_id_with_fallback") as mock_get_query_id,
        patch("tweethoarder.cli.sync.httpx.AsyncClient") as mock_async_client,
        patch("tweethoarder.cli.sync.fetch_thread_async") as mock_fetch_thread,
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

        await sync_reposts_async(db_path, count=10, with_threads=True)

        # Should be called 3 times - once for each synced repost
        assert mock_fetch_thread.call_count == 3
        # Verify each tweet ID was passed
        call_tweet_ids = [call[1]["tweet_id"] for call in mock_fetch_thread.call_args_list]
        assert set(call_tweet_ids) == {"111", "222", "333"}
