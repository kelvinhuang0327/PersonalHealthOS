from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine

from app.core.config import get_settings


GO = "GO"
NO_GO_ZERO_OUTCOMES = "NO_GO_ZERO_OUTCOMES"
NO_GO_ZERO_ACTIONS = "NO_GO_ZERO_ACTIONS"
NO_GO_NO_PAIRABILITY = "NO_GO_NO_PAIRABILITY"
UNKNOWN_DB_UNAVAILABLE = "UNKNOWN_DB_UNAVAILABLE"
BLOCKED_READ_ONLY_NOT_GUARANTEED = "BLOCKED_READ_ONLY_NOT_GUARANTEED"


class ReadOnlySafetyError(RuntimeError):
    """Raised when the checker cannot prove read-only database execution."""


class ReadinessQueryRunner(Protocol):
    def ensure_read_only(self) -> bool:
        ...

    def table_exists(self, table_name: str) -> bool:
        ...

    def columns(self, table_name: str) -> set[str]:
        ...

    def scalar(self, sql: str, params: dict[str, Any] | None = None) -> int:
        ...

    def rows(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        ...


@dataclass(frozen=True)
class ReadinessThresholds:
    min_actions: int = 1
    min_outcomes: int = 1
    min_feedback_labels: int = 1
    min_pairable_examples: int = 1


@dataclass
class ReadinessSnapshot:
    confirmed_report_metrics_count: int | None = None
    symptom_logs_count: int | None = None
    health_metrics_count: int | None = None
    health_actions_count: int | None = None
    action_outcomes_count: int | None = None
    recommendation_actions_count: int | None = None
    feedback_label_distribution: dict[str, int] = field(default_factory=dict)
    outcome_metric_label_distribution: list[dict[str, Any]] = field(default_factory=list)
    before_after_pairability_count: int | None = None
    schema_notes: list[str] = field(default_factory=list)


@dataclass
class ReadinessResult:
    classification: str
    read_only_verified: bool
    snapshot: ReadinessSnapshot
    reasons: list[str] = field(default_factory=list)
    raw_phi_pii_exported: bool = False
    db_writes: str = "NOT_RUN"

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "read_only_verified": self.read_only_verified,
            "snapshot": asdict(self.snapshot),
            "reasons": self.reasons,
            "raw_phi_pii_exported": self.raw_phi_pii_exported,
            "db_writes": self.db_writes,
        }


