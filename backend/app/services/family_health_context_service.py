"""Family Health Context Service — P8 Family / Multi-Person Health Assistant
=============================================================================
Provides pure-function helpers to build a family health context from
pre-loaded relationship and health data.

All core functions are pure (no DB access) — fast, deterministic, testable.
DB-access helpers (load_family_relationships) accept a SQLAlchemy Session.

Anti-hallucination rules
-------------------------
- shared risks must appear in ≥ 1 related-profile's evidence list
- caregiver alerts only generated when relationship_type is 'caregiver' or
  permission_level is 'manage' / 'full_access' for a child/parent profile
- child attention items only surfaced when subject has child-type relative
- family recommendations must not duplicate active actions
- unrelated profiles are never mixed into a family context
- empty / no-data state is always explained via limitations

Public API
----------
get_related_profiles()              — filter and label related profiles
get_family_risk_summary()           — identify cross-profile shared risks
build_family_health_context()       — aggregate full family health context
generate_family_recommendations()   — produce actionable family-level items
load_family_relationships()         — DB helper: load relationships for a user/person
"""
from __future__ import annotations

from collections import Counter
from typing import Any

# ---------------------------------------------------------------------------
# Type aliases (documented shapes)
# ---------------------------------------------------------------------------

RelationshipDict = dict[str, Any]
"""
{
  id: str
  owner_user_id: str
  subject_profile_id: str
  related_profile_id: str
  relationship_type: "self"|"child"|"parent"|"spouse"|"caregiver"
  permission_level: "read_only"|"manage"|"full_access"
  related_display_name: str   # optional — enriched by caller
}
"""

FamilyProfile = dict[str, Any]
"""
{
  profile_id: str
  display_name: str
  relationship_type: str
  permission_level: str
}
"""

FamilyHealthContext = dict[str, Any]
"""
{
  relatedProfiles: list[FamilyProfile]
  sharedRisks: list[str]
  caregiverAlerts: list[str]
  childAttentionItems: list[str]
  familyActionSuggestions: list[str]
  confidence: float
  limitations: list[str]
}
"""

