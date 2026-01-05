"""Twitter API constants and fallback query IDs."""

TWITTER_API_BASE = "https://x.com/i/api/graphql"

DEFAULT_TTL_SECONDS = 24 * 60 * 60  # 24 hours

DISCOVERY_PAGES = [
    "https://x.com/?lang=en",
    "https://x.com/explore",
    "https://x.com/notifications",
    "https://x.com/settings/profile",
]

BUNDLE_URL_PATTERN = (
    r"https://abs\.twimg\.com/responsive-web/client-web(?:-legacy)?/[A-Za-z0-9.-]+\.js"
)

QUERY_ID_PATTERN = r"^[a-zA-Z0-9_-]+$"

FALLBACK_QUERY_IDS: dict[str, str] = {
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
}

TARGET_QUERY_ID_OPERATIONS: list[str] = list(FALLBACK_QUERY_IDS.keys())
