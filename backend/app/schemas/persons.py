from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PersonCreateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    relationship: str = Field(default='family', max_length=30)
    birth_date: Optional[date] = None
    gender: Optional[str] = Field(default=None, max_length=20)
    height_cm: Optional[float] = Field(default=None, ge=50, le=250)
    weight_kg: Optional[float] = Field(default=None, ge=20, le=500)
    allergies: Optional[str] = Field(default=None, max_length=2000)
    family_history: Optional[str] = Field(default=None, max_length=2000)
    chronic_conditions: Optional[str] = Field(default=None, max_length=2000)


class PersonUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    relationship: Optional[str] = Field(default=None, max_length=30)
    birth_date: Optional[date] = None
    gender: Optional[str] = Field(default=None, max_length=20)
    height_cm: Optional[float] = Field(default=None, ge=50, le=250)
    weight_kg: Optional[float] = Field(default=None, ge=20, le=500)
    allergies: Optional[str] = Field(default=None, max_length=2000)
    family_history: Optional[str] = Field(default=None, max_length=2000)
    chronic_conditions: Optional[str] = Field(default=None, max_length=2000)
    is_default: Optional[bool] = None


class PersonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_user_id: UUID
    display_name: str
    relationship: str
    birth_date: Optional[date]
    gender: Optional[str]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    allergies: Optional[str]
    family_history: Optional[str]
    chronic_conditions: Optional[str]
    is_default: bool
    created_at: datetime
    updated_at: datetime
