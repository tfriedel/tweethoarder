"""Tests for the CLI export module."""

from pathlib import Path

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
