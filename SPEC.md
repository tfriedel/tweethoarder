# TweetHoarder - Twitter/X Data Archival Tool Specification

## Overview

TweetHoarder is a Python CLI tool for archiving a user's Twitter/X data (likes, bookmarks, tweets, reposts, replies, and home timeline/feed) locally. It uses cookie-based authentication to access Twitter's internal GraphQL API (no paid API key required), with architecture ported from the [bird](https://github.com/steipete/bird) TypeScript project.

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
| Export Formats | JSON, Markdown, CSV, single-file HTML viewer with virtual scrolling |
| Daemon Mode | No (user runs manually or sets up external cron) |
| Rate Limiting | Exponential backoff with adaptive rate limiting for threads |
| Query ID Refresh | Auto on 404 + manual `refresh-ids` command + static fallbacks |
| Output Style | Progress bar + key events (via Rich) |
| Data Location | XDG-compliant (`~/.config/tweethoarder`, `~/.local/share/tweethoarder`) |
| Deleted Content | Keep forever (never remove from local DB) |
| HTTP Client | httpx (async support) |
| Testing | Unit tests with mocks + integration tests with VCR.py + TDD guard |
| Collection Types | likes, bookmarks, tweets, reposts, replies, feed |

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
│       │   ├── sync.py              # sync likes|bookmarks|tweets|reposts|replies|posts|threads|feed
│       │   ├── export.py            # export json|markdown|csv|html commands (HTML inline)
│       │   ├── thread.py            # thread <tweet_id> command
│       │   ├── stats.py             # stats command
│       │   ├── config.py            # config show/set commands
│       │   └── query_ids.py         # refresh-ids command
│       ├── client/
│       │   ├── __init__.py
│       │   ├── base.py              # TwitterClient base class
│       │   ├── timelines.py         # Bookmarks, likes, home timeline fetching
│       │   ├── features.py          # GraphQL feature flags (ported from bird)
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
│       │   └── checkpoint.py        # Sync progress checkpointing
│       ├── export/
│       │   ├── __init__.py
│       │   ├── json_export.py       # JSON file export
│       │   ├── markdown_export.py   # Markdown export with thread context
│       │   ├── csv_export.py        # CSV export
│       │   └── richtext.py          # Richtext formatting preservation
│       ├── sync/
│       │   ├── __init__.py
│       │   └── sort_index.py        # Sort index generation for ordering
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
    "cryptography>=46.0.3",   # Chrome cookie decryption
    "httpx>=0.28.1",          # HTTP client with async support
    "loguru>=0.7.0",          # Logging
    "pydantic>=2.12.5",       # Data validation
    "rich>=14.2.0",           # Progress bars, pretty output
    "secretstorage>=3.5.0",   # Chrome keyring decryption on Linux
    "typer>=0.21.0",          # CLI framework
]

