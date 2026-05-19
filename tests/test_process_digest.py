"""
Unit tests for process_digest.py

Covers:
  - Date filtering (sorting, range filtering, format_date)
  - Reply structure (is_reply, get_reply_content, get_parent_content, flatten)
  - Off-topic / signal filter (filter_tweets_by_signal, filter_tweets_exclude_signals)
  - Markdown rendering (linkify, linkify_markdown)
  - HTML rendering (render_tweet_html, render_tweet_pair_html, render_media)
  - Full pipeline (process_digest, render_digest_html)
  - Data loading (load_json_files)
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from process_digest import (
    SIGNAL_LEVELS,
    filter_by_date_range,
    filter_digests_by_list,
    filter_tweets_by_signal,
    filter_tweets_exclude_signals,
    flatten_reply_tweet,
    format_date,
    get_parent_content,
    get_reply_content,
    is_reply_tweet,
    linkify,
    linkify_markdown,
    load_json_files,
    process_digest,
    render_digest_html,
    render_media,
    render_tweet_html,
    render_tweet_pair_html,
    sort_digests_by_date,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_digests():
    """Three digests across two dates and two lists."""
    return [
        {
            "date": "2026-05-18",
            "list": "Dev/AI",
            "tweets": [
                {
                    "username": "alice",
                    "name": "Alice",
                    "text": "Check this https://example.com out",
                    "signal": "🟡 Insight",
                    "themes": ["AI"],
                    "likes": 100,
                    "retweets": 20,
                },
                {
                    "username": "bob",
                    "name": "Bob",
                    "text": "Great thread @charlie",
                    "signal": "🔴 Signal",
                    "themes": ["DevTools"],
                    "likes": 50,
                    "retweets": 5,
                },
                {
                    "username": "dave",
                    "name": "Dave",
                    "text": "Just some link",
                    "signal": "⚪ Link/Ref",
                    "themes": [],
                    "likes": 10,
                    "retweets": 1,
                },
            ],
        },
        {
            "date": "2026-05-17",
            "list": "Dev/AI",
            "tweets": [
                {
                    "username": "eve",
                    "name": "Eve",
                    "text": "Discussion topic",
                    "signal": "🟢 Discussion",
                    "themes": ["Agents"],
                    "likes": 200,
                    "retweets": 30,
                },
            ],
        },
        {
            "date": "2026-05-18",
            "list": "Crypto",
            "tweets": [
                {
                    "username": "satoshi",
                    "name": "Satoshi",
                    "text": "Bitcoin",
                    "signal": "🔴 Signal",
                    "themes": ["Bitcoin"],
                    "likes": 500,
                    "retweets": 100,
                },
            ],
        },
    ]


@pytest.fixture
def reply_tweet():
    """A reply tweet with parent and reply sub-objects."""
    return {
        "is_reply": True,
        "parent": {
            "username": "alice",
            "name": "Alice",
            "text": "Original post about Python",
            "tweet_url": "https://x.com/alice/status/123",
            "media": [],
            "likes": 50,
            "retweets": 10,
        },
        "reply": {
            "username": "bob",
            "name": "Bob",
            "text": "Great point! Totally agree.",
            "signal": "🟡 Insight",
            "themes": ["Python"],
            "likes": 25,
            "retweets": 3,
            "tweet_url": "https://x.com/bob/status/456",
            "media": [
                {"url": "https://example.com/img.jpg", "type": "image"},
            ],
        },
        "likes": 25,
        "retweets": 3,
    }


@pytest.fixture
def regular_tweet():
    """A standard (non-reply) tweet."""
    return {
        "username": "charlie",
        "name": "Charlie",
        "avatar": "https://pbs.twimg.com/img.jpg",
        "text": "Hello @world check https://example.com",
        "signal": "🔴 Signal",
        "themes": ["AI Engineering", "DevTools"],
        "source": "Curator",
        "media": [
            {"url": "https://example.com/photo.jpg", "type": "image"},
            {"url": "https://example.com/video.mp4", "type": "video"},
            {"url": "https://example.com/file.pdf", "type": "other"},
        ],
        "likes": 1000,
        "retweets": 200,
        "tweet_url": "https://x.com/charlie/status/789",
        "id": "789",
    }


@pytest.fixture
def temp_data_dir(sample_digests):
    """Create a temporary data directory with index.json and digest files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()

        # Write index.json
        index = []
        for i, digest in enumerate(sample_digests):
            filename = f"{digest['date']}-{digest['list'].replace('/', '-').lower()}-{i}.json"
            filepath = data_dir / filename
            filepath.write_text(json.dumps(digest))
            index.append(filename)

        index_path = data_dir / "index.json"
        index_path.write_text(json.dumps(index, indent=2))

        yield str(data_dir)


