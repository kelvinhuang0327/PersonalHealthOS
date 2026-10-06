"""P112 — normalized_unit migration runtime assurance.

Verifies that:
  A) migrate_p110_normalized_unit.upgrade() adds the column when absent
  B) upgrade() is idempotent — second call does not crash or duplicate the column
  C) self_heal_db.main() detects and repairs missing normalized_unit
  D) upgrade() does not mutate existing row values when column already present

All tests use a temporary persistent SQLite file DB.
No production DB is queried.  No historical rows are backfilled.

SQLite notes:
  - DROP COLUMN requires SQLite >= 3.35.0 (this file guards with a skip
    marker when runtime version is older).
  - Self-heal test uses a minimal declarative Base (no PostgreSQL-specific
    types) to remain SQLite-compatible.

Importing the scripts:
  scripts/ has no __init__.py; we insert scripts/ into sys.path at test
  collection time so pytest can resolve the migration modules without
  touching the production engine (engine creation is lazy in SQLAlchemy).
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, String, create_engine, inspect, text
from sqlalchemy.orm import declarative_base

# ── scripts/ import path ──────────────────────────────────────────────────────
# scripts/ is not a Python package; add it directly so we can import the
# migration modules without touching scripts/__init__.py.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from migrate_p110_normalized_unit import downgrade as _downgrade
from migrate_p110_normalized_unit import has_column as _has_column
from migrate_p110_normalized_unit import upgrade as _upgrade
from self_heal_db import main as _self_heal_main

# ── SQLite DROP COLUMN guard ──────────────────────────────────────────────────
import sqlite3 as _sqlite3

_SQLITE_SUPPORTS_DROP_COLUMN = tuple(
    int(x) for x in _sqlite3.sqlite_version.split(".")
) >= (3, 35, 0)

# ── minimal test Base (SQLite-compatible, no PG-specific types) ───────────────
_TestBase = declarative_base()


class _LabItems(_TestBase):
    """Minimal lab_report_items model — only the columns required for P112."""

    __tablename__ = "lab_report_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    test_name = Column(String(200))
    unit = Column(String(30))
    normalized_unit = Column(String(30), nullable=True)


# ── helper ────────────────────────────────────────────────────────────────────


def _make_temp_db() -> tuple[str, object]:
    """Return (path, engine) for a fresh temporary SQLite file DB."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="p112_test_")
    os.close(fd)
    eng = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )
    return path, eng


