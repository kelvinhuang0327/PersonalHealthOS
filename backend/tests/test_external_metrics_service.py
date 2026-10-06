from app.services.external_metrics_service import mock_external_metrics


def test_mock_external_metrics_contains_expected_fields():
    rows = mock_external_metrics()
    assert len(rows) >= 4
    assert any('steps' in row for row in rows)
    assert all(row.get('source') == 'external_api' for row in rows)
