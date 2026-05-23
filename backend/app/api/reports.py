from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_target_person
from app.models.entities import HealthAction, HealthInsight, HealthMetric, HealthScore, LabReport, LabReportItem, MedicalDocument, PersonProfile, User

router = APIRouter(prefix='/reports', tags=['reports'])

REPORT_DIR = Path(__file__).resolve().parents[3] / 'uploads' / 'reports'
REPORT_DIR.mkdir(parents=True, exist_ok=True)
_REPORT_STATE: dict[str, dict[str, Any]] = {}


class ReportGenerateRequest(BaseModel):
    person_id: Optional[str] = Field(default=None, max_length=36)
    include_sections: list[Annotated[str, Field(max_length=60)]] = Field(
        default_factory=lambda: ['score', 'metrics', 'labs', 'insights', 'actions'],
        max_length=20,
    )


class ReportGenerateResponse(BaseModel):
    report_id: str
    status: str


class ReportStatusResponse(BaseModel):
    status: str
    download_url: Optional[str] = None


def _build_minimal_pdf(lines: list[str]) -> bytes:
    safe_lines = [line.replace('(', '[').replace(')', ']') for line in lines]
    stream_lines = ['BT /F1 12 Tf 50 770 Td']
    for i, line in enumerate(safe_lines):
      y = 770 - (i * 16)
      stream_lines.append(f'50 {y} Td ({line}) Tj')
    stream_lines.append('ET')
    stream = '\n'.join(stream_lines)

    objects: list[str] = []
    objects.append('1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj')
    objects.append('2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj')
    objects.append('3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj')
    objects.append('4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj')
    objects.append(f'5 0 obj << /Length {len(stream.encode("utf-8"))} >> stream\n{stream}\nendstream endobj')

    body = '%PDF-1.4\n'
    offsets = [0]
    for obj in objects:
        offsets.append(len(body.encode('utf-8')))
        body += obj + '\n'
    xref_pos = len(body.encode('utf-8'))
    body += f'xref\n0 {len(objects)+1}\n'
    body += '0000000000 65535 f \n'
    for offset in offsets[1:]:
        body += f'{offset:010d} 00000 n \n'
    body += f'trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n'
    return body.encode('utf-8')


def _build_report_lines(db: Session, user: User, person: PersonProfile, include_sections: list[str]) -> list[str]:
    lines = [
        'PersonalHealthOS Health Summary Report',
        f'Name: {person.display_name}',
        f'Date: {datetime.now(timezone.utc).date().isoformat()}',
        '',
    ]

    person_filter_score = HealthScore.subject_profile_id == person.id
    person_filter_metric = HealthMetric.subject_profile_id == person.id
    person_filter_insight = HealthInsight.subject_profile_id == person.id
    person_filter_action = HealthAction.person_id == person.id
    person_filter_report = LabReport.subject_profile_id == person.id
    person_filter_doc = MedicalDocument.subject_profile_id == person.id

    if person.is_default:
        person_filter_score = or_(person_filter_score, HealthScore.subject_profile_id.is_(None))
        person_filter_metric = or_(person_filter_metric, HealthMetric.subject_profile_id.is_(None))
        person_filter_insight = or_(person_filter_insight, HealthInsight.subject_profile_id.is_(None))
        person_filter_action = or_(person_filter_action, HealthAction.person_id.is_(None))
        person_filter_report = or_(person_filter_report, LabReport.subject_profile_id.is_(None))
        person_filter_doc = or_(person_filter_doc, MedicalDocument.subject_profile_id.is_(None))

    if 'score' in include_sections:
        latest_score = (
            db.query(HealthScore)
            .filter(HealthScore.user_id == user.id, person_filter_score)
            .order_by(HealthScore.calculated_at.desc())
            .first()
        )
        lines.append(f'Health Score: {latest_score.overall_score if latest_score else "N/A"}')

    if 'metrics' in include_sections:
        latest_metric = (
            db.query(HealthMetric)
            .filter(HealthMetric.user_id == user.id, person_filter_metric)
            .order_by(HealthMetric.recorded_at.desc())
            .first()
        )
        if latest_metric:
            lines.append(f'Metrics: BP {latest_metric.systolic_bp}/{latest_metric.diastolic_bp}, Weight {latest_metric.weight_kg}, Glucose {latest_metric.blood_glucose}')
        else:
            lines.append('Metrics: N/A')

    if 'labs' in include_sections:
        latest_report = (
            db.query(LabReport, MedicalDocument)
            .join(MedicalDocument, LabReport.document_id == MedicalDocument.id)
            .filter(LabReport.user_id == user.id, person_filter_report, person_filter_doc, MedicalDocument.confirmed_at.isnot(None))
            .order_by(LabReport.report_date.desc().nullslast(), LabReport.created_at.desc())
            .first()
        )
        if latest_report:
            report, document = latest_report
            items = (
                db.query(LabReportItem)
                .filter(LabReportItem.report_id == report.id)
                .limit(5)
                .all()
            )
            lab_text = ', '.join([f'{it.item_name}:{it.value_num or it.value_text}{it.unit or ""}' for it in items])
            lines.append(f'Latest Labs ({document.original_filename}): {lab_text or "N/A"}')
        else:
            lines.append('Latest Labs: N/A')

    if 'insights' in include_sections:
        insights = (
            db.query(HealthInsight)
            .filter(HealthInsight.user_id == user.id, person_filter_insight, HealthInsight.is_active == True)  # noqa: E712
            .order_by(HealthInsight.generated_at.desc())
            .limit(5)
            .all()
        )
        lines.append(f'Insights: {"; ".join([ins.title for ins in insights]) if insights else "N/A"}')

    if 'actions' in include_sections:
        actions = (
            db.query(HealthAction)
            .filter(HealthAction.user_id == user.id, person_filter_action, HealthAction.status.in_(['todo', 'in_progress']))
            .order_by(HealthAction.created_at.desc())
            .limit(5)
            .all()
        )
        lines.append(f'Actions: {"; ".join([a.title for a in actions]) if actions else "N/A"}')

    lines.extend(['', 'Disclaimer: 本報告由 PersonalHealthOS 生成，僅供參考，非醫療診斷。'])
    return lines


