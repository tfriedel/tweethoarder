# TweetHoarder

Archive your Twitter/X data locally - likes, bookmarks, tweets, reposts, and home feed.

TweetHoarder uses cookie-based authentication to access Twitter's internal GraphQL API (no paid API key required), storing everything in a local SQLite database for offline access and search.

## Features

- **Sync your data**: Likes, bookmarks (with folders), tweets, reposts, replies, and home feed
- **Quote tweets**: Full support for quoted tweets in sync and all export formats
- **Thread expansion**: Archive full threads and conversations with context
- **Rich HTML export**: Twitter-style design with dark/light themes, virtual scrolling, search/filter, and copy-as-markdown
- **Multiple exports**: JSON, Markdown, CSV, and searchable HTML
- **Resume support**: Checkpointing allows interrupted syncs to continue
- **Browser cookie extraction**: Auto-detect from Firefox or Chrome
- **Rate limit handling**: Adaptive backoff prevents API bans
- **Offline-first**: All data stored locally in SQLite

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/tweethoarder.git
cd tweethoarder

# Install with uv
uv sync

# Or install as a package
uv pip install -e .
```

## Quick Start

```bash
# First run - auto-detects cookies from Firefox/Chrome
tweethoarder sync likes

# Sync other collections
tweethoarder sync bookmarks
tweethoarder sync tweets --count 500
tweethoarder sync reposts --all

# Sync your home timeline (last 24 hours)
tweethoarder sync feed

# Export your data
tweethoarder export json --collection likes --output ~/likes.json
tweethoarder export html --collection bookmarks  # Twitter-style HTML viewer
tweethoarder export html --collection all        # Combined export with type filters

# View statistics
tweethoarder stats
```

## Commands

### Sync Commands

Interrupted syncs automatically resume from the last checkpoint.

```bash
# Sync likes (default: 100 tweets, use --all for unlimited)
tweethoarder sync likes [--count N] [--all]

# Sync bookmarks from all folders
tweethoarder sync bookmarks [--count N] [--all]

# Sync your own tweets
tweethoarder sync tweets [--count N] [--all]

# Sync reposts (retweets)
tweethoarder sync reposts [--count N] [--all]

# Sync replies
tweethoarder sync replies [--count N] [--all]

# Sync tweets + reposts in a single efficient API call
tweethoarder sync posts [--count N] [--all]

# Sync home timeline (Following feed)
tweethoarder sync feed [--hours N]  # Default: last 24 hours

# Sync with thread expansion (archives full threads for each tweet)
tweethoarder sync likes --with-threads [--thread-mode thread|conversation]
```

### Thread Commands

```bash
# Fetch thread for a specific tweet (author's chain only)
tweethoarder thread 1234567890

# Fetch full conversation including all replies
tweethoarder thread 1234567890 --mode conversation --limit 200
```

**Thread vs Conversation:**
- **Thread**: Same author's self-reply chain (classic "tweetstorm")
- **Conversation**: All tweets in the discussion, including other participants

### Export Commands

```bash
# Export to JSON
tweethoarder export json [--collection TYPE] [--output PATH]

# Export to Markdown (thread-aware with quote tweet support)
tweethoarder export markdown [--collection TYPE] [--output PATH]

# Export to CSV
tweethoarder export csv [--collection TYPE] [--output PATH]

# Export specific bookmark folder
tweethoarder export json --collection bookmarks --folder "Work"

# Export to HTML (Twitter-style viewer)
tweethoarder export html [--collection TYPE] [--output PATH]

# Combined export with all collection types
tweethoarder export html --collection all
```

**Collection types**: `likes`, `bookmarks`, `tweets`, `reposts`, `replies`, `posts`, `all`

### HTML Export Features

The HTML export generates a single-file Twitter-style viewer:

- **Theme switcher**: Toggle between light and dark modes
- **Virtual scrolling**: Smoothly handles thousands of tweets
- **Search & filter**: Full-text search with author filters
- **Type filtering**: When using `--collection all`, filter by likes/bookmarks/tweets/etc.
- **Copy as Markdown**: Click any tweet to copy as formatted markdown
- **Quote tweets**: Visual display of quoted tweets with proper attribution
- **Media support**: Embedded images with expandable views
- **Clickable links**: @mentions link to Twitter profiles, URLs are clickable

### Utility Commands

```bash
# Show sync statistics
tweethoarder stats

# Force refresh Twitter API query IDs
tweethoarder refresh-ids

