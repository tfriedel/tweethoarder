"""Tests for the refresh-ids CLI command."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from tweethoarder.cli.main import app

runner = CliRunner()


def test_refresh_ids_command_exists() -> None:
    """The refresh-ids command should be available."""
    result = runner.invoke(app, ["refresh-ids", "--help"])
    assert result.exit_code == 0
    assert "refresh" in result.output.lower()


def test_refresh_ids_fetches_and_saves_query_ids(tmp_path: Path) -> None:
    """refresh-ids should fetch query IDs and save them to cache."""
    from tweethoarder.query_ids.store import QueryIdStore

    cache_path = tmp_path / "query-ids-cache.json"

    mock_refresh = AsyncMock(return_value={"Bookmarks": "new_id", "Likes": "another_id"})

    with (
        patch("tweethoarder.cli.main.get_config_dir", return_value=tmp_path),
        patch("tweethoarder.cli.main.refresh_query_ids", mock_refresh),
    ):
        result = runner.invoke(app, ["refresh-ids"])

    assert result.exit_code == 0
    assert "2" in result.output  # Found 2 query IDs

    store = QueryIdStore(cache_path)
    assert store.get_query_id("Bookmarks") == "new_id"
    assert store.get_query_id("Likes") == "another_id"
