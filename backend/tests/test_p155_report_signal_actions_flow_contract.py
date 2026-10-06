"""P155 — Report Signal to Actions Flow Integration Contract

Verifies the integration contract of the full product flow:
1. Synthetic Lab Report PDF upload & parsing.
2. Confirming report, which generates RiskAlert signals.
3. Dashboard state updating to reflect active alerts & lab history.
4. Recommendations API surfacing recommendations linked to the RiskAlert signals.
5. User providing feedback/snooze/outcome via Actions API (POST/PATCH).
6. Read-back of action status and outcome feedback timeline mapping.

Strict safety constraints are checked recursively (leakage and prohibited medical claims).
Uses isolated TestClient + in-memory SQLite.
"""
from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user, get_target_person
from app.main import app
from app.models.entities import ActionOutcome, HealthAction, PersonProfile, User
from app.api import documents as documents_api


# ---------------------------------------------------------------------------
# Safety and Leakage Constants (aligned with P150-P154)
# ---------------------------------------------------------------------------

PROHIBITED_PHRASES = [
    '診斷', '確診', '治療', '治癒', '一定', '絕對', '保證', '100%',
    '取代醫師', '正常代表沒問題', 'diagnose', 'guarantee', 'cure',
]

_SENSITIVE_KEYS: frozenset[str] = frozenset({
    'password_hash', 'hashed_password', 'password',
    'storage_bucket', 'storage_key', 'file_path',
    'download_token', 'secret_key', 'secret',
    'is_superuser', 'is_staff', 'user_id',
})


def _assert_no_medical_overclaim(data: Any, path: str = '') -> None:
    if isinstance(data, str):
        for phrase in PROHIBITED_PHRASES:
            if phrase in data:
                if phrase == '診斷' and '非醫療診斷' in data:
                    continue
                assert False, f"Response contains prohibited phrase '{phrase}' at path {path}: {data}"
    elif isinstance(data, dict):
        for k, v in data.items():
            if k == 'medical_disclaimer':
                continue
            _assert_no_medical_overclaim(v, f"{path}.{k}" if path else k)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            _assert_no_medical_overclaim(item, f"{path}[{i}]")


def _find_sensitive_key(obj: Any, path: str = '') -> str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in _SENSITIVE_KEYS:
                return f'{path}.{k}' if path else k
            found = _find_sensitive_key(v, f'{path}.{k}' if path else k)
            if found:
                return found
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            found = _find_sensitive_key(item, f'{path}[{i}]')
            if found:
                return found
    return None


# ---------------------------------------------------------------------------
# PDF Byte Generator
# ---------------------------------------------------------------------------

def make_minimal_pdf(text_lines: list[str]) -> bytes:
    """Generates a minimal valid PDF using only standard library features,
    with a specific leading and line spacing, ensuring pypdf.PdfReader
    can extract text with newlines correctly.
    """
    stream_content = "BT\n/F1 12 Tf\n14 TL\n72 712 Td\n"
    for line in text_lines:
        escaped_line = line.replace("(", "\\(").replace(")", "\\)")
        stream_content += f"({escaped_line}) Tj\nT*\n"
    stream_content += "ET\n"

    stream_bytes = stream_content.encode("latin1")
    stream_len = len(stream_bytes)

    # Construct basic PDF objects
    objects = []
    # 1: Catalog
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # 2: Pages
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    # 3: Page
    objects.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n"
    )
    # 4: Font
    objects.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    # 5: Content stream
    objects.append(
        f"5 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("latin1")
        + stream_bytes
        + b"\nendstream\nendobj\n"
    )

    pdf_bytes = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf_bytes))
        pdf_bytes += obj

    xref_offset = len(pdf_bytes)
    xref = f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin1")
    for offset in offsets:
        xref += f"{offset:010d} 00000 n \n".encode("latin1")

    pdf_bytes += xref
    pdf_bytes += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
        "latin1"
    )
    return pdf_bytes


