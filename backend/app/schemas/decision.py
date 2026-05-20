"""
Unified Decision Item schema.

This is the single data contract that powers:
  Dashboard → DailyDecisionSurface / DecisionPanel
  Notifications → priority grouping
  Insights → CTA actions
  Actions → today's focus

All pages must consume `decision_items` from the dashboard API
instead of re-computing priority locally.
"""
from typing import Any, Optional
from pydantic import BaseModel


class UnifiedDecisionItem(BaseModel):
    """
    A single ranked decision item, cross-source unified.

    source_type: 'alert' | 'insight' | 'action' | 'recommendation' | 'trend'
    priority:    'high'  | 'medium'  | 'low'
    why_now:     ordered list of reasons (most important first, max 3)
    feedback_state: 'pending' | 'improved' | 'no_change' | 'worse' | 'snoozed'
    score:       0-100 internal ranking score (higher = more urgent)
    """

    id: str
    source_type: str
    source_id: str
    title: str
    description: Optional[str] = None
    priority: str  # 'high' | 'medium' | 'low'
    why_now: list[str]
    next_action: str
    category: str
    status: Optional[str] = None
    due_date: Optional[str] = None
    confidence: float
    evidence_level: str
    guideline_source: Optional[str] = None
    related_metric_types: list[str] = []
    outcome_hint: Optional[str] = None
    feedback_state: str = 'pending'
    score: int
