from datetime import date
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProfileUpsertRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=120)
    birth_date: Optional[date] = None
    gender: Optional[str] = Field(default=None, max_length=20)
    height_cm: Optional[float] = Field(default=None, ge=50, le=250)
    weight_kg: Optional[float] = Field(default=None, ge=20, le=500)
    allergies: Optional[str] = Field(default=None, max_length=2000)
    family_history: Optional[str] = Field(default=None, max_length=2000)
    chronic_conditions: Optional[str] = Field(default=None, max_length=2000)


class ProfileResponse(ProfileUpsertRequest):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class AccountResponse(BaseModel):
    id: UUID
    email: str
    account_settings: dict


class AccountUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    account_settings: Optional[dict] = None
