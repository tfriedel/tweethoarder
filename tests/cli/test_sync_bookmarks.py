"""Tests for bookmarks sync functionality."""

import inspect


def test_sync_bookmarks_async_function_exists() -> None:
    """sync_bookmarks_async function should be importable."""
    from tweethoarder.cli.sync import sync_bookmarks_async

    assert callable(sync_bookmarks_async)


def test_sync_bookmarks_async_accepts_db_path_and_count() -> None:
    """sync_bookmarks_async should accept db_path and count parameters."""
    from tweethoarder.cli.sync import sync_bookmarks_async

    sig = inspect.signature(sync_bookmarks_async)
    params = list(sig.parameters.keys())

    assert "db_path" in params
    assert "count" in params