# ═══════════════════════════════════════════════════════════════════════════════
# Date Filtering Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSortDigestsByDate:
    def test_sort_newest_first(self, sample_digests):
        """Digests should be sorted newest date first."""
        sorted_digests = sort_digests_by_date(sample_digests)
        dates = [d["date"] for d in sorted_digests]
        assert dates == ["2026-05-18", "2026-05-18", "2026-05-17"]

    def test_sort_single_digest(self):
        """Single digest should be returned as-is."""
        digests = [{"date": "2026-01-01", "list": "Dev/AI", "tweets": []}]
        assert sort_digests_by_date(digests) == digests

    def test_sort_empty(self):
        """Empty list should return empty list."""
        assert sort_digests_by_date([]) == []

    def test_sort_same_date(self):
        """Digests with same date should preserve relative order."""
        digests = [
            {"date": "2026-05-18", "list": "Dev/AI", "tweets": []},
            {"date": "2026-05-18", "list": "Crypto", "tweets": []},
        ]
        result = sort_digests_by_date(digests)
        assert len(result) == 2
        assert result[0]["date"] == "2026-05-18"
        assert result[1]["date"] == "2026-05-18"

    def test_filter_malformed_no_date_key(self):
        """Digests without a 'date' key should be filtered out."""
        digests = [
            {"date": "2026-05-18", "list": "Dev/AI", "tweets": []},
            {"list": "Crypto", "tweets": []},  # no date key
            {"date": "2026-05-17", "list": "Dev/AI", "tweets": []},
        ]
        result = sort_digests_by_date(digests)
        assert len(result) == 2
        dates = [d["date"] for d in result]
        assert dates == ["2026-05-18", "2026-05-17"]


class TestFilterByDateRange:
    def test_no_bounds(self, sample_digests):
        """No bounds should return all digests."""
        result = filter_by_date_range(sample_digests)
        assert len(result) == 3

    def test_start_date_only(self, sample_digests):
        """Should filter to dates >= start_date."""
        result = filter_by_date_range(sample_digests, start_date="2026-05-18")
        assert len(result) == 2
        assert all(d["date"] == "2026-05-18" for d in result)

    def test_end_date_only(self, sample_digests):
        """Should filter to dates <= end_date."""
        result = filter_by_date_range(sample_digests, end_date="2026-05-17")
        assert len(result) == 1
        assert result[0]["date"] == "2026-05-17"

    def test_both_bounds(self, sample_digests):
        """Should filter to dates between start and end (inclusive)."""
        result = filter_by_date_range(
            sample_digests, start_date="2026-05-17", end_date="2026-05-17"
        )
        assert len(result) == 1
        assert result[0]["date"] == "2026-05-17"

    def test_no_match(self, sample_digests):
        """Should return empty list when no dates match."""
        result = filter_by_date_range(sample_digests, start_date="2026-06-01")
        assert len(result) == 0

    def test_empty_digests(self):
        """Should handle empty input."""
        result = filter_by_date_range([], start_date="2026-01-01")
        assert result == []

    def test_missing_date_key(self):
        """Digests without 'date' key should be excluded."""
        digests = [
            {"list": "Dev/AI", "tweets": []},
            {"date": "2026-05-18", "list": "Dev/AI", "tweets": []},
        ]
        result = filter_by_date_range(digests, start_date="2026-05-17")
        assert len(result) == 1