@router.post('/generate', response_model=ReportGenerateResponse, status_code=202)
def generate_report(
    payload: ReportGenerateRequest,
    target_person: Annotated[PersonProfile, Depends(get_target_person)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    report_id = str(uuid4())
    token = str(uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    _REPORT_STATE[report_id] = {
        'status': 'generating',
        'token': token,
        'expires_at': expires_at,
        'owner_user_id': str(current_user.id),
    }

    person = target_person
    if payload.person_id and payload.person_id != str(target_person.id):
        person = (
            db.query(PersonProfile)
            .filter(PersonProfile.id == payload.person_id, PersonProfile.owner_user_id == current_user.id)
            .first()
        ) or target_person

    lines = _build_report_lines(db, current_user, person, payload.include_sections)
    file_path = REPORT_DIR / f'{report_id}.pdf'
    file_path.write_bytes(_build_minimal_pdf(lines))
    _REPORT_STATE[report_id] = {
        'status': 'ready',
        'token': token,
        'expires_at': expires_at,
        'file_path': str(file_path),
        'owner_user_id': str(current_user.id),
    }
    return ReportGenerateResponse(report_id=report_id, status='generating')


@router.get('/{report_id}', response_model=ReportStatusResponse)
def get_report_status(
    report_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    state = _REPORT_STATE.get(report_id)
    if not state:
        raise HTTPException(status_code=404, detail='Report not found')
    if str(state.get('owner_user_id')) != str(current_user.id):
        raise HTTPException(status_code=404, detail='Report not found')
    if state['status'] != 'ready':
        return ReportStatusResponse(status=state['status'])
    if datetime.now(timezone.utc) > state['expires_at']:
        return ReportStatusResponse(status='failed')
    url = f'/api/v1/reports/download/{report_id}?token={state["token"]}'
    return ReportStatusResponse(status='ready', download_url=url)


@router.get('/download/{report_id}')
def download_report(
    report_id: str,
    token: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    state = _REPORT_STATE.get(report_id)
    if not state or state.get('status') != 'ready':
        raise HTTPException(status_code=404, detail='Report not ready')
    if str(state.get('owner_user_id')) != str(current_user.id):
        raise HTTPException(status_code=404, detail='Report not found')
    if token != state.get('token'):
        raise HTTPException(status_code=403, detail='Invalid token')
    if datetime.now(timezone.utc) > state['expires_at']:
        raise HTTPException(status_code=403, detail='Link expired')
    return FileResponse(state['file_path'], media_type='application/pdf', filename=f'health_report_{report_id}.pdf')
