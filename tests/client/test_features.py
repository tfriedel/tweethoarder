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


def test_build_likes_features_uses_timeline() -> None:
    """build_likes_features should use timeline features."""
    from tweethoarder.client.features import build_likes_features, build_timeline_features

    likes_features = build_likes_features()
    timeline_features = build_timeline_features()

    # Likes should have same features as timeline
    assert likes_features == timeline_features
