from app.services.health_analysis_service import build_health_analysis


def test_health_analysis_insufficient_data():
    result = build_health_analysis('person-1', [], [], [], [])
    assert result['data_sufficient'] is False
    assert '資料不足' in result['potential_risks'][0]


def test_health_analysis_with_data():
    class Row:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    result = build_health_analysis(
        'person-1',
        [Row()],
        [Row(symptom='頭痛')],
        [Row(item_name='Glucose', abnormal_flag='H')],
        [Row(title='血糖偏高', message='近期偏高')],
    )
    assert result['data_sufficient'] is True
    assert result['abnormal_indicators'][0].startswith('Glucose')
