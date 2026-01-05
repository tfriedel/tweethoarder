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
        get_tweets_by_conversation_id,
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

    # Build thread context for tweets with conversation_id
    thread_context: dict[str, list[dict[str, Any]]] = {}
    for tweet in tweets:
        conv_id = tweet.get("conversation_id")
        if conv_id and conv_id not in thread_context:
            try:
                thread_context[conv_id] = get_tweets_by_conversation_id(db_path, conv_id)
            except Exception:
                thread_context[conv_id] = []

    content = export_tweets_to_markdown(
        tweets, collection=collection, thread_context=thread_context
    )

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
        get_tweets_by_conversation_id,
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

    # Build thread context for tweets with conversation_id
    thread_context: dict[str, list[dict[str, Any]]] = {}
    for tweet in tweets:
        conv_id = tweet.get("conversation_id")
        if conv_id and conv_id not in thread_context:
            try:
                thread_context[conv_id] = get_tweets_by_conversation_id(db_path, conv_id)
            except Exception:
                thread_context[conv_id] = []

    import json
    from collections import Counter

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
        "quoted_tweet_id",
    }
    stripped_tweets = [{k: v for k, v in t.items() if k in used_fields} for t in tweets]
    tweets_json = json.dumps(stripped_tweets)

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
        "<style>",
        "body { font-family: sans-serif; display: flex; margin: 0; }",
        "#filters { width: 250px; padding: 1rem; border-right: 1px solid #ddd; }",
        "#tweets { flex: 1; padding: 1rem; overflow-y: auto; }",
        "article { margin-bottom: 1rem; padding: 1rem; border: 1px solid #e1e8ed; "
        "border-radius: 12px; }",
        ".avatar { width: 48px; height: 48px; border-radius: 50%; }",
        ".avatar-placeholder { width: 48px; height: 48px; border-radius: 50%; background: #ccc; }",
        "a { color: #1DA1F2; }",
        ".quoted-tweet { margin-top: 8px; padding: 12px; border: 1px solid #e1e8ed; "
        "border-radius: 12px; background: #f7f9fa; }",
        ".retweet-header { color: #657786; font-size: 13px; margin-bottom: 4px; }",
        ".media-placeholder { background: #e1e8ed; border-radius: 8px; padding: 40px; "
        "text-align: center; color: #657786; cursor: pointer; margin-top: 8px; }",
        "@media (max-width: 768px) { body { flex-direction: column; } "
        "#filters { width: 100%; border-right: none; border-bottom: 1px solid #ddd; } }",
        "</style>",
        "<script>",
        f"const TWEETS = {tweets_json};",
        f"const FACETS = {facets_json};",
        f"const THREAD_CONTEXT = {thread_context_json};",
        "const TWEETS_MAP = Object.fromEntries(TWEETS.map(t => [t.id, t]));",
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
        "function isValidMediaUrl(url) {",
        "  return url && (url.startsWith('https://pbs.twimg.com/') "
        "|| url.startsWith('https://video.twimg.com/'));",
        "}",
        "function isValidAvatarUrl(url) {",
        "  return url && url.startsWith('https://pbs.twimg.com/');",
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
        "function renderTweets(tweets) {",
        "  const container = document.getElementById('tweets');",
        "  container.innerHTML = tweets.map(t => {",
        "    const threadTweets = getThreadTweets(t);",
        "    const isThread = threadTweets.length > 1;",
        "    const dn = t.author_display_name || t.author_username;",
        "    const dt = t.created_at ? new Date(t.created_at).toLocaleString() : '';",
        "    const url = `https://x.com/${t.author_username}/status/${t.id}`;",
        "    const av = isValidAvatarUrl(t.author_avatar_url)",
        '      ? `<img src="${t.author_avatar_url}" alt="" class="avatar">`',
        "      : '<div class=\"avatar-placeholder\"></div>';",
        "    if (isThread) {",
        "      const threadHtml = threadTweets.map(th => {",
        "        const txt = expandUrls(th.text, th.urls_json);",
        "        const star = th.id === t.id ? '\\u2B50 ' : '';",
        "        return `<p>${star}${linkifyMentions(linkifyUrls(escapeHtml(txt)))}</p>`;",
        "      }).join('');",
        "      return `<article class='thread'>",
        "        ${av}",
        "        <p><strong>\\U0001F9F5 Thread by ${escapeHtml(dn)}</strong> "
        "@${escapeHtml(t.author_username)}</p>",
        "        ${threadHtml}",
        '        <p><small>${dt} | <a href="${url}" target="_blank">View</a></small></p>',
        "      </article>`;",
        "    }",
        "    const txt = expandUrls(t.text, t.urls_json);",
        "    const rtHeader = t.is_retweet ? `<div class='retweet-header'>"
        "\\U0001F501 Retweeted by @${escapeHtml(t.author_username)}</div>` : '';",
        "    const qt = t.quoted_tweet_id ? TWEETS_MAP[t.quoted_tweet_id] : null;",
        "    const qtText = qt ? expandUrls(qt.text, qt.urls_json) : '';",
        "    const qtHtml = (qt && qt.author_username && qt.text) ? `<div class='quoted-tweet'>"
        "<p><strong>${escapeHtml(qt.author_display_name || qt.author_username)}</strong> "
        "@${escapeHtml(qt.author_username)}</p>"
        "<p>${linkifyMentions(linkifyUrls(escapeHtml(qtText)))}</p></div>` :"
        "(t.quoted_tweet_id ? '<div class=\"quoted-tweet\">Quoted tweet unavailable</div>' : '');",
        "    return `<article>",
        "      ${rtHeader}",
        "      ${av}",
        "      <p><strong>${escapeHtml(dn)}</strong> @${escapeHtml(t.author_username)}</p>",
        "      <p>${linkifyMentions(linkifyUrls(escapeHtml(txt)))}</p>",
        "      ${renderMedia(t.media_json)}",
        "      ${qtHtml}",
        '      <p><small>${dt} | <a href="${url}" target="_blank">View</a></small></p>',
        "    </article>`;",
        "  }).join('');",
        "}",
        "document.addEventListener('DOMContentLoaded', () => {",
        "  const search = document.getElementById('search');",
        "  search.addEventListener('input', () => renderTweets(filterTweets(search.value)));",
        "  const loadBtn = document.getElementById('load-images');",
        "  loadBtn.addEventListener('click', () => {",
        "    imagesEnabled = true;",
        "    loadBtn.disabled = true;",
        "    loadBtn.textContent = 'Images Enabled';",
        "    renderTweets(filterTweets(search.value));",
        "  });",
        "  renderTweets(TWEETS);",
        "});",
        "</script>",
        "</head>",
        "<body>",
        '<aside id="filters">',
        '<input type="search" id="search" placeholder="Search tweets...">',
        '<button id="load-images">Load Images</button>',
        "</aside>",
        '<main id="tweets">',
        "</main>",
    ]
    lines.append("</body>")
    lines.append("</html>")
    content = "\n".join(lines)

    output_path = output or _get_default_export_path(data_dir, collection, "html")
    output_path.write_text(content)
