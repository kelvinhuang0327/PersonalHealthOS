from fastapi import APIRouter

from app.api import (
    actions,
    ai_modules,
    ai_summary,
    analytics,
    auth,
    dashboard,
    external_metrics,
    documents,
    health_assistant,
    health_score,
    insights,
    metrics,
    persons,
    profile,
    reports,
    risk_alerts,
    symptoms,
    timeline,
)
from app.orchestrator import api as agent_orchestrator_api

api_router = APIRouter(prefix='/api/v1')
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(reports.router)
api_router.include_router(persons.router)
api_router.include_router(metrics.router)
api_router.include_router(symptoms.router)
api_router.include_router(documents.router)
api_router.include_router(risk_alerts.router)
api_router.include_router(dashboard.router)
api_router.include_router(insights.router)
api_router.include_router(external_metrics.router)
api_router.include_router(ai_summary.router)
api_router.include_router(ai_modules.router)
api_router.include_router(timeline.router)
api_router.include_router(analytics.router)
api_router.include_router(health_score.router)
api_router.include_router(actions.router)
api_router.include_router(health_assistant.router)
api_router.include_router(agent_orchestrator_api.router)
