from app.services.health_score_service import _clamp_int


def test_clamp_int():
    assert _clamp_int(-5) == 0
    assert _clamp_int(50) == 50
    assert _clamp_int(150) == 100