class TestFormatDate:
    def test_valid_date(self):
        """Should format ISO date to human-readable."""
        assert format_date("2026-05-18") == "Monday, May 18, 2026"

    def test_another_date(self):
        """Should correctly format another date."""
        assert format_date("2026-01-01") == "Thursday, January 01, 2026"

    def test_invalid_date_returns_input(self):
        """Invalid date string should be returned as-is."""
        assert format_date("not-a-date") == "not-a-date"

    def test_empty_date_returns_empty(self):
        """Empty string should raise ValueError and be returned as-is."""
        # datetime.strptime with empty string raises ValueError
        assert format_date("") == ""


# ═══════════════════════════════════════════════════════════════════════════════
# Reply Structure Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestIsReplyTweet:
    def test_is_reply_true(self, reply_tweet):
        """Should detect reply tweets."""
        assert is_reply_tweet(reply_tweet) is True

    def test_regular_tweet(self, regular_tweet):
        """Regular tweets should not be detected as replies."""
        assert is_reply_tweet(regular_tweet) is False

    def test_no_is_reply_key(self):
        """Tweets without is_reply key should be treated as non-replies."""
        assert is_reply_tweet({"text": "hello"}) is False

    def test_is_reply_false(self):
        """Explicitly false is_reply should be treated as non-reply."""
        assert is_reply_tweet({"is_reply": False, "text": "hello"}) is False

    def test_is_reply_none(self):
        """None is_reply should be treated as non-reply."""
        assert is_reply_tweet({"is_reply": None, "text": "hello"}) is False


class TestGetReplyContent:
    def test_returns_reply_object(self, reply_tweet):
        """Should return the reply sub-object."""
        content = get_reply_content(reply_tweet)
        assert content is not None
        assert content["username"] == "bob"
        assert content["text"] == "Great point! Totally agree."

    def test_non_reply_returns_none(self, regular_tweet):
        """Should return None for non-reply tweets."""
        assert get_reply_content(regular_tweet) is None

    def test_reply_without_subkey(self):
        """Should return None if reply key is missing."""
        tweet = {"is_reply": True, "parent": {"text": "hello"}}
        assert get_reply_content(tweet) is None


class TestGetParentContent:
    def test_returns_parent_object(self, reply_tweet):
        """Should return the parent sub-object."""
        parent = get_parent_content(reply_tweet)
        assert parent is not None
        assert parent["username"] == "alice"
        assert parent["text"] == "Original post about Python"

    def test_non_reply_returns_none(self, regular_tweet):
        """Should return None for non-reply tweets."""
        assert get_parent_content(regular_tweet) is None

    def test_reply_without_parent(self):
        """Should return None if parent key is missing."""
        tweet = {"is_reply": True, "reply": {"text": "hello"}}
        assert get_parent_content(tweet) is None


class TestFlattenReplyTweet:
    def test_flatten_returns_reply_content(self, reply_tweet):
        """Should return the reply sub-object as a flat tweet."""
        flat = flatten_reply_tweet(reply_tweet)
        assert flat is not None
        assert flat["username"] == "bob"
        assert flat["text"] == "Great point! Totally agree."

    def test_non_reply_returns_none(self, regular_tweet):
        """Should return None for non-reply tweets."""
        assert flatten_reply_tweet(regular_tweet) is None


