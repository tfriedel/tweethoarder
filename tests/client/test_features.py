"""Tests for GraphQL feature flag builders."""


def test_build_timeline_features_returns_dict_of_booleans() -> None:
    """build_timeline_features should return a dict with boolean values."""
    from tweethoarder.client.features import build_timeline_features

    features = build_timeline_features()

    assert isinstance(features, dict)
    assert all(isinstance(v, bool) for v in features.values())


def test_build_timeline_features_includes_required_flags() -> None:
    """build_timeline_features should include essential feature flags."""
    from tweethoarder.client.features import build_timeline_features

    features = build_timeline_features()

    # Check essential flags that Twitter API requires
    essential_flags = [
        "rweb_video_screen_enabled",
        "view_counts_everywhere_api_enabled",
        "longform_notetweets_consumption_enabled",
        "responsive_web_graphql_timeline_navigation_enabled",
    ]
    for flag in essential_flags:
        assert flag in features, f"Missing essential flag: {flag}"


def test_build_bookmarks_features_extends_timeline() -> None:
    """build_bookmarks_features should include timeline features plus bookmark-specific ones."""
    from tweethoarder.client.features import build_bookmarks_features

    features = build_bookmarks_features()

    # Should include timeline features
    assert "rweb_video_screen_enabled" in features
    # Should include bookmark-specific flag
    assert features.get("graphql_timeline_v2_bookmark_timeline") is True


def test_build_likes_features_includes_required_twitter_flags() -> None:
    """build_likes_features should include all flags required by Twitter API."""
    from tweethoarder.client.features import build_likes_features

    features = build_likes_features()

    # These flags are required by Twitter's GraphQL API (from bird reference implementation)
    required_flags = [
        "rweb_video_screen_enabled",
        "profile_label_improvements_pcf_label_in_post_enabled",
        "rweb_tipjar_consumption_enabled",
        "creator_subscriptions_tweet_preview_api_enabled",
        "responsive_web_graphql_timeline_navigation_enabled",
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled",
        "communities_web_enable_tweet_community_results_fetch",
        "c9s_tweet_anatomy_moderator_badge_enabled",
        "articles_preview_enabled",
        "responsive_web_edit_tweet_api_enabled",
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled",
        "view_counts_everywhere_api_enabled",
        "longform_notetweets_consumption_enabled",
        "responsive_web_twitter_article_tweet_consumption_enabled",
        "freedom_of_speech_not_reach_fetch_enabled",
        "standardized_nudges_misinfo",
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled",
        "longform_notetweets_rich_text_read_enabled",
        "longform_notetweets_inline_media_enabled",
        "responsive_web_enhance_cards_enabled",
        "responsive_web_profile_redirect_enabled",
    ]
    for flag in required_flags:
        assert flag in features, f"Missing required flag: {flag}"

    # Should have many more flags than before (was only 4, now ~30+)
    assert len(features) >= 20, f"Expected at least 20 features, got {len(features)}"


def test_build_tweet_detail_features_exists() -> None:
    """build_tweet_detail_features function should be importable."""
    from tweethoarder.client.features import build_tweet_detail_features

    assert callable(build_tweet_detail_features)