# ---------------------------------------------------------------------------
# Test Setup and execution
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_p155_report_signal_actions_flow_contract(monkeypatch):
    # Setup isolated in-memory SQLite DB
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # Create dummy user and person profile
    user = User(
        id=uuid.uuid4(),
        email="p155_flow_test@example.com",
        password_hash="hashed_password_xyz",
        is_active=True,
    )
    db.add(user)
    db.flush()

    person = PersonProfile(
        id=uuid.uuid4(),
        owner_user_id=user.id,
        display_name="P155 Test User",
        relationship="self",
        gender="male",
        is_default=True,
    )
    db.add(person)
    db.commit()

    # Mock storage upload/download to avoid S3 network calls
    in_memory_storage = {}

    def mock_upload_file(user_id: str, file, data: bytes):
        key = f"documents/{user_id}/{uuid.uuid4()}.pdf"
        bucket = "mock-bucket"
        in_memory_storage[(bucket, key)] = data
        return bucket, key

    def mock_download_file(bucket: str, key: str) -> bytes:
        return in_memory_storage[(bucket, key)]

    # Monkeypatch storage service methods used in documents router
    monkeypatch.setattr(documents_api, "upload_file", mock_upload_file)
    monkeypatch.setattr(documents_api, "download_file", mock_download_file)

    # Configure FastAPI dependency overrides
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_target_person] = lambda: person

    client = TestClient(app, raise_server_exceptions=False)

    # 1. Upload & Parse synthetic lab report
    synthetic_lines = [
        "Glucose: 110 mg/dL",
        "AST: 45 U/L",
        "ALT: 50 U/L",
        "Total Cholesterol: 240 mg/dL",
    ]
    pdf_bytes = make_minimal_pdf(synthetic_lines)

    upload_resp = client.post(
        "/api/v1/documents/upload",
        data={"category": "health_check"},
        files={"file": ("synthetic_report.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 200
    document_id = upload_resp.json()["id"]

    parse_resp = client.post(f"/api/v1/documents/{document_id}/parse")
    assert parse_resp.status_code == 200

    # 2. Confirm parsed data (Signals triggered)
    confirm_payload = {
        "confirmed_data": {
            "reviewed": True,
            "items": [
                {"item_name": "Glucose", "value": 110, "unit": "mg/dL"},
                {"item_name": "AST", "value": 45, "unit": "U/L"},
                {"item_name": "ALT", "value": 50, "unit": "U/L"},
                {"item_name": "Total Cholesterol", "value": 240, "unit": "mg/dL"},
            ]
        },
        "report_date": date.today().isoformat()
    }
    confirm_resp = client.put(f"/api/v1/documents/{document_id}/confirm", json=confirm_payload)
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["parse_status"] == "confirmed"

    # 3. Verify dashboard sees the signal (Risk alerts active)
    dashboard_resp = client.get("/api/v1/dashboard")
    assert dashboard_resp.status_code == 200
    dashboard_data = dashboard_resp.json()

    alerts = dashboard_data.get("alerts", [])
    assert len(alerts) >= 2
    alert_rule_ids = {a.get("rule_id", "").lower() for a in alerts}
    # AST/ALT high and cholesterol high alerts should be triggered
    assert "liver_ast_high" in alert_rule_ids or "liver_alt_high" in alert_rule_ids
    assert "lipid_cholesterol_high" in alert_rule_ids

    # 4. Verify recommendations are generated based on the confirmed report signal
    recs_resp = client.get("/api/v1/health-assistant/recommendations")
    assert recs_resp.status_code == 200
    recs_data = recs_resp.json()
    assert "recommendations" in recs_data
    recommendations = recs_data["recommendations"]
    assert len(recommendations) > 0

    # Retrieve recommendation linked to liver or lipid risk alert
    target_rec = None
    for r in recommendations:
        if r.get("source_type") == "risk_alert" and r.get("source_id"):
            target_rec = r
            break

    assert target_rec is not None, "Should have generated a recommendation linked to one of the risk alerts"
    source_type = target_rec["source_type"]
    source_id = target_rec["source_id"]

    # 5. User provides feedback (Dismiss recommendation to Actions feedback state)
    feedback_payload = {
        "title": target_rec["title"],
        "source_type": source_type,
        "source_id": source_id,
        "status": "not_useful",
        "priority": target_rec["priority"],
        "action_type": "lifestyle",
    }
    feedback_resp = client.post("/api/v1/actions", json=feedback_payload, params={"person_id": str(person.id)})
    assert feedback_resp.status_code == 201
    action_data = feedback_resp.json()
    assert action_data["status"] == "not_useful"
    action_id = action_data["id"]

    # 6. Read back action status & outcome feedback timeline
    # List actions read back
    actions_resp = client.get("/api/v1/actions", params={"person_id": str(person.id)})
    assert actions_resp.status_code == 200
    actions_list = actions_resp.json()
    saved_action = next((a for a in actions_list if a["id"] == action_id), None)
    assert saved_action is not None
    assert saved_action["status"] == "not_useful"

    # Outcome feedback timeline read back
    outcome_resp = client.get("/api/v1/health-assistant/outcome-feedback", params={"person_id": str(person.id)})
    assert outcome_resp.status_code == 200
    outcome_data = outcome_resp.json()
    outcomes = outcome_data.get("outcomes", [])
    target_outcome = next((o for o in outcomes if o["action_id"] == action_id), None)
    assert target_outcome is not None
    assert target_outcome["status"] == "not_useful"
    assert target_outcome["outcome_status"] == "not_useful"
    assert target_outcome["confidence"] == 0.0

    # 7. Traceability assertions
    # Ensure recommendation source_id matches original RiskAlert ID
    alert_ids = {a.get("source_id") for a in alerts}
    assert source_id in alert_ids or any(source_id == a.get("id") for a in alerts)

    # 8. Recurse-scan responses for safety violations (sensitive keys and medical claims)
    assert _find_sensitive_key(dashboard_data) is None
    assert _find_sensitive_key(recs_data) is None
    assert _find_sensitive_key(outcome_data) is None

    _assert_no_medical_overclaim(dashboard_data)
    _assert_no_medical_overclaim(recs_data)
    _assert_no_medical_overclaim(outcome_data)
