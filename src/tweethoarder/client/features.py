"""GraphQL feature flag builders for Twitter API requests.

Feature flags are derived from the bird reference implementation
(~/projects/bird/src/lib/twitter-client-features.ts).
"""


def build_timeline_features() -> dict[str, bool]:
    """Build feature flags for timeline requests (bookmarks, likes, etc.).

    These flags match what Twitter's web client sends. Missing flags cause 404 errors.
    """
    return {
        "rweb_video_screen_enabled": True,
        "profile_label_improvements_pcf_label_in_post_enabled": True,
        "responsive_web_profile_redirect_enabled": True,
        "rweb_tipjar_consumption_enabled": True,
        "verified_phone_label_enabled": False,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "premium_content_api_read_enabled": False,
        "communities_web_enable_tweet_community_results_fetch": True,
        "c9s_tweet_anatomy_moderator_badge_enabled": True,
        "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
        "responsive_web_grok_analyze_post_followups_enabled": False,
        "responsive_web_jetfuel_frame": True,
        "responsive_web_grok_share_attachment_enabled": True,
        "responsive_web_grok_annotations_enabled": True,
        "articles_preview_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_twitter_article_tweet_consumption_enabled": True,
        "tweet_awards_web_tipping_enabled": False,
        "responsive_web_grok_show_grok_translated_post": False,
        "responsive_web_grok_analysis_button_from_backend": True,
        "creator_subscriptions_quote_tweet_preview_enabled": False,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": True,
        "responsive_web_grok_image_annotation_enabled": True,
        "responsive_web_grok_imagine_annotation_enabled": True,
        "responsive_web_grok_community_note_auto_translation_is_enabled": False,
        "responsive_web_enhance_cards_enabled": False,
        # Additional flags from bird's buildTimelineFeatures (extends buildSearchFeatures)
        "responsive_web_graphql_exclude_directive_enabled": True,
        "rweb_video_timestamps_enabled": True,
        "blue_business_profile_image_shape_enabled": True,
        "responsive_web_text_conversations_enabled": False,
        "tweetypie_unmention_optimization_enabled": True,
        "vibe_api_enabled": True,
        "responsive_web_twitter_blue_verified_badge_is_enabled": True,
        "interactive_text_enabled": True,
        "longform_notetweets_richtext_consumption_enabled": True,
        "responsive_web_media_download_video_enabled": False,
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


def build_tweet_detail_features() -> dict[str, bool]:
    """Build feature flags for TweetDetail requests."""
    return build_timeline_features()


def build_user_tweets_features() -> dict[str, bool]:
    """Build feature flags for UserTweets and UserTweetsAndReplies requests."""
    return build_timeline_features()