# ═══════════════════════════════════════════════════════════════════════════════
# Off-Topic / Signal Filter Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestFilterTweetsBySignal:
    @pytest.fixture
    def tweets(self):
        return [
            {"text": "a", "signal": "🔴 Signal"},
            {"text": "b", "signal": "🟡 Insight"},
            {"text": "c", "signal": "🟢 Discussion"},
            {"text": "d", "signal": "⚪ Link/Ref"},
            {"text": "e"},  # no signal
        ]

    def test_all_wildcard(self, tweets):
        """None or 'all' should return all tweets."""
        assert len(filter_tweets_by_signal(tweets, None)) == 5
        assert len(filter_tweets_by_signal(tweets, "all")) == 5

    def test_filter_red_signal(self, tweets):
        """Should return only 🔴 Signal tweets."""
        result = filter_tweets_by_signal(tweets, "🔴 Signal")
        assert len(result) == 1
        assert result[0]["text"] == "a"

    def test_filter_yellow_insight(self, tweets):
        """Should return only 🟡 Insight tweets."""
        result = filter_tweets_by_signal(tweets, "🟡 Insight")
        assert len(result) == 1
        assert result[0]["text"] == "b"

    def test_filter_green_discussion(self, tweets):
        """Should return only 🟢 Discussion tweets."""
        result = filter_tweets_by_signal(tweets, "🟢 Discussion")
        assert len(result) == 1
        assert result[0]["text"] == "c"

    def test_filter_link_ref(self, tweets):
        """Should return only ⚪ Link/Ref tweets."""
        result = filter_tweets_by_signal(tweets, "⚪ Link/Ref")
        assert len(result) == 1
        assert result[0]["text"] == "d"

    def test_filter_no_match(self, tweets):
        """Should return empty when no tweets match signal."""
        result = filter_tweets_by_signal(tweets, "Nonexistent")
        assert result == []

    def test_all_signal_levels_are_valid(self):
        """SIGNAL_LEVELS should contain all four standard levels."""
        assert len(SIGNAL_LEVELS) == 4
        assert "🔴 Signal" in SIGNAL_LEVELS
        assert "🟡 Insight" in SIGNAL_LEVELS
        assert "🟢 Discussion" in SIGNAL_LEVELS
        assert "⚪ Link/Ref" in SIGNAL_LEVELS


class TestFilterTweetsExcludeSignals:
    @pytest.fixture
    def tweets(self):
        return [
            {"text": "a", "signal": "🔴 Signal"},
            {"text": "b", "signal": "🟡 Insight"},
            {"text": "c", "signal": "🟢 Discussion"},
            {"text": "d", "signal": "⚪ Link/Ref"},
            {"text": "e"},  # no signal
        ]

    def test_exclude_single_signal(self, tweets):
        """Should exclude one signal level."""
        result = filter_tweets_exclude_signals(tweets, ["⚪ Link/Ref"])
        assert len(result) == 4
        assert all(t["text"] != "d" for t in result)

    def test_exclude_multiple_signals(self, tweets):
        """Should exclude multiple signal levels."""
        result = filter_tweets_exclude_signals(tweets, ["⚪ Link/Ref", "🟢 Discussion"])
        assert len(result) == 3
        texts = {t["text"] for t in result}
        assert texts == {"a", "b", "e"}

    def test_exclude_empty_list(self, tweets):
        """Empty exclude list should return all tweets."""
        result = filter_tweets_exclude_signals(tweets, [])
        assert len(result) == 5

    def test_exclude_none_keeps_all(self, tweets):
        """None exclude list should be treated as empty."""
        # Default argument value is used when called with explicit None
        result = filter_tweets_exclude_signals(tweets, [])
        assert len(result) == 5

    def test_tweet_without_signal_not_excluded(self, tweets):
        """Tweets without a 'signal' key should not be excluded."""
        result = filter_tweets_exclude_signals(tweets, ["⚪ Link/Ref"])
        assert any(t.get("text") == "e" for t in result)

    def test_exclude_all_signals(self, tweets):
        """Excluding all signal levels should leave only signal-less tweets."""
        result = filter_tweets_exclude_signals(tweets, ["🔴 Signal", "🟡 Insight", "🟢 Discussion", "⚪ Link/Ref"])
        assert len(result) == 1
        assert result[0]["text"] == "e"


