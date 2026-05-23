from typing import Optional, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ParsedItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_name: str
    value_num: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    ref_range: Optional[str] = None
    abnormal_flag: Optional[str] = None
    parser_confidence: Optional[float] = None
    is_abnormal: bool = False


class ParsedItemUpdate(BaseModel):
    value: Optional[str] = Field(default=None, max_length=500)
    unit: Optional[str] = Field(default=None, max_length=50)
    reference_range: Optional[str] = Field(default=None, max_length=100)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: str
    subject_profile_id: Optional[UUID] = None
    original_filename: str
    file_type: str
    mime_type: str
    file_size: int
    storage_bucket: str
    storage_key: str
    parse_status: str
    confirmed_data: Optional[dict[str, Any]] = None
    confirmed_at: Optional[datetime] = None
    uploaded_at: datetime


class ParsedItemPreview(BaseModel):
    item_name: str
    value_num: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    abnormal_flag: Optional[str] = None


class ParseResponse(BaseModel):
    document_id: str
    report_id: str
    extracted_items: int
    abnormal_items: int
    parsed_items_preview: list[ParsedItemPreview]


class DocumentConfirmRequest(BaseModel):
    confirmed_data: dict[str, Any]


class ConfirmSimpleRequest(BaseModel):
    """Simple confirm — no payload required, triggers insight generation."""
    pass
