from datetime import date
from datetime import datetime, timezone
import os
import uuid

from decimal import Decimal, InvalidOperation
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.core.cache import cache_invalidate
from app.models.entities import LabReport, LabReportItem, MedicalDocument, PersonProfile, User
from app.schemas.documents import DocumentConfirmRequest, DocumentResponse, ParseResponse, ParsedItemPreview, ParsedItemResponse, ParsedItemUpdate
from app.services.report_parser import extract_text, parse_lab_items
from app.services.risk_engine import evaluate_lab_item_risks
from app.services.storage_service import download_file, upload_file, validate_upload

router = APIRouter(prefix='/documents', tags=['documents'])


def lab_unit_equivalence_key(normalized_unit: Optional[str]) -> Optional[str]:
    """Return the canonical key used for backend unit-equivalence decisions.

    Both NULL and whitespace-only values return None — None is NOT a wildcard
    match; callers receiving None must defer comparison to the frontend
    normalizeUnitForCompare() fallback.
    """
    if not normalized_unit or not normalized_unit.strip():
        return None
    return normalized_unit.strip()


@router.post('/upload', response_model=DocumentResponse)
async def upload_document(
    category: Annotated[str, Form(..., min_length=1, max_length=60)],
    file: Annotated[UploadFile, File(...)],
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    content = await file.read()
    validate_upload(file, content)
    bucket, key = upload_file(str(current_user.id), file, content)

    extension = (file.filename or '').split('.')[-1].lower()
    file_type = 'pdf' if extension == 'pdf' else 'image'
    doc = MedicalDocument(
        user_id=current_user.id,
        subject_profile_id=target_person.id,
        category=category,
        original_filename=os.path.basename(file.filename or '') or 'unknown',
        file_type=file_type,
        mime_type=file.content_type or 'application/octet-stream',
        file_size=len(content),
        storage_bucket=bucket,
        storage_key=key,
        parse_status='pending',
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get('', response_model=list[DocumentResponse])
def list_documents(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    person_filter = MedicalDocument.subject_profile_id == target_person.id
    if target_person.is_default:
        person_filter = or_(person_filter, MedicalDocument.subject_profile_id.is_(None))
    return (
        db.query(MedicalDocument)
        .filter(MedicalDocument.user_id == current_user.id, person_filter)
        .order_by(MedicalDocument.uploaded_at.desc())
        .all()
    )


@router.post('/{document_id}/parse', response_model=ParseResponse)
def parse_document(
    document_id: str,
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='Document not found') from exc
    person_filter = MedicalDocument.subject_profile_id == target_person.id
    if target_person.is_default:
        person_filter = or_(person_filter, MedicalDocument.subject_profile_id.is_(None))
    doc = (
        db.query(MedicalDocument)
        .filter(
            MedicalDocument.id == doc_uuid,
            MedicalDocument.user_id == current_user.id,
            person_filter,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail='Document not found')

    file_bytes = download_file(doc.storage_bucket, doc.storage_key)
    raw_text = extract_text(file_bytes, doc.mime_type)
    report = LabReport(
        user_id=current_user.id,
        subject_profile_id=target_person.id,
        document_id=doc.id,
        report_date=date.today(),
        raw_text=raw_text,
        parser_version='v1',
    )
    db.add(report)
    db.flush()

    extracted = parse_lab_items(raw_text, gender=target_person.gender)
    item_rows: list[LabReportItem] = []
    for row in extracted:
        item = LabReportItem(report_id=report.id, **row)
        db.add(item)
        item_rows.append(item)

    db.flush()
    for item in item_rows:
        alerts = evaluate_lab_item_risks(str(current_user.id), item)
        for alert in alerts:
            alert.subject_profile_id = target_person.id
            db.add(alert)

    doc.parse_status = 'parsed'
    db.commit()

    abnormal_items = sum(1 for row in item_rows if row.abnormal_flag in {'H', 'L'})
    return ParseResponse(
        document_id=str(doc.id),
        report_id=str(report.id),
        extracted_items=len(item_rows),
        abnormal_items=abnormal_items,
        parsed_items_preview=[
            ParsedItemPreview(
                item_name=item.item_name,
                value_num=float(item.value_num) if item.value_num is not None else None,
                value_text=item.value_text,
                unit=item.unit,
                normalized_unit=item.normalized_unit,
                abnormal_flag=item.abnormal_flag,
            )
            for item in item_rows[:20]
        ],
    )


@router.put('/{document_id}/confirm', response_model=DocumentResponse)
def confirm_document(
    document_id: str,
    payload: DocumentConfirmRequest,
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='Document not found') from exc
    person_filter = MedicalDocument.subject_profile_id == target_person.id
    if target_person.is_default:
        person_filter = or_(person_filter, MedicalDocument.subject_profile_id.is_(None))
    doc = (
        db.query(MedicalDocument)
        .filter(
            MedicalDocument.id == doc_uuid,
            MedicalDocument.user_id == current_user.id,
            person_filter,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail='Document not found')

    doc.confirmed_data = payload.confirmed_data
    doc.confirmed_at = datetime.now(timezone.utc)
    doc.parse_status = 'confirmed'
    if payload.report_date is not None:
        lab_report = (
            db.query(LabReport)
            .filter(LabReport.document_id == doc.id)
            .order_by(LabReport.created_at.desc())
            .first()
        )
        if lab_report is not None:
            lab_report.report_date = payload.report_date
    db.commit()
    db.refresh(doc)
    cache_invalidate(f'dashboard:{current_user.id}:')
    return doc


def _resolve_doc(document_id: str, current_user: User, target_person: PersonProfile, db: Session) -> MedicalDocument:
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='Document not found') from exc
    person_filter = MedicalDocument.subject_profile_id == target_person.id
    if target_person.is_default:
        person_filter = or_(person_filter, MedicalDocument.subject_profile_id.is_(None))
    doc = (
        db.query(MedicalDocument)
        .filter(
            MedicalDocument.id == doc_uuid,
            MedicalDocument.user_id == current_user.id,
            person_filter,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail='Document not found')
    return doc


@router.get('/{document_id}/parsed-items', response_model=list[ParsedItemResponse])
def get_parsed_items(
    document_id: str,
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    doc = _resolve_doc(document_id, current_user, target_person, db)
    report = (
        db.query(LabReport)
        .filter(LabReport.document_id == doc.id)
        .order_by(LabReport.created_at.desc())
        .first()
    )
    if not report:
        return []
    items = db.query(LabReportItem).filter(LabReportItem.report_id == report.id).all()
    result = []
    for item in items:
        is_abnormal = item.abnormal_flag in {'H', 'L', 'high', 'low', 'abnormal'}
        # P116: Compute abnormal_flag_reason
        # Conservative, deterministic mapping
        if item.abnormal_flag == 'H':
            abnormal_flag_reason = 'flagged_high'
        elif item.abnormal_flag == 'L':
            abnormal_flag_reason = 'flagged_low'
        elif item.abnormal_flag == 'N':
            abnormal_flag_reason = 'normal_by_rule'
        elif item.abnormal_flag is None:
            # Try to distinguish suppression cases
            # If rule exists but unit-scale mismatch, suppressed
            # If no rule, no_reference_rule
            # If parser_confidence is very low, parser_unavailable
            # Fallback: unknown
            # Use range_source and normalized_unit to infer
            if getattr(item, 'range_source', None) == 'default_rule':
                # Check for unit-scale mismatch
                # If normalized_unit and rule_unit both present but not compatible, suppressed
                # We do not have rule_unit here, so only expose suppressed_unit_scale_mismatch if normalized_unit is present
                if item.normalized_unit and item.unit and item.ref_range:
                    abnormal_flag_reason = 'suppressed_unit_scale_mismatch'
                else:
                    abnormal_flag_reason = 'no_reference_rule'
            elif getattr(item, 'range_source', None) == 'unknown':
                abnormal_flag_reason = 'no_reference_rule'
            elif item.parser_confidence is not None and float(item.parser_confidence) < 0.6:
                abnormal_flag_reason = 'parser_unavailable'
            else:
                abnormal_flag_reason = 'unknown'
        else:
            abnormal_flag_reason = 'unknown'
        result.append(
            ParsedItemResponse(
                id=item.id,
                item_name=item.item_name,
                value_num=float(item.value_num) if item.value_num is not None else None,
                value_text=item.value_text,
                unit=item.unit,
                normalized_unit=item.normalized_unit,
                ref_range=item.ref_range,
                abnormal_flag=item.abnormal_flag,
                abnormal_flag_reason=abnormal_flag_reason,
                parser_confidence=float(item.parser_confidence) if item.parser_confidence is not None else None,
                is_abnormal=is_abnormal,
            )
        )
    return result


@router.patch('/{document_id}/parsed-items/{item_id}', response_model=ParsedItemResponse)
def update_parsed_item(
    document_id: str,
    item_id: str,
    payload: ParsedItemUpdate,
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    doc = _resolve_doc(document_id, current_user, target_person, db)
    try:
        item_uuid = uuid.UUID(item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='Item not found') from exc
    # Ensure item belongs to this document via its report
    report = (
        db.query(LabReport)
        .filter(LabReport.document_id == doc.id)
        .order_by(LabReport.created_at.desc())
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail='Item not found')
    item = (
        db.query(LabReportItem)
        .filter(LabReportItem.id == item_uuid, LabReportItem.report_id == report.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail='Item not found')

    if payload.value is not None:
        try:
            item.value_num = Decimal(payload.value)
            item.value_text = None
        except InvalidOperation:
            item.value_text = payload.value
            item.value_num = None
        # Re-flag abnormal based on updated value
        if item.value_num is not None and item.ref_low is not None and item.ref_high is not None:
            if item.value_num < item.ref_low:
                item.abnormal_flag = 'L'
            elif item.value_num > item.ref_high:
                item.abnormal_flag = 'H'
            else:
                item.abnormal_flag = None

    if payload.unit is not None:
        item.unit = payload.unit
    if payload.reference_range is not None:
        item.ref_range = payload.reference_range

    db.commit()
    db.refresh(item)
    is_abnormal = item.abnormal_flag in {'H', 'L', 'high', 'low', 'abnormal'}
    return ParsedItemResponse(
        id=item.id,
        item_name=item.item_name,
        value_num=float(item.value_num) if item.value_num is not None else None,
        value_text=item.value_text,
        unit=item.unit,
        normalized_unit=item.normalized_unit,
        ref_range=item.ref_range,
        abnormal_flag=item.abnormal_flag,
        parser_confidence=float(item.parser_confidence) if item.parser_confidence is not None else None,
        is_abnormal=is_abnormal,
    )


@router.post('/{document_id}/confirm', response_model=DocumentResponse)
def confirm_document_post(
    document_id: str,
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Mark document as confirmed. Confirmed documents feed into insights engine."""
    doc = _resolve_doc(document_id, current_user, target_person, db)
    doc.confirmed_at = datetime.now(timezone.utc)
    doc.parse_status = 'confirmed'
    if doc.confirmed_data is None:
        doc.confirmed_data = {'reviewed': True}
    db.commit()
    db.refresh(doc)
    cache_invalidate(f'dashboard:{current_user.id}:')
    return doc


@router.get('/lab-history')
def get_lab_history(
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    metric: Optional[str] = Query(default=None, max_length=120),
    limit: int = Query(default=5, ge=2, le=20),
):
    """Return confirmed lab values history for one metric or all metrics."""
    doc_filter = MedicalDocument.subject_profile_id == target_person.id
    report_filter = LabReport.subject_profile_id == target_person.id
    if target_person.is_default:
        doc_filter = or_(doc_filter, MedicalDocument.subject_profile_id.is_(None))
        report_filter = or_(report_filter, LabReport.subject_profile_id.is_(None))

    q = (
        db.query(LabReportItem, LabReport, MedicalDocument)
        .join(LabReport, LabReportItem.report_id == LabReport.id)
        .join(MedicalDocument, LabReport.document_id == MedicalDocument.id)
        .filter(
            MedicalDocument.user_id == current_user.id,
            LabReport.user_id == current_user.id,
            doc_filter,
            report_filter,
            MedicalDocument.confirmed_at.isnot(None),
        )
        .order_by(LabReport.report_date.desc().nullslast(), LabReport.created_at.desc())
    )

    metric_lc = metric.lower() if metric else None
    rows = []
    for item, report, document in q.all():
        if metric_lc and metric_lc not in (item.item_name or '').lower() and metric_lc not in (item.item_code or '').lower():
            continue
        rows.append(
            {
                'metric': item.item_name,
                'report_date': report.report_date.isoformat() if report.report_date else None,
                'document_id': str(document.id),
                'document_name': document.original_filename,
                'value': float(item.value_num) if item.value_num is not None else item.value_text,
                'unit': item.unit,
                'normalized_unit': item.normalized_unit,
                'unit_equivalence_key': lab_unit_equivalence_key(item.normalized_unit),
                'is_abnormal': item.abnormal_flag in {'H', 'L'},
                'reference_range': item.ref_range,
            }
        )

    if metric_lc:
        return rows[:limit]

    # no metric: keep most recent N points per marker
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        marker = row['metric'] or 'Unknown'
        grouped.setdefault(marker, [])
        if len(grouped[marker]) < limit:
            grouped[marker].append(row)

    flattened: list[dict] = []
    for marker, values in grouped.items():
        flattened.extend(values)
    return flattened
