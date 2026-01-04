# TweetHoarder - Twitter/X Data Archival Tool Specification

## Overview

TweetHoarder is a Python CLI tool for archiving a user's Twitter/X data (likes, bookmarks, tweets, reposts) locally. It uses cookie-based authentication to access Twitter's internal GraphQL API (no paid API key required), with architecture ported from the [bird](https://github.com/steipete/bird) TypeScript project.

## Core Requirements Summary

| Requirement | Decision |
|------------|----------|
| Language | Python |
| API Approach | Port bird's GraphQL + query ID refresh mechanism to Python |
| Authentication | Cookie-based (auto-extract from Firefox/Chrome + manual fallback) |
| Storage | SQLite with incremental sync |
| Browser Support | Linux only (Firefox + Chrome/Chromium with keyring decryption) |
| Multi-account | Single account only |
| Media | URLs only (store metadata, no downloading - schema designed for future extension) |
| Thread Depth | Configurable, on-demand only |
| CLI Style | Typer with subcommands |
| Tweet Limit | Default 100 tweets, `--all` for unlimited |
| DB Schema | Denormalized (single table with embedded JSON for complex fields) |
| Export Formats | JSON, Markdown, single-file HTML viewer |
| Daemon Mode | No (user runs manually or sets up external cron) |
| Rate Limiting | Exponential backoff |
| Query ID Refresh | Auto on 404 + manual `refresh-ids` command |
| Output Style | Progress bar + key events |
| Data Location | XDG-compliant (`~/.config/tweethoarder`, `~/.local/share/tweethoarder`) - directories created on first run |
| Deleted Content | Keep forever (never remove from local DB) |
| HTTP Client | httpx (async support) |
| Testing | Unit tests with mocks + integration tests with VCR.py |

---

## Architecture

### Directory Structure

```
tweethoarder/
├── src/
│   └── tweethoarder/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py              # Typer app entry point
│       │   ├── sync.py              # sync likes|bookmarks|tweets|reposts commands
│       │   ├── export.py            # export json|markdown|html commands
│       │   ├── thread.py            # thread <tweet_id> command
│       │   ├── stats.py             # stats command
│       │   └── query_ids.py         # refresh-ids command
│       ├── client/
│       │   ├── __init__.py
│       │   ├── base.py              # TwitterClient base class
│       │   ├── timelines.py         # Bookmarks, likes fetching
│       │   ├── user_tweets.py       # User tweets, reposts
│       │   ├── threads.py           # Thread/conversation fetching
│       │   └── types.py             # Pydantic models for API responses
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── cookies.py           # Cookie extraction (Firefox, Chrome)
│       │   ├── firefox.py           # Firefox cookie reader
│       │   └── chrome.py            # Chrome cookie reader (with keyring)
│       ├── query_ids/
│       │   ├── __init__.py
│       │   ├── store.py             # Query ID cache management
│       │   ├── scraper.py           # Bundle discovery and parsing
│       │   └── constants.py         # Baseline query IDs
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── database.py          # SQLite operations
│       │   ├── models.py            # Database models
│       │   └── checkpoint.py        # Sync progress checkpointing
│       ├── export/
│       │   ├── __init__.py
│       │   ├── json_export.py       # JSON file export
│       │   ├── markdown_export.py   # Markdown export
│       │   └── html_export.py       # Single-file HTML viewer
│       ├── config.py                # Configuration management
│       └── utils.py                 # Shared utilities
├── tests/
│   ├── unit/
│   │   └── ...
│   ├── integration/
│   │   └── ...
│   └── cassettes/                   # VCR.py recorded responses
├── pyproject.toml
├── CLAUDE.md
└── README.md
```

### Key Dependencies

```toml
[project]
dependencies = [
    "typer>=0.9.0",
    "httpx>=0.27.0",
    "rich>=13.0.0",          # Progress bars, pretty output
    "pydantic>=2.0.0",       # Data validation
    "secretstorage>=3.3.0",  # Chrome keyring decryption on Linux
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "vcrpy>=6.0.0",
    "ruff>=0.1.0",
]
```

---

## Data Model

### SQLite Schema (Denormalized)

```sql
-- Main tweets table (stores all tweet data)
CREATE TABLE tweets (
    id TEXT PRIMARY KEY,                    -- Tweet ID
    text TEXT NOT NULL,
    author_id TEXT NOT NULL,
    author_username TEXT NOT NULL,
    author_display_name TEXT,
    created_at TEXT NOT NULL,               -- ISO 8601 timestamp
    conversation_id TEXT,                   -- Thread root ID
    in_reply_to_tweet_id TEXT,              -- Parent tweet if reply
    in_reply_to_user_id TEXT,
    quoted_tweet_id TEXT,                   -- ID of quoted tweet
    is_retweet BOOLEAN DEFAULT FALSE,
    retweeted_tweet_id TEXT,                -- Original if retweet
    reply_count INTEGER DEFAULT 0,
    retweet_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    quote_count INTEGER DEFAULT 0,
    media_json TEXT,                        -- JSON array of media URLs/metadata
    urls_json TEXT,                         -- JSON array of embedded URLs
    hashtags_json TEXT,                     -- JSON array of hashtags
    mentions_json TEXT,                     -- JSON array of mentioned users
    raw_json TEXT,                          -- Full API response for future parsing
    first_seen_at TEXT NOT NULL,            -- When we first synced this
    last_updated_at TEXT NOT NULL,
    FOREIGN KEY (quoted_tweet_id) REFERENCES tweets(id),
    FOREIGN KEY (retweeted_tweet_id) REFERENCES tweets(id)
);

-- Collections (which tweets belong to which collection)
CREATE TABLE collections (
    tweet_id TEXT NOT NULL,
    collection_type TEXT NOT NULL,          -- 'like', 'bookmark', 'tweet', 'repost'
    bookmark_folder_id TEXT,                -- For bookmarks: folder ID (NULL = default)
    bookmark_folder_name TEXT,              -- For bookmarks: folder name
    added_at TEXT NOT NULL,                 -- When added to collection (from API or sync time)
    synced_at TEXT NOT NULL,                -- When we synced this
    PRIMARY KEY (tweet_id, collection_type),
    FOREIGN KEY (tweet_id) REFERENCES tweets(id)
);

-- Thread context (parent tweets for context)
CREATE TABLE thread_context (
    child_tweet_id TEXT NOT NULL,           -- The tweet we have in a collection
    parent_tweet_id TEXT NOT NULL,          -- Ancestor tweet (for context)
    depth INTEGER NOT NULL,                 -- How many levels up (1 = direct parent)
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (child_tweet_id, parent_tweet_id),
    FOREIGN KEY (child_tweet_id) REFERENCES tweets(id),
    FOREIGN KEY (parent_tweet_id) REFERENCES tweets(id)
);

-- Sync progress/checkpoints
CREATE TABLE sync_progress (
    collection_type TEXT PRIMARY KEY,       -- 'likes', 'bookmarks', 'tweets', 'reposts'
    cursor TEXT,                            -- Pagination cursor
    last_tweet_id TEXT,                     -- Last processed tweet ID
    total_synced INTEGER DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    status TEXT DEFAULT 'pending'           -- 'pending', 'in_progress', 'completed', 'failed'
);

-- Metadata
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Indexes for common queries
CREATE INDEX idx_tweets_author ON tweets(author_id);
CREATE INDEX idx_tweets_conversation ON tweets(conversation_id);
CREATE INDEX idx_tweets_created_at ON tweets(created_at);
CREATE INDEX idx_collections_type ON collections(collection_type);
CREATE INDEX idx_collections_added ON collections(added_at);
```

---

## CLI Commands

### Main Commands

```bash
# Sync commands (explicit subcommands)
# Note: Resume is automatic - interrupted syncs continue from last checkpoint
tweethoarder sync likes [--count N] [--all] [--with-threads] [--thread-mode MODE]
tweethoarder sync bookmarks [--count N] [--all] [--with-threads] [--thread-mode MODE]
tweethoarder sync tweets [--count N] [--all] [--with-threads] [--thread-mode MODE]
tweethoarder sync reposts [--count N] [--all] [--with-threads] [--thread-mode MODE]

# Thread fetching (on-demand)
tweethoarder thread <tweet_id> [--mode MODE] [--limit N] [--depth N]

# Export commands
tweethoarder export json [--collection TYPE] [--output PATH]
tweethoarder export markdown [--collection TYPE] [--output PATH]
tweethoarder export html [--collection TYPE] [--output PATH]

# Utility commands
tweethoarder stats                           # Show sync statistics
tweethoarder refresh-ids                     # Force refresh query IDs
tweethoarder config show                     # Show current config
tweethoarder config set KEY VALUE            # Set config value
```

### CLI Examples

```bash
# First run - auto-detects cookies, creates config
$ tweethoarder sync likes
[Auto-detecting cookies from Firefox...]
[Found cookies in ~/.mozilla/firefox/xxx.default/cookies.sqlite]
[Syncing likes...]
████████████████████████████████████████ 100% (2,450 likes)
[Saved to ~/.local/share/tweethoarder/tweethoarder.db]

# Sync with count limit
$ tweethoarder sync tweets --count 500

# Sync all tweets (may take a long time)
$ tweethoarder sync tweets --all

# Fetch thread context for a specific tweet
$ tweethoarder thread 1234567890 --depth 5

# Export to JSON
$ tweethoarder export json --collection likes --output ~/likes.json

# View statistics
$ tweethoarder stats
╭──────────────────────────────────────╮
│         TweetHoarder Stats           │
├──────────────────────────────────────┤
│ Likes:      5,234 (last: 2h ago)     │
│ Bookmarks:    892 (last: 2h ago)     │
│ Tweets:       423 (last: 1d ago)     │
│ Reposts:      156 (last: 1d ago)     │
│ Total Tweets: 6,705                  │
│ Database:     45.2 MB                │
╰──────────────────────────────────────╯
```

---

## Authentication Flow

### Cookie Resolution Priority

1. Environment variables: `TWITTER_AUTH_TOKEN`, `TWITTER_CT0`, `TWITTER_TWID`
2. Config file: `~/.config/tweethoarder/config.toml`
3. Auto-extract from Firefox:
   - Standard: `~/.mozilla/firefox/*/cookies.sqlite`
   - Snap: `~/snap/firefox/common/.mozilla/firefox/*/cookies.sqlite`
4. Auto-extract from Chrome (`~/.config/google-chrome/*/Cookies`) with keyring decryption

**Cookies extracted:** `auth_token`, `ct0`, `twid`

### Cookie Extraction

```python
# Firefox: Read directly from SQLite (unencrypted)
# Chrome: Use secretstorage to decrypt via GNOME Keyring or KDE Wallet

def extract_firefox_cookies(db_path: Path) -> dict[str, str]:
    """Extract auth_token, ct0, and twid from Firefox cookies.sqlite"""

def extract_chrome_cookies(db_path: Path) -> dict[str, str]:
    """Extract and decrypt auth_token, ct0, and twid from Chrome Cookies DB"""
```

---

## Query ID Management

### Ported from bird

The query ID system handles Twitter's rotating GraphQL operation IDs:

1. **Baseline IDs**: Ship with known-working query IDs in `constants.py`
2. **Runtime Cache**: Store discovered IDs in `~/.config/tweethoarder/query-ids-cache.json`
3. **Auto-refresh**: On HTTP 404, scrape Twitter's JS bundles to find new IDs (retry once, then fail)
4. **TTL**: Cache valid for 24 hours

### Bundle Scraping

Bundle scraping uses **unauthenticated requests** to fetch Twitter's public pages and JS bundles.

```python
DISCOVERY_PAGES = [
    "https://x.com/?lang=en",
    "https://x.com/explore",
    "https://x.com/notifications",
    "https://x.com/settings/profile",
]

BUNDLE_URL_PATTERN = r"https://abs\.twimg\.com/responsive-web/client-web(?:-legacy)?/[A-Za-z0-9.-]+\.js"

QUERY_ID_PATTERN = r"^[a-zA-Z0-9_-]+$"  # Validate extracted IDs

# Multiple regex patterns to handle different bundle formats
OPERATION_PATTERNS = [
    r'e\.exports=\{queryId\s*:\s*["\']([^"\']+)["\']\s*,\s*operationName\s*:\s*["\']([^"\']+)["\']',
    r'e\.exports=\{operationName\s*:\s*["\']([^"\']+)["\']\s*,\s*queryId\s*:\s*["\']([^"\']+)["\']',
    r'operationName\s*[:=]\s*["\']([^"\']+)["\'](.{0,4000}?)queryId\s*[:=]\s*["\']([^"\']+)["\']',
    r'queryId\s*[:=]\s*["\']([^"\']+)["\'](.{0,4000}?)operationName\s*[:=]\s*["\']([^"\']+)["\']',
]
```

### Refresh Implementation

```python
async def refresh_query_ids(client: httpx.AsyncClient) -> dict[str, str]:
    """Scrape Twitter bundles for fresh query IDs.

    1. Fetch discovery pages (unauthenticated)
    2. Extract bundle URLs from HTML
    3. Download and parse each bundle
    4. Save discovered IDs to cache file
    """
```

---

## Rate Limiting & Error Handling

### Exponential Backoff

```python
async def fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    max_retries: int = 5,
    base_delay: float = 1.0,
) -> httpx.Response:
    for attempt in range(max_retries):
        response = await client.get(url, headers=headers)

        if response.status_code == 429:  # Rate limited
            delay = base_delay * (2 ** attempt)
            log.warning(f"Rate limited, waiting {delay}s...")
            await asyncio.sleep(delay)
            continue

        if response.status_code == 404:
            # Trigger query ID refresh
            await refresh_query_ids()
            continue

        return response

    raise RateLimitExceeded()
```

### Checkpointing

```python
class SyncCheckpoint:
    """Save progress during sync for resume capability"""

    def save(self, collection_type: str, cursor: str, last_id: str):
        """Save current position"""

    def load(self, collection_type: str) -> Optional[CheckpointData]:
        """Load checkpoint for resuming interrupted sync"""

    def clear(self, collection_type: str):
        """Clear checkpoint after successful completion"""
```

---

## Configuration

### Config File (`~/.config/tweethoarder/config.toml`)

```toml
[auth]
# Manual cookie override (optional)
# auth_token = "your_auth_token"
# ct0 = "your_ct0_token"

# Cookie source priority: "firefox", "chrome", "manual"
cookie_sources = ["firefox", "chrome"]

[sync]
# Default count limits
default_tweet_count = 100
default_like_count = -1      # -1 = unlimited
default_bookmark_count = -1

# Rate limiting
request_delay_ms = 500       # Delay between requests
max_retries = 5

[export]
# Default export directory
export_dir = "~/tweethoarder-exports"

[display]
# Progress display
show_progress = true
verbose = false
```

---

## Export Formats

### Export Defaults

- **Default output directory:** `~/.local/share/tweethoarder/exports/`
- **Filename pattern:** `{collection}_{timestamp}.{format}` (e.g., `likes_2025-01-02T103000.json`)
- **`--output` flag:** Overrides default path with custom location
- **Overwrite behavior:** Prompt before overwriting existing files

### JSON Export

```json
{
  "exported_at": "2025-01-02T10:30:00Z",
  "collection": "likes",
  "count": 5234,
  "tweets": [
    {
      "id": "1234567890",
      "text": "Tweet content here...",
      "author": {
        "id": "9876543210",
        "username": "example_user",
        "display_name": "Example User"
      },
      "created_at": "2025-01-01T12:00:00Z",
      "metrics": {
        "reply_count": 10,
        "retweet_count": 50,
        "like_count": 200
      },
      "media": [
        {
          "type": "photo",
          "url": "https://pbs.twimg.com/media/xxx.jpg"
        }
      ],
      "quoted_tweet": { ... }
    }
  ]
}
```

### Markdown Export

```markdown
# Liked Tweets

Exported: 2025-01-02 10:30:00 UTC
Total: 5,234 tweets

---

## @example_user - Jan 1, 2025

Tweet content here...

[View on Twitter](https://twitter.com/example_user/status/1234567890)

---
```

### HTML Export

Single self-contained HTML file with:
- Inline CSS (minimal, clean design)
- Inline JS (filtering, search)
- All tweet data embedded as JSON
- Works completely offline

---

## Testing Strategy

### Unit Tests (with mocks)

- Cookie extraction logic
- Query ID parsing from bundles
- Database operations
- Export formatting
- CLI argument parsing

### Integration Tests (with VCR.py)

```python
@pytest.mark.vcr()
async def test_fetch_likes():
    """Test fetching likes with recorded API response"""
    client = TwitterClient(cookies=test_cookies)
    likes = await client.get_likes(count=10)
    assert len(likes) == 10
```

### VCR.py Cassette Management

- Record cassettes with real API calls during development
- Replay cassettes in CI (no real API calls)
- Sensitive data (cookies, tokens) scrubbed from cassettes

---

## Implementation Phases

### Phase 1: Core Infrastructure ✅
1. ✅ Project setup (pyproject.toml, directory structure)
2. ✅ Configuration management
3. ✅ SQLite database setup
4. ✅ Basic Typer CLI skeleton

### Phase 2: Authentication ✅
1. ✅ Firefox cookie extraction (including snap path)
2. ✅ Chrome cookie extraction with keyring
3. ✅ Cookie resolution flow
4. ✅ Manual cookie fallback (env vars, config file)

### Phase 3: Twitter Client ✅
1. ✅ Base HTTP client with headers
2. ✅ Query ID management (baseline + cache)
3. ✅ Query ID refresh from bundles
4. ✅ Rate limiting with exponential backoff

### Phase 4: Sync Commands ✅
1. ✅ Likes sync with pagination
2. ✅ Bookmarks sync (including folders)
3. ✅ User tweets sync
4. ✅ Reposts sync
5. ✅ Checkpointing infrastructure

### Phase 5: Additional Features ✅
1. ✅ Thread fetching (on-demand) with thread/conversation modes
2. ✅ Quoted tweet resolution
3. ✅ Stats command (with folder breakdown)
4. ✅ Progress display
5. ✅ Config show/set commands
6. ✅ `--with-threads` sync flag for thread expansion

### Phase 6: Export ✅
1. ✅ JSON export
2. ✅ Markdown export
3. ✅ HTML single-file viewer (with embedded search/filtering)
4. ✅ CSV export
5. ✅ `--folder` flag for bookmark filtering

### Phase 7: Testing & Polish 🟡
1. ✅ Unit tests with mocks (297 tests)
2. ⏳ Integration tests with VCR.py
3. ✅ Error handling edge cases
4. ✅ Documentation (README.md)

### Phase 8: Query ID Resilience ✅
1. ✅ Static fallback query IDs for all operations
2. ✅ Dynamic fallback (auto-refresh on missing ID)

**Legend:** ✅ Complete | 🟡 Partial | ⏳ Pending

---

## Key Files from bird to Port

| bird file | Purpose | tweethoarder equivalent |
|-----------|---------|-------------------------|
| `src/lib/twitter-client-base.ts` | Base client, headers, auth | `src/tweethoarder/client/base.py` |
| `src/lib/twitter-client-timelines.ts` | Bookmarks, likes | `src/tweethoarder/client/timelines.py` |
| `src/lib/runtime-query-ids.ts` | Query ID refresh | `src/tweethoarder/query_ids/store.py` |
| `src/lib/cookies.ts` | Cookie extraction | `src/tweethoarder/auth/cookies.py` |
| `src/lib/twitter-client-constants.ts` | Query IDs, URLs | `src/tweethoarder/query_ids/constants.py` |
| `src/lib/twitter-client-features.ts` | GraphQL feature flags | `src/tweethoarder/client/features.py` |

---

## Risk Mitigation

### Twitter API Changes
- Query ID refresh mechanism handles most changes
- Baseline query IDs updated periodically
- Fallback query IDs for critical operations
- Clear error messages when API changes break the tool

### Rate Limiting
- Conservative request delays
- Exponential backoff on 429
- Checkpointing allows resume after limits

### Cookie Expiration
- Detect expired cookies and prompt user
- Clear instructions for manual cookie refresh

---

## Glossary

This section defines key terms used throughout the specification.

| Term | Definition |
|------|------------|
| **Thread** | A series of tweets by the **same author** that share the same `conversation_id`, where each tweet is a reply to the previous. Classic "tweetstorm" or "1/N" format. |
| **Conversation** | All tweets sharing the same `conversation_id`, including replies from **multiple authors**. A superset of thread - threads are conversations, but not all conversations are threads. |
| **Focal Tweet** | The original tweet that triggered thread/conversation expansion. When you expand a liked tweet's thread, that liked tweet is the focal tweet. |
| **Tombstone** | A placeholder record indicating a deleted or unavailable tweet existed at a position in the thread. Preserves chain structure even when content is gone. |
| **Checkpoint** | Saved progress state allowing sync operations to resume after interruption. Stores cursor position and last processed tweet ID. |
| **Query ID** | Twitter's rotating GraphQL operation identifiers. Change periodically and must be discovered via bundle scraping. |
| **Bundle** | Twitter's compiled JavaScript files containing query IDs and feature flags. Scraped to discover current query IDs. |
| **Conversation ID** | Twitter's identifier linking all tweets in a conversation. The conversation_id equals the root tweet's ID. |

---

## Thread & Conversation Feature

### Overview

The thread command fetches and archives conversation context for tweets. It supports two modes:

1. **Thread Mode**: Extracts only the original author's self-reply chain (classic "unroll")
2. **Conversation Mode**: Archives the full conversation including all participants

### Definitions (Code-Level)

```python
def is_thread_tweet(tweet: Tweet, author_id: str, conversation_id: str) -> bool:
    """A tweet belongs to a thread if:
    - Same author as thread root
    - Same conversation_id
    - Is either the root or a reply to another tweet in the thread
    """
    return (
        tweet.author_id == author_id
        and tweet.conversation_id == conversation_id
    )

def is_conversation_tweet(tweet: Tweet, conversation_id: str) -> bool:
    """A tweet belongs to a conversation if it shares the conversation_id."""
    return tweet.conversation_id == conversation_id
```

### CLI Commands

```bash
# Manual thread/conversation expansion
tweethoarder thread <tweet_id> [--mode thread|conversation] [--limit N]

# Thread expansion during sync
tweethoarder sync likes --with-threads [--thread-mode thread|conversation] [--thread-limit N]
tweethoarder sync bookmarks --with-threads [--thread-mode thread|conversation] [--thread-limit N]

# Examples
tweethoarder thread 1234567890                    # Default: thread mode
tweethoarder thread 1234567890 --mode conversation --limit 200
tweethoarder sync likes --with-threads            # Expand threads for new likes
```

### Default Values

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--mode` | `thread` | Extract author's chain only |
| `--limit` | 200 | Max tweets to fetch per conversation |
| `--thread-limit` | 200 | Same as --limit for sync commands |

### Conversation Limits & Prioritization

Large conversations (viral tweets) can have thousands of replies. To prevent excessive API usage and storage:

**Hard Limits:**
- Thread mode: Unlimited (author threads rarely exceed 100 tweets)
- Conversation mode: 500 tweets maximum (configurable via `--limit`)

**Prioritization Strategy (Author-Centric):**

When a conversation exceeds the limit, prioritize tweets in this order:

1. **Author's replies**: All tweets from the original thread author
2. **Direct parents**: Tweets that author replied to (for context)
3. **High engagement**: Top liked/retweeted replies (> 100 likes)
4. **Chronological**: First N tweets by timestamp

```python
def prioritize_conversation_tweets(
    tweets: list[Tweet],
    author_id: str,
    limit: int
) -> list[Tweet]:
    """Select most valuable tweets when conversation exceeds limit."""
    author_tweets = [t for t in tweets if t.author_id == author_id]
    parent_ids = {t.in_reply_to_tweet_id for t in author_tweets if t.in_reply_to_tweet_id}
    parent_tweets = [t for t in tweets if t.id in parent_ids]

    # Always include author + their context
    must_include = set(author_tweets + parent_tweets)

    remaining = [t for t in tweets if t not in must_include]
    remaining.sort(key=lambda t: t.like_count + t.retweet_count, reverse=True)

    result = list(must_include)
    for tweet in remaining:
        if len(result) >= limit:
            break
        result.append(tweet)

    return sorted(result, key=lambda t: t.created_at)
```

### Database Schema Changes

#### New `threads` Table

```sql
-- Thread/conversation metadata
CREATE TABLE threads (
    id TEXT PRIMARY KEY,                    -- UUID for thread record
    conversation_id TEXT NOT NULL,          -- Twitter's conversation_id (= root tweet ID)
    root_tweet_id TEXT NOT NULL,            -- First tweet in conversation
    focal_tweet_id TEXT,                    -- Tweet that triggered expansion (from collection)
    author_id TEXT NOT NULL,                -- Original thread author
    thread_type TEXT NOT NULL,              -- 'thread' or 'conversation'
    tweet_count INTEGER NOT NULL,           -- Number of tweets stored
    is_complete BOOLEAN DEFAULT FALSE,      -- Did we fetch all available tweets?
    fetched_at TEXT NOT NULL,               -- ISO 8601 timestamp
    FOREIGN KEY (root_tweet_id) REFERENCES tweets(id),
    FOREIGN KEY (focal_tweet_id) REFERENCES tweets(id)
);

CREATE INDEX idx_threads_conversation ON threads(conversation_id);
CREATE INDEX idx_threads_focal ON threads(focal_tweet_id);
```

#### Updated `collections` Table

Add new collection types:

```sql
-- collection_type now includes: 'like', 'bookmark', 'tweet', 'repost', 'thread', 'conversation'
-- For thread/conversation collections, link to threads table:

ALTER TABLE collections ADD COLUMN thread_id TEXT REFERENCES threads(id);
```

#### Tombstone Support

Deleted tweets are represented as partial records:

```sql
-- Tombstone tweets have minimal data
INSERT INTO tweets (
    id,
    text,
    author_id,
    author_username,
    created_at,
    conversation_id,
    first_seen_at,
    last_updated_at,
    raw_json
) VALUES (
    'deleted_tweet_id',
    '[Tweet unavailable]',
    'unknown',
    'unknown',
    '1970-01-01T00:00:00Z',  -- Placeholder date
    'conversation_id',
    datetime('now'),
    datetime('now'),
    '{"tombstone": true, "reason": "deleted"}'
);
```

### API Implementation

#### Fetching Thread/Conversation

Uses Twitter's `TweetDetail` GraphQL endpoint (ported from bird):

```python
async def fetch_thread(
    client: TwitterClient,
    tweet_id: str,
    mode: Literal["thread", "conversation"] = "thread",
    limit: int = 200,
) -> ThreadResult:
    """Fetch thread or conversation for a tweet.

    Args:
        tweet_id: Focal tweet ID to expand
        mode: 'thread' for author-only chain, 'conversation' for all replies
        limit: Maximum tweets to fetch (conversation mode only)

    Returns:
        ThreadResult with tweets and metadata
    """
    # 1. Fetch TweetDetail (returns threaded_conversation_with_injections_v2)
    response = await client.fetch_tweet_detail(tweet_id)

    # 2. Extract all tweets from response
    all_tweets = parse_conversation_tweets(response)

    # 3. Determine conversation root and author
    focal_tweet = find_tweet_by_id(all_tweets, tweet_id)
    conversation_id = focal_tweet.conversation_id
    author_id = find_root_author(all_tweets, conversation_id)

    # 4. Filter based on mode
    if mode == "thread":
        tweets = [t for t in all_tweets if is_thread_tweet(t, author_id, conversation_id)]
    else:
        tweets = [t for t in all_tweets if is_conversation_tweet(t, conversation_id)]
        if len(tweets) > limit:
            tweets = prioritize_conversation_tweets(tweets, author_id, limit)

    # 5. Handle pagination if needed (conversation mode)
    # TweetDetail returns cursor for more replies

    return ThreadResult(
        tweets=tweets,
        conversation_id=conversation_id,
        author_id=author_id,
        focal_tweet_id=tweet_id,
        is_complete=len(tweets) < limit,
    )
```

### Rate Limiting for Thread Expansion

Thread expansion uses **adaptive rate limiting**:

```python
class AdaptiveRateLimiter:
    """Self-tuning rate limiter for thread expansion."""

    def __init__(self, initial_delay: float = 0.5):
        self.delay = initial_delay  # Start at 500ms
        self.min_delay = 0.3
        self.max_delay = 30.0
        self.consecutive_successes = 0
        self.consecutive_failures = 0

    async def wait(self):
        await asyncio.sleep(self.delay)

    def on_success(self):
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        # Speed up after 5 consecutive successes
        if self.consecutive_successes >= 5:
            self.delay = max(self.min_delay, self.delay * 0.8)
            self.consecutive_successes = 0

    def on_rate_limit(self):
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        # Exponential backoff
        self.delay = min(self.max_delay, self.delay * 2)

    def should_stop(self) -> bool:
        # Stop after 3 consecutive rate limits
        return self.consecutive_failures >= 3
```

### Error Handling

| Error Type | Behavior |
|------------|----------|
| Deleted tweet | Create tombstone, continue expansion |
| Suspended account | Create tombstone with reason, continue |
| 429 Rate Limit | Exponential backoff, stop after 3 failures |
| 403 Forbidden | Stop immediately (possible ban risk) |
| 404 Not Found | Trigger query ID refresh, retry once |
| Network error | Retry with backoff, continue sync on success |

### --with-threads During Sync

When `--with-threads` is specified during sync:

1. **Scope**: Only expand threads for **newly fetched tweets** in this sync run
2. **Deduplication**: Skip tweets that already have thread data in DB
3. **Progress**: Show separate progress for thread expansion phase

```bash
$ tweethoarder sync likes --with-threads
[Syncing likes...]
████████████████████████████████████████ 100% (150 new likes)
[Expanding threads for 150 tweets...]
████████████████████████████████████████ 100% (skipped 45 already expanded)
[Saved 1,247 thread tweets]
```

### Output Format

```bash
$ tweethoarder thread 1234567890
Fetching thread for tweet 1234567890...
Found thread by @alice (15 tweets)
Saved to database.

$ tweethoarder thread 1234567890 --mode conversation
Fetching conversation for tweet 1234567890...
Found conversation (127 tweets, limited to 200)
  - @alice: 15 tweets (thread author)
  - 45 other participants
Saved to database.
```

---

## Enhanced HTML Export

### Overview

The HTML export generates a **single self-contained file** with embedded search and filtering capabilities. All tweet data is embedded as JSON, with JavaScript providing interactive features.

### File Size Warning

```bash
$ tweethoarder export html --collection likes
Warning: Exporting 25,000 tweets may create a large file (est. 45MB).
Large files may load slowly in browsers. Continue? [y/N]
```

**Warning thresholds:**
- 20,000 tweets OR
- Estimated file size > 100MB

### Search & Filter Features

#### Pre-Computed Facets (at export time)

These facets are computed during export for instant display:

1. **Authors**: List of all authors with tweet counts
2. **Months**: Year-month buckets with counts
3. **Media Types**: has_photo, has_video, has_link, text_only

#### Live-Computed Filters

These update dynamically as user applies filters:

1. **Full-text search**: Searches tweet text content
2. **Date range**: Custom start/end dates
3. **Engagement thresholds**: Min likes, min retweets
4. **Custom author filter**: Filter to specific authors

### HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TweetHoarder Export - Likes</title>
    <style>
        /* Inline CSS - responsive, clean design */
        /* ~5KB minified */
    </style>
</head>
<body>
    <header>
        <h1>Liked Tweets</h1>
        <p>Exported: 2025-01-03 | 5,234 tweets</p>
    </header>

    <aside id="filters">
        <!-- Search box -->
        <input type="search" id="search" placeholder="Search tweets...">

        <!-- Pre-computed facets -->
        <details open>
            <summary>Authors (127)</summary>
            <ul id="author-facets">
                <!-- Populated from precomputed data -->
            </ul>
        </details>

        <details>
            <summary>Date Range</summary>
            <input type="month" id="date-from">
            <input type="month" id="date-to">
        </details>

        <details>
            <summary>Media Type</summary>
            <label><input type="checkbox" value="photo"> Has Photo (1,234)</label>
            <label><input type="checkbox" value="video"> Has Video (567)</label>
            <label><input type="checkbox" value="link"> Has Link (2,100)</label>
        </details>
    </aside>

    <main id="tweets">
        <!-- Tweets rendered here by JS -->
    </main>

    <script>
        // Embedded tweet data
        const TWEETS = [/* ... */];
        const FACETS = {
            authors: [/* {username, count} */],
            months: [/* {month, count} */],
            media: {photo: 1234, video: 567, link: 2100, text_only: 1333}
        };

        // Search and filter logic (~10KB minified)
    </script>
</body>
</html>
```

### Search Implementation

```javascript
// Simplified search logic
function searchTweets(query, filters) {
    return TWEETS.filter(tweet => {
        // Full-text search
        if (query && !tweet.text.toLowerCase().includes(query.toLowerCase())) {
            return false;
        }

        // Author filter
        if (filters.authors.length && !filters.authors.includes(tweet.author.username)) {
            return false;
        }

        // Date range
        if (filters.dateFrom && tweet.created_at < filters.dateFrom) return false;
        if (filters.dateTo && tweet.created_at > filters.dateTo) return false;

        // Media type
        if (filters.mediaTypes.length) {
            const hasPhoto = tweet.media?.some(m => m.type === 'photo');
            const hasVideo = tweet.media?.some(m => m.type === 'video');
            const hasLink = tweet.urls?.length > 0;

            const matches = filters.mediaTypes.some(type => {
                if (type === 'photo') return hasPhoto;
                if (type === 'video') return hasVideo;
                if (type === 'link') return hasLink;
                if (type === 'text_only') return !hasPhoto && !hasVideo && !hasLink;
            });
            if (!matches) return false;
        }

        return true;
    });
}

// Update facet counts after filtering
function updateFacetCounts(filteredTweets) {
    // Live compute author counts for current filter
    const authorCounts = {};
    filteredTweets.forEach(t => {
        authorCounts[t.author.username] = (authorCounts[t.author.username] || 0) + 1;
    });
    // Update UI...
}
```

---

## Bookmark Folder Export

### Overview

The sync command fetches **all bookmark folders** in one operation. Export commands can filter by folder.

### Sync Behavior

```bash
$ tweethoarder sync bookmarks
[Syncing bookmarks from all folders...]
  - Default: 234 bookmarks
  - Work: 89 bookmarks
  - Read Later: 156 bookmarks
████████████████████████████████████████ 100% (479 total)
```

### Export Filtering

```bash
# Export specific folder
$ tweethoarder export json --collection bookmarks --folder "Work"

# Export all bookmarks (default)
$ tweethoarder export json --collection bookmarks

# List available folders
$ tweethoarder stats
╭──────────────────────────────────────╮
│         TweetHoarder Stats           │
├──────────────────────────────────────┤
│ Bookmarks:    479 total              │
│   - Default:  234                    │
│   - Work:      89                    │
│   - Read Later: 156                  │
╰──────────────────────────────────────╯
```

### Database

Folder information is already stored in the `collections` table:
- `bookmark_folder_id`: Twitter's folder ID
- `bookmark_folder_name`: User-visible folder name

---

## Query ID Resilience

### Current Issue

The `UserTweets` operation is used in sync but missing from `FALLBACK_QUERY_IDS`.

### Solution: Both Static + Dynamic Fallback

1. **Add known IDs to constants.py**:

```python
FALLBACK_QUERY_IDS = {
    "Bookmarks": "...",
    "BookmarkFolderTimeline": "...",
    "Likes": "...",
    "TweetDetail": "...",
    "SearchTimeline": "...",
    "UserTweets": "...",           # ADD THIS
    "UserTweetsAndReplies": "...", # ADD THIS
    "Following": "...",
    "Followers": "...",
}
```

2. **Dynamic fallback**: If operation not in fallbacks, auto-trigger bundle refresh:

```python
async def get_query_id_with_fallback(
    store: QueryIdStore,
    operation: str,
) -> str:
    """Get query ID with automatic refresh fallback."""
    # Try cache first
    query_id = store.get(operation)
    if query_id:
        return query_id

    # Try static fallback
    if operation in FALLBACK_QUERY_IDS:
        return FALLBACK_QUERY_IDS[operation]

    # Dynamic fallback: refresh and retry
    await store.refresh()
    query_id = store.get(operation)
    if query_id:
        return query_id

    raise QueryIdNotFound(f"Cannot find query ID for {operation}")
```

---

## Example SQL Queries

These queries demonstrate common operations on the TweetHoarder database.

### Basic Queries

```sql
-- Get all liked tweets ordered by date
SELECT t.*, c.added_at as liked_at
FROM tweets t
JOIN collections c ON t.id = c.tweet_id
WHERE c.collection_type = 'like'
ORDER BY c.added_at DESC;

-- Get bookmarks from a specific folder
SELECT t.*, c.bookmark_folder_name
FROM tweets t
JOIN collections c ON t.id = c.tweet_id
WHERE c.collection_type = 'bookmark'
  AND c.bookmark_folder_name = 'Work'
ORDER BY c.added_at DESC;

-- Count tweets by collection type
SELECT collection_type, COUNT(*) as count
FROM collections
GROUP BY collection_type;
```

### Thread/Conversation Queries

```sql
-- Get all threads I've archived
SELECT
    th.id,
    th.thread_type,
    th.tweet_count,
    th.fetched_at,
    t.text as root_text,
    t.author_username as author
FROM threads th
JOIN tweets t ON th.root_tweet_id = t.id
ORDER BY th.fetched_at DESC;

-- Get all tweets in a specific thread
SELECT t.*
FROM tweets t
JOIN collections c ON t.id = c.tweet_id
WHERE c.thread_id = 'thread-uuid-here'
ORDER BY t.created_at;

-- Find the thread containing a specific tweet
SELECT th.*
FROM threads th
JOIN collections c ON th.id = c.thread_id
WHERE c.tweet_id = '1234567890';

-- Get conversation tree structure
WITH RECURSIVE thread_tree AS (
    -- Start with root tweet
    SELECT
        t.id,
        t.text,
        t.author_username,
        t.in_reply_to_tweet_id,
        0 as depth
    FROM tweets t
    WHERE t.id = (
        SELECT root_tweet_id FROM threads WHERE id = 'thread-uuid'
    )

    UNION ALL

    -- Recursively get replies
    SELECT
        t.id,
        t.text,
        t.author_username,
        t.in_reply_to_tweet_id,
        tt.depth + 1
    FROM tweets t
    JOIN thread_tree tt ON t.in_reply_to_tweet_id = tt.id
    JOIN collections c ON t.id = c.tweet_id
    WHERE c.thread_id = 'thread-uuid'
)
SELECT * FROM thread_tree ORDER BY depth, id;
```

### Search Queries

```sql
-- Full-text search across all tweets
SELECT t.*, c.collection_type
FROM tweets t
JOIN collections c ON t.id = c.tweet_id
WHERE t.text LIKE '%search term%'
ORDER BY t.created_at DESC;

-- Find tweets with media
SELECT t.*
FROM tweets t
WHERE t.media_json IS NOT NULL
  AND t.media_json != '[]'
ORDER BY t.created_at DESC;

-- Find highly-engaged tweets in my likes
SELECT t.*, (t.like_count + t.retweet_count) as engagement
FROM tweets t
JOIN collections c ON t.id = c.tweet_id
WHERE c.collection_type = 'like'
ORDER BY engagement DESC
LIMIT 50;

-- Find tweets by specific author across all collections
SELECT t.*, c.collection_type
FROM tweets t
JOIN collections c ON t.id = c.tweet_id
WHERE t.author_username = 'elonmusk'
ORDER BY t.created_at DESC;
```

### Statistics Queries

```sql
-- Tweets by month
SELECT
    strftime('%Y-%m', created_at) as month,
    COUNT(*) as tweet_count
FROM tweets
GROUP BY month
ORDER BY month DESC;

-- Top authors in my likes
SELECT
    t.author_username,
    t.author_display_name,
    COUNT(*) as like_count
FROM tweets t
JOIN collections c ON t.id = c.tweet_id
WHERE c.collection_type = 'like'
GROUP BY t.author_id
ORDER BY like_count DESC
LIMIT 20;

-- Database size by collection
SELECT
    c.collection_type,
    COUNT(DISTINCT c.tweet_id) as unique_tweets,
    SUM(LENGTH(t.raw_json)) as raw_json_bytes
FROM collections c
JOIN tweets t ON c.tweet_id = t.id
GROUP BY c.collection_type;
```

### Maintenance Queries

```sql
-- Find orphaned tweets (not in any collection)
SELECT t.id, t.text, t.author_username
FROM tweets t
LEFT JOIN collections c ON t.id = c.tweet_id
WHERE c.tweet_id IS NULL;

-- Find tombstone tweets
SELECT id, conversation_id, first_seen_at
FROM tweets
WHERE text = '[Tweet unavailable]';

-- Check sync progress
SELECT * FROM sync_progress;

-- Find incomplete thread expansions
SELECT * FROM threads WHERE is_complete = FALSE;
```

---

## Updated Implementation Phases

### Phase 5: Additional Features ✅

1. ✅ Quoted tweet resolution
2. ✅ Stats command (with folder breakdown)
3. ✅ Progress display
4. ✅ Config show/set commands
5. ✅ **Thread command** - Full implementation with thread/conversation modes
6. ✅ **--with-threads sync flag** - Thread expansion during sync

### Phase 6: Export ✅

1. ✅ JSON export
2. ✅ Markdown export
3. ✅ CSV export
4. ✅ **HTML export enhancement** - Faceted search, filtering, embedded JS
5. ✅ **Bookmark folder filtering** - `--folder` flag for export commands

### Phase 8: Query ID Resilience ✅

1. ✅ Static fallback query IDs for all operations
2. ✅ Dynamic fallback (auto-refresh on missing ID)

**Legend:** ✅ Complete | 🟡 Partial | ⏳ Pending
