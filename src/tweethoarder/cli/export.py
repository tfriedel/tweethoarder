"""Export commands for TweetHoarder CLI."""

from pathlib import Path
from typing import Any

import typer

app = typer.Typer(
    name="export",
    help="Export synced data to various formats.",
)


@app.command()
def json(
    collection: str | None = typer.Option(
        None,
        "--collection",
        help="Filter by collection type (likes, bookmarks, tweets, reposts).",
    ),
    folder: str | None = typer.Option(
        None,
        "--folder",
        help="Filter bookmarks by folder name (only works with --collection bookmarks).",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Output file path.",
    ),
) -> None:
    """Export tweets to JSON format."""
    import json as json_lib

    from tweethoarder.config import get_data_dir
    from tweethoarder.export.json_export import export_tweets_to_json
    from tweethoarder.storage.database import (
        get_all_tweets,
        get_tweets_by_bookmark_folder,
        get_tweets_by_collection,
    )

    data_dir = get_data_dir()
    db_path = data_dir / "tweethoarder.db"
    collection_type = COLLECTION_MAP.get(collection, collection) if collection else None

    tweets: list[dict[str, Any]]
    if folder and collection_type == "bookmark":
        tweets = get_tweets_by_bookmark_folder(db_path, folder)
    elif collection_type:
        tweets = get_tweets_by_collection(db_path, collection_type)
    else:
        tweets = get_all_tweets(db_path)

    result = export_tweets_to_json(tweets, collection=collection)
    content = json_lib.dumps(result, indent=2, ensure_ascii=False)

    output_path = output or _get_default_export_path(data_dir, collection, "json")
    output_path.write_text(content)


def _get_default_export_path(data_dir: Path, collection: str | None, fmt: str) -> Path:
    """Generate default export path with timestamp."""
    from datetime import UTC, datetime

    exports_dir = data_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    filename = f"{collection or 'all'}_{timestamp}.{fmt}"
    return exports_dir / filename


# Map from CLI plural names to database singular names
COLLECTION_MAP = {
    "likes": "like",
    "bookmarks": "bookmark",
    "tweets": "tweet",
    "reposts": "repost",
}


@app.command()
def markdown(
    collection: str | None = typer.Option(
        None,
        "--collection",
        help="Filter by collection type (likes, bookmarks, tweets, reposts).",
    ),
    folder: str | None = typer.Option(
        None,
        "--folder",
        help="Filter bookmarks by folder name (only works with --collection bookmarks).",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Output file path.",
    ),
) -> None:
    """Export tweets to Markdown format."""
    from tweethoarder.config import get_data_dir
    from tweethoarder.export.markdown_export import export_tweets_to_markdown
    from tweethoarder.storage.database import (
        get_all_tweets,
        get_tweets_by_bookmark_folder,
        get_tweets_by_collection,
    )

    data_dir = get_data_dir()
    db_path = data_dir / "tweethoarder.db"
    collection_type = COLLECTION_MAP.get(collection, collection) if collection else None

    tweets: list[dict[str, Any]]
    if folder and collection_type == "bookmark":
        tweets = get_tweets_by_bookmark_folder(db_path, folder)
    elif collection_type:
        tweets = get_tweets_by_collection(db_path, collection_type)
    else:
        tweets = get_all_tweets(db_path)

    content = export_tweets_to_markdown(tweets, collection=collection)

    output_path = output or _get_default_export_path(data_dir, collection, "md")
    output_path.write_text(content)


@app.command()
def csv(
    collection: str | None = typer.Option(
        None,
        "--collection",
        help="Filter by collection type (likes, bookmarks, tweets, reposts).",
    ),
    folder: str | None = typer.Option(
        None,
        "--folder",
        help="Filter bookmarks by folder name (only works with --collection bookmarks).",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Output file path.",
    ),
) -> None:
    """Export tweets to CSV format."""
    from tweethoarder.config import get_data_dir
    from tweethoarder.export.csv_export import export_tweets_to_csv
    from tweethoarder.storage.database import (
        get_all_tweets,
        get_tweets_by_bookmark_folder,
        get_tweets_by_collection,
    )

    data_dir = get_data_dir()
    db_path = data_dir / "tweethoarder.db"
    collection_type = COLLECTION_MAP.get(collection, collection) if collection else None

    tweets: list[dict[str, Any]]
    if folder and collection_type == "bookmark":
        tweets = get_tweets_by_bookmark_folder(db_path, folder)
    elif collection_type:
        tweets = get_tweets_by_collection(db_path, collection_type)
    else:
        tweets = get_all_tweets(db_path)

    content = export_tweets_to_csv(tweets)

    output_path = output or _get_default_export_path(data_dir, collection, "csv")
    output_path.write_text(content)


