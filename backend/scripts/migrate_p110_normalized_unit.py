"""P110 migration: add nullable normalized_unit column to lab_report_items.

Upgrade: adds normalized_unit VARCHAR(30) NULL to lab_report_items.
Downgrade: removes the column.
No backfill — existing rows keep normalized_unit = NULL.

Engine injection contract (P112):
  All public functions accept an optional ``_engine`` keyword argument.
  When None (default), the production engine from app.core.database is used.
  Tests pass a temporary SQLite engine so the production DB is never touched.

SQLite limitation:
  downgrade() uses ALTER TABLE DROP COLUMN which requires SQLite >= 3.35.0
  (released 2021-03-12).  PostgreSQL supports DROP COLUMN unconditionally.
  Check sqlite3.sqlite_version before calling downgrade() on older SQLite.
"""
from __future__ import annotations

import sys
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.core.database import engine as _default_engine


def has_column(table: str, column: str, _engine=None) -> bool:
    # NULL-fallback contract: None → use production engine (default path)
    eng = _engine if _engine is not None else _default_engine
    inspector = inspect(eng)
    cols = {c['name'] for c in inspector.get_columns(table)}
    return column in cols


def upgrade(_engine=None) -> None:
    eng = _engine if _engine is not None else _default_engine
    if has_column('lab_report_items', 'normalized_unit', eng):
        print('normalized_unit already exists — nothing to do')
        return
    with eng.begin() as conn:
        conn.execute(text(
            'ALTER TABLE lab_report_items ADD COLUMN normalized_unit VARCHAR(30) NULL'
        ))
    print('upgrade complete: normalized_unit added to lab_report_items')


def downgrade(_engine=None) -> None:
    eng = _engine if _engine is not None else _default_engine
    if not has_column('lab_report_items', 'normalized_unit', eng):
        print('normalized_unit does not exist — nothing to do')
        return
    with eng.begin() as conn:
        conn.execute(text(
            'ALTER TABLE lab_report_items DROP COLUMN normalized_unit'
        ))
    print('downgrade complete: normalized_unit removed from lab_report_items')


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'upgrade'
    if action == 'upgrade':
        upgrade()
    elif action == 'downgrade':
        downgrade()
    else:
        print(f'Unknown action: {action}. Use upgrade or downgrade.')
        sys.exit(1)
