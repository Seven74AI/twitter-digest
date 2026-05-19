"""
Twitter Digest Processor

Extracts and transforms Twitter digest JSON data for display.
Replicates the JavaScript rendering logic from index.html in Python,
providing pure functions for filtering, sorting, reply structure handling,
and markdown/HTML rendering.
"""

import html as _html
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Constants ────────────────────────────────────────────────────────────────

SIGNAL_LEVELS = [
    "🔴 Signal",
    "🟡 Insight",
    "🟢 Discussion",
    "⚪ Link/Ref",
]

LIST_NAMES = ["Dev/AI", "Crypto"]


# ── Data Loading ─────────────────────────────────────────────────────────────

def load_json_files(data_dir: str) -> list[dict[str, Any]]:
    """Load all digest JSON files referenced in data/index.json.

    Args:
        data_dir: Path to the data directory containing index.json and digest files.

    Returns:
        List of digest dicts, each with 'date', 'list', and 'tweets' keys.
    """
    index_path = Path(data_dir) / "index.json"

    if not index_path.exists():
        return []

    with open(index_path) as f:
        file_list: list[str] = json.load(f)

    digests: list[dict[str, Any]] = []
    resolved_data_dir = Path(data_dir).resolve()
    for filename in file_list:
        file_path = (Path(data_dir) / filename).resolve()
        # Guard against path traversal (e.g., ../ outside data_dir)
        if not str(file_path).startswith(str(resolved_data_dir) + os.sep):
            continue
        if file_path.exists():
            try:
                with open(file_path) as f:
                    digest = json.load(f)
                    if isinstance(digest, dict) and "date" in digest:
                        digests.append(digest)
            except (json.JSONDecodeError, OSError):
                continue

    return digests


# ── Date Handling ────────────────────────────────────────────────────────────

