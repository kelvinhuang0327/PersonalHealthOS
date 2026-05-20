from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.models.entities import PersonProfile, User
from app.schemas.timeline import TimelineResponse
from app.services.timeline_service import build_health_timeline

router = APIRouter(prefix='/timeline', tags=['timeline'])


@router.get('', response_model=TimelineResponse)
def get_timeline(
    days: int = Query(default=180, ge=7, le=3650),
    limit: int = Query(default=200, ge=10, le=1000),
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = build_health_timeline(
        db,
        str(current_user.id),
        person_id=str(target_person.id),
        include_legacy=target_person.is_default,
        days=days,
        limit=limit,
    )
    return TimelineResponse(items=items)