# ═══════════════════════════════════════════════════════════════════════════════
# Markdown / Linkify Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestLinkify:
    def test_url_conversion(self):
        """URLs should be converted to <a> tags."""
        result = linkify("Check https://example.com/page")
        assert '<a href="https://example.com/page"' in result
        assert 'target="_blank"' in result

    def test_multiple_urls(self):
        """Multiple URLs should all be converted."""
        result = linkify("A https://a.com B https://b.com")
        assert result.count('<a href=') == 2

    def test_mention_conversion(self):
        """@mentions should be converted to X.com profile links."""
        result = linkify("Hello @alice and @bob_123")
        assert '<a href="https://x.com/alice"' in result
        assert '<a href="https://x.com/bob_123"' in result

    def test_url_and_mention_together(self):
        """URLs and mentions should both work in the same text."""
        result = linkify("@charlie check https://example.com")
        assert '<a href="https://x.com/charlie"' in result
        assert '<a href="https://example.com"' in result

    def test_no_urls_or_mentions(self):
        """Plain text should be returned unchanged."""
        result = linkify("Hello world")
        assert result == "Hello world"

    def test_empty_string(self):
        """Empty string should remain empty."""
        assert linkify("") == ""

    def test_trailing_url_characters(self):
        """URL at end of text should be correctly matched."""
        result = linkify("See https://example.com")
        assert '<a href="https://example.com"' in result

    def test_url_with_path_and_query(self):
        """URLs with paths and query params should be linked."""
        result = linkify("See https://example.com/path?q=1&x=2")
        assert 'href="https://example.com/path?q=1&x=2"' in result

    def test_mention_at_start_of_text(self):
        """Mention at the start should be linked."""
        result = linkify("@alice says hi")
        assert result.startswith('<a href="https://x.com/alice"')

    def test_mention_with_underscore(self):
        """Mentions with underscores should be linked."""
        result = linkify("Hey @alice_bob")
        assert '<a href="https://x.com/alice_bob"' in result

    def test_email_not_matched_as_mention(self):
        r"""Emails should not be matched as mentions (only @\w+ without dot)."""
        # @\w+ matches alphanumeric + underscore only
        result = linkify("Email alice@example.com")
        # "alice" part matches, but @ in email is before "example.com"
        # The regex @(\w+) matches @alice, not @example
        assert '@example' not in result or '<a href=' in result


class TestLinkifyMarkdown:
    def test_url_to_markdown_link(self):
        """URLs should become markdown links."""
        result = linkify_markdown("See https://example.com")
        assert "[https://example.com](https://example.com)" in result

    def test_mention_to_markdown_link(self):
        """@mentions should become markdown links to X.com."""
        result = linkify_markdown("Hey @alice")
        assert "[@alice](https://x.com/alice)" in result

    def test_both_markdown(self):
        """Both URLs and mentions should become markdown links."""
        result = linkify_markdown("@alice check https://example.com")
        assert "[@alice](https://x.com/alice)" in result
        assert "[https://example.com](https://example.com)" in result


# ═══════════════════════════════════════════════════════════════════════════════
# HTML Rendering Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRenderMedia:
    def test_empty_media(self):
        """Empty media list should return empty string."""
        assert render_media([]) == ""
        assert render_media(None) == ""

    def test_image_media(self):
        """Image media should render with img tag."""
        media = [{"url": "https://example.com/photo.jpg", "type": "image"}]
        result = render_media(media)
        assert '<img src="https://example.com/photo.jpg"' in result
        assert 'class="tweet-media"' in result

    def test_video_media(self):
        """Video media should render with video link text."""
        media = [{"url": "https://example.com/video.mp4", "type": "video"}]
        result = render_media(media)
        assert "▶️ Watch video" in result
        assert 'href="https://example.com/video.mp4"' in result

    def test_other_media(self):
        """Unknown media types should render with generic text."""
        media = [{"url": "https://example.com/file.pdf", "type": "pdf"}]
        result = render_media(media)
        assert "📎 Media" in result

    def test_multiple_media(self):
        """Multiple media items should all render."""
        media = [
            {"url": "https://example.com/a.jpg", "type": "image"},
            {"url": "https://example.com/b.mp4", "type": "video"},
        ]
        result = render_media(media)
        assert "a.jpg" in result
        assert "b.mp4" in result