def sort_digests_by_date(digests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort digests by date, newest first (descending).

    Digests without a 'date' key (malformed) are silently filtered out
    before sorting.

    Args:
        digests: List of digest dicts.

    Returns:
        Sorted list, newest dates first.
    """
    valid = [d for d in digests if "date" in d]
    return sorted(valid, key=lambda d: d["date"], reverse=True)


def filter_by_date_range(
    digests: list[dict[str, Any]],
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """Filter digests to those within a date range (inclusive).

    Args:
        digests: List of digest dicts.
        start_date: ISO date string (YYYY-MM-DD) for earliest date. None = no lower bound.
        end_date: ISO date string (YYYY-MM-DD) for latest date. None = no upper bound.

    Returns:
        Filtered digests.
    """
    result = digests
    if start_date:
        result = [d for d in result if d.get("date", "") >= start_date]
    if end_date:
        result = [d for d in result if d.get("date", "") <= end_date]
    return result


def format_date(date_str: str) -> str:
    """Format an ISO date string to a human-readable format.

    Args:
        date_str: Date in YYYY-MM-DD format.

    Returns:
        Formatted date, e.g. 'Thursday, May 18, 2026'.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%A, %B %d, %Y")
    except ValueError:
        return date_str


# ── List / Signal Filtering ──────────────────────────────────────────────────

def filter_digests_by_list(
    digests: list[dict[str, Any]],
    list_name: str | None = None,
) -> list[dict[str, Any]]:
    """Filter digests by list name.

    Args:
        digests: List of digest dicts.
        list_name: List name to filter by (e.g. 'Dev/AI', 'Crypto').
                   None or 'all' returns all digests.

    Returns:
        Filtered digests.
    """
    if list_name is None or list_name == "all":
        return digests
    return [d for d in digests if d.get("list") == list_name]


def filter_tweets_by_signal(
    tweets: list[dict[str, Any]],
    signal: str | None = None,
) -> list[dict[str, Any]]:
    """Filter tweets by signal level (off-topic filter).

    Args:
        tweets: List of tweet dicts.
        signal: Signal to filter by. None or 'all' returns all tweets.
                Valid: '🔴 Signal', '🟡 Insight', '🟢 Discussion', '⚪ Link/Ref'

    Returns:
        Filtered tweets.
    """
    if signal is None or signal == "all":
        return tweets
    return [t for t in tweets if t.get("signal") == signal]


def filter_tweets_exclude_signals(
    tweets: list[dict[str, Any]],
    exclude_signals: list[str],
) -> list[dict[str, Any]]:
    """Filter out tweets matching any of the excluded signal levels.

    This is the 'off-topic filter' — exclude low-value signals like Link/Ref
    to focus on substantive content.

    Args:
        tweets: List of tweet dicts.
        exclude_signals: List of signal strings to exclude.

    Returns:
        Filtered tweets.
    """
    if not exclude_signals:
        return tweets
    return [t for t in tweets if t.get("signal") not in exclude_signals]


# ── Reply Structure ──────────────────────────────────────────────────────────

def is_reply_tweet(tweet: dict[str, Any]) -> bool:
    """Check if a tweet is a reply structure.

    In the digest format, reply tweets are structured as:
    {"is_reply": true, "parent": {...}, "reply": {...}}

    Args:
        tweet: Tweet dict from digest data.

    Returns:
        True if the tweet has reply structure.
    """
    return tweet.get("is_reply", False) is True


def get_reply_content(tweet: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the reply sub-object from a reply tweet.

    Args:
        tweet: A reply tweet dict.

    Returns:
        The 'reply' sub-object, or None if not a reply.
    """
    if not is_reply_tweet(tweet):
        return None
    return tweet.get("reply")


def get_parent_content(tweet: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the parent sub-object from a reply tweet.

    Args:
        tweet: A reply tweet dict.

    Returns:
        The 'parent' sub-object, or None if not a reply.
    """
    if not is_reply_tweet(tweet):
        return None
    return tweet.get("parent")


def flatten_reply_tweet(tweet: dict[str, Any]) -> dict[str, Any] | None:
    """Flatten a reply tweet into a single tweet dict using the reply content.

    The reply's own metadata (username, text, etc.) becomes the tweet,
    with parent info accessible separately via get_parent_content().

    Args:
        tweet: A reply tweet dict.

    Returns:
        The reply sub-object as a standalone tweet dict, or None.
    """
    return get_reply_content(tweet)


# ── Markdown / Text Rendering ────────────────────────────────────────────────

_URL_PATTERN = re.compile(r"https?://[^\s]+")
_MENTION_PATTERN = re.compile(r"@(\w+)")


def linkify(text: str) -> str:
    """Convert URLs to <a> links and @mentions to X.com profile links.

    Replicates the JavaScript linkify() function from index.html.

    Args:
        text: Raw tweet text.

    Returns:
        Text with URLs wrapped in <a> tags and @mentions linked to X.com.
    """
    text = _URL_PATTERN.sub(r'<a href="\g<0>" target="_blank">\g<0></a>', text)
    text = _MENTION_PATTERN.sub(
        r'<a href="https://x.com/\1" target="_blank">@\1</a>', text
    )
    return text


def linkify_markdown(text: str) -> str:
    """Convert URLs to markdown links and @mentions to X.com markdown links.

    Useful for markdown rendering of digest content.

    Args:
        text: Raw tweet text.

    Returns:
        Text with markdown links for URLs and @mentions.
    """
    text = _URL_PATTERN.sub(r"[\g<0>](\g<0>)", text)
    text = _MENTION_PATTERN.sub(r"[@\1](https://x.com/\1)", text)
    return text


# ── HTML Rendering ───────────────────────────────────────────────────────────

_SIGNAL_CLASS_MAP = {
    "🔴 Signal": "signal-sig",
    "🟡 Insight": "signal-insight",
    "🟢 Discussion": "signal-disc",
    "⚪ Link/Ref": "signal-link",
}


def _signal_css_class(signal: str | None) -> str:
    if not signal:
        return "signal-link"
    for prefix, cls in _SIGNAL_CLASS_MAP.items():
        if signal.startswith(prefix):
            return cls
    return "signal-link"


def _initial(username: str | None) -> str:
    if not username:
        return "?"
    return username[0].upper()


def _avatar_html(avatar: str | None, username: str | None) -> str:
    if avatar:
        return f'<img class="avatar" src="{avatar}" alt="{username or ""}" loading="lazy">'
    letter = _initial(username)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40">'
        f'<rect fill="#2f3336" width="40" height="40" rx="20"/>'
        f'<text fill="#71767b" x="20" y="24" text-anchor="middle" font-size="16">{letter}</text>'
        f"</svg>"
    )
    data_uri = f"data:image/svg+xml,{svg}"
    return f'<img class="avatar" src="{data_uri}" alt="{username or ""}" loading="lazy">'


def render_media(media: list[dict[str, str]] | None) -> str:
    """Render media items to HTML.

    Args:
        media: List of media dicts with 'url' and 'type' keys.

    Returns:
        HTML string for media grid, or empty string.
    """
    if not media:
        return ""

    parts = []
    for m in media:
        url = m.get("url", "")
        mtype = m.get("type", "")
        if mtype == "image":
            parts.append(
                f'<a href="{url}" target="_blank">'
                f'<img src="{url}" class="tweet-media" loading="lazy" alt="tweet image">'
                f"</a>"
            )
        elif mtype == "video":
            parts.append(
                f'<a href="{url}" target="_blank" class="video-link">▶️ Watch video</a>'
            )
        else:
            parts.append(f'<a href="{url}" target="_blank">📎 Media</a>')

    return f'<div class="media-grid">{"".join(parts)}</div>'


def render_tweet_html(tweet: dict[str, Any]) -> str:
    """Render a single tweet to its HTML representation.

    Replicates the renderTweet() function from index.html.

    Args:
        tweet: Tweet dict with username, name, text, signal, themes, etc.

    Returns:
        HTML string for the tweet.
    """
    username_raw = tweet.get("username", "unknown")
    username = _html.escape(str(username_raw))
    name_raw = tweet.get("name", username_raw or "User")
    name = _html.escape(str(name_raw))
    text = _html.escape(str(tweet.get("text", "")))
    signal = tweet.get("signal")
    themes = tweet.get("themes", [])
    source = tweet.get("source")
    likes = tweet.get("likes")
    retweets = tweet.get("retweets")
    tweet_url = tweet.get("tweet_url")
    avatar = tweet.get("avatar")
    media = tweet.get("media", [])

    sig_class = _signal_css_class(signal)

    parts = [
        '<div class="tweet">',
        _avatar_html(avatar, username),
        '<div class="tweet-body">',
        '<div class="tweet-header">',
        f'<span class="tweet-name">{name}</span>',
        f'<span class="tweet-handle">@{username}</span>',
        "</div>",
        f'<div class="tweet-text">{linkify(text)}</div>',
        render_media(media),
        '<div class="badges">',
    ]

    if signal:
        parts.append(f'<span class="badge badge-signal {sig_class}">{_html.escape(str(signal))}</span>')

    for theme in themes:
        parts.append(f'<span class="badge badge-theme">{_html.escape(str(theme))}</span>')

    if source:
        parts.append(f'<span class="badge badge-source">{_html.escape(str(source))}</span>')

    parts.append("</div>")  # badges

    # Tweet meta
    parts.append('<div class="tweet-meta">')
    if likes is not None:
        parts.append(f"<span>❤️ {likes}</span>")
    if retweets is not None:
        parts.append(f"<span>🔄 {retweets}</span>")
    if tweet_url:
        parts.append(
            f'<a href="{tweet_url}" class="tweet-link" target="_blank">🔗 view on X</a>'
        )
    parts.append("</div>")  # tweet-meta

    parts.append("</div>")  # tweet-body
    parts.append("</div>")  # tweet

    return "\n".join(parts)


def render_tweet_pair_html(tweet: dict[str, Any]) -> str:
    """Render a reply tweet with its parent to HTML.

    Replicates the renderTweetPair() function from index.html.

    Args:
        tweet: Reply tweet dict with 'is_reply', 'parent', and 'reply' keys.

    Returns:
        HTML string for the tweet pair.
    """
    parent = tweet.get("parent")
    reply = tweet.get("reply", {})

    parts = ['<div class="tweet thread">']

    if parent:
        parent_text = _html.escape(str(parent.get("text", "")))
        parent_username = _html.escape(str(parent.get("username", "unknown")))
        parent_media = parent.get("media", [])
        parent_url = parent.get("tweet_url")

        parts.append('<div class="parent-tweet">')
        parts.append(f'<span class="tweet-handle">↳ @{parent_username}</span>')
        parts.append(
            f'<div class="tweet-text" style="color:#71767b;font-size:14px;">'
            f"{linkify(parent_text)}"
            f"</div>"
        )
        parts.append(render_media(parent_media))
        if parent_url:
            parts.append(
                f'<a href="{parent_url}" class="tweet-link" target="_blank">🔗 view on X</a>'
            )
        parts.append("</div>")  # parent-tweet

    parts.append(
        '<div style="margin-left:20px;border-left:2px solid #2f3336;padding-left:12px;">'
    )
    parts.append(render_tweet_html(reply))
    parts.append("</div>")

    parts.append("</div>")  # tweet thread

    return "\n".join(parts)


# ── Digest Processing Pipeline ───────────────────────────────────────────────

def process_digest(
    data_dir: str,
    list_filter: str | None = None,
    signal_filter: str | None = None,
    exclude_signals: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Full digest processing pipeline.

    Loads, filters, and sorts digests, returning structured data
    ready for HTML rendering.

    Args:
        data_dir: Path to data directory.
        list_filter: List name to filter by (None = all).
        signal_filter: Signal to filter tweets by (None = all).
        exclude_signals: Signals to exclude (off-topic filter).
        start_date: Earliest date (inclusive).
        end_date: Latest date (inclusive).

    Returns:
        Dict with 'digests' (filtered/sorted list) and 'total_tweets' count.
    """
    digests = load_json_files(data_dir)
    digests = sort_digests_by_date(digests)
    digests = filter_digests_by_list(digests, list_filter)
    digests = filter_by_date_range(digests, start_date, end_date)

    total_tweets = 0
    processed: list[dict[str, Any]] = []

    for digest in digests:
        tweets = digest.get("tweets", [])
        tweets = filter_tweets_by_signal(tweets, signal_filter)

        if exclude_signals:
            tweets = filter_tweets_exclude_signals(tweets, exclude_signals)

        if tweets:
            total_tweets += len(tweets)
            processed.append({
                "date": digest["date"],
                "list": digest.get("list", ""),
                "tweets": list(tweets),
            })

    return {
        "digests": processed,
        "total_tweets": total_tweets,
    }


def render_digest_html(data_dir: str, **kwargs: Any) -> str:
    """Render the full digest page as an HTML string.

    Args:
        data_dir: Path to data directory.
        **kwargs: Passed through to process_digest().

    Returns:
        Full HTML page string.
    """
    result = process_digest(data_dir, **kwargs)
    digests = result["digests"]
    total_tweets = result["total_tweets"]

    if not digests:
        return '<div class="empty">No digests for this list yet.</div>'

    html_parts: list[str] = []
    for digest in digests:
        date_str = digest["date"]
        list_name = digest.get("list", "")
        tweets = digest["tweets"]

        html_parts.append(
            f'<div class="day-header">'
            f"{format_date(date_str)} · {list_name} · {len(tweets)} tweets"
            f"</div>"
        )

        for tweet in tweets:
            if is_reply_tweet(tweet):
                html_parts.append(render_tweet_pair_html(tweet))
            else:
                html_parts.append(render_tweet_html(tweet))

    if not html_parts:
        return '<div class="empty">No tweets match this filter.</div>'

    # Build date range label
    date_range = ""
    if len(digests) > 1:
        newest = digests[0]["date"]
        oldest = digests[-1]["date"]
        date_range = f"{oldest} → {newest} · {total_tweets} tweets"
    elif digests:
        date_range = f"{digests[0]['date']} · {total_tweets} tweets"

    return "\n".join(html_parts)
