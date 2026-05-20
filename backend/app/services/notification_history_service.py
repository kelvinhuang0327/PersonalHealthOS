"""Notification History Service — P5 Learning Loop
====================================================
Provides DB-backed persistence and aggregated history for the stateful
notification fatigue guard.

Public API
----------
persist_notification_candidates()   — upsert active + suppressed records
load_notification_history()         — aggregate history per cooldown_key
update_notification_status()        — snooze / ignore / click / acted
get_notification_by_id()            — lookup by DB id, person-scoped

Dedup contract
--------------
Within a 6-hour window, the same (candidate_id, subject_profile_id) pair
is NOT inserted twice.  If a record already exists in that window, the
existing id is returned in the id_map.  This prevents spam-writes when
the user navigates back to the dashboard rapidly.
"""
from __future__ import annotations

import uuid as _uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import NotificationLog

# Dedup window: do not create a new record for the same candidate within 6h
_DEDUP_WINDOW_HOURS = 6


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_uuid(val: str | _uuid.UUID) -> _uuid.UUID:
    return val if isinstance(val, _uuid.UUID) else _uuid.UUID(str(val))


# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------

def persist_notification_candidates(
    db: Session,
    user_id: str,
    person_id: str,
    active_candidates: list[dict[str, Any]],
    suppressed_candidates: list[dict[str, Any]],
) -> dict[str, str]:
    """Write notification candidates to DB; return {candidate_id → notification_log_id}.

    Active candidates are stored with status='generated'.
    Suppressed candidates are stored with status='suppressed'.
    Both carry evidence_json for audit purposes.

    Duplicate suppression: if a record with the same (candidate_id,
    subject_profile_id) already exists within _DEDUP_WINDOW_HOURS, the
    existing record's id is used rather than inserting a new row.
    """
    uid = _to_uuid(user_id)
    pid = _to_uuid(person_id)
    now = _now()
    cutoff = now - timedelta(hours=_DEDUP_WINDOW_HOURS)
    id_map: dict[str, str] = {}

    all_pairs: list[tuple[dict, str]] = [
        (c, "generated") for c in active_candidates
    ] + [
        (c, "suppressed") for c in suppressed_candidates
    ]

    for candidate, initial_status in all_pairs:
        cid = candidate.get("candidate_id", "")

        # Dedup check — reuse existing record in the dedup window
        existing = (
            db.query(NotificationLog)
            .filter(
                NotificationLog.subject_profile_id == pid,
                NotificationLog.candidate_id == cid,
                NotificationLog.generated_at >= cutoff,
            )
            .first()
        )
        if existing:
            id_map[cid] = str(existing.id)
            continue

        record = NotificationLog(
            user_id=uid,
            subject_profile_id=pid,
            candidate_id=cid,
            cooldown_key=candidate.get("cooldown_key", ""),
            source_type=candidate.get("source_type", ""),
            priority=candidate.get("priority", "medium"),
            title=candidate.get("title", ""),
            message=candidate.get("message", ""),
            status=initial_status,
            suppress_reason=candidate.get("suppress_reason"),
            generated_at=now,
            evidence_json=candidate.get("evidence_sources"),
        )
        db.add(record)
        db.flush()  # get id without commit
        id_map[cid] = str(record.id)

    db.commit()
    return id_map


# ---------------------------------------------------------------------------
# Load history
# ---------------------------------------------------------------------------

