"""Tests for sync all functionality (callback-based)."""

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tweethoarder.cli.main import app

runner = CliRunner()


def test_sync_without_subcommand_is_handled() -> None:
    """Running 'sync' without a subcommand should work (not show help)."""
    # For now, just verify it doesn't error with "Missing command"
    result = runner.invoke(app, ["sync"])
    # Strip ANSI escape codes
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    # Should not show "Missing command" error - we'll implement the callback
    assert "Missing command" not in clean_output or result.exit_code == 0


def test_sync_accepts_likes_flag() -> None:
    """The sync command should accept --likes flag."""
    result = runner.invoke(app, ["sync", "--help"])
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--likes" in clean_output


def test_sync_accepts_bookmarks_flag() -> None:
    """The sync command should accept --bookmarks flag."""
    result = runner.invoke(app, ["sync", "--help"])
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--bookmarks" in clean_output


def test_sync_accepts_all_collection_flags() -> None:
    """The sync command should accept all collection flags."""
    result = runner.invoke(app, ["sync", "--help"])
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--tweets" in clean_output
    assert "--reposts" in clean_output
    assert "--replies" in clean_output
    assert "--feed" in clean_output
    assert "--threads" in clean_output


def test_sync_accepts_count_option() -> None:
    """The sync command should accept --count option."""
    result = runner.invoke(app, ["sync", "--help"])
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--count" in clean_output


def test_sync_accepts_with_threads_option() -> None:
    """The sync command should accept --with-threads option."""
    result = runner.invoke(app, ["sync", "--help"])
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--with-threads" in clean_output


def test_sync_accepts_full_option() -> None:
    """The sync command should accept --full option."""
    result = runner.invoke(app, ["sync", "--help"])
    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "--full" in clean_output


def test_sync_all_async_function_exists() -> None:
    """sync_all_async function should be importable."""
    from tweethoarder.cli.sync import sync_all_async

    assert callable(sync_all_async)


def test_sync_all_async_accepts_db_path() -> None:
    """sync_all_async should accept db_path parameter."""
    import inspect

    from tweethoarder.cli.sync import sync_all_async

    sig = inspect.signature(sync_all_async)
    params = list(sig.parameters.keys())

    assert "db_path" in params


def test_sync_all_async_accepts_include_flags() -> None:
    """sync_all_async should accept include_* parameters."""
    import inspect

    from tweethoarder.cli.sync import sync_all_async

    sig = inspect.signature(sync_all_async)
    params = list(sig.parameters.keys())

    assert "include_likes" in params


@pytest.mark.asyncio
async def test_sync_all_async_calls_sync_likes_when_enabled(tmp_path: Path) -> None:
    """sync_all_async should call sync_likes_async when include_likes=True."""
    from unittest.mock import AsyncMock, patch

    from tweethoarder.cli.sync import sync_all_async
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    with patch("tweethoarder.cli.sync.sync_likes_async", new_callable=AsyncMock) as mock_likes:
        mock_likes.return_value = {"synced_count": 10}

        await sync_all_async(
            db_path=db_path,
            include_likes=True,
            include_bookmarks=False,
            include_tweets=False,
            include_reposts=False,
            include_replies=False,
        )

        mock_likes.assert_called_once()


@pytest.mark.asyncio
async def test_sync_all_async_calls_sync_bookmarks_when_enabled(tmp_path: Path) -> None:
    """sync_all_async should call sync_bookmarks_async when include_bookmarks=True."""
    from unittest.mock import AsyncMock, patch

    from tweethoarder.cli.sync import sync_all_async
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    with patch(
        "tweethoarder.cli.sync.sync_bookmarks_async", new_callable=AsyncMock
    ) as mock_bookmarks:
        mock_bookmarks.return_value = {"synced_count": 5}

        await sync_all_async(
            db_path=db_path,
            include_likes=False,
            include_bookmarks=True,
            include_tweets=False,
            include_reposts=False,
            include_replies=False,
        )

        mock_bookmarks.assert_called_once()


