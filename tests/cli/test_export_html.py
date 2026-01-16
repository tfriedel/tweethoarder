"""Tests for HTML export CLI command."""

import json
import re
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

        # Should have CSS for circular avatar styling (Twitter uses 9999px for circles)
        assert ".avatar" in content
        assert "border-radius: 9999px" in content

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

        # Should have border-radius for rounded elements (avatars, buttons, etc.)
        assert "border-radius" in content
        # Should have Twitter blue via CSS variable
        assert "--accent-blue" in content
        # Articles should have Twitter-style border-bottom dividers
        assert "article {" in content or "article{" in content
        # Article should have border-bottom (Twitter-style tweet dividers)
        import re

        article_match = re.search(r"article\s*\{[^}]+\}", content)
        assert article_match is not None
        article_css = article_match.group(0)
        assert "border-bottom" in article_css


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


def test_html_export_auto_loads_images_with_aspect_ratio(tmp_path: Path) -> None:
    """HTML export should auto-load images with aspect-ratio for layout stability."""
    media = '[{"type": "photo", "media_url_https": "https://example.com/img.jpg", '
    media += '"width": 800, "height": 600}]'
    mock_tweets = [
        {
            "id": "1",
            "text": "Tweet with image",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "media_json": media,
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

        # JS should parse media_json and call renderMedia
        assert "media_json" in content
        assert "renderMedia" in content

        # renderMedia should use aspect-ratio for layout stability
        assert "aspect-ratio" in content

        # Images should use lazy loading
        assert "loading='lazy'" in content or 'loading="lazy"' in content

        # Should NOT have a toggle button (images auto-load)
        assert "load-images" not in content
        assert "loadBtn" not in content


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


def test_html_export_validates_media_urls(tmp_path: Path) -> None:
    """HTML export should validate media URLs to prevent XSS."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Tweet with image",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "media_json": '[{"type": "photo", "media_url_https": "https://pbs.twimg.com/media/test.jpg"}]',
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

        # Should have URL validation function
        assert "isValidMediaUrl" in content
        # Should check for pbs.twimg.com or video.twimg.com
        assert "pbs.twimg.com" in content
        assert "video.twimg.com" in content
        # Should use validation in renderMedia
        assert "isValidMediaUrl(url)" in content


def test_html_export_validates_avatar_urls(tmp_path: Path) -> None:
    """HTML export should validate avatar URLs to prevent XSS."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Tweet with avatar",
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

        # Should validate avatar URL before rendering
        assert "isValidAvatarUrl" in content
        # Should check for pbs.twimg.com (Twitter profile image CDN)
        # Avatar validation should use the function
        assert "isValidAvatarUrl(t.author_avatar_url)" in content


def test_html_export_expandurls_logs_errors(tmp_path: Path) -> None:
    """HTML export should log errors when expandUrls fails to parse JSON."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Tweet with URLs",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "urls_json": '[{"url": "https://t.co/abc", "expanded_url": "https://example.com"}]',
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

        # expandUrls catch block should log errors with console.warn
        assert "console.warn" in content
        assert "expandUrls" in content or "Failed to expand" in content


def test_html_export_strips_media_tco_urls(tmp_path: Path) -> None:
    """HTML export should strip t.co URLs not in urls_json (media URLs)."""
    import json

    mock_tweets = [
        {
            "id": "1",
            "text": "Check this https://t.co/link and image https://t.co/media123",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "urls_json": json.dumps(
                [{"url": "https://t.co/link", "expanded_url": "https://example.com"}]
            ),
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

        # The JS should have stripMediaUrls function
        assert "stripMediaUrls" in content or "t.co" in content
        # Ensure the function strips leftover t.co URLs
        assert "https://t.co/" in content  # regex pattern should be present
        assert ".replace" in content  # should use replace to strip


def test_html_export_makes_urls_clickable(tmp_path: Path) -> None:
    """HTML export should make URLs clickable with anchor tags."""
    import json

    mock_tweets = [
        {
            "id": "1",
            "text": "Check this https://t.co/link",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "urls_json": json.dumps(
                [{"url": "https://t.co/link", "expanded_url": "https://example.com/page"}]
            ),
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

        # Should have a linkifyUrls or makeClickable function
        assert "linkifyUrls" in content or "makeClickable" in content
        # Should create anchor tags with href
        assert '<a href="' in content or "<a href='" in content
        assert 'target="_blank"' in content or "target='_blank'" in content


def test_html_export_makes_mentions_clickable(tmp_path: Path) -> None:
    """HTML export should make @mentions clickable with links to profiles."""
    mock_tweets = [
        {
            "id": "1",
            "text": "@charliermarsh Donald Knuth, @jeremyphoward and nbdev would approve",
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

        # Should have a linkifyMentions function
        assert "linkifyMentions" in content
        # Should create links to x.com profiles
        assert "x.com/" in content


def test_html_export_rendermedia_logs_errors(tmp_path: Path) -> None:
    """HTML export should log errors when renderMedia fails to parse JSON."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Tweet with media",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "media_json": '[{"type": "photo", "media_url_https": "https://pbs.twimg.com/media/test.jpg"}]',
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

        # renderMedia catch block should log errors
        assert "console.error" in content
        assert "Failed to render media" in content


def test_html_export_quoted_tweet_validates_fields(tmp_path: Path) -> None:
    """HTML export should validate quoted tweet fields before rendering."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Check out this tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "quoted_tweet_id": "2",
        }
    ]

    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_tweets_by_collection") as mock_get_tweets,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_get_thread,
        patch("tweethoarder.storage.database.get_tweets_by_ids") as mock_get_by_ids,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_tweets.return_value = mock_tweets
        mock_get_thread.return_value = []
        mock_get_by_ids.return_value = []  # No quoted tweets available

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "likes", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Should validate quoted tweet has required fields before rendering
        assert "qt.author_username" in content and "qt.text" in content
        # Should have fallback for unavailable quoted tweets
        assert "Quoted tweet unavailable" in content


def test_html_export_handles_malformed_media_json(tmp_path: Path) -> None:
    """HTML export should handle malformed media_json gracefully."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Tweet with bad media",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "media_json": "not valid json",  # Malformed JSON
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

        # Export should succeed - no crash
        assert result.exit_code == 0
        content = output_file.read_text()

        # Should contain the tweet text (proves rendering worked)
        assert "Tweet with bad media" in content
        # Should have error handler in renderMedia
        assert "console.error" in content
        assert "Failed to render media" in content


def test_html_export_preserves_newlines(tmp_path: Path) -> None:
    """HTML export should convert newlines to <br> tags for display."""
    mock_tweets = [
        {
            "id": "1",
            "text": "First paragraph.\n\nSecond paragraph.\n\nThird paragraph.",
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

        # Should have a function to convert newlines to <br>
        # or should handle newlines in the text processing
        assert (
            ".replace(/\\n/g" in content  # JS regex to replace newlines
            or "formatNewlines" in content
            or "<br>" in content  # direct br tags
        )


def test_html_export_separates_main_and_quoted_tweets(tmp_path: Path) -> None:
    """HTML export should only render main collection tweets, not quoted tweets.

    Quoted tweets should be available in TWEETS_MAP for lookup but not in the
    main TWEETS array that gets rendered.
    """
    import json as json_lib

    mock_tweets = [
        {
            "id": "1",
            "text": "Check out this tweet!",
            "author_id": "user1",
            "author_username": "quoter",
            "created_at": "2025-01-01T12:00:00Z",
            "quoted_tweet_id": "2",
        },
    ]
    quoted_tweets = [
        {
            "id": "2",
            "text": "Original quoted tweet",
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
        patch("tweethoarder.storage.database.get_tweets_by_ids") as mock_get_by_ids,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_tweets.return_value = mock_tweets
        mock_get_thread.return_value = []
        mock_get_by_ids.return_value = quoted_tweets

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "likes", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Parse the TWEETS array from the HTML
        start = content.find("const TWEETS = [")
        end = content.find("];", start) + 1
        tweets_json = content[start + 14 : end]
        tweets_arr = json_lib.loads(tweets_json)

        # TWEETS array should only contain main tweets (1), not quoted tweets
        assert len(tweets_arr) == 1
        assert tweets_arr[0]["id"] == "1"

        # TWEETS_MAP should contain both main and quoted tweets for lookup
        assert "TWEETS_MAP" in content
        # The quoted tweet should be available for lookup
        assert "Original quoted tweet" in content


def test_html_export_applies_richtext_formatting(tmp_path: Path) -> None:
    """HTML export should apply bold/italic formatting from richtext_tags."""
    import json

    raw_json = json.dumps(
        {
            "note_tweet": {
                "note_tweet_results": {
                    "result": {
                        "text": "Hello world today",
                        "richtext": {
                            "richtext_tags": [
                                {"from_index": 0, "to_index": 5, "richtext_types": ["Bold"]},
                                {"from_index": 12, "to_index": 17, "richtext_types": ["Italic"]},
                            ]
                        },
                    }
                }
            }
        }
    )

    mock_tweets = [
        {
            "id": "1",
            "text": "Hello world today",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "raw_json": raw_json,
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

        # Should have a function to apply rich text formatting
        assert "applyRichtext" in content
        # Should have richtext_tags data in the tweet object
        assert "richtext_tags" in content
        # Should call applyRichtext in the rendering pipeline
        assert "applyRichtext(" in content


def test_html_export_facets_include_display_name(tmp_path: Path) -> None:
    """FACETS.authors should include display_name for author filtering."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Test tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "author_display_name": "Test User Display",
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

        # FACETS should include display_name in authors array
        import json
        import re

        # Extract FACETS JSON from the HTML
        facets_match = re.search(r"const FACETS = ({.*?});", content, re.DOTALL)
        assert facets_match is not None, "FACETS not found in HTML"

        facets = json.loads(facets_match.group(1))
        assert "authors" in facets
        assert len(facets["authors"]) == 1

        author = facets["authors"][0]
        assert "username" in author
        assert "display_name" in author
        assert "count" in author
        assert author["username"] == "testuser"
        assert author["display_name"] == "Test User Display"
        assert author["count"] == 1


def test_html_export_has_author_filter_input(tmp_path: Path) -> None:
    """HTML export should have an input field for filtering authors."""
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

        # Should have an input for filtering authors
        assert 'id="author-search"' in content or "id='author-search'" in content

        # Should have a container for the author list
        assert 'id="author-list"' in content or "id='author-list'" in content

        # Should have date range inputs
        assert 'id="date-from"' in content or "id='date-from'" in content
        assert 'id="date-to"' in content or "id='date-to'" in content

        # Should have clear filters button
        assert 'id="clear-filters"' in content or "id='clear-filters'" in content

        # Should have results count element
        assert 'id="results-count"' in content or "id='results-count'" in content


def test_html_export_has_filter_javascript_functions(tmp_path: Path) -> None:
    """HTML export should have JavaScript functions for advanced filtering."""
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

        # Should have selectedAuthors state variable
        assert "let selectedAuthors" in content or "const selectedAuthors" in content

        # Should have renderAuthorList function
        assert "function renderAuthorList" in content

        # Should have applyAllFilters function
        assert "function applyAllFilters" in content

        # Should have event handlers for filter inputs
        assert "author-search" in content and "addEventListener" in content
        assert "author-list" in content
        assert "date-from" in content and "date-to" in content
        assert "clear-filters" in content


def test_html_export_collection_all_includes_collection_types(tmp_path: Path) -> None:
    """HTML export with --collection all should include collection_types for each tweet."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Liked and bookmarked tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "collection_types": ["like", "bookmark"],
        },
        {
            "id": "2",
            "text": "My own tweet",
            "author_id": "user2",
            "author_username": "otheruser",
            "created_at": "2025-01-02T12:00:00Z",
            "collection_types": ["tweet"],
        },
    ]

    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_all_tweets_with_collection_types") as mock_get_all,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_get_thread,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_all.return_value = mock_tweets
        mock_get_thread.return_value = []

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "all", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Should have collection_types in the JSON
        assert "collection_types" in content
        assert '"like"' in content
        assert '"bookmark"' in content
        assert '"tweet"' in content


def test_html_export_collection_all_has_type_filter_ui(tmp_path: Path) -> None:
    """HTML export with --collection all should have type filter checkboxes."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Liked tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "collection_types": ["like"],
        },
        {
            "id": "2",
            "text": "Bookmarked tweet",
            "author_id": "user2",
            "author_username": "otheruser",
            "created_at": "2025-01-02T12:00:00Z",
            "collection_types": ["bookmark"],
        },
    ]

    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_all_tweets_with_collection_types") as mock_get_all,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_get_thread,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_all.return_value = mock_tweets
        mock_get_thread.return_value = []

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "all", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Should have type filter section
        assert "type-list" in content or "Type" in content
        # Should have collection type counts in facets
        assert "types" in content


def test_html_export_collection_all_has_type_filter_javascript(tmp_path: Path) -> None:
    """HTML export with --collection all should have JavaScript for type filtering."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Liked tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "collection_types": ["like"],
        },
    ]

    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_all_tweets_with_collection_types") as mock_get_all,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_get_thread,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_all.return_value = mock_tweets
        mock_get_thread.return_value = []

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "all", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Should have selectedTypes state variable
        assert "selectedTypes" in content
        # Should have renderTypeList function
        assert "renderTypeList" in content


def test_html_export_collection_all_has_type_badges(tmp_path: Path) -> None:
    """HTML export with --collection all should render type badges for tweets."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Liked tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "collection_types": ["like"],
        },
    ]

    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_all_tweets_with_collection_types") as mock_get_all,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_get_thread,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_all.return_value = mock_tweets
        mock_get_thread.return_value = []

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "all", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Should have renderTypeBadges function
        assert "renderTypeBadges" in content
        # Should have TYPE_ICONS constant
        assert "TYPE_ICONS" in content


def test_html_export_uses_css_variables(tmp_path: Path) -> None:
    """HTML export should use CSS custom properties for theming."""
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

        # Should have CSS custom properties defined in :root
        assert ":root {" in content or ":root{" in content
        assert "--bg-primary" in content
        assert "--text-primary" in content
        assert "--border-color" in content
        assert "--accent-blue" in content

        # Should have theme variants
        assert '[data-theme="light"]' in content
        assert '[data-theme="dim"]' in content

        # CSS should use var() references
        assert "var(--bg-primary)" in content
        assert "var(--text-primary)" in content
        assert "var(--border-color)" in content


def test_html_export_has_theme_switcher_ui(tmp_path: Path) -> None:
    """HTML export should have a theme switcher with Light/Dark/Dim buttons."""
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

        # Should have theme switcher container
        assert 'id="theme-switcher"' in content

        # Should have buttons for each theme
        assert 'data-theme="dark"' in content
        assert 'data-theme="dim"' in content
        assert 'data-theme="light"' in content

        # Should have CSS for theme switcher
        assert "#theme-switcher" in content
        assert "#theme-switcher button" in content


def test_html_export_has_theme_switcher_javascript(tmp_path: Path) -> None:
    """HTML export should have JavaScript to switch themes with localStorage."""
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

        # Should have setTheme function
        assert "function setTheme" in content

        # Should use localStorage for persistence
        assert "localStorage" in content
        assert "tweethoarder-theme" in content

        # Should set data-theme attribute on document
        assert "dataset.theme" in content or "data-theme" in content

        # Should have event listener for theme switcher
        assert "theme-switcher" in content and "addEventListener" in content


def test_html_export_tweet_flex_layout(tmp_path: Path) -> None:
    """HTML export should use flex layout for tweets with avatar and content columns."""
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

        # CSS should have flex layout for tweet container
        assert ".tweet-container" in content
        assert "display: flex" in content

        # CSS should have avatar column and content column
        assert ".tweet-avatar-col" in content
        assert ".tweet-content-col" in content

        # JavaScript template should generate flex layout HTML structure (in template literals)
        # Check for class names in the JavaScript return template, not just CSS
        assert (
            "<div class='tweet-container'>" in content or '<div class="tweet-container">' in content
        )
        assert (
            "<div class='tweet-avatar-col'>" in content
            or '<div class="tweet-avatar-col">' in content
        )
        assert (
            "<div class='tweet-content-col'>" in content
            or '<div class="tweet-content-col">' in content
        )


def test_html_export_author_handle_separation(tmp_path: Path) -> None:
    """HTML export should separate author name and handle with distinct styling."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Test tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "author_display_name": "Test User",
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

        # CSS should have separate styling for author name and handle
        assert ".author-name" in content
        assert ".author-handle" in content

        # JavaScript template should use these classes
        assert "class='author-name'" in content or 'class="author-name"' in content
        assert "class='author-handle'" in content or 'class="author-handle"' in content


def test_html_export_thread_connector_css(tmp_path: Path) -> None:
    """HTML export should have CSS for thread connector lines."""
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

        # CSS should have thread connector styling
        assert ".thread-connector" in content
        assert "var(--border-color)" in content


def test_html_export_tweet_max_width(tmp_path: Path) -> None:
    """HTML export should constrain tweet width to match Twitter's 600px layout."""
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

        # Should have max-width CSS variable
        assert "--tweet-max-width" in content

        # #tweets should use max-width
        assert "#tweets" in content and "max-width" in content


def test_html_export_twitter_font_stack(tmp_path: Path) -> None:
    """HTML export should use Twitter-style font stack."""
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

        # Should have font stack CSS variable with system fonts
        assert "--font-stack" in content
        assert "-apple-system" in content
        assert "BlinkMacSystemFont" in content
        assert "Segoe UI" in content


def test_html_export_deduplicates_repost_and_liked_original(tmp_path: Path) -> None:
    """HTML export should deduplicate when a repost and the original liked tweet both appear.

    When the same underlying tweet appears both as:
    1. A repost (is_retweet=True, retweeted_tweet_id=X) in the repost collection
    2. The original tweet (id=X) in the like collection

    They should be merged into ONE entry showing both collection badges.
    """
    # Original tweet that was liked
    original_tweet = {
        "id": "1001",
        "text": "Original tweet content",
        "author_id": "author1",
        "author_username": "originalauthor",
        "author_display_name": "Original Author",
        "created_at": "2025-01-01T12:00:00Z",
        "is_retweet": False,
        "collection_types": ["like"],
    }
    # Repost of that same tweet
    repost_tweet = {
        "id": "2001",
        "text": "Original tweet content",
        "author_id": "author1",
        "author_username": "originalauthor",
        "author_display_name": "Original Author",
        "created_at": "2025-01-02T14:00:00Z",
        "is_retweet": True,
        "retweeted_tweet_id": "1001",  # Points to the original
        "collection_types": ["repost"],
    }

    mock_tweets = [repost_tweet, original_tweet]  # Repost comes first by created_at

    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_all_tweets_with_collection_types") as mock_get_all,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_get_thread,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_all.return_value = mock_tweets
        mock_get_thread.return_value = []

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "all", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Parse the TWEETS JSON from the HTML to verify deduplication
        import json
        import re

        # Extract the TWEETS array from JavaScript
        tweets_match = re.search(r"const TWEETS = (\[.*?\]);", content, re.DOTALL)
        assert tweets_match is not None, "Should find TWEETS array in HTML"

        tweets_json = tweets_match.group(1)
        tweets = json.loads(tweets_json)

        # Should have only 1 tweet (deduplicated), not 2
        assert len(tweets) == 1, f"Expected 1 deduplicated tweet, got {len(tweets)}"

        # The deduplicated tweet should be the original (not the repost shell)
        deduped = tweets[0]
        assert deduped["id"] == "1001", "Should use the original tweet ID"

        # Should have both collection types merged
        collection_types = deduped.get("collection_types", [])
        assert "like" in collection_types, "Should have 'like' collection type"
        assert "repost" in collection_types, "Should have 'repost' collection type"


def test_html_export_keeps_repost_when_original_not_in_collection(tmp_path: Path) -> None:
    """HTML export should keep repost entries when the original tweet isn't in any collection.

    When we only have a repost (no liked/bookmarked original), it should remain as-is.
    """
    # Repost where the original tweet is NOT in our collection
    repost_tweet = {
        "id": "2001",
        "text": "Some other content",
        "author_id": "author1",
        "author_username": "originalauthor",
        "author_display_name": "Original Author",
        "created_at": "2025-01-02T14:00:00Z",
        "is_retweet": True,
        "retweeted_tweet_id": "9999",  # Original not in collection
        "collection_types": ["repost"],
    }

    mock_tweets = [repost_tweet]

    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_all_tweets_with_collection_types") as mock_get_all,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_get_thread,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_all.return_value = mock_tweets
        mock_get_thread.return_value = []

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "all", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        import json
        import re

        tweets_match = re.search(r"const TWEETS = (\[.*?\]);", content, re.DOTALL)
        assert tweets_match is not None

        tweets = json.loads(tweets_match.group(1))

        # Should still have 1 tweet (the repost was kept)
        assert len(tweets) == 1
        assert tweets[0]["id"] == "2001"
        assert tweets[0]["collection_types"] == ["repost"]


def test_html_export_deduplicates_tweets_from_same_thread(tmp_path: Path) -> None:
    """HTML export should show thread only once when multiple tweets from it are liked."""
    # User liked tweets 3/, 5/, 8/ from the same thread
    mock_tweets = [
        {
            "id": "1003",
            "text": "3/ Third tweet in thread",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:02:00Z",
            "conversation_id": "1001",
        },
        {
            "id": "1005",
            "text": "5/ Fifth tweet in thread",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:04:00Z",
            "conversation_id": "1001",
        },
        {
            "id": "1008",
            "text": "8/ Eighth tweet in thread",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:07:00Z",
            "conversation_id": "1001",
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
        mock_get_thread.return_value = mock_tweets  # Thread context returns same tweets

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "likes", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        import json
        import re

        tweets_match = re.search(r"const TWEETS = (\[.*?\]);", content, re.DOTALL)
        assert tweets_match is not None

        tweets = json.loads(tweets_match.group(1))

        # Should have only 1 entry (deduplicated by conversation_id)
        assert len(tweets) == 1
        # Should have all three liked tweet IDs tracked
        assert set(tweets[0]["highlighted_tweet_ids"]) == {"1003", "1005", "1008"}


def test_html_export_does_not_deduplicate_replies_to_others(tmp_path: Path) -> None:
    """Replies to other users' comments should NOT be deduplicated with the thread.

    If the author replies to someone else's comment on their thread, that reply
    should appear as a separate entry, not grouped with the main thread.
    """
    author_id = "author123"
    other_user_id = "other456"
    conversation_id = "1001"  # Thread start

    # Tweet in the main thread (thread start)
    thread_tweet = {
        "id": "1001",
        "text": "Starting a thread",
        "author_id": author_id,
        "author_username": "author",
        "created_at": "2025-01-01T12:00:00Z",
        "conversation_id": conversation_id,
        "in_reply_to_user_id": None,
        "in_reply_to_tweet_id": None,
    }

    # Author's reply to someone else's comment (NOT part of main thread)
    reply_to_other = {
        "id": "1003",
        "text": "@otheruser Thanks for the feedback!",
        "author_id": author_id,
        "author_username": "author",
        "created_at": "2025-01-01T12:10:00Z",
        "conversation_id": conversation_id,
        "in_reply_to_user_id": other_user_id,  # Reply to OTHER user
        "in_reply_to_tweet_id": "1002",  # Other user's comment
    }

    mock_tweets = [thread_tweet, reply_to_other]
    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_tweets_by_collection") as mock_get,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_thread,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get.return_value = mock_tweets
        mock_thread.return_value = mock_tweets

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "likes", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # Parse the TWEETS array
        match = re.search(r"const TWEETS = (\[.*?\]);", content, re.DOTALL)
        assert match
        tweets = json.loads(match.group(1))

        # Should have TWO entries: the thread AND the reply to other user
        assert len(tweets) == 2

        # First should be the thread start
        assert tweets[0]["id"] == "1001"
        assert tweets[0]["highlighted_tweet_ids"] == ["1001"]

        # Second should be the reply to other user (separate entry)
        assert tweets[1]["id"] == "1003"
        assert tweets[1]["highlighted_tweet_ids"] == ["1003"]


def test_html_export_has_copy_as_markdown_function(tmp_path: Path) -> None:
    """HTML export should have a copyAsMarkdown JavaScript function."""
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

        # Should have copyAsMarkdown function
        assert "function copyAsMarkdown" in content


def test_html_export_has_copy_link_next_to_view(tmp_path: Path) -> None:
    """HTML export should have a Copy link next to the View link."""
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

        # Should have Copy link in template (View | Copy pattern)
        assert ">View</a>" in content
        assert ">Copy</a>" in content


def test_html_export_thread_has_copy_link(tmp_path: Path) -> None:
    """HTML export should have Copy link for threads too."""
    # Thread with 2 tweets
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
            "in_reply_to_tweet_id": "1",
            "in_reply_to_user_id": "user1",
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
        content = output_file.read_text()

        # Thread template should also have Copy link
        # The thread template has a specific pattern with article class='thread
        assert "article class='thread" in content
        # Count Copy links - should be at least 2 (one for threads, one for single tweets)
        copy_count = content.count(">Copy</a>")
        assert copy_count >= 2, f"Expected at least 2 Copy links, found {copy_count}"


def test_html_export_copy_markdown_uses_clipboard_api(tmp_path: Path) -> None:
    """CopyAsMarkdown should use navigator.clipboard.writeText."""
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

        # Should use navigator.clipboard.writeText
        assert "navigator.clipboard.writeText" in content


def test_html_export_has_format_tweet_as_markdown_function(tmp_path: Path) -> None:
    """HTML export should have a function to format tweet as markdown."""
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

        # Should have a function to format tweet as markdown
        assert "function formatTweetAsMarkdown" in content


def test_html_export_format_markdown_includes_view_link(tmp_path: Path) -> None:
    """FormatTweetAsMarkdown should include a View on X link."""
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

        # formatTweetAsMarkdown should build x.com URL and View on X link
        assert "x.com" in content
        assert "View on X" in content


def test_html_export_format_markdown_includes_author_info(tmp_path: Path) -> None:
    """FormatTweetAsMarkdown should include author username and display name."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Test tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "author_display_name": "Test User",
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

        # formatTweetAsMarkdown should include author username with @ and bold
        assert "t.author_username" in content
        assert "t.author_display_name" in content


def test_html_export_format_markdown_includes_tweet_text(tmp_path: Path) -> None:
    """FormatTweetAsMarkdown should include tweet text."""
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

        # formatTweetAsMarkdown should include tweet text (t.text)
        assert "t.text" in content


def test_html_export_has_url_expansion_for_markdown(tmp_path: Path) -> None:
    """HTML export should have a function to expand URLs for markdown copy."""
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

        # Should have a function to get plain text with expanded URLs
        assert "function getPlainTextWithUrls" in content


def test_html_export_url_expansion_replaces_tco_urls(tmp_path: Path) -> None:
    """GetPlainTextWithUrls should replace t.co URLs with expanded URLs."""
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

        # getPlainTextWithUrls should parse URLs JSON and replace
        assert "getPlainTextWithUrls" in content
        # Should replace t.co URLs
        assert "t.co" in content


def test_html_export_copy_link_calls_format_markdown(tmp_path: Path) -> None:
    """Copy link onclick should call formatTweetAsMarkdown."""
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

        # onclick should call formatTweetAsMarkdown
        assert "formatTweetAsMarkdown" in content
        # Copy link should invoke both format and copy
        assert "copyAsMarkdown(formatTweetAsMarkdown" in content


def test_html_export_format_markdown_detailed_format(tmp_path: Path) -> None:
    """FormatTweetAsMarkdown should return detailed format with author, text, link."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Test tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "author_display_name": "Test User",
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

        # formatTweetAsMarkdown should format with bold @username and display name
        assert "**@${t.author_username}**" in content
        # Should call getPlainTextWithUrls for the text
        assert "getPlainTextWithUrls(t.text" in content


def test_html_export_format_markdown_includes_display_name(tmp_path: Path) -> None:
    """FormatTweetAsMarkdown should include display name in parentheses."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Test tweet",
            "author_id": "user1",
            "author_username": "testuser",
            "author_display_name": "Test User",
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

        # Should include display name reference with parentheses
        # The format should be: **@username** (Display Name)
        assert "t.author_display_name" in content
        assert "(${" in content  # Has template literal with parentheses


def test_html_export_has_handle_copy_function(tmp_path: Path) -> None:
    """HTML export should have a handleCopy convenience function."""
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

        # Should have handleCopy function for shorter onclick handlers
        assert "function handleCopy" in content


def test_html_export_copy_link_uses_handle_copy(tmp_path: Path) -> None:
    """Copy link onclick should use handleCopy for shorter lines."""
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

        # onclick should use hc(id) which looks up tweet from TWEETS_MAP internally
        assert "function hc" in content
        assert "hc('${t.id}')" in content


def test_html_export_format_markdown_includes_quoted_tweet(tmp_path: Path) -> None:
    """Format markdown should include quoted tweet when present."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Check out this quote",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "quoted_tweet_id": "2",
        }
    ]

    output_file = tmp_path / "test.html"

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch("tweethoarder.storage.database.get_tweets_by_collection") as mock_get_tweets,
        patch("tweethoarder.storage.database.get_tweets_by_conversation_id") as mock_get_thread,
        patch("tweethoarder.storage.database.get_tweets_by_ids") as mock_get_by_ids,
    ):
        mock_data_dir.return_value = tmp_path
        mock_get_tweets.return_value = mock_tweets
        mock_get_thread.return_value = []
        mock_get_by_ids.return_value = [
            {
                "id": "2",
                "text": "Original quoted content",
                "author_id": "user2",
                "author_username": "quoteduser",
                "created_at": "2025-01-01T11:00:00Z",
            }
        ]

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "likes", "--output", str(output_file)],
        )

        assert result.exit_code == 0
        content = output_file.read_text()

        # formatTweetAsMarkdown should format quoted tweet with > blockquote
        assert "formatQuotedTweetMarkdown" in content


def test_html_export_format_markdown_includes_images(tmp_path: Path) -> None:
    """Format markdown should include images when present."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Check out this photo",
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

        # formatTweetAsMarkdown should format images as markdown
        assert "formatMediaMarkdown" in content


def test_html_export_format_media_markdown_parses_json(tmp_path: Path) -> None:
    """Format media markdown should parse media JSON and return image syntax."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Test",
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

        # formatMediaMarkdown should parse JSON and return markdown image syntax
        assert "JSON.parse(mediaJson)" in content
        assert "![](" in content


def test_html_export_format_tweet_markdown_calls_format_media(tmp_path: Path) -> None:
    """Format tweet markdown should call formatMediaMarkdown for images."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Test",
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

        # formatTweetAsMarkdown should call formatMediaMarkdown with t.media_json
        assert "formatMediaMarkdown(t.media_json)" in content


def test_html_export_has_tweet_content_wrapper_for_scrollbar_position(
    tmp_path: Path,
) -> None:
    """HTML export should have tweet-content wrapper so scrollbar appears at screen edge."""
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

        # Should have tweet-content wrapper for centered content with borders
        assert '<div id="tweet-content">' in content
        # CSS for tweet-content should center content and have borders
        assert "#tweet-content {" in content or "#tweet-content { " in content


def test_html_export_renders_videos_with_video_tag(tmp_path: Path) -> None:
    """HTML export should render videos with <video> tag instead of <img>."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Tweet with video",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "media_json": (
                '[{"type": "video", "media_url_https": "https://pbs.twimg.com/thumb.jpg", '
                '"video_url": "https://video.twimg.com/ext_tw_video/123/pu/vid/video.mp4", '
                '"width": 1280, "height": 720}]'
            ),
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

        # renderMedia should check media type and use <video> for videos
        assert "m.type === 'video'" in content or 'm.type === "video"' in content
        # Should use video_url for video source
        assert "m.video_url" in content
        # Should have video tag with controls
        assert "<video" in content
        assert "controls" in content


def test_html_export_renders_animated_gifs_with_autoplay(tmp_path: Path) -> None:
    """HTML export should render animated_gif with autoplay loop muted attributes."""
    mock_tweets = [
        {
            "id": "1",
            "text": "Tweet with GIF",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
            "media_json": (
                '[{"type": "animated_gif", '
                '"media_url_https": "https://pbs.twimg.com/thumb.jpg", '
                '"video_url": "https://video.twimg.com/tweet_video/gif.mp4", '
                '"width": 480, "height": 270}]'
            ),
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

        # renderMedia should check for animated_gif type
        assert "m.type === 'animated_gif'" in content or 'm.type === "animated_gif"' in content
        # GIFs should autoplay, loop, and be muted (like Twitter)
        assert "autoplay" in content
        assert "loop" in content
        assert "muted" in content


def test_html_export_dompurify_allows_video_tags(tmp_path: Path) -> None:
    """DOMPurify allowlist should include video and source tags for video rendering."""
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

        # DOMPurify ALLOWED_TAGS should include video and source for video rendering
        assert "'video'" in content or '"video"' in content
        assert "'source'" in content or '"source"' in content
        # ALLOWED_ATTR should include video attributes
        assert "'controls'" in content or '"controls"' in content
        assert "'autoplay'" in content or '"autoplay"' in content
        assert "'loop'" in content or '"loop"' in content
        assert "'muted'" in content or '"muted"' in content
        assert "'playsinline'" in content or '"playsinline"' in content
        assert "'preload'" in content or '"preload"' in content


def test_html_export_format_media_markdown_handles_videos(tmp_path: Path) -> None:
    """Copy as markdown should output video URL as link, not image markdown."""
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

        # formatMediaMarkdown should output [Video] link for video types
        assert "formatMediaMarkdown" in content
        assert "[Video]" in content or "[GIF]" in content
