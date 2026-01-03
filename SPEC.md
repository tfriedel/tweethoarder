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
tweethoarder sync likes [--count N] [--all] [--resume]
tweethoarder sync bookmarks [--folder NAME] [--resume]
tweethoarder sync tweets [--count N] [--all] [--resume]
tweethoarder sync reposts [--count N] [--all] [--resume]

# Thread fetching (on-demand)
tweethoarder thread <tweet_id> [--depth N]   # Fetch thread context for a tweet

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

### Phase 5: Additional Features 🟡
1. ⏳ Thread fetching (on-demand) - CLI stub exists
2. ✅ Quoted tweet resolution
3. ✅ Stats command
4. ✅ Progress display
5. ✅ Config show/set commands

### Phase 6: Export ✅
1. ✅ JSON export
2. ✅ Markdown export
3. ✅ HTML single-file viewer
4. ✅ CSV export

### Phase 7: Testing & Polish 🟡
1. ✅ Unit tests with mocks (217 tests)
2. ⏳ Integration tests with VCR.py
3. ✅ Error handling edge cases
4. ⏳ Documentation

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
