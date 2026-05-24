from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.models.entities import PersonProfile, User
from app.schemas.profile import AccountResponse, AccountUpdateRequest, ProfileResponse, ProfileUpsertRequest

router = APIRouter(prefix='/profile', tags=['profile'])


@router.get('/me', response_model=ProfileResponse)
def get_my_profile(target_person: PersonProfile = Depends(get_target_person)):
    return {
        'id': target_person.id,
        'full_name': target_person.display_name,
        'birth_date': target_person.birth_date,
        'gender': target_person.gender,
        'height_cm': target_person.height_cm,
        'weight_kg': target_person.weight_kg,
        'allergies': target_person.allergies,
        'family_history': target_person.family_history,
        'chronic_conditions': target_person.chronic_conditions,
    }


@router.put('/me', response_model=ProfileResponse)
def upsert_profile(
    payload: ProfileUpsertRequest,
    target_person: PersonProfile = Depends(get_target_person),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_person.display_name = payload.full_name or target_person.display_name
    target_person.birth_date = payload.birth_date
    target_person.gender = payload.gender
    target_person.height_cm = payload.height_cm
    target_person.weight_kg = payload.weight_kg
    target_person.allergies = payload.allergies
    target_person.family_history = payload.family_history
    target_person.chronic_conditions = payload.chronic_conditions

    db.commit()
    db.refresh(target_person)
    return {
        'id': target_person.id,
        'full_name': target_person.display_name,
        'birth_date': target_person.birth_date,
        'gender': target_person.gender,
        'height_cm': target_person.height_cm,
        'weight_kg': target_person.weight_kg,
        'allergies': target_person.allergies,
        'family_history': target_person.family_history,
        'chronic_conditions': target_person.chronic_conditions,
    }


@router.get('/account', response_model=AccountResponse)
def get_account(current_user: User = Depends(get_current_user)):
    return AccountResponse(
        id=current_user.id,
        email=current_user.email,
        account_settings=current_user.account_settings or {},
    )


@router.put('/account', response_model=AccountResponse)
def update_account(
    payload: AccountUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.email:
        current_user.email = payload.email.lower()
    if payload.account_settings is not None:
        current_user.account_settings = payload.account_settings
    db.commit()
    db.refresh(current_user)
    return AccountResponse(
        id=current_user.id,
        email=current_user.email,
        account_settings=current_user.account_settings or {},
    )