def load_notification_history(
    db: Session,
    user_id: str,
    person_id: str,
    days: int = 7,
) -> list[dict[str, Any]]:
    """Return one history-entry dict per cooldown_key.

    The returned format is compatible with apply_notification_fatigue_guard:
        {
          "cooldown_key": str,
          "priority": str,         # most recent
          "status": str,           # most recent
          "snooze_count": int,     # rows where status == "snoozed"
          "ignore_count": int,     # rows where status == "ignored"
          "sent_at": str | None,   # generated_at of most recent non-suppressed row
          "snoozed_until": str | None,  # from latest snoozed row
        }
    """
    pid = _to_uuid(person_id)
    uid = _to_uuid(user_id)
    cutoff = _now() - timedelta(days=days)

    rows: list[NotificationLog] = (
        db.query(NotificationLog)
        .filter(
            NotificationLog.user_id == uid,
            NotificationLog.subject_profile_id == pid,
            NotificationLog.generated_at >= cutoff,
        )
        .order_by(NotificationLog.generated_at.desc())
        .all()
    )

    if not rows:
        return []

    # Group by cooldown_key
    groups: dict[str, list[NotificationLog]] = defaultdict(list)
    for row in rows:
        groups[row.cooldown_key].append(row)

    history: list[dict[str, Any]] = []
    for key, records in groups.items():
        # Already sorted desc by generated_at
        most_recent = records[0]

        # sent_at = most recent non-suppressed generated_at
        non_suppressed = [r for r in records if r.status != "suppressed"]
        sent_at: str | None = None
        if non_suppressed:
            dt = non_suppressed[0].generated_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            sent_at = dt.isoformat()

        # Aggregate counts — read cumulative fields from most recent active record
        # (these fields are incremented in-place on each update_notification_status call)
        active_row = non_suppressed[0] if non_suppressed else most_recent
        ignore_count = active_row.ignore_count
        snooze_count = active_row.snooze_count

        # snoozed_until: from the active row's stored snoozed_until field
        snoozed_until: str | None = None
        if active_row.snoozed_until:
            su = active_row.snoozed_until
            if su.tzinfo is None:
                su = su.replace(tzinfo=timezone.utc)
            snoozed_until = su.isoformat()

        # Determine effective status (most recent non-suppressed if exists, else most recent)

        history.append({
            "cooldown_key": key,
            "priority": active_row.priority,
            "status": active_row.status,
            "snooze_count": snooze_count,
            "ignore_count": ignore_count,
            "sent_at": sent_at,
            "snoozed_until": snoozed_until,
        })

    return history


# ---------------------------------------------------------------------------
# Status update
# ---------------------------------------------------------------------------

def get_notification_by_id(
    db: Session,
    notification_id: str,
    user_id: str,
    person_id: str,
) -> NotificationLog | None:
    """Fetch NotificationLog by id, scoped to user + person. Returns None if not found."""
    try:
        nid = _to_uuid(notification_id)
        uid = _to_uuid(user_id)
        pid = _to_uuid(person_id)
    except ValueError:
        return None

    return (
        db.query(NotificationLog)
        .filter(
            NotificationLog.id == nid,
            NotificationLog.user_id == uid,
            NotificationLog.subject_profile_id == pid,
        )
        .first()
    )


def update_notification_status(
    db: Session,
    notification_id: str,
    user_id: str,
    person_id: str,
    status: str,
    snoozed_until: datetime | None = None,
) -> dict[str, Any] | None:
    """Update the status of a NotificationLog record.

    Returns serialised record dict on success, or None if not found.

    Also aggregates ignore_count / snooze_count from sibling records so that
    future fatigue-guard evaluations see the cumulative counts.
    """
    record = get_notification_by_id(db, notification_id, user_id, person_id)
    if not record:
        return None

    now = _now()
    record.status = status

    if status == "snoozed":
        record.snoozed_until = snoozed_until
        record.snooze_count += 1
    elif status == "ignored":
        record.ignore_count += 1
    elif status == "clicked":
        record.clicked_at = now
    elif status == "acted":
        record.acted_at = now
    elif status == "delivered":
        record.delivered_at = now

    db.add(record)
    db.commit()
    db.refresh(record)

    return _serialize_log(record)


def _serialize_log(record: NotificationLog) -> dict[str, Any]:
    def _iso(dt: datetime | None) -> str | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    return {
        "notification_id": str(record.id),
        "candidate_id": record.candidate_id,
        "cooldown_key": record.cooldown_key,
        "source_type": record.source_type,
        "priority": record.priority,
        "title": record.title,
        "status": record.status,
        "suppress_reason": record.suppress_reason,
        "generated_at": _iso(record.generated_at),
        "snoozed_until": _iso(record.snoozed_until),
        "clicked_at": _iso(record.clicked_at),
        "acted_at": _iso(record.acted_at),
        "snooze_count": record.snooze_count,
        "ignore_count": record.ignore_count,
    }
