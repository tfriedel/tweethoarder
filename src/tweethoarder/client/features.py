"""GraphQL feature flag builders for Twitter API requests."""


def build_timeline_features() -> dict[str, bool]:
    """Build feature flags for timeline requests (bookmarks, likes, etc.)."""
    return {
        "rweb_video_screen_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
    }


def build_bookmarks_features() -> dict[str, bool]:
    """Build feature flags for bookmarks requests."""
    return {
        **build_timeline_features(),
        "graphql_timeline_v2_bookmark_timeline": True,
    }


def build_likes_features() -> dict[str, bool]:
    """Build feature flags for likes requests."""
    return build_timeline_features()
