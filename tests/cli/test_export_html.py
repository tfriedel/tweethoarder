"""Tests for HTML export CLI command."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from tweethoarder.cli.main import app

runner = CliRunner()


def test_html_export_renders_avatar_with_styling(tmp_path: Path) -> None:
    """HTML export should render avatars with circular styling."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Test tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "author_avatar_url": "https://pbs.twimg.com/profile/test.jpg",
            "created_at": "2025-01-01T12:00:00Z",
        }
    ]

    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_tweets_by_collection") as mock_get_tweets,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_get_thread,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_tweets.return_value = mock_tweets
        mock_get_thread.return_value = []

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "likes", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Should have CSS for circular avatar styling
        assert ".avatar" in content
        assert "border-radius: 50%" in content

        # JS should render avatar img with class="avatar"
        assert 'class="avatar"' in content or "class='avatar'" in content


def test_html_export_renders_avatar_placeholder(tmp_path: Path) -> None:
    """HTML export should render placeholder when avatar URL is missing."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Test tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            # No author_avatar_url
        }
    ]

    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_tweets_by_collection") as mock_get_tweets,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_get_thread,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_tweets.return_value = mock_tweets
        mock_get_thread.return_value = []

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "likes", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Should have CSS for placeholder styling
        assert ".avatar-placeholder" in content

        # JS should render placeholder div when no avatar URL
        assert "avatar-placeholder" in content
        has_placeholder = '<div class="avatar-placeholder">' in content
        assert has_placeholder or "class='avatar-placeholder'" in content


def test_html_export_twitter_like_card_styling(tmp_path: Path) -> None:
    """HTML export should have Twitter-like card styling for tweets."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Test tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
        }
    ]

    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_tweets_by_collection") as mock_get_tweets,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_get_thread,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_tweets.return_value = mock_tweets
        mock_get_thread.return_value = []

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "likes", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Should have card-like article styling with border-radius
        assert "border-radius" in content
        # Should have Twitter blue for links
        assert "#1DA1F2" in content or "#1da1f2" in content
        # Articles should have card styling
        assert "article {" in content or "article{" in content
        # Article should have rounded corners (card style)
        # Extract the article CSS rule and check for border-radius
        import re

        article_match = re.search(r"article\s*\{[^}]+\}", content)
        assert article_match is not None
        article_css = article_match.group(0)
        assert "border-radius" in article_css


def test_html_export_renders_quote_tweets(tmp_path: Path) -> None:
    """HTML export should render quote tweets with nested styling."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Check out this tweet!",
            "author_id": "user1",
            "author_username": "quoter",
            "created_at": "2025-01-01T12:00:00Z",
            "quoted_tweet_id": "2",
        },
        {
            "id": "2",
            "text": "Original tweet content",
            "author_id": "user2",
            "author_username": "original_author",
            "created_at": "2025-01-01T11:00:00Z",
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
        mock_get_thread.return_value = []

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "likes", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Should have CSS for quoted tweet styling
        assert ".quoted-tweet" in content

        # JS should build a map of tweets for lookup
        assert "TWEETS_MAP" in content or "tweetsMap" in content

        # JS should check for quoted_tweet_id and render nested tweet
        assert "quoted_tweet_id" in content
        assert "TWEETS_MAP[t.quoted_tweet_id]" in content


def test_html_export_renders_retweets(tmp_path: Path) -> None:
    """HTML export should render retweets with proper styling."""
    mock_tweets = [
        {
            "id": "1",
            "text": "RT content here",
            "author_id": "user1",
            "author_username": "retweeter",
            "created_at": "2025-01-01T12:00:00Z",
            "is_retweet": True,
            "retweeted_tweet_id": "2",
        },
        {
            "id": "2",
            "text": "Original tweet content",
            "author_id": "user2",
            "author_username": "original_author",
            "created_at": "2025-01-01T11:00:00Z",
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
        mock_get_thread.return_value = []

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "likes", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Should have CSS for retweet styling
        assert ".retweet-header" in content

        # JS should check for is_retweet and render header
        assert "is_retweet" in content
        assert "t.is_retweet" in content
        assert "${rtHeader}" in content


def test_html_export_image_toggle(tmp_path: Path) -> None:
    """HTML export should have toggle to load images."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Tweet with image",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "media_json": '[{"type": "photo", "media_url_https": "https://example.com/img.jpg"}]',
        }
    ]

    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_tweets_by_collection") as mock_get_tweets,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_get_thread,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_tweets.return_value = mock_tweets
        mock_get_thread.return_value = []

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "likes", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Should have CSS for image placeholder
        assert ".media-placeholder" in content

        # Should have a toggle button for images
        assert "load-images" in content or "loadImages" in content

        # JS should parse media_json and render placeholders
        assert "media_json" in content
        assert "renderMedia" in content or "t.media_json" in content

        # Load Images button should have event listener that sets imagesEnabled
        assert "load-images" in content
        assert (
            "loadBtn.addEventListener" in content
            or "getElementById('load-images').addEventListener" in content
        )

        # Media placeholders should be clickable to load individual images
        assert "media-placeholder" in content
        assert "onclick=" in content  # inline click handler on placeholder


def test_html_export_renders_media_in_template(tmp_path: Path) -> None:
    """HTML export should call renderMedia in the tweet template."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Tweet with image",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "media_json": '[{"type": "photo", "media_url_https": "https://example.com/img.jpg"}]',
        }
    ]

    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_tweets_by_collection") as mock_get_tweets,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_get_thread,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_tweets.return_value = mock_tweets
        mock_get_thread.return_value = []

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "likes", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Template should call renderMedia with media_json
        assert "renderMedia(t.media_json)" in content


def test_html_export_strips_unused_fields(tmp_path: Path) -> None:
    """HTML export should only include fields used by JS rendering."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Test tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            # Fields that should be stripped:
            "raw_json": '{"very": "large", "raw": "data"}',
            "some_unused_field": "should be stripped",
        }
    ]

    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_tweets_by_collection") as mock_get_tweets,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_get_thread,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_tweets.return_value = mock_tweets
        mock_get_thread.return_value = []

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "likes", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Should NOT contain unused fields
        assert "raw_json" not in content
        assert "some_unused_field" not in content


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