FamilyRecommendation = dict[str, Any]
"""
{
  text: str
  target_profile_id: str | None
  audience: "caregiver"|"member"|"family"
  urgency: "high"|"medium"|"low"
  evidence_source: str
}
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CAREGIVER_TYPES = frozenset({"caregiver", "parent"})
_CAREGIVER_PERMISSIONS = frozenset({"manage", "full_access"})
_CHILD_TYPES = frozenset({"child"})
_SHARED_MIN_PROFILES = 2        # risk must appear in ≥ 2 profiles to be "shared"
_MAX_SUGGESTIONS_PER_MEMBER = 3  # prevent notification spam per member

# ---------------------------------------------------------------------------
# Task 2a — get_related_profiles
# ---------------------------------------------------------------------------

def get_related_profiles(
    relationships: list[RelationshipDict],
) -> list[FamilyProfile]:
    """Extract the set of related profiles from a relationship list.

    Returns one FamilyProfile entry per unique related_profile_id.
    If the same profile appears multiple times (e.g. child + caregiver),
    the first entry is kept (stable ordering).
    """
    seen: set[str] = set()
    results: list[FamilyProfile] = []

    for rel in relationships:
        pid = str(rel.get("related_profile_id", ""))
        if not pid or pid in seen:
            continue
        seen.add(pid)
        results.append({
            "profile_id": pid,
            "display_name": rel.get("related_display_name") or rel.get("display_name") or "未知成員",
            "relationship_type": rel.get("relationship_type", "self"),
            "permission_level": rel.get("permission_level", "read_only"),
        })

    return results


# ---------------------------------------------------------------------------
# Task 2b — get_family_risk_summary
# ---------------------------------------------------------------------------

def get_family_risk_summary(
    relationships: list[RelationshipDict],
    risk_alerts_by_profile: dict[str, list[str]],
) -> list[str]:
    """Return risks that appear across ≥ 2 related profiles.

    Only profiles present in 'relationships' are considered.
    """
    related_pids = {str(r.get("related_profile_id", "")) for r in relationships}
    related_pids.discard("")

    risk_counter: Counter[str] = Counter()
    for pid in related_pids:
        for risk in risk_alerts_by_profile.get(pid, []):
            risk_counter[risk] += 1

    return sorted(item for item, cnt in risk_counter.items() if cnt >= _SHARED_MIN_PROFILES)


# ---------------------------------------------------------------------------
# Task 2c — build_family_health_context
# ---------------------------------------------------------------------------

def build_family_health_context(
    relationships: list[RelationshipDict],
    recommendations_by_profile: dict[str, list[str]] | None = None,
    narrative_memories_by_profile: dict[str, list[dict]] | None = None,
    escalations_by_profile: dict[str, list[str]] | None = None,
    lab_abnormalities_by_profile: dict[str, list[str]] | None = None,
    symptom_patterns_by_profile: dict[str, list[str]] | None = None,
) -> FamilyHealthContext:
    """Aggregate full family health context from relationship and evidence data.

    All evidence maps are keyed by profile_id (str) and are optional.
    Returns an explainable empty context when no relationships exist.

    Never emits medical diagnoses — factual observations only.
    Never mixes health data from profiles not in 'relationships'.
    """
    recommendations_by_profile = recommendations_by_profile or {}
    escalations_by_profile = escalations_by_profile or {}
    lab_abnormalities_by_profile = lab_abnormalities_by_profile or {}
    symptom_patterns_by_profile = symptom_patterns_by_profile or {}
    narrative_memories_by_profile = narrative_memories_by_profile or {}

    limitations: list[str] = []

    if not relationships:
        return {
            "relatedProfiles": [],
            "sharedRisks": [],
            "caregiverAlerts": [],
            "childAttentionItems": [],
            "familyActionSuggestions": [],
            "confidence": 0.0,
            "limitations": ["尚未設定家庭成員關係，無法建立家庭健康脈絡。"],
        }

    related_profiles = get_related_profiles(relationships)

    # ── Build risk pool across all related profiles ───────────────────────────
    all_risk_pools: dict[str, list[str]] = {}
    for rel in relationships:
        pid = str(rel.get("related_profile_id", ""))
        if not pid:
            continue
        all_risks: list[str] = []
        all_risks.extend(escalations_by_profile.get(pid, []))
        all_risks.extend(lab_abnormalities_by_profile.get(pid, []))
        all_risks.extend(symptom_patterns_by_profile.get(pid, []))
        all_risk_pools[pid] = all_risks

    shared_risks = get_family_risk_summary(relationships, all_risk_pools)

    # ── Caregiver alerts: surfaced to caregiver / parent relationships ────────
    caregiver_alerts: list[str] = []
    child_attention_items: list[str] = []

    for rel in relationships:
        rel_type = rel.get("relationship_type", "")
        perm = rel.get("permission_level", "read_only")
        pid = str(rel.get("related_profile_id", ""))
        display = rel.get("related_display_name") or rel.get("display_name") or "家庭成員"

        profile_risks = all_risk_pools.get(pid, [])

        if rel_type in _CAREGIVER_TYPES or perm in _CAREGIVER_PERMISSIONS:
            for risk in profile_risks:
                alert = f"{display}：{risk}"
                if alert not in caregiver_alerts:
                    caregiver_alerts.append(alert)

        if rel_type in _CHILD_TYPES:
            for risk in profile_risks:
                item = f"{display}：{risk}"
                if item not in child_attention_items:
                    child_attention_items.append(item)

    # ── Family action suggestions: from recommendations across profiles ────────
    suggestion_counter: Counter[str] = Counter()
    for rel in relationships:
        pid = str(rel.get("related_profile_id", ""))
        for rec in recommendations_by_profile.get(pid, []):
            suggestion_counter[rec] += 1

    family_action_suggestions = [
        sug for sug, _ in suggestion_counter.most_common(5)
    ]

    # ── Confidence: based on data richness ───────────────────────────────────
    n_profiles = len(related_profiles)
    evidence_count = sum(len(v) for v in all_risk_pools.values())
    base_confidence = min(n_profiles / 4.0, 1.0) * 0.5
    evidence_bonus = min(evidence_count / 10.0, 1.0) * 0.3
    confidence = round(min(base_confidence + evidence_bonus, 1.0), 3)

    if n_profiles == 0:
        limitations.append("無相關家庭成員資料。")
    if evidence_count == 0:
        limitations.append("相關成員尚無健康資料，無法評估共同風險。")
    if not caregiver_alerts and not child_attention_items:
        limitations.append("目前無照護者警示或兒童注意事項需要顯示。")

    return {
        "relatedProfiles": related_profiles,
        "sharedRisks": shared_risks,
        "caregiverAlerts": caregiver_alerts,
        "childAttentionItems": child_attention_items,
        "familyActionSuggestions": family_action_suggestions,
        "confidence": confidence,
        "limitations": limitations,
    }


# ---------------------------------------------------------------------------
# Task 3 — generate_family_recommendations
# ---------------------------------------------------------------------------

def generate_family_recommendations(
    family_context: FamilyHealthContext,
    active_actions_by_profile: dict[str, list[str]] | None = None,
    max_per_member: int = _MAX_SUGGESTIONS_PER_MEMBER,
) -> list[FamilyRecommendation]:
    """Generate actionable family-level recommendations.

    Sources:
    - childAttentionItems  → caregiver-audience recommendations (urgency=high)
    - caregiverAlerts      → caregiver-audience recommendations (urgency=medium)
    - familyActionSuggestions → family-audience recommendations (urgency=low)
    - sharedRisks          → family-audience shared risk notices (urgency=medium)

    Dedup rules:
    - Text (case-insensitive) must not match any active_actions_by_profile entry
    - Same text appears at most once in the output
    - Total output capped at max_per_member * (1 + len(relatedProfiles))
    """
    active_actions_by_profile = active_actions_by_profile or {}

    # Build flat set of all active action titles (lowercase) for dedup
    all_active: set[str] = set()
    for titles in active_actions_by_profile.values():
        for t in titles:
            all_active.add(t.lower().strip())

    results: list[FamilyRecommendation] = []
    seen_texts: set[str] = set()
    max_total = max_per_member * max(1, 1 + len(family_context.get("relatedProfiles", [])))

    def _add(
        text: str,
        audience: str,
        urgency: str,
        source: str,
        target_pid: str | None = None,
    ) -> None:
        if len(results) >= max_total:
            return
        key = text.lower().strip()
        if key in seen_texts or key in all_active:
            return
        seen_texts.add(key)
        results.append({
            "text": text,
            "target_profile_id": target_pid,
            "audience": audience,
            "urgency": urgency,
            "evidence_source": source,
        })

    # Child attention items → high-urgency caregiver
    for item in family_context.get("childAttentionItems", []):
        _add(item, "caregiver", "high", "child_attention_item")

    # Caregiver alerts → medium-urgency caregiver
    for alert in family_context.get("caregiverAlerts", []):
        _add(alert, "caregiver", "medium", "caregiver_alert")

    # Shared risks → medium-urgency family
    for risk in family_context.get("sharedRisks", []):
        _add(f"家庭共同關注：{risk}", "family", "medium", "shared_risk")

    # Family action suggestions → low-urgency family
    for sug in family_context.get("familyActionSuggestions", []):
        _add(sug, "family", "low", "family_suggestion")

    # Sort: urgency (high→medium→low)
    _urgency_order = {"high": 0, "medium": 1, "low": 2}
    results.sort(key=lambda x: _urgency_order.get(x["urgency"], 9))
    return results


# ---------------------------------------------------------------------------
# P9 — extract_family_evidence_from_bundle (pure helper)
# ---------------------------------------------------------------------------

def extract_family_evidence_from_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """Extract family-relevant evidence summaries from a build_evidence_bundle output.

    Pure function — no DB access. Converts a raw evidence bundle into string
    summaries suitable for the evidence dicts expected by
    build_family_health_context() and generate_family_recommendations().

    Returns:
      lab_abnormality_summaries   list[str]  — e.g. "LDL-C 異常（high）"
      symptom_pattern_summaries   list[str]  — e.g. "頭痛 重複發作"
      escalation_summaries        list[str]  — device-signal escalation reasons
      action_titles               list[str]  — active action titles (for dedup)
    """
    lab_abnormality_summaries: list[str] = []
    for abn in bundle.get("lab_abnormalities", []):
        name = abn.get("labItemName") or ""
        severity = abn.get("severity") or "異常"
        if name:
            lab_abnormality_summaries.append(f"{name} 異常（{severity}）")

    symptom_pattern_summaries: list[str] = []
    for pat in bundle.get("symptom_patterns", []):
        symptom = pat.get("symptomType") or ""
        label = pat.get("label") or pat.get("patternType") or ""
        if symptom and label and symptom != label:
            symptom_pattern_summaries.append(f"{symptom} {label}")
        elif symptom:
            symptom_pattern_summaries.append(symptom)
        elif label:
            symptom_pattern_summaries.append(label)

    escalation_summaries: list[str] = []
    esc = bundle.get("device_escalation") or {}
    level = esc.get("escalationLevel", "none")
    if level in ("urgent", "warning"):
        for reason in esc.get("reasons", []):
            if reason:
                escalation_summaries.append(str(reason))
        if not escalation_summaries and level == "urgent":
            escalation_summaries.append("裝置訊號顯示需緊急關注")

    action_titles: list[str] = []
    for act in bundle.get("actions", []):
        title = act.get("summary") or act.get("title") or ""
        if title:
            action_titles.append(title)

    return {
        "lab_abnormality_summaries": lab_abnormality_summaries,
        "symptom_pattern_summaries": symptom_pattern_summaries,
        "escalation_summaries": escalation_summaries,
        "action_titles": action_titles,
    }


# ---------------------------------------------------------------------------
# P9 — load_family_evidence_data (DB helper)
# ---------------------------------------------------------------------------

def load_family_evidence_data(
    db: Any,
    owner_user_id: str,
    relationships: list[RelationshipDict],
) -> dict[str, Any]:
    """Load per-profile evidence bundles for all related profiles.

    For each unique related_profile_id in relationships, calls
    build_evidence_bundle(db, owner_user_id, profile_id) and extracts
    family-relevant evidence summaries.

    All related profiles belong to the same owner — enforced at relationship
    creation via POST /family-relationships.

    Returns:
      lab_abnormalities_by_profile    {pid: list[str]}
      symptom_patterns_by_profile     {pid: list[str]}
      escalations_by_profile          {pid: list[str]}
      active_actions_by_profile       {pid: list[str]}
      recommendations_by_profile      {pid: list[str]}
    """
    from app.services.health_assistant_service import build_evidence_bundle

    lab_abnormalities_by_profile: dict[str, list[str]] = {}
    symptom_patterns_by_profile: dict[str, list[str]] = {}
    escalations_by_profile: dict[str, list[str]] = {}
    active_actions_by_profile: dict[str, list[str]] = {}
    recommendations_by_profile: dict[str, list[str]] = {}

    seen_pids: set[str] = set()
    for rel in relationships:
        pid = str(rel.get("related_profile_id", ""))
        if not pid or pid in seen_pids:
            continue
        seen_pids.add(pid)

        try:
            bundle = build_evidence_bundle(db, owner_user_id, pid)
        except Exception:
            # Never crash the family context endpoint due to a single
            # profile's evidence loading error — skip and continue.
            continue

        extracted = extract_family_evidence_from_bundle(bundle)

        lab_abnormalities_by_profile[pid] = extracted["lab_abnormality_summaries"]
        symptom_patterns_by_profile[pid] = extracted["symptom_pattern_summaries"]
        escalations_by_profile[pid] = extracted["escalation_summaries"]
        active_actions_by_profile[pid] = extracted["action_titles"]
        recommendations_by_profile[pid] = extracted["action_titles"]

    return {
        "lab_abnormalities_by_profile": lab_abnormalities_by_profile,
        "symptom_patterns_by_profile": symptom_patterns_by_profile,
        "escalations_by_profile": escalations_by_profile,
        "active_actions_by_profile": active_actions_by_profile,
        "recommendations_by_profile": recommendations_by_profile,
    }


# ---------------------------------------------------------------------------
# DB helper — load_family_relationships
# ---------------------------------------------------------------------------

def load_family_relationships(
    db: Any,
    owner_user_id: str,
    subject_profile_id: str,
) -> list[RelationshipDict]:
    """Load all FamilyRelationship rows for a given owner+subject pair.

    Returns dicts suitable for the pure functions above.
    Includes related PersonProfile.display_name as 'related_display_name'.
    """
    import uuid as _uuid_mod
    from app.models.entities import FamilyRelationship, PersonProfile

    # Convert strings to uuid.UUID so SQLAlchemy's UUID(as_uuid=True) column
    # type processes them correctly on both PostgreSQL and SQLite.
    try:
        uid = _uuid_mod.UUID(owner_user_id)
        pid = _uuid_mod.UUID(subject_profile_id)
    except (ValueError, AttributeError):
        return []

    rows = (
        db.query(FamilyRelationship, PersonProfile)
        .join(
            PersonProfile,
            PersonProfile.id == FamilyRelationship.related_profile_id,
        )
        .filter(
            FamilyRelationship.owner_user_id == uid,
            FamilyRelationship.subject_profile_id == pid,
        )
        .all()
    )

    result: list[RelationshipDict] = []
    for rel, profile in rows:
        result.append({
            "id": str(rel.id),
            "owner_user_id": str(rel.owner_user_id),
            "subject_profile_id": str(rel.subject_profile_id),
            "related_profile_id": str(rel.related_profile_id),
            "relationship_type": rel.relationship_type,
            "permission_level": rel.permission_level,
            "related_display_name": profile.display_name,
            "created_at": rel.created_at.isoformat() if rel.created_at else None,
        })
    return result
