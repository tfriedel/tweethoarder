"""Tests for rich text formatting utilities."""

import json

from tweethoarder.export.richtext import (
    apply_richtext_tags_html,
    apply_richtext_tags_markdown,
    extract_richtext_tags,
)


class TestApplyRichtextTagsMarkdown:
    """Tests for apply_richtext_tags_markdown function."""

    def test_returns_text_unchanged_when_no_tags(self) -> None:
        """Text should be returned unchanged when tags is None."""
        text = "Hello world"
        result = apply_richtext_tags_markdown(text, None)
        assert result == "Hello world"

    def test_returns_text_unchanged_when_empty_tags(self) -> None:
        """Text should be returned unchanged when tags list is empty."""
        text = "Hello world"
        result = apply_richtext_tags_markdown(text, [])
        assert result == "Hello world"

    def test_applies_bold_formatting(self) -> None:
        """Bold tags should wrap text in ** markers."""
        text = "Hello world"
        tags = [{"from_index": 0, "to_index": 5, "richtext_types": ["Bold"]}]
        result = apply_richtext_tags_markdown(text, tags)
        assert result == "**Hello** world"

    def test_applies_italic_formatting(self) -> None:
        """Italic tags should wrap text in * markers."""
        text = "Hello world"
        tags = [{"from_index": 6, "to_index": 11, "richtext_types": ["Italic"]}]
        result = apply_richtext_tags_markdown(text, tags)
        assert result == "Hello *world*"

    def test_applies_multiple_tags(self) -> None:
        """Multiple tags should all be applied correctly."""
        text = "Hello world today"
        tags = [
            {"from_index": 0, "to_index": 5, "richtext_types": ["Bold"]},
            {"from_index": 12, "to_index": 17, "richtext_types": ["Italic"]},
        ]
        result = apply_richtext_tags_markdown(text, tags)
        assert result == "**Hello** world *today*"

    def test_applies_bold_and_italic_together(self) -> None:
        """Text with both Bold and Italic should get both markers."""
        text = "Hello world"
        tags = [{"from_index": 0, "to_index": 5, "richtext_types": ["Bold", "Italic"]}]
        result = apply_richtext_tags_markdown(text, tags)
        # Order: italic first, then bold wraps around it
        assert result == "***Hello*** world"

    def test_handles_overlapping_tags(self) -> None:
        """Adjacent/overlapping tags should be handled correctly."""
        text = "Hello world"
        tags = [
            {"from_index": 0, "to_index": 5, "richtext_types": ["Bold"]},
            {"from_index": 6, "to_index": 11, "richtext_types": ["Bold"]},
        ]
        result = apply_richtext_tags_markdown(text, tags)
        assert result == "**Hello** **world**"

    def test_ignores_invalid_indices(self) -> None:
        """Tags with invalid indices should be ignored."""
        text = "Hello"
        tags = [
            {"from_index": 10, "to_index": 15, "richtext_types": ["Bold"]},  # Beyond text
            {"from_index": 5, "to_index": 3, "richtext_types": ["Bold"]},  # Reversed
        ]
        result = apply_richtext_tags_markdown(text, tags)
        assert result == "Hello"


class TestApplyRichtextTagsHtml:
    """Tests for apply_richtext_tags_html function."""

    def test_returns_text_unchanged_when_no_tags(self) -> None:
        """Text should be returned unchanged when tags is None."""
        text = "Hello world"
        result = apply_richtext_tags_html(text, None)
        assert result == "Hello world"

    def test_applies_bold_formatting(self) -> None:
        """Bold tags should wrap text in <strong> tags."""
        text = "Hello world"
        tags = [{"from_index": 0, "to_index": 5, "richtext_types": ["Bold"]}]
        result = apply_richtext_tags_html(text, tags)
        assert result == "<strong>Hello</strong> world"

    def test_applies_italic_formatting(self) -> None:
        """Italic tags should wrap text in <em> tags."""
        text = "Hello world"
        tags = [{"from_index": 6, "to_index": 11, "richtext_types": ["Italic"]}]
        result = apply_richtext_tags_html(text, tags)
        assert result == "Hello <em>world</em>"

    def test_applies_bold_and_italic_together(self) -> None:
        """Text with both Bold and Italic should get both tags."""
        text = "Hello world"
        tags = [{"from_index": 0, "to_index": 5, "richtext_types": ["Bold", "Italic"]}]
        result = apply_richtext_tags_html(text, tags)
        assert result == "<strong><em>Hello</em></strong> world"


class TestExtractRichtextTags:
    """Tests for extract_richtext_tags function."""

    def test_returns_none_when_raw_json_is_none(self) -> None:
        """Should return None when raw_json is None."""
        result = extract_richtext_tags(None)
        assert result is None

    def test_returns_none_when_no_note_tweet(self) -> None:
        """Should return None when raw_json has no note_tweet."""
        raw_json = json.dumps({"legacy": {"full_text": "Hello"}})
        result = extract_richtext_tags(raw_json)
        assert result is None

    def test_returns_none_when_no_richtext_tags(self) -> None:
        """Should return None when note_tweet has no richtext_tags."""
        raw_json = json.dumps(
            {
                "note_tweet": {
                    "note_tweet_results": {
                        "result": {
                            "text": "Hello",
                            "entity_set": {"hashtags": [], "urls": []},
                        }
                    }
                }
            }
        )
        result = extract_richtext_tags(raw_json)
        assert result is None

    def test_extracts_richtext_tags_from_valid_structure(self) -> None:
        """Should extract richtext_tags when present in the expected location."""
        expected_tags = [
            {"from_index": 0, "to_index": 5, "richtext_types": ["Bold"]},
            {"from_index": 10, "to_index": 15, "richtext_types": ["Italic"]},
        ]
        raw_json = json.dumps(
            {
                "note_tweet": {
                    "note_tweet_results": {
                        "result": {
                            "text": "Hello world today",
                            "richtext": {"richtext_tags": expected_tags},
                        }
                    }
                }
            }
        )
        result = extract_richtext_tags(raw_json)
        assert result == expected_tags

    def test_handles_malformed_json_gracefully(self) -> None:
        """Should return None for malformed JSON."""
        result = extract_richtext_tags("not valid json")
        assert result is None
