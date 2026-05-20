import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
import uuid

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.models.entities import HealthInsight, PersonProfile, User
from app.schemas.insights import HealthInsightResponse
from app.services.health_insights_service import generate_health_insights
from app.services.health_ai_engine.orchestrator import HealthEngineOrchestrator
from app.services.health_ai_engine.insight_engine import list_active_insights

router = APIRouter(prefix='/insights', tags=['insights'])


@router.get('', response_model=list[HealthInsightResponse])
def list_insights(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return list_active_insights(db, str(current_user.id), str(target_person.id), target_person.is_default, limit=50)


@router.post('/generate', response_model=list[HealthInsightResponse])
def generate_insights(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    orchestrator = HealthEngineOrchestrator(db, target_person)
    asyncio.run(
        orchestrator.run_full_analysis(
            {
                'user_id': str(current_user.id),
                'person_id': str(target_person.id),
                'include_legacy': target_person.is_default,
            }
        )
    )
    return generate_health_insights(db, str(current_user.id), target_person, target_person.is_default)


@router.post('/{insight_id}/dismiss', response_model=HealthInsightResponse, responses={404: {'description': 'Insight not found'}})
def dismiss_insight(
    insight_id: str,
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    insight_filter = HealthInsight.subject_profile_id == target_person.id
    if target_person.is_default:
        insight_filter = or_(insight_filter, HealthInsight.subject_profile_id.is_(None))
    row = (
        db.query(HealthInsight)
        .filter(HealthInsight.id == _uuid_or_raw(insight_id), HealthInsight.user_id == current_user.id, insight_filter)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail='Insight not found')
    row.is_active = False
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _uuid_or_raw(value: str):
    try:
        return uuid.UUID(value)
    except ValueError:
        return value
