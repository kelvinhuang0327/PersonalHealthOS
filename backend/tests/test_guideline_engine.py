from types import SimpleNamespace

from app.services.health_ai_engine.guideline_engine import derive_clinical_labels


def test_guideline_engine_derives_labels_with_metadata():
    metrics = [SimpleNamespace(systolic_bp=145, diastolic_bp=92, weight_kg=85)]
    labs = [SimpleNamespace(item_name='ALT', value_num=58, ref_high=40), SimpleNamespace(item_name='Uric Acid', value_num=7.5)]
    labels = derive_clinical_labels(metrics, labs)
    assert labels
    assert any(label['label'].startswith('BP:hypertension') for label in labels)
    assert all('guideline_source' in label for label in labels)
