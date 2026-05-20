from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import ensure_default_person_profile, get_current_user
from app.models.entities import PersonProfile, User
from app.schemas.persons import PersonCreateRequest, PersonResponse, PersonUpdateRequest

router = APIRouter(prefix='/persons', tags=['persons'])


@router.get('', response_model=list[PersonResponse])
def list_persons(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_default_person_profile(db, current_user)
    return (
        db.query(PersonProfile)
        .filter(PersonProfile.owner_user_id == current_user.id)
        .order_by(PersonProfile.is_default.desc(), PersonProfile.created_at.asc())
        .all()
    )


@router.post('', response_model=PersonResponse)
def create_person(
    payload: PersonCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_default_person_profile(db, current_user)
    person = PersonProfile(owner_user_id=current_user.id, **payload.model_dump())
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@router.put('/{person_id}', response_model=PersonResponse)
def update_person(
    person_id: str,
    payload: PersonUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    person = (
        db.query(PersonProfile)
        .filter(PersonProfile.id == person_id, PersonProfile.owner_user_id == current_user.id)
        .first()
    )
    if not person:
        raise HTTPException(status_code=404, detail='Person profile not found')

    data = payload.model_dump(exclude_unset=True)
    if data.get('is_default'):
        (
            db.query(PersonProfile)
            .filter(PersonProfile.owner_user_id == current_user.id, PersonProfile.id != person.id)
            .update({'is_default': False})
        )

    for field, value in data.items():
        setattr(person, field, value)
    db.commit()
    db.refresh(person)
    return person


@router.delete('/{person_id}', status_code=204)
def delete_person(
    person_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    person = (
        db.query(PersonProfile)
        .filter(PersonProfile.id == person_id, PersonProfile.owner_user_id == current_user.id)
        .first()
    )
    if not person:
        raise HTTPException(status_code=404, detail='Person profile not found')
    if person.is_default:
        raise HTTPException(status_code=400, detail='Default profile cannot be deleted')

    db.delete(person)
    db.commit()
