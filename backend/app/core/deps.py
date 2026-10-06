import uuid
from typing import Optional

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.entities import PersonProfile, User, UserProfile

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get('sub')
        if not user_id:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise credentials_exception
    return user


def ensure_default_person_profile(db: Session, current_user: User) -> PersonProfile:
    person = (
        db.query(PersonProfile)
        .filter(PersonProfile.owner_user_id == current_user.id, PersonProfile.is_default.is_(True))
        .first()
    )
    if person:
        return person

    legacy_profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    person = PersonProfile(
        owner_user_id=current_user.id,
        display_name=(legacy_profile.full_name if legacy_profile and legacy_profile.full_name else '本人'),
        relationship='self',
        birth_date=legacy_profile.birth_date if legacy_profile else None,
        gender=legacy_profile.gender if legacy_profile else None,
        height_cm=legacy_profile.height_cm if legacy_profile else None,
        weight_kg=legacy_profile.weight_kg if legacy_profile else None,
        allergies=legacy_profile.allergies if legacy_profile else None,
        family_history=legacy_profile.family_history if legacy_profile else None,
        chronic_conditions=legacy_profile.chronic_conditions if legacy_profile else None,
        is_default=True,
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def get_target_person(
    person_id: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PersonProfile:
    default_person = ensure_default_person_profile(db, current_user)
    if not person_id:
        return default_person
    try:
        person_uuid = uuid.UUID(person_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='Person profile not found') from exc

    person = (
        db.query(PersonProfile)
        .filter(PersonProfile.id == person_uuid, PersonProfile.owner_user_id == current_user.id)
        .first()
    )
    if not person:
        raise HTTPException(status_code=404, detail='Person profile not found')
    return person
