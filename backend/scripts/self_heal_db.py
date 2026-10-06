"""Self-heal DB: detect schema drift and recreate tables as needed.

Engine injection contract (P112):
  has_column() and main() accept optional ``_engine`` / ``_base`` kwargs.
  None (default) → use production engine/Base from app.core.database.
  Tests pass a temporary SQLite engine so the production DB is never touched.

Destructive behaviour (by design):
  When drift is detected, main() calls drop_all() + create_all() which
  destroys and recreates ALL tables.  Do NOT call on production data without
  a backup.  This behaviour is intentional for dev/CI environments only.
"""
from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.exc import NoSuchTableError

from app.core.database import Base as _default_base, engine as _default_engine


def has_column(table: str, column: str, _engine=None) -> bool:
    # NULL-fallback contract: None → use production engine (default path)
    eng = _engine if _engine is not None else _default_engine
    inspector = inspect(eng)
    try:
        cols = {c['name'] for c in inspector.get_columns(table)}
    except NoSuchTableError:
        return False
    return column in cols


def main(_engine=None, _base=None) -> None:
    eng = _engine if _engine is not None else _default_engine
    base = _base if _base is not None else _default_base
    base.metadata.create_all(bind=eng)
    required = [
        ('symptom_logs', 'estimated_start_date'),
        ('symptom_logs', 'estimated_duration_days'),
        ('medical_documents', 'confirmed_data'),
        ('health_insights', 'evidence_json'),
        ('lab_report_items', 'normalized_unit'),
    ]
    drift = [(t, c) for t, c in required if not has_column(t, c, eng)]
    if drift:
        print(f'schema drift detected: {drift}')
        base.metadata.drop_all(bind=eng)
        base.metadata.create_all(bind=eng)
        print('schema recreated')
    else:
        print('schema healthy')


if __name__ == '__main__':
    main()
