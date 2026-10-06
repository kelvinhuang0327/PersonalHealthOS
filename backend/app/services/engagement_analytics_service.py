"""Engagement Analytics Service — P6.2 Adaptive Timing Optimization
=====================================================================
Pure-function module (no DB access) that analyses notification history
to surface engagement trends, best response windows, response delays,
and completion rates.

Public API
----------
build_engagement_analytics(history) -> dict
    Main entry point.  Computes all analytics from the history list and
    returns an EngagementAnalytics dict safe for API responses.

    Safe to call with an empty history — returns sensible defaults without
    hallucinating patterns from insufficient data.

Design contracts
----------------
- No hallucination: windows and trends reported only when data is sufficient
- Minimum records thresholds enforce this (see constants below)
- Unknown / insufficient data always returns explicit neutral / empty values
- No DB access — works entirely from serialised history dicts
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Time-window definitions (24-hour clock, local UTC)
# ---------------------------------------------------------------------------

# Named windows and their (start_hour_inclusive, end_hour_exclusive).
# "night" wraps midnight: 22 ≤ hour or hour < 6
_WINDOW_HOURS: dict[str, tuple[int, int]] = {
    "morning":   (6,  12),
    "afternoon": (12, 18),
    "evening":   (18, 22),
    "night":     (22, 6),   # wraps midnight
}

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Minimum history entries to compute a reliable trend
_MIN_RECORDS_FOR_TREND = 5
# Minimum entries per window to count that window as qualified
_MIN_RECORDS_PER_WINDOW = 3
# Split history into "recent" (0–14 d) vs "older" (14–28 d)
_TREND_RECENT_DAYS = 14
# Engagement delta thresholds for labelling trend
_IMPROVEMENT_THRESHOLD = 0.10
_DECLINE_THRESHOLD = 0.10  # negative delta ≤ -_DECLINE_THRESHOLD → declining
# Act/ignore rate thresholds for window labelling
_BEST_WINDOW_ACT_RATE = 0.30      # act rate > 30 % → best window
_IGNORED_WINDOW_RATE = 0.30       # ignore rate > 30 % → ignored window
# Max response delay (minutes) counted as a real response (not stale)
_MAX_VALID_DELAY_MINUTES = 1440   # 24 h

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_iso(s: str | None) -> datetime | None:
    """Parse ISO-8601 string to timezone-aware datetime, or None."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _get_window(hour: int) -> str:
    """Map 0–23 hour to a named window label."""
    for name, (start, end) in _WINDOW_HOURS.items():
        if start < end:          # normal range
            if start <= hour < end:
                return name
        else:                    # wraps midnight (night)
            if hour >= start or hour < end:
                return name
    return "morning"             # fallback (should never reach here)


def _engagement_score_from_entries(entries: list[dict[str, Any]]) -> float:
    """Compute a 0.0–1.0 engagement score from a slice of history entries."""
    if not entries:
        return 0.5
    acted = sum(1 for e in entries if e.get("status") == "acted")
    clicked = sum(1 for e in entries if e.get("status") == "clicked")
    ignored = sum(int(e.get("ignore_count") or 0) for e in entries)
    snoozed = sum(int(e.get("snooze_count") or 0) for e in entries)
    n = len(entries)
    positive = acted * 0.60 + clicked * 0.30
    negative = ignored * 0.20 + snoozed * 0.10
    raw = (positive - negative) / max(n, 1)
    return max(0.0, min(1.0, 0.5 + raw))


# ---------------------------------------------------------------------------
# Individual analytics functions
# ---------------------------------------------------------------------------


def calculate_engagement_trend(history: list[dict[str, Any]]) -> str:
    """Return 'improving' | 'stable' | 'declining'.

    Requires at least _MIN_RECORDS_FOR_TREND entries to avoid hallucination.
    Splits history into recent (0–14 d) vs older (14–28 d) periods using
    sent_at timestamps and compares engagement scores.
    """
    if len(history) < _MIN_RECORDS_FOR_TREND:
        return "stable"

    now = datetime.now(timezone.utc)
    recent: list[dict] = []
    older: list[dict] = []

    for h in history:
        sent = _parse_iso(h.get("sent_at"))
        if sent is None:
            continue
        age_days = (now - sent).total_seconds() / 86400
        if age_days <= _TREND_RECENT_DAYS:
            recent.append(h)
        elif age_days <= _TREND_RECENT_DAYS * 2:
            older.append(h)

    # Need data in both windows to make a comparison
    if not recent or not older:
        return "stable"

    recent_score = _engagement_score_from_entries(recent)
    older_score = _engagement_score_from_entries(older)
    delta = recent_score - older_score

    if delta >= _IMPROVEMENT_THRESHOLD:
        return "improving"
    if delta <= -_DECLINE_THRESHOLD:
        return "declining"
    return "stable"


