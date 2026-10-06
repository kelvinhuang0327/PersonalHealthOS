from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import PersonProfile
from app.services.health_ai_engine.anomaly_engine import detect_anomalies
from app.services.health_ai_engine.clinical_score_engine import calculate_clinical_scores
from app.services.health_ai_engine.insight_engine import generate_health_narrative_v3, list_active_insights
from app.services.health_ai_engine.recommendation_engine import generate_recommendations
from app.services.health_ai_engine.risk_stratification_engine import stratify_risk_level

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    clinical_scores: Any = None
    anomalies: Any = None
    risk_level: Any = None
    insights: Any = None
    recommendations: Any = None
    narrative: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


class HealthEngineOrchestrator:
    """Single entry point for health analysis with graceful stage isolation."""

    def __init__(self, db: Session, person: PersonProfile):
        self.db = db
        self.person = person

    async def run_full_analysis(self, context: dict[str, Any]) -> AnalysisResult:
        results = AnalysisResult()

        results.clinical_scores = await self._run(self._clinical_scores_engine, context)
        results.anomalies = await self._run(self._anomaly_engine, context)

        risk_context = {**context, 'clinical_scores': results.clinical_scores, 'anomalies': results.anomalies}
        results.risk_level = await self._run(self._risk_engine, risk_context)
        results.insights = await self._run(self._insight_engine, risk_context)

        recommendation_context = {
            **risk_context,
            'risk_level': results.risk_level,
            'insights': results.insights,
        }
        results.recommendations = await self._run(self._recommendation_engine, recommendation_context)

        narrative_context = {
            **recommendation_context,
            'recommendations': results.recommendations,
        }
        results.narrative = await self._run(self._narrative_engine, narrative_context)
        return results

    async def _run(self, engine_fn, context: dict[str, Any]):
        try:
            result = engine_fn(context)
            if inspect.isawaitable(result):
                return await result
            return result
        except Exception as exc:  # pragma: no cover - exercised in tests
            logger.error('Engine %s failed: %s', getattr(engine_fn, '__name__', 'unknown'), exc)
            return None

    def _clinical_scores_engine(self, context: dict[str, Any]):
        return calculate_clinical_scores(context.get('metrics') or [], context.get('labs') or [])

    def _anomaly_engine(self, context: dict[str, Any]):
        return detect_anomalies(context.get('metrics') or [], context.get('baseline_metrics') or [])

    def _risk_engine(self, context: dict[str, Any]):
        return stratify_risk_level(
            context.get('metrics') or [],
            context.get('labs') or [],
            int(context.get('long_term_symptoms') or 0),
            int(context.get('active_alerts_count') or 0),
        )

    def _insight_engine(self, context: dict[str, Any]):
        user_id = context.get('user_id')
        person_id = context.get('person_id')
        if not user_id or not person_id:
            return context.get('insights')
        return list_active_insights(
            self.db,
            str(user_id),
            str(person_id),
            bool(context.get('include_legacy')),
            limit=int(context.get('insight_limit') or 50),
        )

    def _recommendation_engine(self, context: dict[str, Any]):
        risk_level = context.get('risk_level') or {}
        if isinstance(risk_level, dict):
            risk_value = risk_level.get('risk_level', 'low')
        else:
            risk_value = risk_level or 'low'
        return generate_recommendations(
            context.get('clinical_labels') or [],
            risk_value,
            context.get('alerts') or [],
            float(context.get('calibrated_confidence') or 0.6),
        )

    def _narrative_engine(self, context: dict[str, Any]):
        return generate_health_narrative_v3(
            context.get('narrative_context') or context,
            context.get('previous_narrative'),
            context.get('completed_actions') or [],
        )
