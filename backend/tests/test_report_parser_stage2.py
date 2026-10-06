from app.services.report_parser import normalize_unit, parse_lab_items


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


# ── normalize_unit() unit tests ───────────────────────────────────────────────

def test_normalize_unit_iu_l_upper():
    assert normalize_unit('IU/L') == 'U/L'


def test_normalize_unit_iu_l_lower():
    assert normalize_unit('iu/l') == 'U/L'


def test_normalize_unit_iu_l_mixed():
    assert normalize_unit('IU/l') == 'U/L'


def test_normalize_unit_u_l_passthrough():
    assert normalize_unit('U/L') == 'U/L'


def test_normalize_unit_unicode_mu_prefix():
    assert normalize_unit('μmol/L') == 'umol/L'


def test_normalize_unit_unicode_micro_sign_prefix():
    assert normalize_unit('µmol/L') == 'umol/L'


def test_normalize_unit_ascii_u_passthrough():
    assert normalize_unit('umol/L') == 'umol/L'


def test_normalize_unit_mg_dl_unchanged():
    assert normalize_unit('mg/dL') == 'mg/dL'


def test_normalize_unit_mmol_l_unchanged():
    assert normalize_unit('mmol/L') == 'mmol/L'


def test_normalize_unit_none_returns_none():
    assert normalize_unit(None) is None


def test_normalize_unit_empty_string_returns_none():
    assert normalize_unit('') is None


def test_normalize_unit_whitespace_only_returns_none():
    assert normalize_unit('   ') is None


def test_normalize_unit_mg_dl_not_converted_to_mmol():
    result = normalize_unit('mg/dL')
    assert result != 'mmol/L'


def test_normalize_unit_mmol_l_not_converted_to_mg_dl():
    result = normalize_unit('mmol/L')
    assert result != 'mg/dL'


# ── parse_lab_items() includes normalized_unit ────────────────────────────────

def test_parse_lab_items_includes_normalized_unit_key():
    raw_text = 'ALT 32 U/L'
    items = parse_lab_items(raw_text)
    assert len(items) > 0
    assert 'normalized_unit' in items[0]


def test_parse_lab_items_preserves_raw_unit():
    raw_text = 'ALT 32 IU/L'
    items = parse_lab_items(raw_text)
    item_map = {i['item_name']: i for i in items}
    assert 'ALT' in item_map
    assert item_map['ALT']['unit'] == 'IU/L'


def test_parse_lab_items_normalized_unit_for_iu_l():
    raw_text = 'ALT 32 IU/L'
    items = parse_lab_items(raw_text)
    item_map = {i['item_name']: i for i in items}
    assert item_map['ALT']['normalized_unit'] == 'U/L'


def test_parse_lab_items_normalized_unit_for_unicode_mu():
    raw_text = 'Uric Acid 6.5 μmol/L'
    items = parse_lab_items(raw_text)
    assert len(items) > 0
    item = items[0]
    assert item['unit'] == 'μmol/L'
    assert item['normalized_unit'] == 'umol/L'


def test_parse_lab_items_normalized_unit_none_when_no_unit():
    raw_text = 'Glucose 5.5'
    items = parse_lab_items(raw_text)
    item_map = {i['item_name']: i for i in items}
    if 'Glucose' in item_map:
        assert item_map['Glucose']['normalized_unit'] is None


def test_parse_lab_items_normalized_unit_mg_dl_unchanged():
    raw_text = 'Glucose 110 mg/dL 70-99'
    items = parse_lab_items(raw_text)
    item_map = {i['item_name']: i for i in items}
    assert 'Glucose' in item_map
    assert item_map['Glucose']['unit'] == 'mg/dL'
    assert item_map['Glucose']['normalized_unit'] == 'mg/dL'
