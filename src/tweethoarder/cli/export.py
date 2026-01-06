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
    """Export tweets to HTML format."""
    from tweethoarder.config import get_data_dir
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

    facets = {
        "authors": sorted(author_data.values(), key=lambda x: -int(x["count"])),
        "months": [{"month": m, "count": c} for m, c in sorted(month_counts.items())],
        "media": media_counts,
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
        "#filters h3 { margin: 1rem 0 0.5rem; font-size: 14px; color: #657786; }",
        "#filters h3:first-child { margin-top: 0; }",
        "#filters input[type='search'], #filters input[type='text'], "
        "#filters input[type='date'] { width: 100%; padding: 8px; margin-bottom: 8px; "
        "border: 1px solid #e1e8ed; border-radius: 8px; box-sizing: border-box; }",
        "#author-list { max-height: 200px; overflow-y: auto; border: 1px solid #e1e8ed; "
        "border-radius: 8px; margin-bottom: 8px; }",
        "#author-list label { display: flex; align-items: center; padding: 8px; "
        "cursor: pointer; border-bottom: 1px solid #e1e8ed; font-size: 13px; gap: 4px; }",
        "#author-list label:last-child { border-bottom: none; }",
        "#author-list label:hover { background: #f7f9fa; }",
        "#author-list label.selected { background: #e8f5fd; }",
        "#author-list .author-name { flex: 1; overflow: hidden; text-overflow: ellipsis; "
        "white-space: nowrap; min-width: 0; }",
        "#author-list .author-count { flex-shrink: 0; color: #657786; }",
        "#filters button { width: 100%; padding: 8px; margin-top: 8px; "
        "border: 1px solid #e1e8ed; border-radius: 8px; cursor: pointer; "
        "background: #fff; }",
        "#filters button:hover { background: #f7f9fa; }",
        "#results-count { margin-top: 8px; font-size: 13px; color: #657786; }",
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
        "function renderTweets(tweets) {",
        "  const container = document.getElementById('tweets');",
        "  container.innerHTML = tweets.map(t => {",
        "    const threadTweets = getThreadTweets(t);",
        "    const isThread = threadTweets.length > 1;",
        "    const dn = t.author_display_name || t.author_username;",
        "    const dt = t.created_at ? t.created_at.slice(0, 16).replace('T', ' ') : '';",
        "    const url = `https://x.com/${t.author_username}/status/${t.id}`;",
        "    const av = isValidAvatarUrl(t.author_avatar_url)",
        '      ? `<img src="${t.author_avatar_url}" alt="" class="avatar">`',
        "      : '<div class=\"avatar-placeholder\"></div>';",
        "    if (isThread) {",
        "      const threadHtml = threadTweets.map(th => {",
        "        const richTxt = applyRichtext(th.text, th.richtext_tags);",
        "        const txt = expandUrls(richTxt, th.urls_json);",
        "        const star = th.id === t.id ? '\\u2B50 ' : '';",
        "        return `<p>${star}${formatNewlines(linkifyMentions(linkifyUrls(txt)))}</p>`;",
        "      }).join('');",
        "      return `<article class='thread'>",
        "        ${av}",
        "        <p><strong>🧵 Thread by ${escapeHtml(dn)}</strong> "
        "@${escapeHtml(t.author_username)}</p>",
        "        ${threadHtml}",
        '        <p><small>${dt} | <a href="${url}" target="_blank">View</a></small></p>',
        "      </article>`;",
        "    }",
        "    const richTxt = applyRichtext(t.text, t.richtext_tags);",
        "    const txt = expandUrls(richTxt, t.urls_json);",
        "    const rtHeader = (t.is_retweet && t.retweeter_username) ? "
        "`<div class='retweet-header'>🔁 Retweeted by @${escapeHtml(t.retweeter_username)}"
        "</div>` : '';",
        "    const qt = t.quoted_tweet_id ? TWEETS_MAP[t.quoted_tweet_id] : null;",
        "    const qtRichTxt = qt ? applyRichtext(qt.text, qt.richtext_tags) : '';",
        "    const qtText = qt ? expandUrls(qtRichTxt, qt.urls_json) : '';",
        "    const qtHtml = (qt && qt.author_username && qt.text) ? `<div class='quoted-tweet'>"
        "<p><strong>${escapeHtml(qt.author_display_name || qt.author_username)}</strong> "
        "@${escapeHtml(qt.author_username)}</p>"
        "<p>${formatNewlines(linkifyMentions(linkifyUrls(qtText)))}</p></div>` :"
        "(t.quoted_tweet_id ? '<div class=\"quoted-tweet\">Quoted tweet unavailable</div>' : '');",
        "    return `<article>",
        "      ${rtHeader}",
        "      ${av}",
        "      <p><strong>${escapeHtml(dn)}</strong> @${escapeHtml(t.author_username)}</p>",
        "      <p>${formatNewlines(linkifyMentions(linkifyUrls(txt)))}</p>",
        "      ${renderMedia(t.media_json)}",
        "      ${qtHtml}",
        '      <p><small>${dt} | <a href="${url}" target="_blank">View</a></small></p>',
        "    </article>`;",
        "  }).join('');",
        "}",
        "document.addEventListener('DOMContentLoaded', () => {",
        "  const search = document.getElementById('search');",
        "  search.addEventListener('input', applyAllFilters);",
        "  const authorSearch = document.getElementById('author-search');",
        "  authorSearch.addEventListener('input', () => renderAuthorList(authorSearch.value));",
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
        "    document.getElementById('date-from').value = '';",
        "    document.getElementById('date-to').value = '';",
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
        "  renderAuthorList('');",
        "  applyAllFilters();",
        "});",
        "</script>",
        "</head>",
        "<body>",
        '<aside id="filters">',
        "<h3>Search</h3>",
        '<input type="search" id="search" placeholder="Search tweet content...">',
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
        '<main id="tweets">',
        "</main>",
    ]
    lines.append("</body>")
    lines.append("</html>")
    content = "\n".join(lines)

    output_path = output or _get_default_export_path(data_dir, collection, "html")
    output_path.write_text(content)