def _create_table_without_normalized_unit(eng) -> None:
    """Create lab_report_items WITHOUT normalized_unit (pre-P110 state)."""
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS lab_report_items (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name   TEXT,
                    value       REAL,
                    unit        TEXT
                )
                """
            )
        )


def _column_names(eng, table: str) -> set[str]:
    return {c["name"] for c in inspect(eng).get_columns(table)}


def _all_column_names_list(eng, table: str) -> list[str]:
    return [c["name"] for c in inspect(eng).get_columns(table)]


# ── Test A: migration adds missing column ─────────────────────────────────────


def test_migration_adds_missing_column():
    """Test A — upgrade() adds normalized_unit when column is absent.

    Runtime smoke output:
      temp DB path      → printed via pytest -s
      before schema     → no normalized_unit
      after schema      → normalized_unit present
    """
    path, eng = _make_temp_db()
    try:
        _create_table_without_normalized_unit(eng)

        before = _column_names(eng, "lab_report_items")
        print(f"\n[A] temp DB: {path}")
        print(f"[A] before schema: {sorted(before)}")
        assert "normalized_unit" not in before, (
            "pre-condition: column must not exist before upgrade()"
        )

        _upgrade(_engine=eng)

        after = _column_names(eng, "lab_report_items")
        print(f"[A] after schema: {sorted(after)}")
        assert "normalized_unit" in after, (
            "post-condition: upgrade() must add normalized_unit"
        )
    finally:
        eng.dispose()
        Path(path).unlink(missing_ok=True)


# ── Test B: migration idempotent ──────────────────────────────────────────────


def test_migration_idempotent():
    """Test B — calling upgrade() twice does not crash and column appears once.

    Idempotency result: second upgrade() must print 'already exists' and not
    raise, and the column count must remain 1.
    """
    path, eng = _make_temp_db()
    try:
        _create_table_without_normalized_unit(eng)
        _upgrade(_engine=eng)  # first call — adds column
        _upgrade(_engine=eng)  # second call — must be silent no-op

        all_cols = _all_column_names_list(eng, "lab_report_items")
        count = all_cols.count("normalized_unit")
        print(f"\n[B] temp DB: {path}")
        print(f"[B] idempotency: column count = {count} (expected 1)")
        assert count == 1, (
            f"idempotency failure: normalized_unit appears {count} times"
        )
    finally:
        eng.dispose()
        Path(path).unlink(missing_ok=True)


# ── Test C: self-heal detects and repairs missing column ──────────────────────


@pytest.mark.skipif(
    not _SQLITE_SUPPORTS_DROP_COLUMN,
    reason=f"SQLite {_sqlite3.sqlite_version} < 3.35.0: DROP COLUMN not supported",
)
def test_self_heal_detects_and_repairs_missing_normalized_unit():
    """Test C — self_heal_main() detects drift and recreates schema with column.

    Uses a minimal _TestBase (SQLite-compatible) so no PostgreSQL-specific
    types are involved.  The test drops normalized_unit after create_all to
    simulate a pre-P110 deployment, then confirms self-heal restores it.
    """
    path, eng = _make_temp_db()
    try:
        # Create tables via minimal Base (includes normalized_unit)
        _TestBase.metadata.create_all(bind=eng)

        assert "normalized_unit" in _column_names(eng, "lab_report_items"), (
            "pre-condition: create_all() must include normalized_unit"
        )

        # Simulate schema drift: drop the column
        with eng.begin() as conn:
            conn.execute(
                text("ALTER TABLE lab_report_items DROP COLUMN normalized_unit")
            )
        assert "normalized_unit" not in _column_names(eng, "lab_report_items"), (
            "pre-condition: column must be absent to trigger self-heal"
        )
        print(f"\n[C] temp DB: {path}")
        print("[C] before self-heal: normalized_unit ABSENT (drift injected)")

        # Run self-heal with temp engine and minimal Base
        _self_heal_main(_engine=eng, _base=_TestBase)

        after = _column_names(eng, "lab_report_items")
        print(f"[C] after self-heal schema: {sorted(after)}")
        assert "normalized_unit" in after, (
            "self-heal must restore normalized_unit via drop_all+create_all"
        )
        print("[C] self-heal result: REPAIRED")
    finally:
        eng.dispose()
        Path(path).unlink(missing_ok=True)


# ── Test D: existing normalized_unit data preserved after migration ────────────


def test_migration_preserves_existing_normalized_unit_data():
    """Test D — upgrade() on a DB that already has normalized_unit leaves data intact.

    Data preservation result: upgrade() is a no-op when column exists; the
    previously stored normalized_unit value must not be mutated.
    """
    path, eng = _make_temp_db()
    try:
        _create_table_without_normalized_unit(eng)
        _upgrade(_engine=eng)  # adds column

        # Insert a known row with normalized_unit already populated
        with eng.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO lab_report_items (test_name, unit, normalized_unit) "
                    "VALUES ('ALT', 'IU/L', 'U/L')"
                )
            )

        # Confirm value is stored
        with eng.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT normalized_unit FROM lab_report_items "
                    "WHERE test_name = 'ALT'"
                )
            ).fetchall()
        assert rows[0][0] == "U/L", "pre-condition: value must be stored"

        # Run upgrade again — must be idempotent, must not touch existing data
        _upgrade(_engine=eng)

        with eng.connect() as conn:
            rows_after = conn.execute(
                text(
                    "SELECT normalized_unit FROM lab_report_items "
                    "WHERE test_name = 'ALT'"
                )
            ).fetchall()

        print(f"\n[D] temp DB: {path}")
        print(f"[D] data preservation: normalized_unit = {rows_after[0][0]!r} (expected 'U/L')")
        assert len(rows_after) == 1
        assert rows_after[0][0] == "U/L", (
            "data preservation failure: upgrade() must not mutate existing normalized_unit"
        )
    finally:
        eng.dispose()
        Path(path).unlink(missing_ok=True)
