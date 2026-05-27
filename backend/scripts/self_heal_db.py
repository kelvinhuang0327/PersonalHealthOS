from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.exc import NoSuchTableError

from app.core.database import Base, engine


def has_column(table: str, column: str) -> bool:
    inspector = inspect(engine)
    try:
        cols = {c['name'] for c in inspector.get_columns(table)}
    except NoSuchTableError:
        return False
    return column in cols


def main() -> None:
    Base.metadata.create_all(bind=engine)
    required = [
        ('symptom_logs', 'estimated_start_date'),
        ('symptom_logs', 'estimated_duration_days'),
        ('medical_documents', 'confirmed_data'),
        ('health_insights', 'evidence_json'),
        ('lab_report_items', 'normalized_unit'),
    ]
    drift = [(t, c) for t, c in required if not has_column(t, c)]
    if drift:
        print(f'schema drift detected: {drift}')
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print('schema recreated')
    else:
        print('schema healthy')


if __name__ == '__main__':
    main()
