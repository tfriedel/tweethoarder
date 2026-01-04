"""Tests for thread fetching functionality."""

from pathlib import Path

import pytest


def test_fetch_thread_async_exists() -> None:
    """fetch_thread_async function should be importable."""
    from tweethoarder.cli.thread import fetch_thread_async

    assert callable(fetch_thread_async)


@pytest.mark.asyncio
async def test_fetch_thread_async_returns_result(tmp_path: Path) -> None:
    """fetch_thread_async should return a result dict."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.thread import fetch_thread_async
    from tweethoarder.storage.database import init_database

    mock_response = {
        "data": {
            "threaded_conversation_with_injections_v2": {
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
                                                    "created_at": "Wed Jan 01 12:00:00 +0000 2025",
                                                    "conversation_id_str": "123",
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
                                    }
                                },
                            }
                        ],
                    }
                ]
            }
        }
    }

    db_path = tmp_path / "test.db"
    init_database(db_path)

    with (
        patch("tweethoarder.cli.thread.resolve_cookies") as mock_cookies,
        patch("tweethoarder.cli.thread.TwitterClient") as mock_client_class,
        patch("tweethoarder.cli.thread.get_config_dir") as mock_config_dir,
        patch("tweethoarder.cli.thread.get_query_id_with_fallback") as mock_get_query_id,
        patch("tweethoarder.cli.thread.httpx.AsyncClient") as mock_async_client,
    ):
        mock_cookies.return_value = {"twid": "u%3D789"}
        mock_client_class.return_value.get_base_headers.return_value = {}
        mock_config_dir.return_value = tmp_path
        mock_get_query_id.return_value = "DETAIL123"

        mock_http = AsyncMock()
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_http_response
        mock_async_client.return_value.__aenter__.return_value = mock_http

        result = await fetch_thread_async(
            db_path=db_path,
            tweet_id="123",
            mode="thread",
            limit=200,
        )

        assert isinstance(result, dict)
        assert "tweet_count" in result
        assert result["tweet_count"] == 1


@pytest.mark.asyncio
async def test_fetch_thread_async_filters_in_thread_mode(tmp_path: Path) -> None:
    """fetch_thread_async should filter to only author's tweets in thread mode."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.thread import fetch_thread_async
    from tweethoarder.storage.database import init_database

    mock_response = {
        "data": {
            "threaded_conversation_with_injections_v2": {
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
                                                    "full_text": "Hello from author1",
                                                    "created_at": "Wed Jan 01 12:00:00 +0000 2025",
                                                },
                                                "core": {
                                                    "user_results": {
                                                        "result": {
                                                            "rest_id": "author1",
                                                            "core": {"screen_name": "user1"},
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
                                                    "full_text": "Hello from author2",
                                                    "created_at": "Wed Jan 01 13:00:00 +0000 2025",
                                                },
                                                "core": {
                                                    "user_results": {
                                                        "result": {
                                                            "rest_id": "author2",
                                                            "core": {"screen_name": "user2"},
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

    db_path = tmp_path / "test.db"
    init_database(db_path)

    with (
        patch("tweethoarder.cli.thread.resolve_cookies") as mock_cookies,
        patch("tweethoarder.cli.thread.TwitterClient") as mock_client_class,
        patch("tweethoarder.cli.thread.get_config_dir") as mock_config_dir,
        patch("tweethoarder.cli.thread.get_query_id_with_fallback") as mock_get_query_id,
        patch("tweethoarder.cli.thread.httpx.AsyncClient") as mock_async_client,
    ):
        mock_cookies.return_value = {"twid": "u%3D789"}
        mock_client_class.return_value.get_base_headers.return_value = {}
        mock_config_dir.return_value = tmp_path
        mock_get_query_id.return_value = "DETAIL123"

        mock_http = AsyncMock()
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_http_response
        mock_async_client.return_value.__aenter__.return_value = mock_http

        result = await fetch_thread_async(
            db_path=db_path,
            tweet_id="123",
            mode="thread",
            limit=200,
        )

        # With mode="thread" and focal tweet author "author1", only 1 tweet should be counted
        assert result["tweet_count"] == 1


@pytest.mark.asyncio
async def test_fetch_thread_async_saves_tweets_to_db(tmp_path: Path) -> None:
    """fetch_thread_async should save tweets to database."""
    import sqlite3
    from unittest.mock import AsyncMock, MagicMock, patch

    from tweethoarder.cli.thread import fetch_thread_async
    from tweethoarder.storage.database import init_database

    mock_response = {
        "data": {
            "threaded_conversation_with_injections_v2": {
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
                                                    "created_at": "Wed Jan 01 12:00:00 +0000 2025",
                                                    "conversation_id_str": "123",
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
                                    }
                                },
                            }
                        ],
                    }
                ]
            }
        }
    }

    db_path = tmp_path / "test.db"
    init_database(db_path)

    with (
        patch("tweethoarder.cli.thread.resolve_cookies") as mock_cookies,
        patch("tweethoarder.cli.thread.TwitterClient") as mock_client_class,
        patch("tweethoarder.cli.thread.get_config_dir") as mock_config_dir,
        patch("tweethoarder.cli.thread.get_query_id_with_fallback") as mock_get_query_id,
        patch("tweethoarder.cli.thread.httpx.AsyncClient") as mock_async_client,
    ):
        mock_cookies.return_value = {"twid": "u%3D789"}
        mock_client_class.return_value.get_base_headers.return_value = {}
        mock_config_dir.return_value = tmp_path
        mock_get_query_id.return_value = "DETAIL123"

        mock_http = AsyncMock()
        mock_http_response = MagicMock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status = MagicMock()
        mock_http.get.return_value = mock_http_response
        mock_async_client.return_value.__aenter__.return_value = mock_http

        await fetch_thread_async(
            db_path=db_path,
            tweet_id="123",
            mode="thread",
            limit=200,
        )

    # Verify tweet was saved to database
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT id, text FROM tweets WHERE id = ?", ("123",))
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "123"
    assert row[1] == "Hello world"