@pytest.mark.asyncio
async def test_sync_all_async_calls_sync_tweets_when_enabled(tmp_path: Path) -> None:
    """sync_all_async should call sync_tweets_async when include_tweets=True."""
    from unittest.mock import AsyncMock, patch

    from tweethoarder.cli.sync import sync_all_async
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    with patch("tweethoarder.cli.sync.sync_tweets_async", new_callable=AsyncMock) as mock_tweets:
        mock_tweets.return_value = {"synced_count": 3}

        await sync_all_async(
            db_path=db_path,
            include_likes=False,
            include_bookmarks=False,
            include_tweets=True,
            include_reposts=False,
            include_replies=False,
        )

        mock_tweets.assert_called_once()


@pytest.mark.asyncio
async def test_sync_all_async_calls_sync_reposts_when_enabled(tmp_path: Path) -> None:
    """sync_all_async should call sync_reposts_async when include_reposts=True."""
    from unittest.mock import AsyncMock, patch

    from tweethoarder.cli.sync import sync_all_async
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    with patch("tweethoarder.cli.sync.sync_reposts_async", new_callable=AsyncMock) as mock_reposts:
        mock_reposts.return_value = {"synced_count": 2}

        await sync_all_async(
            db_path=db_path,
            include_likes=False,
            include_bookmarks=False,
            include_tweets=False,
            include_reposts=True,
            include_replies=False,
        )

        mock_reposts.assert_called_once()


@pytest.mark.asyncio
async def test_sync_all_async_calls_sync_replies_when_enabled(tmp_path: Path) -> None:
    """sync_all_async should call sync_replies_async when include_replies=True."""
    from unittest.mock import AsyncMock, patch

    from tweethoarder.cli.sync import sync_all_async
    from tweethoarder.storage.database import init_database

    db_path = tmp_path / "test.db"
    init_database(db_path)

    with patch("tweethoarder.cli.sync.sync_replies_async", new_callable=AsyncMock) as mock_replies:
        mock_replies.return_value = {"synced_count": 1}

        await sync_all_async(
            db_path=db_path,
            include_likes=False,
            include_bookmarks=False,
            include_tweets=False,
            include_reposts=False,
            include_replies=True,
        )

        mock_replies.assert_called_once()


def test_sync_callback_calls_sync_all_async() -> None:
    """The sync callback should call sync_all_async when no subcommand given."""
    from unittest.mock import AsyncMock, patch

    with patch("tweethoarder.cli.sync.sync_all_async", new_callable=AsyncMock) as mock_sync_all:
        runner.invoke(app, ["sync"])

        # Should have called sync_all_async
        mock_sync_all.assert_called_once()


def test_sync_callback_with_likes_flag_only_syncs_likes() -> None:
    """When --likes flag is given, only include_likes should be True."""
    from unittest.mock import ANY, AsyncMock, patch

    with patch("tweethoarder.cli.sync.sync_all_async", new_callable=AsyncMock) as mock_sync_all:
        runner.invoke(app, ["sync", "--likes"])

        mock_sync_all.assert_called_once_with(
            db_path=ANY,
            include_likes=True,
            include_bookmarks=False,
            include_tweets=False,
            include_reposts=False,
            include_replies=False,
        )


def test_sync_callback_with_no_flags_syncs_all_except_feed() -> None:
    """When no flags given, should sync all collections except feed."""
    from unittest.mock import ANY, AsyncMock, patch

    with patch("tweethoarder.cli.sync.sync_all_async", new_callable=AsyncMock) as mock_sync_all:
        runner.invoke(app, ["sync"])

        mock_sync_all.assert_called_once_with(
            db_path=ANY,
            include_likes=True,
            include_bookmarks=True,
            include_tweets=True,
            include_reposts=True,
            include_replies=True,
        )


def test_sync_posts_subcommand_removed() -> None:
    """The 'sync posts' subcommand should be removed (use --tweets --reposts instead)."""
    from tweethoarder.cli.sync import app as sync_app

    result = runner.invoke(sync_app, ["posts", "--help"])

    # Command should not exist - expect error
    assert result.exit_code != 0 or "No such command" in result.output


def test_sync_threads_subcommand_removed() -> None:
    """The 'sync threads' subcommand should be removed (use --threads flag instead)."""
    from tweethoarder.cli.sync import app as sync_app

    result = runner.invoke(sync_app, ["threads", "--help"])

    # Command should not exist - expect error
    assert result.exit_code != 0 or "No such command" in result.output