class SqlAlchemyReadOnlyRunner:
    def __init__(self, database_url: str | None = None, engine: Engine | None = None) -> None:
        self._database_url = database_url
        self._engine = engine
        self._owns_engine = engine is None
        self._conn: Connection | None = None
        self._transaction: Any = None

    def __enter__(self) -> "SqlAlchemyReadOnlyRunner":
        if self._engine is None:
            self._engine = create_engine(self._database_url or get_settings().database_url, future=True, pool_pre_ping=True)
        self._conn = self._engine.connect()
        self._transaction = self._conn.begin()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._transaction is not None:
            self._transaction.rollback()
        if self._conn is not None:
            self._conn.close()
        if self._owns_engine and self._engine is not None:
            self._engine.dispose()

    @property
    def conn(self) -> Connection:
        if self._conn is None:
            raise RuntimeError("runner must be used as a context manager")
        return self._conn

    def ensure_read_only(self) -> bool:
        dialect_name = self.conn.dialect.name
        if dialect_name == "postgresql":
            self.conn.execute(text("SET TRANSACTION READ ONLY"))
            value = str(self.conn.execute(text("SHOW transaction_read_only")).scalar() or "").lower()
            if value != "on":
                raise ReadOnlySafetyError("PostgreSQL transaction_read_only was not on")
            return True
        if dialect_name == "sqlite":
            self.conn.execute(text("PRAGMA query_only = ON"))
            value = self.conn.execute(text("PRAGMA query_only")).scalar()
            if int(value or 0) != 1:
                raise ReadOnlySafetyError("SQLite query_only pragma was not enabled")
            return True
        raise ReadOnlySafetyError(f"unsupported dialect for proven read-only mode: {dialect_name}")

    def table_exists(self, table_name: str) -> bool:
        return table_name in inspect(self.conn).get_table_names()

    def columns(self, table_name: str) -> set[str]:
        if not self.table_exists(table_name):
            return set()
        return {row["name"] for row in inspect(self.conn).get_columns(table_name)}

    def scalar(self, sql: str, params: dict[str, Any] | None = None) -> int:
        value = self.conn.execute(text(sql), params or {}).scalar()
        return int(value or 0)

    def rows(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        result = self.conn.execute(text(sql), params or {})
        return [dict(row) for row in result.mappings().all()]


def evaluate_action_feedback_readiness(
    runner: ReadinessQueryRunner,
    thresholds: ReadinessThresholds | None = None,
) -> ReadinessResult:
    thresholds = thresholds or ReadinessThresholds()
    snapshot = ReadinessSnapshot()
    try:
        if not runner.ensure_read_only():
            raise ReadOnlySafetyError("read-only check returned false")
        snapshot = _collect_snapshot(runner)
    except ReadOnlySafetyError as exc:
        return ReadinessResult(
            classification=BLOCKED_READ_ONLY_NOT_GUARANTEED,
            read_only_verified=False,
            snapshot=snapshot,
            reasons=[str(exc)],
        )
    except Exception as exc:
        return ReadinessResult(
            classification=UNKNOWN_DB_UNAVAILABLE,
            read_only_verified=False,
            snapshot=snapshot,
            reasons=[str(exc)],
        )

    classification, reasons = _classify_snapshot(snapshot, thresholds)
    return ReadinessResult(
        classification=classification,
        read_only_verified=True,
        snapshot=snapshot,
        reasons=reasons,
    )


def _collect_snapshot(runner: ReadinessQueryRunner) -> ReadinessSnapshot:
    snapshot = ReadinessSnapshot()
    snapshot.confirmed_report_metrics_count = _confirmed_report_metrics_count(runner, snapshot.schema_notes)
    snapshot.symptom_logs_count = _count_table(runner, "symptom_logs", snapshot.schema_notes)
    snapshot.health_metrics_count = _count_table(runner, "health_metrics", snapshot.schema_notes)
    snapshot.health_actions_count = _count_table(runner, "health_actions", snapshot.schema_notes)
    snapshot.action_outcomes_count = _count_table(runner, "action_outcomes", snapshot.schema_notes)
    snapshot.recommendation_actions_count = _count_table(runner, "recommendation_actions", snapshot.schema_notes)
    snapshot.feedback_label_distribution = _feedback_label_distribution(runner, snapshot.schema_notes)
    snapshot.outcome_metric_label_distribution = _outcome_metric_label_distribution(runner, snapshot.schema_notes)
    snapshot.before_after_pairability_count = _before_after_pairability_count(runner, snapshot.schema_notes)
    return snapshot


def _count_table(runner: ReadinessQueryRunner, table_name: str, schema_notes: list[str]) -> int | None:
    if not runner.table_exists(table_name):
        schema_notes.append(f"{table_name}: missing")
        return None
    return runner.scalar(f"SELECT COUNT(*) FROM {table_name}")


def _confirmed_report_metrics_count(runner: ReadinessQueryRunner, schema_notes: list[str]) -> int | None:
    required_tables = ("lab_report_items", "lab_reports", "medical_documents")
    missing = [table for table in required_tables if not runner.table_exists(table)]
    if missing:
        schema_notes.append(f"confirmed_report_metrics: missing tables {', '.join(missing)}")
        return None

    lab_report_columns = runner.columns("lab_reports")
    document_columns = runner.columns("medical_documents")
    if "document_id" not in lab_report_columns:
        schema_notes.append("confirmed_report_metrics: lab_reports.document_id missing")
        return None

    confirmation_predicates: list[str] = []
    if "confirmed_at" in document_columns:
        confirmation_predicates.append("md.confirmed_at IS NOT NULL")
    if "confirmed_data" in document_columns:
        confirmation_predicates.append("md.confirmed_data IS NOT NULL")
    if not confirmation_predicates:
        schema_notes.append("confirmed_report_metrics: confirmation columns missing")
        return None

    where_clause = " OR ".join(confirmation_predicates)
    return runner.scalar(
        """
        SELECT COUNT(*)
        FROM lab_report_items lri
        JOIN lab_reports lr ON lri.report_id = lr.id
        JOIN medical_documents md ON lr.document_id = md.id
        WHERE """ + where_clause
    )


def _feedback_label_distribution(runner: ReadinessQueryRunner, schema_notes: list[str]) -> dict[str, int]:
    if not runner.table_exists("action_outcomes"):
        schema_notes.append("feedback_label_distribution: action_outcomes missing")
        return {}
    columns = runner.columns("action_outcomes")
    if not {"metric_type", "outcome_label"}.issubset(columns):
        schema_notes.append("feedback_label_distribution: metric_type/outcome_label missing")
        return {}
    rows = runner.rows(
        """
        SELECT COALESCE(outcome_label, 'unknown') AS outcome_label, COUNT(*) AS count
        FROM action_outcomes
        WHERE metric_type = :feedback_metric
        GROUP BY COALESCE(outcome_label, 'unknown')
        ORDER BY COALESCE(outcome_label, 'unknown')
        """,
        {"feedback_metric": "user_feedback"},
    )
    return {str(row["outcome_label"]): int(row["count"]) for row in rows}


def _outcome_metric_label_distribution(runner: ReadinessQueryRunner, schema_notes: list[str]) -> list[dict[str, Any]]:
    if not runner.table_exists("action_outcomes"):
        schema_notes.append("outcome_metric_label_distribution: action_outcomes missing")
        return []
    columns = runner.columns("action_outcomes")
    if not {"metric_type", "outcome_label"}.issubset(columns):
        schema_notes.append("outcome_metric_label_distribution: metric_type/outcome_label missing")
        return []
    return runner.rows(
        """
        SELECT
            COALESCE(metric_type, 'unknown') AS metric_type,
            COALESCE(outcome_label, 'unknown') AS outcome_label,
            COUNT(*) AS count
        FROM action_outcomes
        GROUP BY COALESCE(metric_type, 'unknown'), COALESCE(outcome_label, 'unknown')
        ORDER BY COALESCE(metric_type, 'unknown'), COALESCE(outcome_label, 'unknown')
        """
    )


def _before_after_pairability_count(runner: ReadinessQueryRunner, schema_notes: list[str]) -> int | None:
    if not runner.table_exists("action_outcomes"):
        schema_notes.append("before_after_pairability: action_outcomes missing")
        return None
    columns = runner.columns("action_outcomes")
    if not {"before_value", "after_value"}.issubset(columns):
        schema_notes.append("before_after_pairability: before_value/after_value missing")
        return None
    return runner.scalar(
        """
        SELECT COUNT(*)
        FROM action_outcomes
        WHERE before_value IS NOT NULL AND after_value IS NOT NULL
        """
    )


def _classify_snapshot(
    snapshot: ReadinessSnapshot,
    thresholds: ReadinessThresholds,
) -> tuple[str, list[str]]:
    health_actions_count = snapshot.health_actions_count or 0
    action_outcomes_count = snapshot.action_outcomes_count or 0
    pairability_count = snapshot.before_after_pairability_count or 0
    feedback_label_count = sum(snapshot.feedback_label_distribution.values())

    if action_outcomes_count < thresholds.min_outcomes:
        return NO_GO_ZERO_OUTCOMES, [f"action_outcomes_count={action_outcomes_count} below {thresholds.min_outcomes}"]
    if health_actions_count < thresholds.min_actions:
        return NO_GO_ZERO_ACTIONS, [f"health_actions_count={health_actions_count} below {thresholds.min_actions}"]
    if pairability_count < thresholds.min_pairable_examples:
        return NO_GO_NO_PAIRABILITY, [
            f"before_after_pairability_count={pairability_count} below {thresholds.min_pairable_examples}"
        ]
    if feedback_label_count < thresholds.min_feedback_labels:
        return NO_GO_NO_PAIRABILITY, [f"feedback_label_count={feedback_label_count} below {thresholds.min_feedback_labels}"]
    return GO, ["all configured action/outcome/feedback/pairability thresholds met"]


def run_with_database_url(database_url: str | None = None) -> ReadinessResult:
    try:
        with SqlAlchemyReadOnlyRunner(database_url=database_url) as runner:
            return evaluate_action_feedback_readiness(runner)
    except Exception as exc:
        return ReadinessResult(
            classification=UNKNOWN_DB_UNAVAILABLE,
            read_only_verified=False,
            snapshot=ReadinessSnapshot(),
            reasons=[str(exc)],
        )


def format_markdown(result: ReadinessResult) -> str:
    data = result.to_dict()
    snapshot = data["snapshot"]
    lines = [
        "# Action Feedback Readiness",
        "",
        f"- classification: `{result.classification}`",
        f"- read_only_verified: `{result.read_only_verified}`",
        f"- db_writes: `{result.db_writes}`",
        f"- raw_phi_pii_exported: `{result.raw_phi_pii_exported}`",
        "",
        "## Aggregate Counts",
        f"- confirmed_report_metrics_count: `{snapshot['confirmed_report_metrics_count']}`",
        f"- symptom_logs_count: `{snapshot['symptom_logs_count']}`",
        f"- health_metrics_count: `{snapshot['health_metrics_count']}`",
        f"- health_actions_count: `{snapshot['health_actions_count']}`",
        f"- action_outcomes_count: `{snapshot['action_outcomes_count']}`",
        f"- recommendation_actions_count: `{snapshot['recommendation_actions_count']}`",
        f"- before_after_pairability_count: `{snapshot['before_after_pairability_count']}`",
        "",
        "## Feedback Label Distribution",
    ]
    if snapshot["feedback_label_distribution"]:
        lines.extend(
            f"- {label}: `{count}`"
            for label, count in sorted(snapshot["feedback_label_distribution"].items())
        )
    else:
        lines.append("- empty")

    lines.extend(["", "## Outcome Metric / Label Distribution"])
    if snapshot["outcome_metric_label_distribution"]:
        lines.extend(
            f"- {row['metric_type']} / {row['outcome_label']}: `{row['count']}`"
            for row in snapshot["outcome_metric_label_distribution"]
        )
    else:
        lines.append("- empty")

    lines.extend(["", "## Reasons"])
    lines.extend(f"- {reason}" for reason in result.reasons)

    if snapshot["schema_notes"]:
        lines.extend(["", "## Schema Notes"])
        lines.extend(f"- {note}" for note in snapshot["schema_notes"])
    return "\n".join(lines) + "\n"


def _write_output(content: str, output_path: str | None) -> None:
    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
    else:
        print(content, end="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only aggregate action-feedback training readiness checker.")
    parser.add_argument("--database-url", default=None, help="Database URL. Defaults to app settings.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", default=None, help="Optional report path. No files are written unless this is set.")
    args = parser.parse_args(argv)

    result = run_with_database_url(args.database_url)
    if args.format == "json":
        content = json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
    else:
        content = format_markdown(result)
    _write_output(content, args.output)
    return 0 if result.classification in {GO, NO_GO_ZERO_ACTIONS, NO_GO_ZERO_OUTCOMES, NO_GO_NO_PAIRABILITY} else 2


if __name__ == "__main__":
    raise SystemExit(main())
