from app.services.report_parser import parse_lab_items


def test_parse_lab_items_with_reference_range_and_abnormal_flag():
    raw_text = '''
    Glucose 110 mg/dL 70-99
    ALT 32 U/L
    HDL 35 mg/dL
    '''
    items = parse_lab_items(raw_text, gender='male')
    item_map = {item['item_name']: item for item in items}

    assert 'Glucose' in item_map
    assert item_map['Glucose']['abnormal_flag'] == 'H'
    assert item_map['Glucose']['ref_low'] == 70.0
    assert item_map['Glucose']['ref_high'] == 99.0

    assert 'HDL' in item_map
    assert item_map['HDL']['abnormal_flag'] == 'L'
