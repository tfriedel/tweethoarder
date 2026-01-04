"""Tests for the CLI export module."""

from pathlib import Path

import pytest
from conftest import strip_ansi
from typer.testing import CliRunner

from tweethoarder.cli.main import app

runner = CliRunner()


def _setup_test_db(tmp_path: Path) -> Path:
    """Set up a test database with sample data in XDG structure."""
    from tweethoarder.storage.database import (
        add_to_collection,
        init_database,
        save_tweet,
    )

    data_dir = tmp_path / "tweethoarder"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "tweethoarder.db"
    init_database(db_path)
    save_tweet(
        db_path,
        {
            "id": "123",
            "text": "Test tweet",
            "author_id": "456",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    add_to_collection(db_path, "123", "like")
    return db_path


def test_export_json_command_exists() -> None:
    """Export json subcommand should be available."""
    result = runner.invoke(app, ["export", "json", "--help"])
    assert result.exit_code == 0
    assert "Export tweets to JSON format" in result.output


def test_export_json_has_collection_option() -> None:
    """Export json command should have collection option."""
    result = runner.invoke(app, ["export", "json", "--help"])
    assert result.exit_code == 0
    assert "--collection" in strip_ansi(result.output)


def test_export_json_has_output_option() -> None:
    """Export json command should have output path option."""
    result = runner.invoke(app, ["export", "json", "--help"])
    assert result.exit_code == 0
    assert "--output" in strip_ansi(result.output)


def test_export_json_writes_file(tmp_path: Path, monkeypatch: object) -> None:
    """Export json command should write to file."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.json"
    result = runner.invoke(
        app, ["export", "json", "--collection", "likes", "--output", str(output_path)]
    )

    assert result.exit_code == 0
    assert output_path.exists()
    content = output_path.read_text()
    assert "testuser" in content


def test_export_markdown_command_exists() -> None:
    """Export markdown subcommand should be available."""
    result = runner.invoke(app, ["export", "markdown", "--help"])
    assert result.exit_code == 0
    assert "Export tweets to Markdown format" in result.output


def test_export_markdown_has_collection_option() -> None:
    """Export markdown command should have collection option."""
    result = runner.invoke(app, ["export", "markdown", "--help"])
    assert result.exit_code == 0
    assert "--collection" in strip_ansi(result.output)


def test_export_markdown_writes_file(tmp_path: Path, monkeypatch: object) -> None:
    """Export markdown command should write to file."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.md"
    result = runner.invoke(
        app, ["export", "markdown", "--collection", "likes", "--output", str(output_path)]
    )

    assert result.exit_code == 0
    assert output_path.exists()
    content = output_path.read_text()
    assert "# Liked Tweets" in content
    assert "@testuser" in content


def test_export_markdown_uses_default_output_path(tmp_path: Path, monkeypatch: object) -> None:
    """Export markdown command should write to default path when --output not specified."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    result = runner.invoke(app, ["export", "markdown", "--collection", "likes"])

    assert result.exit_code == 0
    # Check that file was created in exports directory
    exports_dir = tmp_path / "tweethoarder" / "exports"
    assert exports_dir.exists()
    md_files = list(exports_dir.glob("likes_*.md"))
    assert len(md_files) == 1
    content = md_files[0].read_text()
    assert "# Liked Tweets" in content


def test_export_markdown_exports_all_tweets_when_no_collection(
    tmp_path: Path, monkeypatch: object
) -> None:
    """Export markdown without --collection should export all tweets."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "all.md"
    result = runner.invoke(app, ["export", "markdown", "--output", str(output_path)])

    assert result.exit_code == 0
    content = output_path.read_text()
    assert "@testuser" in content
    assert "Test tweet" in content


def test_export_csv_command_exists() -> None:
    """Export csv subcommand should be available."""
    result = runner.invoke(app, ["export", "csv", "--help"])
    assert result.exit_code == 0
    assert "Export tweets to CSV format" in result.output


def test_export_csv_has_collection_option() -> None:
    """Export csv command should have collection option."""
    result = runner.invoke(app, ["export", "csv", "--help"])
    assert result.exit_code == 0
    assert "--collection" in strip_ansi(result.output)


def test_export_csv_writes_file(tmp_path: Path, monkeypatch: object) -> None:
    """Export csv command should write to file."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.csv"
    result = runner.invoke(
        app, ["export", "csv", "--collection", "likes", "--output", str(output_path)]
    )

    assert result.exit_code == 0
    assert output_path.exists()
    content = output_path.read_text()
    assert "id" in content
    assert "testuser" in content


def test_export_html_command_exists() -> None:
    """Export html subcommand should be available."""
    result = runner.invoke(app, ["export", "html", "--help"])
    assert result.exit_code == 0
    assert "Export tweets to HTML format" in result.output


def test_export_html_writes_file(tmp_path: Path, monkeypatch: object) -> None:
    """Export html command should write self-contained HTML file."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.html"
    result = runner.invoke(
        app, ["export", "html", "--collection", "likes", "--output", str(output_path)]
    )

    assert result.exit_code == 0
    assert output_path.exists()
    content = output_path.read_text()
    assert "<!DOCTYPE html>" in content
    assert "testuser" in content


def test_export_html_has_inline_css(tmp_path: Path, monkeypatch: object) -> None:
    """Export html should include inline CSS for offline viewing."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    assert "<style>" in content


def test_export_html_has_embedded_data(tmp_path: Path, monkeypatch: object) -> None:
    """Export html should embed tweet data as JSON for search functionality."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    assert "<script>" in content


def test_export_html_has_tweets_json(tmp_path: Path, monkeypatch: object) -> None:
    """Export html should embed tweet data as TWEETS JSON array."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    assert "const TWEETS = [" in content


def test_export_html_has_facets_json(tmp_path: Path, monkeypatch: object) -> None:
    """Export html should embed pre-computed facets for filtering."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    assert "const FACETS = {" in content


def test_export_html_has_search_input(tmp_path: Path, monkeypatch: object) -> None:
    """Export html should include a search input for filtering tweets."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    assert 'type="search"' in content or 'id="search"' in content


def test_export_html_has_main_container(tmp_path: Path, monkeypatch: object) -> None:
    """Export html should have a main container for tweets."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    assert 'id="tweets"' in content or "<main" in content


def test_export_html_has_filters_sidebar(tmp_path: Path, monkeypatch: object) -> None:
    """Export html should have a filters sidebar."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    assert 'id="filters"' in content or "<aside" in content


def test_export_html_has_filter_function(tmp_path: Path, monkeypatch: object) -> None:
    """Export html should include JavaScript filtering function."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    assert "function" in content and "filter" in content.lower()


def test_export_html_has_render_function(tmp_path: Path, monkeypatch: object) -> None:
    """Export html should include JavaScript render function."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    assert "renderTweets" in content or "render" in content.lower()


def test_export_html_has_search_event_listener(tmp_path: Path, monkeypatch: object) -> None:
    """Export html should wire up search input to filtering logic."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    assert "addEventListener" in content or "oninput" in content


def test_export_html_has_responsive_layout(tmp_path: Path, monkeypatch: object) -> None:
    """Export html should have responsive CSS for sidebar layout."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    assert "display:" in content or "@media" in content or "flex" in content


def test_export_html_media_facets_are_mutually_exclusive(
    tmp_path: Path, monkeypatch: object
) -> None:
    """Media facet counts should not double-count tweets with both media and URLs."""
    import sqlite3

    from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

    data_dir = tmp_path / "tweethoarder"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "tweethoarder.db"
    init_database(db_path)

    # Save tweet first
    save_tweet(
        db_path,
        {
            "id": "tweet_with_both",
            "text": "Photo and link",
            "author_id": "user1",
            "author_username": "testuser",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    # Manually update media_json and urls_json (save_tweet doesn't support these yet)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE tweets SET media_json = ?, urls_json = ? WHERE id = ?",
            ('[{"type": "photo"}]', '[{"url": "https://example.com"}]', "tweet_with_both"),
        )
    add_to_collection(db_path, "tweet_with_both", "like")

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    # Parse FACETS from the HTML
    import json
    import re

    facets_match = re.search(r"const FACETS = ({.*?});", content)
    assert facets_match is not None
    facets = json.loads(facets_match.group(1))
    media = facets["media"]
    # Total should equal 1 (not 2 from double-counting)
    total = media["photo"] + media["video"] + media["link"] + media["text_only"]
    assert total == 1, f"Expected 1 tweet counted once, got {total} counts"


def test_export_html_escapes_special_chars_in_render(tmp_path: Path, monkeypatch: object) -> None:
    """Export html should escape HTML special chars to prevent XSS."""
    from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

    data_dir = tmp_path / "tweethoarder"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "tweethoarder.db"
    init_database(db_path)

    # Tweet with HTML/script content
    save_tweet(
        db_path,
        {
            "id": "xss_tweet",
            "text": "<script>alert('xss')</script>",
            "author_id": "attacker",
            "author_username": "evil<script>user",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    add_to_collection(db_path, "xss_tweet", "like")

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    # The render function should use escapeHtml or textContent, not raw innerHTML
    # Check that the JavaScript uses a safe rendering method
    assert "escapeHtml" in content or "textContent" in content or "createTextNode" in content


def test_export_html_no_duplicate_server_rendering(tmp_path: Path, monkeypatch: object) -> None:
    """Export html should not render tweets server-side when JS renders them."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    # Check that main container is empty (JS will populate it)
    assert '<main id="tweets">\n</main>' in content or '<main id="tweets"></main>' in content


def test_export_json_has_folder_option() -> None:
    """Export json command should have --folder option."""
    result = runner.invoke(app, ["export", "json", "--help"])
    assert result.exit_code == 0
    assert "--folder" in strip_ansi(result.output)


def test_export_json_folder_filters_bookmarks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Export json with --folder should only include bookmarks from that folder."""
    import json
    import sqlite3

    from tweethoarder.storage.database import init_database, save_tweet

    data_dir = tmp_path / "tweethoarder"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "tweethoarder.db"
    init_database(db_path)

    # Create two tweets
    save_tweet(
        db_path,
        {
            "id": "work_tweet",
            "text": "Work bookmark",
            "author_id": "user1",
            "author_username": "worker",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    save_tweet(
        db_path,
        {
            "id": "personal_tweet",
            "text": "Personal bookmark",
            "author_id": "user2",
            "author_username": "personal",
            "created_at": "2025-01-01T13:00:00Z",
        },
    )

    # Add to bookmarks with different folders
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO collections (tweet_id, collection_type, bookmark_folder_name, "
            "added_at, synced_at) VALUES (?, ?, ?, ?, ?)",
            ("work_tweet", "bookmark", "Work", "2025-01-01T12:00:00Z", "2025-01-01T12:00:00Z"),
        )
        conn.execute(
            "INSERT INTO collections (tweet_id, collection_type, bookmark_folder_name, "
            "added_at, synced_at) VALUES (?, ?, ?, ?, ?)",
            (
                "personal_tweet",
                "bookmark",
                "Personal",
                "2025-01-01T13:00:00Z",
                "2025-01-01T13:00:00Z",
            ),
        )

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # type: ignore[attr-defined]

    output_path = tmp_path / "output.json"
    result = runner.invoke(
        app,
        [
            "export",
            "json",
            "--collection",
            "bookmarks",
            "--folder",
            "Work",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    content = json.loads(output_path.read_text())
    # Should only include the Work bookmark
    assert len(content["tweets"]) == 1
    assert content["tweets"][0]["id"] == "work_tweet"


def test_export_markdown_has_folder_option() -> None:
    """Export markdown command should have --folder option."""
    result = runner.invoke(app, ["export", "markdown", "--help"])
    assert result.exit_code == 0
    assert "--folder" in strip_ansi(result.output)


def test_export_csv_has_folder_option() -> None:
    """Export csv command should have --folder option."""
    result = runner.invoke(app, ["export", "csv", "--help"])
    assert result.exit_code == 0
    assert "--folder" in strip_ansi(result.output)


def test_export_html_has_folder_option() -> None:
    """Export html command should have --folder option."""
    result = runner.invoke(app, ["export", "html", "--help"])
    assert result.exit_code == 0
    assert "--folder" in strip_ansi(result.output)


def test_export_html_includes_view_on_twitter_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Export html should include a View on Twitter link in the render function."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    # The render function should include a link to x.com/username/status/id
    assert "x.com" in content or "twitter.com" in content


def test_export_html_renders_author_display_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Export html renderTweets should use author display name."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    # The render function should use t.author_display_name in the template
    assert "t.author_display_name" in content


def test_export_html_renders_created_at(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Export html renderTweets should display created_at date."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    # The render function should use t.created_at in the template
    assert "t.created_at" in content


def test_export_html_has_expand_urls_function(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Export html should include a function to expand t.co URLs."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    # Should have an expandUrls function that uses urls_json
    assert "function expandUrls" in content


def test_export_html_render_uses_expand_urls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Export html renderTweets should call expandUrls on tweet text."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    # Render should call expandUrls with text and urls_json
    assert "expandUrls(t.text, t.urls_json)" in content


def test_export_html_renders_author_avatar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Export html renderTweets should display author avatar if available."""
    _setup_test_db(tmp_path)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    output_path = tmp_path / "output.html"
    runner.invoke(app, ["export", "html", "--collection", "likes", "--output", str(output_path)])

    content = output_path.read_text()
    # Render should reference author_avatar_url
    assert "t.author_avatar_url" in content


def test_export_json_folder_ignored_for_non_bookmarks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Export json with --folder should be ignored when collection is not bookmarks."""
    import json

    from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

    data_dir = tmp_path / "tweethoarder"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "tweethoarder.db"
    init_database(db_path)

    # Create a liked tweet
    save_tweet(
        db_path,
        {
            "id": "liked_tweet",
            "text": "A liked tweet",
            "author_id": "user1",
            "author_username": "liker",
            "created_at": "2025-01-01T12:00:00Z",
        },
    )
    add_to_collection(db_path, "liked_tweet", "like")

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    output_path = tmp_path / "output.json"
    # Using --folder with --collection likes should still export the like
    result = runner.invoke(
        app,
        [
            "export",
            "json",
            "--collection",
            "likes",
            "--folder",
            "SomeFolder",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    content = json.loads(output_path.read_text())
    # Should export the liked tweet (folder is ignored for non-bookmark collections)
    assert len(content["tweets"]) == 1
    assert content["tweets"][0]["id"] == "liked_tweet"


def test_export_markdown_includes_thread_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Export markdown should include thread context when available."""
    from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

    data_dir = tmp_path / "tweethoarder"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "tweethoarder.db"
    init_database(db_path)

    # Create a thread with 3 tweets
    save_tweet(
        db_path,
        {
            "id": "100",
            "text": "1/ First in thread",
            "author_id": "user1",
            "author_username": "threadauthor",
            "created_at": "2025-01-01T12:00:00Z",
            "conversation_id": "100",
        },
    )
    save_tweet(
        db_path,
        {
            "id": "101",
            "text": "2/ Second in thread",
            "author_id": "user1",
            "author_username": "threadauthor",
            "created_at": "2025-01-01T12:01:00Z",
            "conversation_id": "100",
        },
    )
    save_tweet(
        db_path,
        {
            "id": "102",
            "text": "3/ Third in thread",
            "author_id": "user1",
            "author_username": "threadauthor",
            "created_at": "2025-01-01T12:02:00Z",
            "conversation_id": "100",
        },
    )
    # Like only the second tweet
    add_to_collection(db_path, "101", "like")

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    output_path = tmp_path / "output.md"
    result = runner.invoke(
        app, ["export", "markdown", "--collection", "likes", "--output", str(output_path)]
    )

    assert result.exit_code == 0
    content = output_path.read_text()
    # Should show all 3 tweets in thread
    assert "1/ First in thread" in content
    assert "2/ Second in thread" in content
    assert "3/ Third in thread" in content
    # Should have thread indicator
    assert "🧵" in content
    # Should mark the liked tweet
    assert "⭐" in content


def test_export_markdown_continues_on_thread_context_error(tmp_path: Path) -> None:
    """Export should continue even if fetching thread context fails."""
    from unittest.mock import patch

    from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

    data_dir = tmp_path / "tweethoarder"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "tweethoarder.db"
    init_database(db_path)

    save_tweet(
        db_path,
        {
            "id": "1",
            "text": "Tweet with thread context",
            "author_id": "100",
            "author_username": "user",
            "created_at": "2025-01-01T12:00:00Z",
            "conversation_id": "1",
        },
    )
    add_to_collection(db_path, "1", "like")

    output_path = tmp_path / "test.md"

    def failing_get_tweets(*args: object, **kwargs: object) -> list[dict[str, object]]:
        raise Exception("Database error")

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch(
            "tweethoarder.storage.database.get_tweets_by_conversation_id",
            side_effect=failing_get_tweets,
        ),
    ):
        mock_data_dir.return_value = data_dir

        result = runner.invoke(
            app,
            ["export", "markdown", "--collection", "likes", "--output", str(output_path)],
        )

        # Export should succeed despite thread context error
        assert result.exit_code == 0
        content = output_path.read_text()
        # Tweet should still be exported
        assert "Tweet with thread context" in content


def test_export_html_continues_on_thread_context_error(tmp_path: Path) -> None:
    """HTML export should continue even if fetching thread context fails."""
    from unittest.mock import patch

    from tweethoarder.storage.database import add_to_collection, init_database, save_tweet

    data_dir = tmp_path / "tweethoarder"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "tweethoarder.db"
    init_database(db_path)

    save_tweet(
        db_path,
        {
            "id": "1",
            "text": "Tweet with thread context",
            "author_id": "100",
            "author_username": "user",
            "created_at": "2025-01-01T12:00:00Z",
            "conversation_id": "1",
        },
    )
    add_to_collection(db_path, "1", "like")

    output_path = tmp_path / "test.html"

    def failing_get_tweets(*args: object, **kwargs: object) -> list[dict[str, object]]:
        raise Exception("Database error")

    with (
        patch("tweethoarder.config.get_data_dir") as mock_data_dir,
        patch(
            "tweethoarder.storage.database.get_tweets_by_conversation_id",
            side_effect=failing_get_tweets,
        ),
    ):
        mock_data_dir.return_value = data_dir

        result = runner.invoke(
            app,
            ["export", "html", "--collection", "likes", "--output", str(output_path)],
        )

        # Export should succeed despite thread context error
        assert result.exit_code == 0
        content = output_path.read_text()
        # Tweet should still be exported
        assert "Tweet with thread context" in content