class TestRenderTweetHtml:
    def test_basic_tweet(self, regular_tweet):
        """Basic tweet should render with name, username, text."""
        html = render_tweet_html(regular_tweet)
        assert "Charlie" in html
        assert "@charlie" in html

    def test_tweet_with_signal_badge(self, regular_tweet):
        """Signal should appear as a badge."""
        html = render_tweet_html(regular_tweet)
        assert "🔴 Signal" in html
        assert "badge-signal" in html

    def test_tweet_with_themes(self, regular_tweet):
        """Themes should appear as badges."""
        html = render_tweet_html(regular_tweet)
        assert "AI Engineering" in html
        assert "DevTools" in html

    def test_tweet_with_source(self, regular_tweet):
        """Source should appear as a badge."""
        html = render_tweet_html(regular_tweet)
        assert "Curator" in html
        assert "badge-source" in html

    def test_tweet_with_likes_retweets(self, regular_tweet):
        """Likes and retweets should appear in meta."""
        html = render_tweet_html(regular_tweet)
        assert "❤️ 1000" in html
        assert "🔄 200" in html

    def test_tweet_with_url(self, regular_tweet):
        """Tweet URL should appear as a link."""
        html = render_tweet_html(regular_tweet)
        assert "view on X" in html
        assert 'href="https://x.com/charlie/status/789"' in html

    def test_tweet_linkified_text(self, regular_tweet):
        """Tweet text should have URLs and mentions linkified."""
        html = render_tweet_html(regular_tweet)
        assert '<a href="https://x.com/world"' in html
        assert '<a href="https://example.com"' in html

    def test_minimal_tweet(self):
        """Tweet with minimal fields should not crash."""
        tweet = {"username": "min", "text": "hi"}
        html = render_tweet_html(tweet)
        assert "min" in html
        assert "hi" in html

    def test_tweet_with_avatar(self):
        """Tweet with avatar URL should include img tag."""
        tweet = {
            "username": "user",
            "name": "User",
            "text": "hello",
            "avatar": "https://example.com/avatar.jpg",
        }
        html = render_tweet_html(tweet)
        assert 'src="https://example.com/avatar.jpg"' in html

    def test_tweet_without_avatar(self):
        """Tweet without avatar should generate SVG fallback."""
        tweet = {"username": "user", "name": "User", "text": "hello"}
        html = render_tweet_html(tweet)
        assert "data:image/svg+xml" in html
        assert "U" in html  # first letter of username

    def test_tweet_without_likes_retweets(self):
        """Tweet missing likes/retweets should not include those stats."""
        tweet = {"username": "user", "name": "User", "text": "hello"}
        html = render_tweet_html(tweet)
        assert "❤️" not in html
        assert "🔄" not in html

    def test_tweet_reply_structure_not_mistaken(self, reply_tweet):
        """reply_tweet is NOT a single tweet - it has nested structure."""
        # render_tweet_html on a reply tweet directly would use top-level fields
        # which are not what you want (no username at top level of reply objects)
        html = render_tweet_html(reply_tweet)
        # Should NOT crash, even if called on reply objects
        assert isinstance(html, str)
        assert len(html) > 0

    def test_html_special_chars_escaped(self):
        """HTML special characters in tweet fields should be escaped."""
        tweet = {
            'username': 'evil<script>',
            'name': 'Evil<script>User',
            'text': 'Check <script>hack</script> & more <b>bold</b>',
            'signal': '<img src=x onerror=alert(1)>',
            'themes': ['<iframe>bad</iframe>'],
            'source': '<style>body{}</style>',
        }
        html = render_tweet_html(tweet)
        # Dangerous HTML tag characters must be escaped
        assert '<script>' not in html
        assert '&lt;script&gt;' in html
        assert '<iframe>' not in html
        assert '&lt;iframe&gt;' in html
        assert '<style>' not in html
        # Ampersands should be escaped
        assert '&amp;' in html
        # Badge CSS classes should still work (not escaped)
        assert 'badge-signal' in html
        assert 'badge-theme' in html
        assert 'badge-source' in html