@app.command()
def html(
    collection: str | None = typer.Option(
        None,
        "--collection",
        help="Filter by collection type (likes, bookmarks, tweets, reposts).",
    ),
    folder: str | None = typer.Option(
        None,
        "--folder",
        help="Filter bookmarks by folder name (only works with --collection bookmarks).",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Output file path.",
    ),
) -> None:
    """Export tweets to HTML format."""
    from tweethoarder.config import get_data_dir
    from tweethoarder.storage.database import (
        get_all_tweets,
        get_tweets_by_bookmark_folder,
        get_tweets_by_collection,
    )

    data_dir = get_data_dir()
    db_path = data_dir / "tweethoarder.db"
    collection_type = COLLECTION_MAP.get(collection, collection) if collection else None

    tweets: list[dict[str, Any]]
    if folder and collection_type == "bookmark":
        tweets = get_tweets_by_bookmark_folder(db_path, folder)
    elif collection_type:
        tweets = get_tweets_by_collection(db_path, collection_type)
    else:
        tweets = get_all_tweets(db_path)

    import json
    from collections import Counter

    tweets_json = json.dumps(tweets)

    # Compute facets
    author_counts: Counter[str] = Counter()
    month_counts: Counter[str] = Counter()
    media_counts = {"photo": 0, "video": 0, "link": 0, "text_only": 0}

    for tweet in tweets:
        username = tweet.get("author_username", "unknown")
        author_counts[username] += 1

        created_at = tweet.get("created_at", "")
        if created_at and len(created_at) >= 7:
            month = created_at[:7]  # YYYY-MM
            month_counts[month] += 1

        media_json = tweet.get("media_json")
        urls_json = tweet.get("urls_json")
        has_media = False

        if media_json:
            has_media = True
            if "video" in str(media_json).lower():
                media_counts["video"] += 1
            else:
                media_counts["photo"] += 1
        elif urls_json:
            has_media = True
            media_counts["link"] += 1
        if not has_media:
            media_counts["text_only"] += 1

    facets = {
        "authors": [{"username": u, "count": c} for u, c in author_counts.most_common()],
        "months": [{"month": m, "count": c} for m, c in sorted(month_counts.items())],
        "media": media_counts,
    }
    facets_json = json.dumps(facets)

    lines = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<style>",
        "body { font-family: sans-serif; display: flex; margin: 0; }",
        "#filters { width: 250px; padding: 1rem; border-right: 1px solid #ddd; }",
        "#tweets { flex: 1; padding: 1rem; overflow-y: auto; }",
        "article { margin-bottom: 1rem; padding: 0.5rem; border-bottom: 1px solid #eee; }",
        "@media (max-width: 768px) { body { flex-direction: column; } "
        "#filters { width: 100%; border-right: none; border-bottom: 1px solid #ddd; } }",
        "</style>",
        "<script>",
        f"const TWEETS = {tweets_json};",
        f"const FACETS = {facets_json};",
        "function escapeHtml(s) {",
        "  const div = document.createElement('div');",
        "  div.textContent = s;",
        "  return div.innerHTML;",
        "}",
        "function filterTweets(query) {",
        "  return TWEETS.filter(t => "
        "!query || t.text.toLowerCase().includes(query.toLowerCase()));",
        "}",
        "function renderTweets(tweets) {",
        "  const container = document.getElementById('tweets');",
        "  container.innerHTML = tweets.map(t => "
        "`<article><p>@${escapeHtml(t.author_username)}: "
        "${escapeHtml(t.text)}</p></article>`).join('');",
        "}",
        "document.addEventListener('DOMContentLoaded', () => {",
        "  const search = document.getElementById('search');",
        "  search.addEventListener('input', () => renderTweets(filterTweets(search.value)));",
        "  renderTweets(TWEETS);",
        "});",
        "</script>",
        "</head>",
        "<body>",
        '<aside id="filters">',
        '<input type="search" id="search" placeholder="Search tweets...">',
        "</aside>",
        '<main id="tweets">',
        "</main>",
    ]
    lines.append("</body>")
    lines.append("</html>")
    content = "\n".join(lines)

    output_path = output or _get_default_export_path(data_dir, collection, "html")
    output_path.write_text(content)
