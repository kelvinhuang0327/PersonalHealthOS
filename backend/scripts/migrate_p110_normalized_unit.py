"""P110 migration: add nullable normalized_unit column to lab_report_items.

Upgrade: adds normalized_unit VARCHAR(30) NULL to lab_report_items.
Downgrade: removes the column.
No backfill — existing rows keep normalized_unit = NULL.
"""
from __future__ import annotations

import sys
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.core.database import engine


def has_column(table: str, column: str) -> bool:
    inspector = inspect(engine)
    cols = {c['name'] for c in inspector.get_columns(table)}
    return column in cols


def upgrade() -> None:
    if has_column('lab_report_items', 'normalized_unit'):
        print('normalized_unit already exists — nothing to do')
        return
    with engine.begin() as conn:
        conn.execute(text(
            'ALTER TABLE lab_report_items ADD COLUMN normalized_unit VARCHAR(30) NULL'
        ))
    print('upgrade complete: normalized_unit added to lab_report_items')


def downgrade() -> None:
    if not has_column('lab_report_items', 'normalized_unit'):
        print('normalized_unit does not exist — nothing to do')
        return
    with engine.begin() as conn:
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
