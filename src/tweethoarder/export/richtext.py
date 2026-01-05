"""Rich text formatting utilities for Note tweets.

Handles extraction and application of rich text formatting (bold, italic)
from Twitter Notes' richtext_tags structure.
"""

import json
from typing import Any


def extract_richtext_tags(raw_json: str | None) -> list[dict[str, Any]] | None:
    """Extract richtext_tags from raw_json if available.

    Args:
        raw_json: The raw JSON string from the Twitter API response.

    Returns:
        List of richtext_tags dictionaries, or None if not available.
        Each tag has: from_index, to_index, richtext_types (list of "Bold", "Italic", etc.)
    """
    if not raw_json:
        return None

    try:
        data = json.loads(raw_json)
        note_tweet = data.get("note_tweet", {}).get("note_tweet_results", {}).get("result", {})
        richtext = note_tweet.get("richtext", {})
        tags = richtext.get("richtext_tags")
        if tags is None:
            return None
        return list(tags)  # Explicit conversion to satisfy type checker
    except (json.JSONDecodeError, TypeError, AttributeError):
        return None


def apply_richtext_tags_markdown(text: str, tags: list[dict[str, Any]] | None) -> str:
    """Apply rich text formatting tags to text for Markdown output.

    Args:
        text: The plain text to format.
        tags: List of richtext_tags from the Twitter API.
            Each tag has: from_index, to_index, richtext_types

    Returns:
        Text with Markdown formatting applied (**bold**, *italic*).
    """
    if not tags:
        return text

    # Sort tags by from_index in reverse order to avoid index shifting
    sorted_tags = sorted(tags, key=lambda t: t.get("from_index", 0), reverse=True)

    result = text
    for tag in sorted_tags:
        from_idx = tag.get("from_index", 0)
        to_idx = tag.get("to_index", 0)
        types = tag.get("richtext_types", [])

        # Skip invalid indices
        if from_idx >= to_idx or to_idx > len(result) or from_idx < 0:
            continue

        segment = result[from_idx:to_idx]

        # Apply formatting (italic first, then bold wraps around)
        if "Italic" in types:
            segment = f"*{segment}*"
        if "Bold" in types:
            segment = f"**{segment}**"

        result = result[:from_idx] + segment + result[to_idx:]

    return result


def apply_richtext_tags_html(text: str, tags: list[dict[str, Any]] | None) -> str:
    """Apply rich text formatting tags to text for HTML output.

    Args:
        text: The plain text to format.
        tags: List of richtext_tags from the Twitter API.
            Each tag has: from_index, to_index, richtext_types

    Returns:
        Text with HTML formatting applied (<strong>, <em>).
    """
    if not tags:
        return text

    # Sort tags by from_index in reverse order to avoid index shifting
    sorted_tags = sorted(tags, key=lambda t: t.get("from_index", 0), reverse=True)

    result = text
    for tag in sorted_tags:
        from_idx = tag.get("from_index", 0)
        to_idx = tag.get("to_index", 0)
        types = tag.get("richtext_types", [])

        # Skip invalid indices
        if from_idx >= to_idx or to_idx > len(result) or from_idx < 0:
            continue

        segment = result[from_idx:to_idx]

        # Apply formatting (italic first, then bold wraps around)
        if "Italic" in types:
            segment = f"<em>{segment}</em>"
        if "Bold" in types:
            segment = f"<strong>{segment}</strong>"

        result = result[:from_idx] + segment + result[to_idx:]

    return result
