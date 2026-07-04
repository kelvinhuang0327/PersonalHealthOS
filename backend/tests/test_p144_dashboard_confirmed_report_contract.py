from __future__ import annotations

import io
import uuid
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user, get_target_person
from app.main import app
from app.models.entities import MedicalDocument, PersonProfile, User
from app.api import documents as documents_api


# ---------------------------------------------------------------------------
# In-test minimal PDF byte generator from P142 / P143
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
# Database & Test Setup
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_p144_dashboard_confirmed_report_contract(monkeypatch):
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
        email="p144_dashboard_test@example.com",
        password_hash="hashed_password",
        is_active=True,
    )
    db.add(user)
    db.flush()

    person = PersonProfile(
        id=uuid.uuid4(),
        owner_user_id=user.id,
        display_name="P144 Test User",
        relationship="self",
        gender="male",
        is_default=True,
    )
    db.add(person)
    db.commit()

    # Force OpenAI API Key to empty to verify graceful fallback logic
    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "openai_api_key", "")

    # In-memory storage mock to intercept upload/download calls without real S3
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

    # 1. Generate purely synthetic lab values PDF including unit scale mismatch and unknown markers
    synthetic_lines = [
        "Glucose: 110 mg/dL",
        "AST: 45 U/L",
        "Total Cholesterol: 240 mg/dL",
        "LDL: 3.4 mmol/L",  # to test suppressed_unit_scale_mismatch
        "Random Marker: 99",  # to test no_reference_rule
    ]
    pdf_bytes = make_minimal_pdf(synthetic_lines)

    # 2. Upload synthetic PDF through documents API
    upload_resp = client.post(
        "/api/v1/documents/upload",
        data={"category": "health_check"},
        files={"file": ("synthetic_report.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
    upload_data = upload_resp.json()
    document_id = upload_data["id"]
    assert upload_data["parse_status"] == "pending"

    # 3. Parse the uploaded document
    parse_resp = client.post(f"/api/v1/documents/{document_id}/parse")
    assert parse_resp.status_code == 200, f"Parse failed: {parse_resp.text}"
    parse_data = parse_resp.json()
    assert parse_data["document_id"] == document_id

    # 4. Get parsed-items to verify flow works with standard structured lab values
    items_resp = client.get(f"/api/v1/documents/{document_id}/parsed-items")
    assert items_resp.status_code == 200, f"Get parsed-items failed: {items_resp.text}"
    parsed_items = items_resp.json()
    assert len(parsed_items) >= 5

    item_map = {item["item_name"]: item for item in parsed_items}

    # Verify standard structured lab values match the synthetic ones exactly
    assert "Glucose" in item_map
    glucose_item = item_map["Glucose"]
    assert glucose_item["value_num"] == 110.0
    assert glucose_item["unit"] == "mg/dL"
    assert glucose_item["abnormal_flag"] == "H"
    assert glucose_item["is_abnormal"] is True

    assert "AST" in item_map
    ast_item = item_map["AST"]
    assert ast_item["value_num"] == 45.0
    assert ast_item["unit"] == "U/L"
    assert ast_item["abnormal_flag"] == "H"
    assert ast_item["is_abnormal"] is True

    assert "Total Cholesterol" in item_map
    chol_item = item_map["Total Cholesterol"]
    assert chol_item["value_num"] == 240.0
    assert chol_item["unit"] == "mg/dL"
    assert chol_item["abnormal_flag"] == "H"
    assert chol_item["is_abnormal"] is True

    # Assert not-judged / unknown state is not mislabeled as normal
    assert "LDL" in item_map
    ldl_item = item_map["LDL"]
    assert ldl_item["value_num"] == 3.4
    assert ldl_item["unit"] == "mmol/L"
    assert ldl_item["abnormal_flag"] is None
    assert ldl_item["abnormal_flag_reason"] == "suppressed_unit_scale_mismatch"
    assert ldl_item["is_abnormal"] is False

    assert "Random Marker" in item_map
    random_item = item_map["Random Marker"]
    assert random_item["value_num"] == 99.0
    assert random_item["abnormal_flag"] is None
    assert random_item["abnormal_flag_reason"] == "no_reference_rule"
    assert random_item["is_abnormal"] is False

    # 5. Confirm the document is successfully transitioned to confirmed state
    confirm_payload = {
        "confirmed_data": {
            "reviewed": True,
            "items": [
                {"item_name": "Glucose", "value": 110, "unit": "mg/dL"},
                {"item_name": "AST", "value": 45, "unit": "U/L"},
                {"item_name": "Total Cholesterol", "value": 240, "unit": "mg/dL"},
                {"item_name": "LDL", "value": 3.4, "unit": "mmol/L"},
                {"item_name": "Random Marker", "value": 99, "unit": None},
            ]
        },
        "report_date": date.today().isoformat()
    }
    confirm_resp = client.put(f"/api/v1/documents/{document_id}/confirm", json=confirm_payload)
    assert confirm_resp.status_code == 200, f"Confirm failed: {confirm_resp.text}"
    confirm_data = confirm_resp.json()
    assert confirm_data["parse_status"] == "confirmed"
    assert confirm_data["confirmed_at"] is not None

    # 6. Call dashboard and journey backend endpoints to assert confirmed report presence
    # Check GET /api/v1/dashboard
    dashboard_resp = client.get("/api/v1/dashboard")
    assert dashboard_resp.status_code == 200, f"Dashboard API failed: {dashboard_resp.text}"
    dashboard_data = dashboard_resp.json()

    # Assert confirmed report is returned in recent_labs
    recent_labs = dashboard_data.get("recent_labs", [])
    assert len(recent_labs) >= 1
    report_entry = recent_labs[0]
    assert report_entry["abnormal_items"] == 3  # AST, Glucose, Total Cholesterol are 'H'

    # Assert active alerts list contains evaluated risk alerts from the report
    alerts = dashboard_data.get("alerts", [])
    assert len(alerts) >= 2
    alert_rule_ids = {a.get("rule_id", "").lower() for a in alerts}
    assert "liver_ast_high" in alert_rule_ids
    assert "lipid_cholesterol_high" in alert_rule_ids

    # Assert health score contains the penalty for active risk alerts
    health_score = dashboard_data.get("health_score", {})
    components = health_score.get("components", {})
    assert components.get("risk_alerts_penalty", 0) > 0

    # Check GET /api/v1/dashboard/overview
    overview_resp = client.get("/api/v1/dashboard/overview")
    assert overview_resp.status_code == 200, f"Dashboard overview failed: {overview_resp.text}"
    overview_data = overview_resp.json()
    active_alerts = overview_data.get("active_alerts", [])
    assert len(active_alerts) >= 2
    overview_rule_ids = {a.get("severity") for a in active_alerts}
    assert len(overview_rule_ids) > 0

    # Check GET /api/v1/health-assistant/daily-summary (journey companion card state)
    summary_resp = client.get("/api/v1/health-assistant/daily-summary")
    assert summary_resp.status_code == 200, f"Daily summary failed: {summary_resp.text}"
    summary_data = summary_resp.json()
    assert summary_data.get("topRisk") is not None

    # Check GET /api/v1/health-assistant/recommendations (first-run recommendations)
    recs_resp = client.get("/api/v1/health-assistant/recommendations")
    assert recs_resp.status_code == 200, f"Recommendations failed: {recs_resp.text}"
    recs_data = recs_resp.json()
    assert "recommendations" in recs_data

    # Check GET /api/v1/documents (first-run checklist source)
    docs_resp = client.get("/api/v1/documents")
    assert docs_resp.status_code == 200, f"List documents failed: {docs_resp.text}"
    docs_list = docs_resp.json()
    assert any(doc.get("parse_status") == "confirmed" for doc in docs_list)

    # 7. Safety Audits
    # Assert absolutely no real patient data is included in inputs, database, or results
    prohibited_names = {"Kelvin", "John", "Doe", "Smith"}
    for line in synthetic_lines:
        for name in prohibited_names:
            assert name.lower() not in line.lower(), f"Prohibited patient name '{name}' found in input line"

    # Assert no diagnostic, treatment, cure, or guarantee claims/language is introduced
    prohibited_keywords = [
        "diagnos",  # diagnosis, diagnose, diagnostic
        "cure",
        "guarante",  # guarantee, guaranteed
        "診斷",
        "治療",
        "保證",
        "處方",
        "pre-script",
    ]
    for word in prohibited_keywords:
        for line in synthetic_lines:
            assert word not in line.lower(), f"Prohibited word '{word}' found in synthetic line: {line}"

    # Helper to recursively check for prohibited keywords and names in the responses,
    # skipping "medical_disclaimer" field and allowing "非醫療診斷" (part of standard medical disclaimer).
    def scan_safety(val, path=""):
        if isinstance(val, str):
            for name in prohibited_names:
                assert name.lower() not in val.lower(), f"Safety violation: real patient name '{name}' found at {path}: {val}"
            for word in prohibited_keywords:
                if word in val.lower():
                    if word == "診斷" and "非醫療診斷" in val:
                        continue
                    assert False, f"Safety violation: prohibited keyword '{word}' found at {path}: {val}"
        elif isinstance(val, dict):
            for k, v in val.items():
                if k == "medical_disclaimer":
                    continue
                scan_safety(v, f"{path}.{k}")
        elif isinstance(val, list):
            for idx, item in enumerate(val):
                scan_safety(item, f"{path}[{idx}]")

    scan_safety(dashboard_data, "dashboard_data")
    scan_safety(overview_data, "overview_data")
    scan_safety(summary_data, "summary_data")
    scan_safety(recs_data, "recs_data")