# View/modify configuration
tweethoarder config show
tweethoarder config set sync.default_tweet_count 500
```

## Authentication

TweetHoarder automatically extracts cookies from your browser. Priority order:

1. **Environment variables**: `TWITTER_AUTH_TOKEN`, `TWITTER_CT0`, `TWITTER_TWID`
2. **Config file**: `~/.config/tweethoarder/config.toml`
3. **Firefox**: Auto-detect from `~/.mozilla/firefox/*/cookies.sqlite`
4. **Chrome**: Auto-detect with keyring decryption

### Manual Cookie Setup

If auto-detection fails, you can set cookies manually:

```bash
# Via environment variables
export TWITTER_AUTH_TOKEN="your_auth_token"
export TWITTER_CT0="your_ct0_token"

# Or in config file (~/.config/tweethoarder/config.toml)
[auth]
auth_token = "your_auth_token"
ct0 = "your_ct0_token"
```

To find your cookies:
1. Open Twitter/X in your browser
2. Open Developer Tools (F12) > Application > Cookies
3. Copy values for `auth_token` and `ct0`

## Data Storage

All data is stored in SQLite at `~/.local/share/tweethoarder/tweethoarder.db`

### Database Schema

- **tweets**: All tweet content and metadata (including quote tweets)
- **collections**: Which tweets belong to which collection (likes, bookmarks, tweets, reposts, replies, feed)
- **threads**: Thread/conversation metadata
- **sync_progress**: Checkpoints for resumable syncs

### Example Queries

```sql
-- Find all liked tweets from a specific author
SELECT t.* FROM tweets t
JOIN collections c ON t.id = c.tweet_id
WHERE c.collection_type = 'like' AND t.author_username = 'elonmusk';

-- Get highly-engaged tweets in your likes
SELECT t.*, (t.like_count + t.retweet_count) as engagement
FROM tweets t
JOIN collections c ON t.id = c.tweet_id
WHERE c.collection_type = 'like'
ORDER BY engagement DESC LIMIT 50;

-- Get recent tweets from your home feed
SELECT t.* FROM tweets t
JOIN collections c ON t.id = c.tweet_id
WHERE c.collection_type = 'feed'
ORDER BY t.created_at DESC LIMIT 100;
```

See [SPEC.md](SPEC.md) for comprehensive SQL query examples.

## Configuration

Config file location: `~/.config/tweethoarder/config.toml`

```toml
[auth]
cookie_sources = ["firefox", "chrome"]  # Priority order

[sync]
default_tweet_count = 100
request_delay_ms = 500
max_retries = 5

[export]
export_dir = "~/tweethoarder-exports"

[display]
show_progress = true
verbose = false
```

## Development

### Setup

```bash
# Install dependencies
just setup

# Or manually:
uv sync --dev
uv run prek install
```

### Commands

```bash
just test          # Run tests
just lint          # Check code quality
just format        # Format code
just ci            # Run full CI pipeline
```

### Project Structure

```
tweethoarder/
├── src/tweethoarder/
│   ├── cli/           # Typer CLI commands
│   ├── client/        # Twitter API client
│   ├── auth/          # Cookie extraction
│   ├── query_ids/     # Query ID management
│   ├── storage/       # SQLite database
│   └── export/        # Export formatters
├── tests/             # Unit tests
├── SPEC.md            # Detailed specification
└── CLAUDE.md          # Development guidelines
```

## How It Works

TweetHoarder uses Twitter's internal GraphQL API (the same one the web app uses):

1. **Authentication**: Extracts session cookies from your browser
2. **Query IDs**: Discovers Twitter's rotating GraphQL operation IDs from JS bundles
3. **Fetching**: Paginates through your likes/bookmarks/tweets with rate limiting
4. **Storage**: Saves everything to SQLite with full metadata
5. **Export**: Generates various output formats for offline viewing

The architecture is ported from [bird](https://github.com/steipete/bird), a TypeScript Twitter client.

## Troubleshooting

### "Cookie extraction failed"

- Make sure you're logged into Twitter in your browser
- Try closing the browser completely before running
- For Chrome, ensure GNOME Keyring or KDE Wallet is accessible

### "Query ID not found" / 404 errors

Twitter periodically rotates their API identifiers. Run:
```bash
tweethoarder refresh-ids
```

### Rate limiting

TweetHoarder uses adaptive rate limiting. If you hit limits:
- Wait a few minutes and retry (syncs auto-resume from checkpoint)
- Increase `request_delay_ms` in config for slower but safer syncing

## License

MIT

## Acknowledgments

- [bird](https://github.com/steipete/bird) - TypeScript Twitter client (reference implementation)
- [python-copier-template](https://github.com/tfriedel/python-copier-template) - Project template
