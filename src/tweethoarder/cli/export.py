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
    from tweethoarder.storage.database import get_all_tweets, get_tweets_by_collection

    data_dir = get_data_dir()
    db_path = data_dir / "tweethoarder.db"
    collection_type = COLLECTION_MAP.get(collection, collection) if collection else None
    tweets: list[dict[str, Any]] = (
        get_tweets_by_collection(db_path, collection_type)
        if collection_type
        else get_all_tweets(db_path)
    )
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
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Output file path.",
    ),
) -> None:
    """Export tweets to Markdown format."""
    from tweethoarder.config import get_data_dir
    from tweethoarder.export.markdown_export import export_tweets_to_markdown
    from tweethoarder.storage.database import get_all_tweets, get_tweets_by_collection

    data_dir = get_data_dir()
    db_path = data_dir / "tweethoarder.db"
    collection_type = COLLECTION_MAP.get(collection, collection) if collection else None
    tweets: list[dict[str, Any]] = (
        get_tweets_by_collection(db_path, collection_type)
        if collection_type
        else get_all_tweets(db_path)
    )
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
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Output file path.",
    ),
) -> None:
    """Export tweets to CSV format."""
    from tweethoarder.config import get_data_dir
    from tweethoarder.export.csv_export import export_tweets_to_csv
    from tweethoarder.storage.database import get_all_tweets, get_tweets_by_collection

    data_dir = get_data_dir()
    db_path = data_dir / "tweethoarder.db"
    collection_type = COLLECTION_MAP.get(collection, collection) if collection else None
    tweets: list[dict[str, Any]] = (
        get_tweets_by_collection(db_path, collection_type)
        if collection_type
        else get_all_tweets(db_path)
    )
    content = export_tweets_to_csv(tweets)

    output_path = output or _get_default_export_path(data_dir, collection, "csv")
    output_path.write_text(content)
