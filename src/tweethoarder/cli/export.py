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
        help="Filter by collection type (likes, bookmarks, tweets, reposts, replies, posts).",
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
        get_tweets_by_collections,
    )

    data_dir = get_data_dir()
    db_path = data_dir / "tweethoarder.db"
    collection_type = COLLECTION_MAP.get(collection, collection) if collection else None

    tweets: list[dict[str, Any]]
    if folder and collection_type == "bookmark":
        tweets = get_tweets_by_bookmark_folder(db_path, folder)
    elif isinstance(collection_type, list):
        # Combined collection (e.g., "posts" = tweets + replies + reposts)
        tweets = get_tweets_by_collections(db_path, collection_type)
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
    "replies": "reply",
    "posts": ["tweet", "repost"],  # Combined collection (replies not available via API)
    "all": "all",  # Export all tweets with collection types
}


@app.command()
def markdown(
    collection: str | None = typer.Option(
        None,
        "--collection",
        help="Filter by collection type (likes, bookmarks, tweets, reposts, replies, posts).",
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
        get_tweets_by_collections,
        get_tweets_by_conversation_id,
        get_tweets_by_ids,
    )

    data_dir = get_data_dir()
    db_path = data_dir / "tweethoarder.db"
    collection_type = COLLECTION_MAP.get(collection, collection) if collection else None

    tweets: list[dict[str, Any]]
    if folder and collection_type == "bookmark":
        tweets = get_tweets_by_bookmark_folder(db_path, folder)
    elif isinstance(collection_type, list):
        tweets = get_tweets_by_collections(db_path, collection_type)
    elif collection_type:
        tweets = get_tweets_by_collection(db_path, collection_type)
    else:
        tweets = get_all_tweets(db_path)

    # Build thread context for tweets with conversation_id
    thread_context: dict[str, list[dict[str, Any]]] = {}
    for tweet in tweets:
        conv_id = tweet.get("conversation_id")
        if conv_id and conv_id not in thread_context:
            try:
                thread_context[conv_id] = get_tweets_by_conversation_id(db_path, conv_id)
            except Exception:
                thread_context[conv_id] = []

    # Collect quoted tweet IDs and fetch them
    tweet_ids_in_collection = {t["id"] for t in tweets}
    quoted_tweet_ids = [
        t["quoted_tweet_id"]
        for t in tweets
        if t.get("quoted_tweet_id") and t["quoted_tweet_id"] not in tweet_ids_in_collection
    ]
    quoted_tweets_list = get_tweets_by_ids(db_path, quoted_tweet_ids)
    quoted_tweets = {t["id"]: t for t in quoted_tweets_list}
    # Also add quoted tweets that are already in our collection
    for t in tweets:
        quoted_tweets[t["id"]] = t

    # Collect parent tweet IDs for replies and fetch them
    parent_tweet_ids = [
        t["in_reply_to_tweet_id"]
        for t in tweets
        if t.get("in_reply_to_tweet_id")
        and t["in_reply_to_tweet_id"] not in tweet_ids_in_collection
    ]
    parent_tweets_list = get_tweets_by_ids(db_path, parent_tweet_ids)
    parent_tweets = {t["id"]: t for t in parent_tweets_list}

    content = export_tweets_to_markdown(
        tweets,
        collection=collection,
        thread_context=thread_context,
        quoted_tweets=quoted_tweets,
        parent_tweets=parent_tweets,
    )

    output_path = output or _get_default_export_path(data_dir, collection, "md")
    output_path.write_text(content)


@app.command()
def csv(
    collection: str | None = typer.Option(
        None,
        "--collection",
        help="Filter by collection type (likes, bookmarks, tweets, reposts, replies, posts).",
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
        get_tweets_by_collections,
    )

    data_dir = get_data_dir()
    db_path = data_dir / "tweethoarder.db"
    collection_type = COLLECTION_MAP.get(collection, collection) if collection else None

    tweets: list[dict[str, Any]]
    if folder and collection_type == "bookmark":
        tweets = get_tweets_by_bookmark_folder(db_path, folder)
    elif isinstance(collection_type, list):
        tweets = get_tweets_by_collections(db_path, collection_type)
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
        help="Filter by collection type (likes, bookmarks, tweets, reposts, replies, posts, all).",
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
        get_all_tweets_with_collection_types,
        get_tweets_by_bookmark_folder,
        get_tweets_by_collection,
        get_tweets_by_collections,
        get_tweets_by_conversation_id,
        get_tweets_by_ids,
    )

    data_dir = get_data_dir()
    db_path = data_dir / "tweethoarder.db"
    collection_type = COLLECTION_MAP.get(collection, collection) if collection else None

    tweets: list[dict[str, Any]]
    if collection_type == "all":
        tweets = get_all_tweets_with_collection_types(db_path)
    elif folder and collection_type == "bookmark":
        tweets = get_tweets_by_bookmark_folder(db_path, folder)
    elif isinstance(collection_type, list):
        tweets = get_tweets_by_collections(db_path, collection_type)
    elif collection_type:
        tweets = get_tweets_by_collection(db_path, collection_type)
    else:
        tweets = get_all_tweets(db_path)

    # Build thread context for tweets with conversation_id
    thread_context: dict[str, list[dict[str, Any]]] = {}
    for tweet in tweets:
        conv_id = tweet.get("conversation_id")
        if conv_id and conv_id not in thread_context:
            try:
                thread_context[conv_id] = get_tweets_by_conversation_id(db_path, conv_id)
            except Exception:
                thread_context[conv_id] = []

    # Collect quoted tweet IDs that aren't already in our collection
    tweet_ids_in_collection = {t["id"] for t in tweets}
    quoted_tweet_ids = [
        t["quoted_tweet_id"]
        for t in tweets
        if t.get("quoted_tweet_id") and t["quoted_tweet_id"] not in tweet_ids_in_collection
    ]
    # Fetch quoted tweets from database
    quoted_tweets = get_tweets_by_ids(db_path, quoted_tweet_ids)

    import json
    from collections import Counter

    from tweethoarder.export.richtext import extract_richtext_tags

    def extract_retweeter_username(raw_json: str | None) -> str | None:
        """Extract retweeter username from raw_json for retweets."""
        if not raw_json:
            return None
        try:
            raw = json.loads(raw_json)
            # Check if this is a retweet
            if not raw.get("legacy", {}).get("retweeted_status_result"):
                return None
            # The retweeter is the user in core.user_results
            user_result = raw.get("core", {}).get("user_results", {}).get("result", {})
            screen_name: str | None = user_result.get("legacy", {}).get(
                "screen_name"
            ) or user_result.get("core", {}).get("screen_name")
            return screen_name
        except (json.JSONDecodeError, TypeError):
            return None

    # Extract richtext_tags and retweeter_username from raw_json for each tweet
    for tweet in tweets:
        richtext_tags = extract_richtext_tags(tweet.get("raw_json"))
        if richtext_tags:
            tweet["richtext_tags"] = richtext_tags
        retweeter = extract_retweeter_username(tweet.get("raw_json"))
        if retweeter:
            tweet["retweeter_username"] = retweeter
    for tweet in quoted_tweets:
        richtext_tags = extract_richtext_tags(tweet.get("raw_json"))
        if richtext_tags:
            tweet["richtext_tags"] = richtext_tags

    # Deduplicate: merge repost entries with their original tweets if both exist
    # When we have both a repost (is_retweet=True, retweeted_tweet_id=X) and
    # the original tweet (id=X) in our collection, merge them into one entry
    tweet_by_id = {t["id"]: t for t in tweets}
    repost_ids_to_remove: set[str] = set()

    for tweet in tweets:
        if tweet.get("is_retweet") and tweet.get("retweeted_tweet_id"):
            original_id = tweet["retweeted_tweet_id"]
            if original_id in tweet_by_id:
                # Original tweet exists in our collection - merge collection types
                original_tweet = tweet_by_id[original_id]
                repost_types = tweet.get("collection_types", [])
                original_types = original_tweet.get("collection_types", [])
                # Merge collection types (avoiding duplicates)
                merged_types = list(original_types)
                for ct in repost_types:
                    if ct not in merged_types:
                        merged_types.append(ct)
                original_tweet["collection_types"] = merged_types
                # Mark this repost entry for removal
                repost_ids_to_remove.add(tweet["id"])

    # Remove merged repost entries
    if repost_ids_to_remove:
        tweets = [t for t in tweets if t["id"] not in repost_ids_to_remove]

    # Strip unused fields to reduce HTML size
    used_fields = {
        "id",
        "text",
        "author_id",
        "author_username",
        "author_display_name",
        "author_avatar_url",
        "created_at",
        "conversation_id",
        "urls_json",
        "media_json",
        "is_retweet",
        "retweeter_username",
        "quoted_tweet_id",
        "richtext_tags",
        "collection_types",
    }
    stripped_tweets = [{k: v for k, v in t.items() if k in used_fields} for t in tweets]
    # Include quoted tweets separately for TWEETS_MAP lookup only
    stripped_quoted = [{k: v for k, v in t.items() if k in used_fields} for t in quoted_tweets]
    tweets_json = json.dumps(stripped_tweets)
    quoted_tweets_json = json.dumps(stripped_quoted)

    # Compute facets
    author_data: dict[str, dict[str, str | int]] = {}
    month_counts: Counter[str] = Counter()
    media_counts = {"photo": 0, "video": 0, "link": 0, "text_only": 0}
    type_counts: Counter[str] = Counter()

    for tweet in tweets:
        username = tweet.get("author_username", "unknown")
        if username not in author_data:
            author_data[username] = {
                "username": username,
                "display_name": tweet.get("author_display_name", username),
                "count": 0,
            }
        author_data[username]["count"] = int(author_data[username]["count"]) + 1

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

        # Count collection types
        collection_types = tweet.get("collection_types", [])
        for ct in collection_types:
            type_counts[ct] += 1

    facets = {
        "authors": sorted(author_data.values(), key=lambda x: -int(x["count"])),
        "months": [{"month": m, "count": c} for m, c in sorted(month_counts.items())],
        "media": media_counts,
        "types": dict(type_counts),
    }
    facets_json = json.dumps(facets)
    # Extract richtext_tags for thread context tweets
    for thread_tweets in thread_context.values():
        for tweet in thread_tweets:
            richtext_tags = extract_richtext_tags(tweet.get("raw_json"))
            if richtext_tags:
                tweet["richtext_tags"] = richtext_tags
    # Strip unused fields from thread context too
    stripped_thread_context = {
        conv_id: [{k: v for k, v in t.items() if k in used_fields} for t in thread_tweets]
        for conv_id, thread_tweets in thread_context.items()
    }
    thread_context_json = json.dumps(stripped_thread_context)

    lines = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '<meta charset="utf-8">',
        # DOMPurify for safe HTML sanitization
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.6/purify.min.js"'
        ' integrity="sha512-H+rglffZ6f5gF7UJgvH4Naa+fGCgjrHKMgoFOGmcPjXeDNcgKOj'
        'pIDK/RbAHbU2HcwrugFrHPkpJNZpyT1eQzQ=="'
        ' crossorigin="anonymous" referrerpolicy="no-referrer"></script>',
        "<style>",
        # CSS Variables - Default to Dark ("Lights Out") theme
        ":root { "
        "--bg-primary: hsl(0 0% 0%); "
        "--bg-secondary: hsl(220 12% 10%); "
        "--text-primary: hsl(200 7% 91%); "
        "--text-secondary: hsl(240 5% 65%); "
        "--border-color: hsl(210 7% 18%); "
        "--accent-blue: hsl(204 88% 53%); "
        "--accent-pink: hsl(356 91% 54%); "
        "--accent-green: hsl(160 100% 36%); "
        "--font-stack: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
        "Helvetica, Arial, sans-serif; "
        "--tweet-max-width: 600px; "
        "--avatar-size: 48px; "
        "}",
        # Light theme
        '[data-theme="light"] { '
        "--bg-primary: hsl(0 0% 100%); "
        "--bg-secondary: hsl(180 14% 97%); "
        "--text-primary: hsl(210 25% 8%); "
        "--text-secondary: hsl(206 15% 38%); "
        "--border-color: hsl(197 16% 91%); "
        "}",
        # Dim theme
        '[data-theme="dim"] { '
        "--bg-primary: hsl(210 34% 13%); "
        "--bg-secondary: hsl(213 25% 16%); "
        "--text-primary: hsl(180 14% 97%); "
        "--text-secondary: hsl(240 5% 65%); "
        "--border-color: hsl(210 21% 28%); "
        "}",
        # Base styles
        "* { box-sizing: border-box; }",
        "body { font-family: var(--font-stack); display: flex; margin: 0; "
        "background: var(--bg-primary); color: var(--text-primary); min-height: 100vh; }",
        "#filters { width: 280px; padding: 16px; border-right: 1px solid var(--border-color); "
        "background: var(--bg-primary); overflow-y: auto; height: 100vh; "
        "position: sticky; top: 0; }",
        "#tweets { flex: 1; max-width: var(--tweet-max-width); margin: 0 auto; "
        "border-left: 1px solid var(--border-color); "
        "border-right: 1px solid var(--border-color); }",
        # Tweet card styles
        "article { border-bottom: 1px solid var(--border-color); padding: 12px 16px; }",
        ".tweet-container { display: flex; gap: 12px; }",
        ".tweet-avatar-col { flex-shrink: 0; display: flex; flex-direction: column; "
        "align-items: center; }",
        ".tweet-content-col { flex: 1; min-width: 0; }",
        ".avatar { width: var(--avatar-size); height: var(--avatar-size); "
        "border-radius: 9999px; object-fit: cover; }",
        ".avatar-placeholder { width: var(--avatar-size); height: var(--avatar-size); "
        "border-radius: 9999px; background: var(--text-secondary); }",
        ".thread-connector { width: 2px; flex: 1; background: var(--border-color); "
        "margin-top: 4px; min-height: 12px; }",
        # Tweet header and content
        ".tweet-header { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px; }",
        ".author-name { font-weight: 700; color: var(--text-primary); font-size: 15px; }",
        ".author-handle { color: var(--text-secondary); font-size: 15px; }",
        ".tweet-time { color: var(--text-secondary); font-size: 15px; }",
        ".tweet-time::before { content: '·'; margin: 0 4px; }",
        ".tweet-body { color: var(--text-primary); font-size: 15px; line-height: 1.4; "
        "word-wrap: break-word; margin-top: 4px; }",
        # Links
        "a { color: var(--accent-blue); text-decoration: none; }",
        "a:hover { text-decoration: underline; }",
        # Quoted tweets and retweets
        ".quoted-tweet { margin-top: 12px; padding: 12px; border: 1px solid var(--border-color); "
        "border-radius: 16px; background: var(--bg-secondary); }",
        ".retweet-header { color: var(--text-secondary); font-size: 13px; font-weight: 700; "
        "margin-bottom: 4px; margin-left: calc(var(--avatar-size) + 12px); }",
        # Type badges
        ".type-badges { display: inline-flex; margin-left: 4px; }",
        ".type-badge { font-size: 14px; margin-right: 2px; cursor: default; }",
        # Media
        ".media-placeholder { background: var(--bg-secondary); "
        "border: 1px solid var(--border-color); border-radius: 16px; padding: 40px; "
        "text-align: center; color: var(--text-secondary); cursor: pointer; margin-top: 12px; }",
        ".tweet-actions { margin-top: 12px; }",
        ".view-link { color: var(--accent-blue); font-size: 13px; }",
        # Theme switcher - subtle, compact
        "#theme-switcher { display: flex; gap: 4px; margin-bottom: 12px; }",
        "#theme-switcher button { padding: 4px 8px; border: 1px solid var(--border-color); "
        "background: transparent; color: var(--text-secondary); border-radius: 4px; "
        "cursor: pointer; font-size: 11px; }",
        "#theme-switcher button:hover { color: var(--text-primary); "
        "border-color: var(--text-secondary); }",
        "#theme-switcher button.active { color: var(--text-primary); "
        "border-color: var(--text-primary); }",
        # Filter sidebar
        "#filters h3 { margin: 16px 0 8px; font-size: 14px; font-weight: 700; "
        "color: var(--text-primary); }",
        "#filters h3:first-of-type { margin-top: 0; }",
        "#filters input[type='search'], #filters input[type='text'], "
        "#filters input[type='date'] { width: 100%; padding: 12px 16px; "
        "border: 1px solid var(--border-color); border-radius: 9999px; "
        "background: var(--bg-secondary); color: var(--text-primary); "
        "font-size: 15px; margin-bottom: 8px; }",
        "#filters input:focus { outline: none; border-color: var(--accent-blue); }",
        "#type-list, #author-list { max-height: 200px; overflow-y: auto; "
        "border: 1px solid var(--border-color); border-radius: 12px; margin-bottom: 8px; }",
        "#type-list label, #author-list label { display: flex; align-items: center; "
        "padding: 12px; cursor: pointer; border-bottom: 1px solid var(--border-color); "
        "font-size: 14px; gap: 8px; }",
        "#type-list label:last-child, #author-list label:last-child { border-bottom: none; }",
        "#type-list label:hover, #author-list label:hover { background: var(--bg-secondary); }",
        "#type-list .author-name, #author-list .author-name { flex: 1; overflow: hidden; "
        "text-overflow: ellipsis; white-space: nowrap; min-width: 0; }",
        "#type-list .author-count, #author-list .author-count { "
        "flex-shrink: 0; color: var(--text-secondary); }",
        "#filters button { width: 100%; padding: 12px; margin-top: 8px; "
        "border: 1px solid var(--border-color); border-radius: 9999px; cursor: pointer; "
        "background: var(--bg-secondary); color: var(--text-primary); font-weight: 700; }",
        "#filters button:hover { background: var(--text-secondary); color: var(--bg-primary); }",
        "#results-count { margin-top: 12px; font-size: 13px; "
        "color: var(--text-secondary); text-align: center; }",
        # Find bar styles (Ctrl+F replacement)
        "#find-bar { display: none; position: fixed; top: 0; right: 0; "
        "background: var(--bg-secondary); border: 1px solid var(--border-color); "
        "border-radius: 0 0 0 8px; padding: 8px 12px; gap: 8px; align-items: center; "
        "z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }",
        "#find-input { padding: 6px 10px; border: 1px solid var(--border-color); "
        "border-radius: 4px; background: var(--bg-primary); color: var(--text-primary); "
        "font-size: 14px; width: 200px; }",
        "#find-input:focus { outline: none; border-color: var(--accent-blue); }",
        "#find-count { font-size: 13px; color: var(--text-secondary); min-width: 70px; }",
        "#find-bar button { padding: 4px 8px; border: 1px solid var(--border-color); "
        "background: transparent; color: var(--text-primary); border-radius: 4px; "
        "cursor: pointer; font-size: 14px; }",
        "#find-bar button:hover { background: var(--bg-primary); }",
        "article.find-highlight { background: rgba(29, 155, 240, 0.15); }",
        "mark.find-match { background: rgba(250, 204, 21, 0.4); color: inherit; "
        "border-radius: 2px; padding: 0 2px; }",
        # Virtual scrolling styles
        "#tweets { position: relative; overflow-y: auto; height: 100vh; }",
        "#tweet-viewport { position: relative; }",
        "#tweet-container { position: absolute; top: 0; left: 0; right: 0; }",
        # Responsive
        "@media (max-width: 768px) { body { flex-direction: column; } "
        "#filters { width: 100%; height: auto; position: static; border-right: none; "
        "border-bottom: 1px solid var(--border-color); } "
        "#tweets { border-left: none; border-right: none; } }",
        "</style>",
        "<script>",
        f"const TWEETS = {tweets_json};",
        f"const QUOTED_TWEETS = {quoted_tweets_json};",
        f"const FACETS = {facets_json};",
        f"const THREAD_CONTEXT = {thread_context_json};",
        "const TWEETS_MAP = Object.fromEntries([...TWEETS, ...QUOTED_TWEETS].map(t => [t.id, t]));",
        "function escapeHtml(s) {",
        "  const div = document.createElement('div');",
        "  div.textContent = s;",
        "  return div.innerHTML;",
        "}",
        "function expandUrls(text, urlsJson) {",
        "  if (urlsJson) {",
        "    try {",
        "      const urls = JSON.parse(urlsJson);",
        "      urls.forEach(u => { text = text.replace(u.url, u.expanded_url); });",
        "    } catch (e) { console.warn('Failed to expand URLs:', e.message); }",
        "  }",
        "  text = text.replace(/\\s*https:\\/\\/t\\.co\\/\\w+/g, '');",
        "  return text;",
        "}",
        "function linkifyUrls(text) {",
        "  return text.replace(/(https?:\\/\\/[^\\s<]+)/g, "
        '\'<a href="$1" target="_blank">$1</a>\');',
        "}",
        "function linkifyMentions(text) {",
        "  return text.replace(/@(\\w+)/g, "
        '\'<a href="https://x.com/$1" target="_blank">@$1</a>\');',
        "}",
        "function formatNewlines(text) {",
        "  return text.replace(/\\n/g, '<br>');",
        "}",
        "function applyRichtext(text, tags) {",
        "  if (!tags || !tags.length) return escapeHtml(text);",
        "  // Sort tags by from_index in reverse order to avoid index shifting",
        "  const sorted = [...tags].sort((a, b) => b.from_index - a.from_index);",
        "  // Collect all boundaries",
        "  const boundaries = new Set([0, text.length]);",
        "  sorted.forEach(t => { boundaries.add(t.from_index); boundaries.add(t.to_index); });",
        "  const sortedBoundaries = [...boundaries].sort((a, b) => a - b);",
        "  // Build result by processing each segment",
        "  let result = '';",
        "  for (let i = 0; i < sortedBoundaries.length - 1; i++) {",
        "    const start = sortedBoundaries[i];",
        "    const end = sortedBoundaries[i + 1];",
        "    let segment = escapeHtml(text.slice(start, end));",
        "    // Find all tags that cover this segment",
        "    for (const tag of sorted) {",
        "      if (tag.from_index <= start && tag.to_index >= end) {",
        "        if (tag.richtext_types.includes('Italic')) segment = `<em>${segment}</em>`;",
        "        if (tag.richtext_types.includes('Bold')) segment = `<strong>${segment}</strong>`;",
        "      }",
        "    }",
        "    result += segment;",
        "  }",
        "  return result;",
        "}",
        "function isValidMediaUrl(url) {",
        "  return url && (url.startsWith('https://pbs.twimg.com/') "
        "|| url.startsWith('https://video.twimg.com/'));",
        "}",
        "function isValidAvatarUrl(url) {",
        "  return url && url.startsWith('https://pbs.twimg.com/');",
        "}",
        "function setTheme(theme) {",
        "  document.documentElement.dataset.theme = theme;",
        "  localStorage.setItem('tweethoarder-theme', theme);",
        "  document.querySelectorAll('#theme-switcher button').forEach(btn => {",
        "    btn.classList.toggle('active', btn.dataset.theme === theme);",
        "  });",
        "}",
        "let imagesEnabled = false;",
        "function renderMedia(mediaJson) {",
        "  if (!mediaJson) return '';",
        "  try {",
        "    const media = JSON.parse(mediaJson);",
        "    return media.map(m => {",
        "      const url = m.media_url_https || m.media_url;",
        "      if (!isValidMediaUrl(url)) return '';",
        "      if (imagesEnabled) {",
        "        return `<img src='${url}' "
        "style='max-width:100%;border-radius:8px;margin-top:8px'>`;",
        "      }",
        "      return `<div class='media-placeholder' data-src='${url}' "
        'onclick=\'this.outerHTML=\\`<img src="${url}" '
        'style="max-width:100%;border-radius:8px;margin-top:8px">\\`\'>'
        "Click to load image</div>`;",
        "    }).join('');",
        "  } catch (e) { console.error('Failed to render media:', e.message); return ''; }",
        "}",
        "function getThreadText(tweet) {",
        "  const convId = tweet.conversation_id;",
        "  if (!convId || !THREAD_CONTEXT[convId]) return '';",
        "  return THREAD_CONTEXT[convId].map(t => t.text).join(' ');",
        "}",
        "function filterTweets(query) {",
        "  if (!query) return TWEETS;",
        "  const q = query.toLowerCase();",
        "  return TWEETS.filter(t => {",
        "    const mainText = t.text.toLowerCase();",
        "    const threadText = getThreadText(t).toLowerCase();",
        "    return mainText.includes(q) || threadText.includes(q);",
        "  });",
        "}",
        "let selectedAuthors = new Set();",
        "let selectedTypes = new Set();",
        "const TYPE_LABELS = {like: 'Likes', bookmark: 'Bookmarks', tweet: 'My Tweets', "
        "repost: 'Reposts', reply: 'Replies'};",
        "const TYPE_ICONS = {like: '\\u2764\\uFE0F', bookmark: '\\uD83D\\uDD16', "
        "tweet: '\\uD83D\\uDC64', repost: '\\uD83D\\uDD01', reply: '\\u21A9\\uFE0F'};",
        "function renderTypeBadges(types) {",
        "  if (!types || types.length === 0) return '';",
        "  return '<span class=\"type-badges\">' + types.map(t => "
        '`<span class="type-badge" title="${TYPE_LABELS[t] || t}">${TYPE_ICONS[t] || \'\'}'
        "</span>`).join('') + '</span>';",
        "}",
        "function renderTypeList() {",
        "  const list = document.getElementById('type-list');",
        "  if (!FACETS.types || Object.keys(FACETS.types).length === 0) {",
        "    list.style.display = 'none';",
        "    const header = list.previousElementSibling;",
        "    if (header && header.tagName === 'H3') header.style.display = 'none';",
        "    return;",
        "  }",
        "  list.replaceChildren();",
        "  Object.entries(FACETS.types).forEach(([type, count]) => {",
        "    const label = document.createElement('label');",
        "    label.className = selectedTypes.has(type) ? 'selected' : '';",
        "    const checkbox = document.createElement('input');",
        "    checkbox.type = 'checkbox';",
        "    checkbox.value = type;",
        "    checkbox.checked = selectedTypes.size === 0 || selectedTypes.has(type);",
        "    const nameSpan = document.createElement('span');",
        "    nameSpan.className = 'author-name';",
        "    nameSpan.textContent = TYPE_LABELS[type] || type;",
        "    const countSpan = document.createElement('span');",
        "    countSpan.className = 'author-count';",
        "    countSpan.textContent = count;",
        "    label.appendChild(checkbox);",
        "    label.appendChild(nameSpan);",
        "    label.appendChild(countSpan);",
        "    list.appendChild(label);",
        "  });",
        "}",
        "function renderAuthorList(filterText) {",
        "  const list = document.getElementById('author-list');",
        "  list.replaceChildren();",
        "  const ft = (filterText || '').toLowerCase();",
        "  const filtered = ft.length >= 3",
        "    ? FACETS.authors.filter(a =>",
        "        a.username.toLowerCase().includes(ft) ||",
        "        a.display_name.toLowerCase().includes(ft))",
        "    : FACETS.authors;",
        "  filtered.forEach(a => {",
        "    const label = document.createElement('label');",
        "    label.className = selectedAuthors.has(a.username) ? 'selected' : '';",
        "    const checkbox = document.createElement('input');",
        "    checkbox.type = 'checkbox';",
        "    checkbox.value = a.username;",
        "    checkbox.checked = selectedAuthors.has(a.username);",
        "    const nameSpan = document.createElement('span');",
        "    nameSpan.className = 'author-name';",
        "    nameSpan.textContent = a.display_name + ' (@' + a.username + ')';",
        "    const countSpan = document.createElement('span');",
        "    countSpan.className = 'author-count';",
        "    countSpan.textContent = a.count;",
        "    label.appendChild(checkbox);",
        "    label.appendChild(nameSpan);",
        "    label.appendChild(countSpan);",
        "    list.appendChild(label);",
        "  });",
        "}",
        "function applyAllFilters() {",
        "  const query = document.getElementById('search').value.toLowerCase();",
        "  const fromDate = document.getElementById('date-from').value;",
        "  const toDate = document.getElementById('date-to').value;",
        "  let filtered = TWEETS;",
        "  if (query) {",
        "    filtered = filtered.filter(t => {",
        "      const mainText = t.text.toLowerCase();",
        "      const threadText = getThreadText(t).toLowerCase();",
        "      return mainText.includes(query) || threadText.includes(query);",
        "    });",
        "  }",
        "  if (selectedTypes.size > 0) {",
        "    filtered = filtered.filter(t => {",
        "      const types = t.collection_types || [];",
        "      return types.some(ct => selectedTypes.has(ct));",
        "    });",
        "  }",
        "  if (selectedAuthors.size > 0) {",
        "    filtered = filtered.filter(t => selectedAuthors.has(t.author_username));",
        "  }",
        "  if (fromDate) {",
        "    filtered = filtered.filter(t => t.created_at >= fromDate);",
        "  }",
        "  if (toDate) {",
        "    filtered = filtered.filter(t => t.created_at <= toDate + 'T23:59:59');",
        "  }",
        "  document.getElementById('results-count').textContent =",
        "    filtered.length + ' of ' + TWEETS.length + ' tweets';",
        "  renderTweets(filtered);",
        "}",
        "function getThreadTweets(tweet) {",
        "  const convId = tweet.conversation_id;",
        "  if (!convId || !THREAD_CONTEXT[convId]) return [];",
        "  const allTweets = THREAD_CONTEXT[convId];",
        "  const authorId = tweet.author_id;",
        "  return allTweets.filter(t => {",
        "    if (t.author_id !== authorId) return false;",
        "    if (t.id === convId) return true;",
        "    return !t.text.startsWith('@');",
        "  }).sort((a,b) => a.created_at.localeCompare(b.created_at));",
        "}",
        "// Virtual scrolling configuration",
        "const ESTIMATED_ROW_HEIGHT = 150;",
        "const BUFFER_SIZE = 10;",
        "let currentFilteredTweets = [];",
        "let scrollContainer = null;",
        "let viewport = null;",
        "let tweetContainer = null;",
        "let rafId = null;",
        "// Safe HTML rendering using template element",
        "// Falls back gracefully if DOMPurify unavailable (e.g., local file:// protocol)",
        "function safeRenderHTML(container, htmlContent) {",
        "  const template = document.createElement('template');",
        "  if (typeof DOMPurify !== 'undefined') {",
        "    template.innerHTML = DOMPurify.sanitize(htmlContent, {",
        "      ALLOWED_TAGS: ['article','div','p','span','a','img',"
        "'strong','em','small','br','mark'],",
        "      ALLOWED_ATTR: ['class','href','src','alt','target','title','style','loading',"
        "'data-src','onclick']",
        "    });",
        "  } else {",
        "    template.innerHTML = htmlContent;",
        "  }",
        "  container.replaceChildren(template.content);",
        "}",
        "function renderSingleTweet(t, tweetIdx, currentMatchIdx) {",
        "  const isCurrentMatch = tweetIdx === currentMatchIdx;",
        "  const highlightClass = isCurrentMatch ? ' find-highlight' : '';",
        "  const threadTweets = getThreadTweets(t);",
        "  const isThread = threadTweets.length > 1;",
        "  const dn = t.author_display_name || t.author_username;",
        "  const dt = t.created_at ? t.created_at.slice(0, 16).replace('T', ' ') : '';",
        "  const url = `https://x.com/${t.author_username}/status/${t.id}`;",
        "  const av = isValidAvatarUrl(t.author_avatar_url)",
        '    ? `<img src="${escapeHtml(t.author_avatar_url)}" alt="" '
        'class="avatar" loading="lazy">`',
        "    : '<div class=\"avatar-placeholder\"></div>';",
        "  if (isThread) {",
        "    const threadHtml = threadTweets.map(th => {",
        "      const richTxt = applyRichtext(th.text, th.richtext_tags);",
        "      const txt = expandUrls(richTxt, th.urls_json);",
        "      const star = th.id === t.id ? '\\u2B50 ' : '';",
        "      return `<p>${star}${formatNewlines(linkifyMentions(linkifyUrls(txt)))}</p>`;",
        "    }).join('');",
        "    const badges = renderTypeBadges(t.collection_types);",
        "    return `<article class='thread${highlightClass}'>",
        "      <div class='tweet-container'>",
        "        <div class='tweet-avatar-col'>",
        "          ${av}",
        "        </div>",
        "        <div class='tweet-content-col'>",
        "          <p>🧵 <span class='author-name'>Thread by ${escapeHtml(dn)}</span> "
        "<span class='author-handle'>@${escapeHtml(t.author_username)}</span> ${badges}</p>",
        "          ${threadHtml}",
        '          <p><small>${dt} | <a href="${url}" target="_blank">View</a></small></p>',
        "        </div>",
        "      </div>",
        "    </article>`;",
        "  }",
        "  const richTxt = applyRichtext(t.text, t.richtext_tags);",
        "  const txt = expandUrls(richTxt, t.urls_json);",
        "  const rtHeader = (t.is_retweet && t.retweeter_username) ? "
        "`<div class='retweet-header'>🔁 Retweeted by @${escapeHtml(t.retweeter_username)}"
        "</div>` : '';",
        "  const qt = t.quoted_tweet_id ? TWEETS_MAP[t.quoted_tweet_id] : null;",
        "  const qtRichTxt = qt ? applyRichtext(qt.text, qt.richtext_tags) : '';",
        "  const qtText = qt ? expandUrls(qtRichTxt, qt.urls_json) : '';",
        "  const qtHtml = (qt && qt.author_username && qt.text) ? `<div class='quoted-tweet'>"
        "<p><strong>${escapeHtml(qt.author_display_name || qt.author_username)}</strong> "
        "@${escapeHtml(qt.author_username)}</p>"
        "<p>${formatNewlines(linkifyMentions(linkifyUrls(qtText)))}</p></div>` :"
        "(t.quoted_tweet_id ? '<div class=\"quoted-tweet\">Quoted tweet unavailable</div>' : '');",
        "  const badges = renderTypeBadges(t.collection_types);",
        "  return `<article class='${highlightClass.trim()}'>",
        "    ${rtHeader}",
        "    <div class='tweet-container'>",
        "      <div class='tweet-avatar-col'>",
        "        ${av}",
        "      </div>",
        "      <div class='tweet-content-col'>",
        "        <p><span class='author-name'>${escapeHtml(dn)}</span> "
        "<span class='author-handle'>@${escapeHtml(t.author_username)}</span> ${badges}</p>",
        "        <p>${highlightFindText(formatNewlines(linkifyMentions(linkifyUrls(txt))))}</p>",
        "        ${renderMedia(t.media_json)}",
        "        ${qtHtml}",
        '        <p><small>${dt} | <a href="${url}" target="_blank">View</a></small></p>',
        "      </div>",
        "    </div>",
        "  </article>`;",
        "}",
        "function updateVirtualScroll() {",
        "  if (!scrollContainer || !viewport || !tweetContainer) return;",
        "  const tweets = currentFilteredTweets;",
        "  const totalHeight = tweets.length * ESTIMATED_ROW_HEIGHT;",
        "  viewport.style.height = totalHeight + 'px';",
        "  const scrollTop = scrollContainer.scrollTop;",
        "  const viewportHeight = scrollContainer.clientHeight;",
        "  const startIdx = Math.max(0, "
        "Math.floor(scrollTop / ESTIMATED_ROW_HEIGHT) - BUFFER_SIZE);",
        "  const visibleCount = Math.ceil(viewportHeight / ESTIMATED_ROW_HEIGHT);",
        "  const endIdx = Math.min(tweets.length, startIdx + visibleCount + BUFFER_SIZE * 2);",
        "  const visibleTweets = tweets.slice(startIdx, endIdx);",
        "  tweetContainer.style.transform = `translateY(${startIdx * ESTIMATED_ROW_HEIGHT}px)`;",
        "  const currentMatchTweetIdx = findCurrentIdx >= 0 ? findMatches[findCurrentIdx] : -1;",
        "  const html = visibleTweets.map((t, i) => "
        "renderSingleTweet(t, startIdx + i, currentMatchTweetIdx)).join('');",
        "  safeRenderHTML(tweetContainer, html);",
        "}",
        "function scheduleVirtualScrollUpdate() {",
        "  if (rafId || isJumpingToMatch) return;",
        "  rafId = requestAnimationFrame(() => {",
        "    rafId = null;",
        "    if (!isJumpingToMatch) updateVirtualScroll();",
        "  });",
        "}",
        "function renderTweets(tweets) {",
        "  currentFilteredTweets = tweets;",
        "  if (scrollContainer) scrollContainer.scrollTop = 0;",
        "  updateVirtualScroll();",
        "}",
        "// Debounce utility for filter inputs",
        "function debounce(fn, delay) {",
        "  let timeoutId;",
        "  return function(...args) {",
        "    clearTimeout(timeoutId);",
        "    timeoutId = setTimeout(() => fn.apply(this, args), delay);",
        "  };",
        "}",
        "// Find bar state (Ctrl+F replacement for virtual scroll)",
        "let findMatches = [];",
        "let findCurrentIdx = -1;",
        "let findQuery = '';",
        "let isJumpingToMatch = false;",
        "function openFindBar() {",
        "  const bar = document.getElementById('find-bar');",
        "  bar.style.display = 'flex';",
        "  const input = document.getElementById('find-input');",
        "  input.focus();",
        "  input.select();",
        "}",
        "function closeFindBar() {",
        "  document.getElementById('find-bar').style.display = 'none';",
        "  findMatches = [];",
        "  findCurrentIdx = -1;",
        "  findQuery = '';",
        "  document.getElementById('find-count').textContent = '';",
        "  updateVirtualScroll();",
        "}",
        "function updateFindMatches(query) {",
        "  findQuery = query.toLowerCase();",
        "  if (!findQuery) {",
        "    findMatches = [];",
        "    findCurrentIdx = -1;",
        "    document.getElementById('find-count').textContent = '';",
        "    return;",
        "  }",
        "  findMatches = [];",
        "  currentFilteredTweets.forEach((t, idx) => {",
        "    if (t.text.toLowerCase().includes(findQuery)) findMatches.push(idx);",
        "  });",
        "  findCurrentIdx = findMatches.length > 0 ? 0 : -1;",
        "  updateFindCount();",
        "  if (findCurrentIdx >= 0) jumpToFindMatch();",
        "}",
        "function updateFindCount() {",
        "  const countEl = document.getElementById('find-count');",
        "  if (findMatches.length === 0) {",
        "    countEl.textContent = findQuery ? 'No matches' : '';",
        "  } else {",
        "    countEl.textContent = `${findCurrentIdx + 1} of ${findMatches.length}`;",
        "  }",
        "}",
        "function jumpToFindMatch() {",
        "  if (findCurrentIdx < 0 || findMatches.length === 0) return;",
        "  isJumpingToMatch = true;",
        "  const tweetIdx = findMatches[findCurrentIdx];",
        "  const scrollTop = tweetIdx * ESTIMATED_ROW_HEIGHT;",
        "  scrollContainer.scrollTop = scrollTop;",
        "  updateFindCount();",
        "  updateVirtualScroll();",
        "  // After render, scroll the highlighted element into view",
        "  setTimeout(() => {",
        "    const highlighted = document.querySelector('.find-highlight');",
        "    if (highlighted) {",
        "      highlighted.scrollIntoView({ block: 'center', behavior: 'instant' });",
        "    }",
        "    setTimeout(() => { isJumpingToMatch = false; }, 50);",
        "  }, 20);",
        "}",
        "// Highlight matching text in content",
        "function highlightFindText(text) {",
        "  if (!findQuery) return text;",
        "  const esc = findQuery.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&');",
        "  const regex = new RegExp(`(${esc})`, 'gi');",
        "  return text.replace(regex, '<mark class=\"find-match\">$1</mark>');",
        "}",
        "function findNext() {",
        "  if (findMatches.length === 0) return;",
        "  findCurrentIdx = (findCurrentIdx + 1) % findMatches.length;",
        "  jumpToFindMatch();",
        "}",
        "function findPrev() {",
        "  if (findMatches.length === 0) return;",
        "  findCurrentIdx = (findCurrentIdx - 1 + findMatches.length) % findMatches.length;",
        "  jumpToFindMatch();",
        "}",
        "document.addEventListener('keydown', (e) => {",
        "  if ((e.ctrlKey || e.metaKey) && e.key === 'f') {",
        "    e.preventDefault();",
        "    openFindBar();",
        "  }",
        "  if (e.key === 'Escape') closeFindBar();",
        "});",
        "// Global wheel scrolling - scroll tweets container from anywhere on page",
        "document.addEventListener('wheel', (e) => {",
        "  if (!scrollContainer) return;",
        "  // Don't interfere with scrollable sidebar elements",
        "  if (e.target.closest('#author-list, #type-list')) return;",
        "  scrollContainer.scrollTop += e.deltaY;",
        "}, { passive: true });",
        "document.addEventListener('DOMContentLoaded', () => {",
        "  // Initialize virtual scroll containers",
        "  scrollContainer = document.getElementById('tweets');",
        "  viewport = document.getElementById('tweet-viewport');",
        "  tweetContainer = document.getElementById('tweet-container');",
        "  // Add scroll listener for virtual scrolling",
        "  scrollContainer.addEventListener('scroll', scheduleVirtualScrollUpdate, "
        "{ passive: true });",
        "  const search = document.getElementById('search');",
        "  // Debounce search input for better performance",
        "  const debouncedFilter = debounce(applyAllFilters, 150);",
        "  search.addEventListener('input', debouncedFilter);",
        "  const typeList = document.getElementById('type-list');",
        "  typeList.addEventListener('change', (e) => {",
        "    if (e.target.type === 'checkbox') {",
        "      const type = e.target.value;",
        "      if (e.target.checked) {",
        "        selectedTypes.add(type);",
        "        if (selectedTypes.size === Object.keys(FACETS.types).length) {",
        "          selectedTypes.clear();",
        "        }",
        "      } else {",
        "        if (selectedTypes.size === 0) {",
        "          Object.keys(FACETS.types).forEach(t => {",
        "            if (t !== type) selectedTypes.add(t);",
        "          });",
        "        } else {",
        "          selectedTypes.delete(type);",
        "        }",
        "      }",
        "      renderTypeList();",
        "      applyAllFilters();",
        "    }",
        "  });",
        "  const authorSearch = document.getElementById('author-search');",
        "  const debouncedAuthorSearch = debounce("
        "() => renderAuthorList(authorSearch.value), 150);",
        "  authorSearch.addEventListener('input', debouncedAuthorSearch);",
        "  const authorList = document.getElementById('author-list');",
        "  authorList.addEventListener('change', (e) => {",
        "    if (e.target.type === 'checkbox') {",
        "      if (e.target.checked) {",
        "        selectedAuthors.add(e.target.value);",
        "      } else {",
        "        selectedAuthors.delete(e.target.value);",
        "      }",
        "      renderAuthorList(authorSearch.value);",
        "      applyAllFilters();",
        "    }",
        "  });",
        "  document.getElementById('date-from').addEventListener('change', applyAllFilters);",
        "  document.getElementById('date-to').addEventListener('change', applyAllFilters);",
        "  document.getElementById('clear-filters').addEventListener('click', () => {",
        "    search.value = '';",
        "    authorSearch.value = '';",
        "    selectedAuthors.clear();",
        "    selectedTypes.clear();",
        "    document.getElementById('date-from').value = '';",
        "    document.getElementById('date-to').value = '';",
        "    renderTypeList();",
        "    renderAuthorList('');",
        "    applyAllFilters();",
        "  });",
        "  const loadBtn = document.getElementById('load-images');",
        "  loadBtn.addEventListener('click', () => {",
        "    imagesEnabled = true;",
        "    loadBtn.disabled = true;",
        "    loadBtn.textContent = 'Images Enabled';",
        "    applyAllFilters();",
        "  });",
        "  const themeSwitcher = document.getElementById('theme-switcher');",
        "  themeSwitcher.addEventListener('click', (e) => {",
        "    if (e.target.dataset.theme) setTheme(e.target.dataset.theme);",
        "  });",
        "  const savedTheme = localStorage.getItem('tweethoarder-theme') || 'dark';",
        "  setTheme(savedTheme);",
        "  renderTypeList();",
        "  renderAuthorList('');",
        "  applyAllFilters();",
        "  // Find bar event listeners",
        "  const findInput = document.getElementById('find-input');",
        "  const debouncedFind = debounce((e) => updateFindMatches(e.target.value), 100);",
        "  findInput.addEventListener('input', debouncedFind);",
        "  findInput.addEventListener('keydown', (e) => {",
        "    if (e.key === 'Enter') {",
        "      e.preventDefault();",
        "      if (e.shiftKey) findPrev(); else findNext();",
        "    }",
        "  });",
        "});",
        "</script>",
        "</head>",
        "<body>",
        '<aside id="filters">',
        "<h3>Theme</h3>",
        '<div id="theme-switcher">',
        '<button data-theme="dark">Lights Out</button>',
        '<button data-theme="dim">Dim</button>',
        '<button data-theme="light">Light</button>',
        "</div>",
        "<h3>Search</h3>",
        '<input type="search" id="search" placeholder="Filter by content...">',
        "<h3>Type</h3>",
        '<div id="type-list"></div>',
        "<h3>Author</h3>",
        '<input type="text" id="author-search" placeholder="Filter authors...">',
        '<div id="author-list"></div>',
        "<h3>Date Range</h3>",
        '<input type="date" id="date-from">',
        '<input type="date" id="date-to">',
        '<button id="clear-filters">Clear All Filters</button>',
        '<button id="load-images">Load Images</button>',
        '<div id="results-count"></div>',
        "</aside>",
        # Find bar (Ctrl+F replacement)
        '<div id="find-bar">',
        '<input type="text" id="find-input" placeholder="Find in tweets...">',
        '<span id="find-count"></span>',
        '<button onclick="findPrev()" title="Previous (Shift+Enter)">&#9650;</button>',
        '<button onclick="findNext()" title="Next (Enter)">&#9660;</button>',
        '<button onclick="closeFindBar()" title="Close (Esc)">&times;</button>',
        "</div>",
        '<main id="tweets">',
        '<div id="tweet-viewport">',
        '<div id="tweet-container"></div>',
        "</div>",
        "</main>",
    ]
    lines.append("</body>")
    lines.append("</html>")
    content = "\n".join(lines)

    output_path = output or _get_default_export_path(data_dir, collection, "html")
    output_path.write_text(content)
