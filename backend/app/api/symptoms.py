import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.models.entities import PersonProfile, SymptomLog, User
from app.schemas.symptoms import SymptomCreateRequest, SymptomResponse, SymptomUpdateRequest
from app.services.temporal_symptom_parser import parse_temporal_symptom

router = APIRouter(prefix='/symptoms', tags=['symptoms'])


@router.post('', response_model=SymptomResponse)
def create_symptom(
    payload: SymptomCreateRequest,
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payload_data = payload.model_dump()
    symptom_names = payload_data.get('symptom_names') or []
    base_occurred_at = payload_data.get('occurred_at') or datetime.now(timezone.utc)

    if payload_data.get('duration_category') and payload_data.get('estimated_duration_days') is None:
        duration_map = {
            'today': 1,
            'days': 3,
            'week_plus': 10,
            'chronic': 30,
        }
        payload_data['estimated_duration_days'] = duration_map.get(str(payload_data.get('duration_category')), None)

    created_symptoms: list[SymptomLog] = []
    resolved_names = symptom_names if symptom_names else [payload_data.get('symptom')]

    for name in resolved_names:
        if not name:
            continue
        parsed = parse_temporal_symptom(payload.note or str(name))
        row_data = {
            'symptom': parsed.get('symptom') if str(name) == '歷史症狀自述' and parsed.get('symptom') else name,
            'occurred_at': base_occurred_at,
            'duration_minutes': payload_data.get('duration_minutes'),
            'severity': payload_data.get('severity'),
            'note': payload_data.get('note'),
            'estimated_start_date': payload_data.get('estimated_start_date') or parsed.get('estimated_start_date'),
            'estimated_duration_days': payload_data.get('estimated_duration_days') or parsed.get('estimated_duration_days'),
            'temporal_source': payload_data.get('temporal_source') or parsed.get('temporal_source'),
            'confidence_score': payload_data.get('confidence_score') or parsed.get('confidence_score'),
        }
        symptom = SymptomLog(
            user_id=current_user.id,
            subject_profile_id=target_person.id,
            **row_data,
        )
        db.add(symptom)
        created_symptoms.append(symptom)

    db.commit()
    first = created_symptoms[0]
    db.refresh(first)
    return first


@router.get('', response_model=list[SymptomResponse])
def list_symptoms(
    limit: int = Query(default=50, ge=1, le=200),
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    person_filter = SymptomLog.subject_profile_id == target_person.id
    if target_person.is_default:
        person_filter = or_(person_filter, SymptomLog.subject_profile_id.is_(None))
    return (
        db.query(SymptomLog)
        .filter(SymptomLog.user_id == current_user.id, person_filter)
        .order_by(SymptomLog.occurred_at.desc())
        .limit(limit)
        .all()
    )


@router.put('/{symptom_id}', response_model=SymptomResponse)
def update_symptom(
    symptom_id: str,
    payload: SymptomUpdateRequest,
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        symptom_uuid = uuid.UUID(symptom_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='Symptom not found') from exc

    person_filter = SymptomLog.subject_profile_id == target_person.id
    if target_person.is_default:
        person_filter = or_(person_filter, SymptomLog.subject_profile_id.is_(None))

    symptom = (
        db.query(SymptomLog)
        .filter(
            SymptomLog.id == symptom_uuid,
            SymptomLog.user_id == current_user.id,
            person_filter,
        )
        .first()
    )
    if not symptom:
        raise HTTPException(status_code=404, detail='Symptom not found')

    update_data = payload.model_dump(exclude_unset=True)
    should_parse = 'note' in update_data or 'symptom' in update_data
    if should_parse:
        parsed = parse_temporal_symptom(update_data.get('note') or update_data.get('symptom') or symptom.note or symptom.symptom)
        if update_data.get('symptom') == '歷史症狀自述' and parsed.get('symptom'):
            update_data['symptom'] = parsed['symptom']
        if 'estimated_start_date' not in update_data:
            update_data['estimated_start_date'] = parsed.get('estimated_start_date')
        if 'estimated_duration_days' not in update_data:
            update_data['estimated_duration_days'] = parsed.get('estimated_duration_days')
        if 'temporal_source' not in update_data:
            update_data['temporal_source'] = parsed.get('temporal_source')
        if 'confidence_score' not in update_data:
            update_data['confidence_score'] = parsed.get('confidence_score')

    for field, value in update_data.items():
        setattr(symptom, field, value)
    db.commit()
    db.refresh(symptom)
    return symptom
