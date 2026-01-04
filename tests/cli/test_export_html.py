"""Tests for HTML export CLI command."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from tweethoarder.cli.main import app

runner = CliRunner()


def test_html_export_includes_thread_context(tmp_path: Path) -> None:
    """HTML export should fetch and include thread context for tweets."""
    mock_tweets = [
        {
            "id": "1",
            "text": "First tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "conversation_id": "1",
        }
    ]
    thread_tweets = [
        {
            "id": "1",
            "text": "First tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "conversation_id": "1",
        },
        {
            "id": "2",
            "text": "Second tweet in thread",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:01:00Z",
            "conversation_id": "1",
        },
    ]

    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_tweets_by_collection") as mock_get_tweets,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_get_thread,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_tweets.return_value = mock_tweets
        mock_get_thread.return_value = thread_tweets

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "likes", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        # Should have called get_tweets_by_conversation_id for thread context
        mock_get_thread.assert_called_once()

        # Check that thread_context is included in the HTML output
        content = output_file.read_text()
        assert "THREAD_CONTEXT" in content
        assert "Second tweet in thread" in content
        # Check that JS has thread rendering function and uses it
        assert "getThreadTweets" in content
        assert "getThreadTweets(t)" in content  # Used in renderTweets
        # Check that search includes thread context
        assert "THREAD_CONTEXT" in content
        assert "getThreadText" in content  # Search uses thread text
