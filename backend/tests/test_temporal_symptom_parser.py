from app.services.temporal_symptom_parser import parse_temporal_symptom


def test_parse_temporal_symptom_years():
    result = parse_temporal_symptom('大約20年的尿酸過高')
    assert result['symptom'] == '尿酸過高'
    assert result['estimated_duration_days'] == 20 * 365
    assert result['temporal_source'] == 'user_narrative'
    assert result['confidence_score'] >= 0.8


def test_parse_temporal_symptom_recent_half_year():
    result = parse_temporal_symptom('最近半年頭痛')
    assert result['symptom'] == '頭痛'
    assert result['estimated_duration_days'] == 182


def test_parse_temporal_symptom_suffix_years():
    result = parse_temporal_symptom('腰痠大概10年')
    assert result['symptom'] == '腰痠'
    assert result['estimated_duration_days'] == 10 * 365
