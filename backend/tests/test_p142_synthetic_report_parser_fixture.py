from __future__ import annotations

import io
import pypdf
import pytest
from app.services.report_parser import extract_text, parse_lab_items


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


def test_p142_synthetic_report_parser_fixture():
    # 1. Prepare synthetic report lines without diagnostic, treatment, cure, or guarantee claims
    # Also ensure absolutely zero real patient data is included
    synthetic_lines = [
        "Glucose: 110 mg/dL",
        "AST: 45 U/L",
        "Total Cholesterol: 240 mg/dL",
    ]

    # Generate the synthetic PDF bytes
    pdf_bytes = make_minimal_pdf(synthetic_lines)

    # 2. Extract text using the report parser's utility
    extracted_text = extract_text(pdf_bytes, "application/pdf")

    # Assert newlines exist and standard structured data is extracted properly
    assert "Glucose" in extracted_text
    assert "AST" in extracted_text
    assert "Total Cholesterol" in extracted_text

    # 3. Parse the lab items
    parsed_items = parse_lab_items(extracted_text)

    # Assert at least two expected lab items are extracted
    assert len(parsed_items) >= 2

    # Map parsed items for easy assertion
    item_map = {item["item_name"]: item for item in parsed_items}

    # Verify key properties of the parsed items to ensure correctness and prevent 0 parsed-items dogfood confusion
    assert "Glucose" in item_map
    glucose_item = item_map["Glucose"]
    assert glucose_item["value_num"] == 110.0
    assert glucose_item["unit"] == "mg/dL"
    assert glucose_item["normalized_unit"] == "mg/dL"

    assert "AST" in item_map
    ast_item = item_map["AST"]
    assert ast_item["value_num"] == 45.0
    assert ast_item["unit"] == "U/L"
    assert ast_item["normalized_unit"] == "U/L"

    assert "Total Cholesterol" in item_map
    chol_item = item_map["Total Cholesterol"]
    assert chol_item["value_num"] == 240.0
    assert chol_item["unit"] == "mg/dL"
    assert chol_item["normalized_unit"] == "mg/dL"

    # 4. Prohibit real patient data
    prohibited_patient_names = {"Kelvin", "John", "Doe", "Smith"}
    for line in synthetic_lines:
        for name in prohibited_patient_names:
            assert name.lower() not in line.lower()

    # 5. Prohibit diagnostic, cure, or guarantee language
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

    # Assert no prohibited keywords in the input lines, the extracted text, or the parsed items keys/values
    for word in prohibited_keywords:
        for line in synthetic_lines:
            assert word not in line.lower(), f"Prohibited word '{word}' found in synthetic line: {line}"
        assert word not in extracted_text.lower(), f"Prohibited word '{word}' found in extracted text"
        for item in parsed_items:
            for val in item.values():
                if isinstance(val, str):
                    assert word not in val.lower(), f"Prohibited word '{word}' found in parsed item attribute: {val}"
