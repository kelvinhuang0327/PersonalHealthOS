import uuid
from decimal import Decimal
from types import SimpleNamespace

from app.services.risk_engine import evaluate_metric_risks


def test_metric_risks_trigger_for_obese_bp_and_glucose():
    user_id = str(uuid.uuid4())
    profile = SimpleNamespace(height_cm=Decimal('170'))
    metric = SimpleNamespace(
        id=uuid.uuid4(),
        weight_kg=Decimal('90'),
        systolic_bp=145,
        diastolic_bp=95,
        blood_glucose=Decimal('140'),
    )

    alerts = evaluate_metric_risks(user_id, profile, metric)
    codes = {a.rule_code for a in alerts}

    assert 'BMI_OBESE' in codes
    assert 'BP_HIGH' in codes
    assert 'GLUCOSE_HIGH' in codes