def calculate_response_delay(history: list[dict[str, Any]]) -> float | None:
    """Return average minutes from sent_at → acted_at / clicked_at.

    Returns None when fewer than 2 valid measurements are available
    (no hallucination guarantee).
    """
    delays: list[float] = []
    for h in history:
        sent = _parse_iso(h.get("sent_at"))
        responded = _parse_iso(h.get("acted_at")) or _parse_iso(h.get("clicked_at"))
        if sent and responded and responded > sent:
            minutes = (responded - sent).total_seconds() / 60
            if 0 < minutes < _MAX_VALID_DELAY_MINUTES:
                delays.append(minutes)
    if len(delays) < 2:
        return None
    return round(sum(delays) / len(delays), 1)


def calculate_best_notification_windows(
    history: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    """Return (best_windows, ignored_windows).

    best_windows   — windows where acted/clicked rate > _BEST_WINDOW_ACT_RATE
    ignored_windows — windows where ignore rate > _IGNORED_WINDOW_RATE

    Both lists are empty when data is insufficient (_MIN_RECORDS_PER_WINDOW
    threshold not met for any window).
    """
    window_acts: dict[str, int] = {w: 0 for w in _WINDOW_HOURS}
    window_ignores: dict[str, int] = {w: 0 for w in _WINDOW_HOURS}
    window_total: dict[str, int] = {w: 0 for w in _WINDOW_HOURS}

    for h in history:
        sent = _parse_iso(h.get("sent_at"))
        if sent is None:
            continue
        win = _get_window(sent.hour)
        window_total[win] += 1

        status = h.get("status", "")
        if status in ("acted", "clicked"):
            window_acts[win] += 1
        if int(h.get("ignore_count") or 0) > 0:
            window_ignores[win] += 1

    # Only consider windows with sufficient data
    qualified = [w for w, cnt in window_total.items() if cnt >= _MIN_RECORDS_PER_WINDOW]
    if not qualified:
        return [], []

    best = sorted(
        w for w in qualified
        if window_total[w] and (window_acts[w] / window_total[w]) > _BEST_WINDOW_ACT_RATE
    )
    ignored = sorted(
        w for w in qualified
        if window_total[w] and (window_ignores[w] / window_total[w]) > _IGNORED_WINDOW_RATE
    )
    return best, ignored


def calculate_action_completion_rate(history: list[dict[str, Any]]) -> float:
    """Fraction of non-suppressed entries with status 'acted'."""
    non_suppressed = [h for h in history if h.get("status") != "suppressed"]
    if not non_suppressed:
        return 0.0
    acted = sum(1 for h in non_suppressed if h.get("status") == "acted")
    return round(acted / len(non_suppressed), 3)


def calculate_notification_open_rate(history: list[dict[str, Any]]) -> float:
    """Fraction of non-suppressed entries that were clicked or acted."""
    non_suppressed = [h for h in history if h.get("status") != "suppressed"]
    if not non_suppressed:
        return 0.0
    opened = sum(1 for h in non_suppressed if h.get("status") in ("clicked", "acted"))
    return round(opened / len(non_suppressed), 3)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def build_engagement_analytics(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute all engagement analytics from notification history.

    Returns an EngagementAnalytics dict:
      {
        engagementTrend:          "improving" | "stable" | "declining"
        avgResponseDelayMinutes:  float | None
        bestNotificationWindows:  list[str]
        ignoredTimeWindows:       list[str]
        actionCompletionRate:     float   (0.0–1.0)
        notificationOpenRate:     float   (0.0–1.0)
      }

    Safe to call with empty or very short history — returns neutral defaults
    without hallucinating patterns.
    """
    best_windows, ignored_windows = calculate_best_notification_windows(history)

    return {
        "engagementTrend": calculate_engagement_trend(history),
        "avgResponseDelayMinutes": calculate_response_delay(history),
        "bestNotificationWindows": best_windows,
        "ignoredTimeWindows": ignored_windows,
        "actionCompletionRate": calculate_action_completion_rate(history),
        "notificationOpenRate": calculate_notification_open_rate(history),
    }