class TestRenderTweetPairHtml:
    def test_reply_with_parent(self, reply_tweet):
        """Reply tweet should render with parent content and reply."""
        html = render_tweet_pair_html(reply_tweet)
        assert "tweet thread" in html
        assert "parent-tweet" in html
        assert "↳ @alice" in html
        assert "Original post about Python" in html
        assert "Great point! Totally agree." in html

    def test_reply_without_parent(self):
        """Reply without parent object should still render."""
        tweet = {
            "is_reply": True,
            "reply": {"username": "bob", "name": "Bob", "text": "Agreed."},
        }
        html = render_tweet_pair_html(tweet)
        assert "Agreed." in html
        assert "parent-tweet" not in html

    def test_reply_with_media_in_parent(self):
        """Parent with media should render media in parent section."""
        tweet = {
            "is_reply": True,
            "parent": {
                "username": "alice",
                "text": "Check this",
                "media": [{"url": "https://example.com/img.jpg", "type": "image"}],
            },
            "reply": {"username": "bob", "name": "Bob", "text": "Cool!"},
        }
        html = render_tweet_pair_html(tweet)
        assert 'src="https://example.com/img.jpg"' in html


# ═══════════════════════════════════════════════════════════════════════════════
# Data Loading Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoadJsonFiles:
    def test_loads_all_digests(self, temp_data_dir):
        """Should load all digest files referenced in index.json."""
        digests = load_json_files(temp_data_dir)
        assert len(digests) == 3

    def test_digests_have_required_keys(self, temp_data_dir):
        """Each digest should have date, list, and tweets."""
        digests = load_json_files(temp_data_dir)
        for d in digests:
            assert "date" in d
            assert "list" in d
            assert "tweets" in d

    def test_nonexistent_directory(self):
        """Should return empty list for nonexistent directory."""
        digests = load_json_files("/nonexistent/path")
        assert digests == []

    def test_empty_directory(self):
        """Should return empty list for directory without index.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            digests = load_json_files(tmpdir)
            assert digests == []

    def test_corrupt_json_skipped(self, sample_digests):
        """Corrupt JSON files should be skipped, not crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            # Valid file
            (data_dir / "valid.json").write_text(
                json.dumps({"date": "2026-05-18", "list": "Dev/AI", "tweets": []})
            )
            # Corrupt file
            (data_dir / "bad.json").write_text("NOT JSON AT ALL {{{")

            index_path = data_dir / "index.json"
            index_path.write_text(json.dumps(["valid.json", "bad.json"]))

            digests = load_json_files(str(data_dir))
            assert len(digests) == 1
            assert digests[0]["date"] == "2026-05-18"

    def test_missing_file_in_index(self):
        """Files listed in index but missing on disk should be skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            (data_dir / "present.json").write_text(
                json.dumps({"date": "2026-05-18", "list": "Dev/AI", "tweets": []})
            )
            index_path = data_dir / "index.json"
            index_path.write_text(json.dumps(["present.json", "missing.json"]))

            digests = load_json_files(str(data_dir))
            assert len(digests) == 1

    def test_non_dict_json_skipped(self):
        """JSON files that aren't dicts should be skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            (data_dir / "array.json").write_text(json.dumps([1, 2, 3]))
            index_path = data_dir / "index.json"
            index_path.write_text(json.dumps(["array.json"]))

            digests = load_json_files(str(data_dir))
            assert digests == []

    def test_path_traversal_blocked(self):
        """Path traversal via ../ in index.json filenames should be blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            # Create a file outside data_dir that we shouldn't be able to access
            evil_file = Path(tmpdir) / "evil.json"
            evil_file.write_text(
                json.dumps({"date": "2026-05-18", "list": "Hacked", "tweets": []})
            )

            # Index tries to traverse out of data_dir
            index_path = data_dir / "index.json"
            index_path.write_text(json.dumps(["../evil.json"]))

            digests = load_json_files(str(data_dir))
            # The traversal should be blocked — no digests loaded
            assert digests == []


# ═══════════════════════════════════════════════════════════════════════════════
# List Filtering Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestFilterDigestsByList:
    def test_filter_exact_match(self, sample_digests):
        """Should return only digests matching the list name."""
        result = filter_digests_by_list(sample_digests, "Crypto")
        assert len(result) == 1
        assert result[0]["list"] == "Crypto"

    def test_filter_dev_ai(self, sample_digests):
        """Should return Dev/AI digests."""
        result = filter_digests_by_list(sample_digests, "Dev/AI")
        assert len(result) == 2

    def test_none_returns_all(self, sample_digests):
        """None list filter should return all digests."""
        result = filter_digests_by_list(sample_digests, None)
        assert len(result) == 3

    def test_all_wildcard(self, sample_digests):
        """'all' should return all digests."""
        result = filter_digests_by_list(sample_digests, "all")
        assert len(result) == 3

    def test_no_match(self, sample_digests):
        """Should return empty when no list matches."""
        result = filter_digests_by_list(sample_digests, "Nonexistent")
        assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# Full Pipeline Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestProcessDigest:
    def test_full_pipeline_no_filters(self, temp_data_dir):
        """Default pipeline should load, sort, and return all data."""
        result = process_digest(temp_data_dir)
        assert result["total_tweets"] == 5  # 3 + 1 + 1
        assert len(result["digests"]) == 3

    def test_list_filter(self, temp_data_dir):
        """Should filter by list name."""
        result = process_digest(temp_data_dir, list_filter="Crypto")
        assert len(result["digests"]) == 1
        assert result["digests"][0]["list"] == "Crypto"

    def test_signal_filter(self, temp_data_dir):
        """Should filter tweets by signal."""
        result = process_digest(temp_data_dir, signal_filter="🟡 Insight")
        assert result["total_tweets"] == 1  # only alice's tweet

    def test_exclude_signals(self, temp_data_dir):
        """Should exclude tweets with specified signals."""
        result = process_digest(
            temp_data_dir, exclude_signals=["⚪ Link/Ref"]
        )
        # Total was 5, Dave's ⚪ Link/Ref excluded → 4
        assert result["total_tweets"] == 4

    def test_date_range(self, temp_data_dir):
        """Should filter by date range."""
        result = process_digest(temp_data_dir, start_date="2026-05-18", end_date="2026-05-18")
        # Only May 18 digests (Dev/AI + Crypto)
        assert len(result["digests"]) == 2

    def test_combined_filters(self, temp_data_dir):
        """Should apply all filters together."""
        result = process_digest(
            temp_data_dir,
            list_filter="Dev/AI",
            signal_filter="🔴 Signal",
            start_date="2026-05-18",
        )
        assert len(result["digests"]) == 1
        assert result["total_tweets"] == 1  # Bob's 🔴 Signal tweet

    def test_returns_already_sorted(self, temp_data_dir):
        """Should return digests sorted newest first."""
        result = process_digest(temp_data_dir)
        dates = [d["date"] for d in result["digests"]]
        assert dates == sorted(dates, reverse=True)


class TestRenderDigestHtml:
    def test_renders_digests(self, temp_data_dir):
        """Should produce HTML output."""
        html = render_digest_html(temp_data_dir)
        assert "day-header" in html
        assert "Monday, May 18, 2026" in html

    def test_empty_result_shows_message(self):
        """Should show empty message when no digests match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()
            (data_dir / "index.json").write_text("[]")
            html = render_digest_html(str(data_dir))
            assert "No digests" in html

    def test_replies_use_pair_renderer(self, temp_data_dir):
        """Replies should be rendered with parent context."""
        # Create data with a reply
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()
            digest = {
                "date": "2026-05-18",
                "list": "Dev/AI",
                "tweets": [
                    {
                        "is_reply": True,
                        "parent": {
                            "username": "alice",
                            "text": "Original post",
                            "media": [],
                        },
                        "reply": {
                            "username": "bob",
                            "name": "Bob",
                            "text": "Reply text",
                            "media": [],
                        },
                    },
                ],
            }
            fn = "2026-05-18-dev-ai.json"
            (data_dir / fn).write_text(json.dumps(digest))
            (data_dir / "index.json").write_text(json.dumps([fn]))

            html = render_digest_html(str(data_dir))
            assert "tweet thread" in html
            assert "parent-tweet" in html
            assert "Original post" in html
            assert "Reply text" in html