[project.optional-dependencies]
dev = [
    "coverage>=7.9.2",
    "deptry>=0.25.0",
    "git-cliff>=3.0.1",
    "prek>=0.1.0",            # Fast pre-commit replacement
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=6.2.1",
    "pytest-sugar>=1.0.0",
    "ruff>=0.11.12",
    "sync-with-uv>=0.3.1",
    "tdd-guard-pytest>=0.8.1",
    "vcrpy>=6.0.0",
    "zuban>=0.4.0",
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
    collection_type TEXT NOT NULL,          -- 'like', 'bookmark', 'tweet', 'repost', 'reply', 'feed'
    bookmark_folder_id TEXT,                -- For bookmarks: folder ID (NULL = default)
    bookmark_folder_name TEXT,              -- For bookmarks: folder name
    added_at TEXT NOT NULL,                 -- When added to collection (from API or sync time)
    synced_at TEXT NOT NULL,                -- When we synced this
    sort_index INTEGER,                     -- Order-preserving index for pagination
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
# Sync all collections at once (recommended)
# Note: Resume is automatic - interrupted syncs continue from last checkpoint
tweethoarder sync                            # Sync all collections (likes, bookmarks, tweets, reposts, replies)
tweethoarder sync --likes                    # Sync only likes
tweethoarder sync --likes --bookmarks        # Sync likes and bookmarks
tweethoarder sync --tweets --reposts         # Sync tweets and reposts
tweethoarder sync --feed                     # Sync feed (excluded from default sync)
tweethoarder sync --count N                  # Limit items per collection
tweethoarder sync --full                     # Force complete resync (ignore existing)

# Individual sync subcommands (for backwards compatibility)
tweethoarder sync likes [--count N] [--all] [--with-threads] [--thread-mode MODE] [--store-raw/--no-store-raw]
tweethoarder sync bookmarks [--count N] [--all] [--with-threads] [--thread-mode MODE] [--store-raw/--no-store-raw]
tweethoarder sync tweets [--count N] [--all] [--with-threads] [--thread-mode MODE] [--store-raw/--no-store-raw]
tweethoarder sync reposts [--count N] [--all] [--with-threads] [--thread-mode MODE] [--store-raw/--no-store-raw]
tweethoarder sync replies [--count N] [--all] [--with-threads] [--thread-mode MODE] [--store-raw/--no-store-raw]
tweethoarder sync feed [--hours N] [--all]   # Sync Following/home timeline (default: last 24h)

# Thread fetching (on-demand)
tweethoarder thread <tweet_id> [--mode MODE] [--limit N] [--depth N]

# Export commands
tweethoarder export json [--collection TYPE] [--output PATH] [--folder NAME]
tweethoarder export markdown [--collection TYPE] [--output PATH] [--folder NAME]
tweethoarder export csv [--collection TYPE] [--output PATH] [--folder NAME]
tweethoarder export html [--collection TYPE] [--output PATH] [--folder NAME]

# Utility commands
tweethoarder stats                           # Show sync statistics with folder breakdown
tweethoarder refresh-ids                     # Force refresh query IDs
tweethoarder config show                     # Show current config
tweethoarder config set KEY VALUE            # Set config value
```

### Sync Command Details

| Command | Description |
|---------|-------------|
| `sync` | Sync all collections (likes, bookmarks, tweets, reposts, replies) |
| `sync --likes` | Sync only likes |
| `sync --bookmarks` | Sync only bookmarks |
| `sync --tweets` | Sync only tweets |
| `sync --reposts` | Sync only reposts |
| `sync --replies` | Sync only replies |
| `sync --feed` | Sync feed (excluded from default sync) |
| `sync likes` | Sync liked tweets (subcommand) |
| `sync bookmarks` | Sync bookmarks (subcommand) |
| `sync tweets` | Sync user's original tweets (subcommand) |
| `sync reposts` | Sync user's retweets (subcommand) |
| `sync replies` | Sync user's replies (subcommand) |
| `sync feed` | Sync home timeline (subcommand) |

### Common Sync Flags

| Flag | Description |
|------|-------------|
| `--count N` | Limit to N items per collection (default: unlimited incremental) |
| `--all` | Sync all available items (no limit) - for subcommands |
| `--full` | Force complete resync, ignoring existing tweets |
| `--with-threads` | Expand threads for synced tweets |
| `--thread-mode` | `thread` (author only) or `conversation` (all replies) |
| `--store-raw/--no-store-raw` | Store raw JSON response (default: yes) |
| `--hours N` | For `sync feed`: fetch posts from last N hours (default: 24) |

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

# Sync home timeline from the last 24 hours (default)
$ tweethoarder sync feed

# Sync home timeline from the last 48 hours
$ tweethoarder sync feed --hours 48

# Sync replies separately
$ tweethoarder sync replies --all

# Sync all collections at once (recommended)
$ tweethoarder sync

# Sync only likes and bookmarks
$ tweethoarder sync --likes --bookmarks

# Fetch thread context for a specific tweet
$ tweethoarder thread 1234567890

# Export to JSON
$ tweethoarder export json --collection likes --output ~/likes.json

# Export bookmarks from specific folder
$ tweethoarder export json --collection bookmarks --folder "Read Later"

# Export all collections to interactive HTML viewer
$ tweethoarder export html --collection all --output ~/twitter-archive.html

# View statistics
$ tweethoarder stats
╭──────────────────────────────────────╮
│         TweetHoarder Stats           │
├──────────────────────────────────────┤
│ Likes:      5,234 (last: 2h ago)     │
│ Bookmarks:    892 (last: 2h ago)     │
│   - Default:  500                    │
│   - Work:     250                    │
│   - Read Later: 142                  │
│ Tweets:       423 (last: 1d ago)     │
│ Reposts:      156 (last: 1d ago)     │
│ Replies:       89 (last: 1d ago)     │
│ Feed:       1,200 (last: 3h ago)     │
│ Total Tweets: 8,094                  │
│ Database:     52.3 MB                │
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
5. ✅ Feature flags ported from bird

### Phase 4: Sync Commands ✅
1. ✅ Likes sync with pagination
2. ✅ Bookmarks sync (including folders)
3. ✅ User tweets sync
4. ✅ Reposts sync
5. ✅ Replies sync (user's replies to others)
6. ✅ Posts sync (tweets + reposts combined)
7. ✅ Feed sync (home timeline/Following)
8. ✅ Batch thread sync command
9. ✅ Checkpointing infrastructure
10. ✅ Sort index for order preservation

### Phase 5: Additional Features ✅
1. ✅ Thread fetching (on-demand) with thread/conversation modes
2. ✅ Quoted tweet resolution
3. ✅ Stats command (with folder breakdown)
4. ✅ Progress display
5. ✅ Config show/set commands
6. ✅ `--with-threads` sync flag for thread expansion
7. ✅ `--store-raw` flag for raw JSON storage

### Phase 6: Export ✅
1. ✅ JSON export
2. ✅ Markdown export with thread context
3. ✅ CSV export
4. ✅ HTML single-file viewer:
   - ✅ Virtual scrolling for performance
   - ✅ Light/dark theme switcher
   - ✅ Full-text search with faceted filtering
   - ✅ Author/type/media/date filtering
   - ✅ Copy as markdown with quoted tweets
   - ✅ Deduplication logic
   - ✅ Richtext formatting preservation
5. ✅ `--folder` flag for bookmark filtering

### Phase 7: Testing & Polish ✅
1. ✅ Unit tests with mocks (300+ tests)
2. ✅ Integration tests with VCR.py cassettes
3. ✅ Error handling edge cases
4. ✅ Documentation (README.md)
5. ✅ TDD guard enforcement

### Phase 8: Query ID Resilience ✅
1. ✅ Static fallback query IDs for all 11 operations
2. ✅ Dynamic fallback (auto-refresh on missing ID)
3. ✅ HomeLatestTimeline support for feed sync

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

The HTML export generates a **single self-contained file** with embedded search, filtering, and interactive features. All tweet data is embedded as JSON, with JavaScript providing a Twitter-like viewing experience with virtual scrolling for performance.

### Key Features

| Feature | Description |
|---------|-------------|
| **Virtual Scrolling** | Renders only visible tweets for smooth performance with 10,000+ tweets |
| **Theme Switcher** | Light/dark mode toggle persisted in localStorage |
| **Full-text Search** | Instant search across tweet text, author names |
| **Author Filtering** | Click authors to filter; live facet counts update |
| **Type Filtering** | Filter by collection type when using `--collection all` |
| **Media Filtering** | Filter by photo, video, link, or text-only |
| **Date Range** | Filter by date range with month picker |
| **Copy as Markdown** | One-click copy of tweet as formatted markdown |
| **Quoted Tweets** | Inline rendering of quoted tweets with visual attribution |
| **Richtext Formatting** | Preserves bold, italic, links from original tweets |
| **Deduplication** | Merges reposts with originals; highlights thread tweets |
| **Scrollbar** | Fixed scrollbar at screen edge for easier navigation |

### File Size Warning

```bash
$ tweethoarder export html --collection likes
Warning: Exporting 25,000 tweets may create a large file (est. 45MB).
Large files may load slowly in browsers. Continue? [y/N]
```

### UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  TweetHoarder - Liked Tweets (5,234)            🌙 Toggle   │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────┐  ┌────────────────────────────────────────┐ │
│ │  FILTERS    │  │  Tweet 1                          📋   │ │
│ │             │  │  @author · Jan 1, 2025                 │ │
│ │ Search...   │  │  Tweet content here with **bold**      │ │
│ │             │  │  ┌──────────────────────────────────┐  │ │
│ │ ▼ Authors   │  │  │ Quoted Tweet                     │  │ │
│ │   @alice 42 │  │  │ @quoted_author                   │  │ │
│ │   @bob   31 │  │  └──────────────────────────────────┘  │ │
│ │             │  │  ♥ 1.2K  🔁 456  💬 89                 │ │
│ │ ▼ Type      │  ├────────────────────────────────────────┤ │
│ │   □ likes   │  │  Tweet 2 ...                           │ │
│ │   □ tweets  │  │  ...                                   │ │
│ │             │  │                                        │ │
│ │ ▼ Media     │  │  (virtual scroll renders visible only) │ │
│ │   □ photo   │  │                                        │ │
│ │   □ video   │  │                                        │ │
│ └─────────────┘  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Search & Filter Features

#### Pre-Computed Facets (at export time)

1. **Authors**: List of all authors with tweet counts
2. **Collection Types**: When using `--collection all`, shows type breakdown
3. **Media Types**: has_photo, has_video, has_link, text_only

#### Live-Computed Filters

1. **Full-text search**: Instant search with debouncing
2. **Date range**: Custom start/end dates
3. **Author filter**: Click to add/remove authors from filter
4. **Type filter**: Filter by collection type (likes, bookmarks, tweets, etc.)

### Copy as Markdown

Each tweet has a copy button that generates markdown like:

```markdown
> **Tweet content with formatting preserved**
>
> ![Image](https://pbs.twimg.com/media/xxx.jpg)
>
> > **Quoted tweet content**
> > — @quoted_author

— @author ([source](https://x.com/author/status/123))
```

### Deduplication Logic

When a tweet appears in multiple collections (e.g., liked AND retweeted):
- Shows tweet once with merged metadata
- Indicates all collection types it appears in
- Thread tweets marked with visual indicator

### Performance Optimizations

- **Virtual scrolling**: Only renders ~20 visible tweets at a time
- **Debounced search**: 150ms delay before filtering
- **Lazy facet computation**: Only recalculates on filter change
- **Minimal DOM**: Single-file with inlined CSS/JS (~50KB base)

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

### Implementation Status: ✅ Complete

All required GraphQL operations now have fallback query IDs.

### Solution: Both Static + Dynamic Fallback ✅

1. **Known IDs in constants.py** (all operations covered):

```python
FALLBACK_QUERY_IDS = {
    "Bookmarks": "RV1g3b8n_SGOHwkqKYSCFw",
    "BookmarkFolderTimeline": "KJIQpsvxrTfRIlbaRIySHQ",
    "Likes": "JR2gceKucIKcVNB_9JkhsA",
    "TweetDetail": "97JF30KziU00483E_8elBA",
    "SearchTimeline": "M1jEez78PEfVfbQLvlWMvQ",
    "UserArticlesTweets": "8zBy9h4L90aDL02RsBcCFg",
    "UserTweets": "Wms1GvIiHXAPBaCr9KblaA",
    "UserTweetsAndReplies": "_P1zJA2kS9W1PLHKdThsrg",
    "Following": "BEkNpEt5pNETESoqMsTEGA",
    "Followers": "kuFUYP9eV1FPoEy4N-pi7w",
    "HomeLatestTimeline": "iOEZpOdfekFsxSlPQCQtPg",
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

