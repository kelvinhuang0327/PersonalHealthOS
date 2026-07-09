import pytest

from app.services.action_feedback_readiness import (
    BLOCKED_READ_ONLY_NOT_GUARANTEED,
    GO,
    NO_GO_NO_PAIRABILITY,
    NO_GO_ZERO_ACTIONS,
    NO_GO_ZERO_OUTCOMES,
    UNKNOWN_DB_UNAVAILABLE,
    ReadOnlySafetyError,
    evaluate_action_feedback_readiness,
    run_with_database_url,
)
import app.services.action_feedback_readiness as readiness_module


class FakeReadinessRunner:
    def __init__(
        self,
        *,
        counts=None,
        feedback_labels=None,
        metric_labels=None,
        pairability=0,
        read_only=True,
        read_only_error=None,
    ):
        self.counts = counts or {}
        self.feedback_labels = feedback_labels or {}
        self.metric_labels = metric_labels or []
        self.pairability = pairability
        self.read_only = read_only
        self.read_only_error = read_only_error
        self.executed_sql = []
        self._tables = {
            "lab_report_items",
            "lab_reports",
            "medical_documents",
            "symptom_logs",
            "health_metrics",
            "health_actions",
            "action_outcomes",
        }
        self._columns = {
            "lab_reports": {"id", "document_id"},
            "medical_documents": {"id", "confirmed_at", "confirmed_data"},
            "action_outcomes": {"metric_type", "outcome_label", "before_value", "after_value"},
        }

    def ensure_read_only(self):
        if self.read_only_error:
            raise self.read_only_error
        return self.read_only

    def table_exists(self, table_name):
        return table_name in self._tables

    def columns(self, table_name):
        return self._columns.get(table_name, set())

    def scalar(self, sql, params=None):
        self.executed_sql.append(sql)
        compact = " ".join(sql.split())
        if "FROM lab_report_items" in compact:
            return self.counts.get("confirmed_report_metrics", 0)
        if "FROM symptom_logs" in compact:
            return self.counts.get("symptom_logs", 0)
        if "FROM health_metrics" in compact:
            return self.counts.get("health_metrics", 0)
        if "FROM health_actions" in compact:
            return self.counts.get("health_actions", 0)
        if "FROM action_outcomes" in compact and "before_value IS NOT NULL" in compact:
            return self.pairability
        if "FROM action_outcomes" in compact:
            return self.counts.get("action_outcomes", 0)
        raise AssertionError(f"unexpected scalar query: {sql}")

    def rows(self, sql, params=None):
        self.executed_sql.append(sql)
        compact = " ".join(sql.split())
        if "WHERE metric_type = :feedback_metric" in compact:
            return [
                {"outcome_label": label, "count": count}
                for label, count in self.feedback_labels.items()
            ]
        if "GROUP BY COALESCE(metric_type" in compact:
            return self.metric_labels
        raise AssertionError(f"unexpected rows query: {sql}")


def _base_counts(action_outcomes):
    return {
        "confirmed_report_metrics": 20,
        "symptom_logs": 10,
        "health_metrics": 74,
        "health_actions": 3,
        "action_outcomes": action_outcomes,
    }


def test_zero_outcomes_returns_no_go_zero_outcomes():
    counts = _base_counts(action_outcomes=0)
    counts["health_actions"] = 0
    runner = FakeReadinessRunner(counts=counts)

    result = evaluate_action_feedback_readiness(runner)

    assert result.classification == NO_GO_ZERO_OUTCOMES
    assert result.read_only_verified is True
    assert result.snapshot.action_outcomes_count == 0


def test_zero_actions_with_existing_outcomes_returns_no_go_zero_actions():
    counts = _base_counts(action_outcomes=2)
    counts["health_actions"] = 0
    runner = FakeReadinessRunner(
        counts=counts,
        feedback_labels={"improved": 2},
        metric_labels=[{"metric_type": "user_feedback", "outcome_label": "improved", "count": 2}],
        pairability=1,
    )

    result = evaluate_action_feedback_readiness(runner)

    assert result.classification == NO_GO_ZERO_ACTIONS
    assert result.snapshot.health_actions_count == 0


def test_nonzero_outcomes_without_pairability_returns_no_go_no_pairability():
    runner = FakeReadinessRunner(
        counts=_base_counts(action_outcomes=2),
        feedback_labels={"improved": 2},
        metric_labels=[{"metric_type": "user_feedback", "outcome_label": "improved", "count": 2}],
        pairability=0,
    )

    result = evaluate_action_feedback_readiness(runner)

    assert result.classification == NO_GO_NO_PAIRABILITY
    assert result.snapshot.before_after_pairability_count == 0


def test_enough_mocked_aggregate_values_returns_go():
    runner = FakeReadinessRunner(
        counts=_base_counts(action_outcomes=4),
        feedback_labels={"improved": 3, "no_change": 1},
        metric_labels=[
            {"metric_type": "steps", "outcome_label": "improved", "count": 1},
            {"metric_type": "user_feedback", "outcome_label": "improved", "count": 3},
        ],
        pairability=2,
    )

    result = evaluate_action_feedback_readiness(runner)

    assert result.classification == GO
    assert result.snapshot.feedback_label_distribution == {"improved": 3, "no_change": 1}
    assert result.snapshot.before_after_pairability_count == 2


def test_db_unavailable_returns_unknown():
    runner = FakeReadinessRunner(read_only_error=ConnectionError("database unavailable"))

    result = evaluate_action_feedback_readiness(runner)

    assert result.classification == UNKNOWN_DB_UNAVAILABLE
    assert result.read_only_verified is False


def test_database_connection_open_failure_returns_unknown(monkeypatch):
    class UnavailableRunner:
        def __init__(self, database_url=None):
            pass

        def __enter__(self):
            raise ConnectionError("database unavailable")

        def __exit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(readiness_module, "SqlAlchemyReadOnlyRunner", UnavailableRunner)

    result = run_with_database_url("postgresql+psycopg2://example")

    assert result.classification == UNKNOWN_DB_UNAVAILABLE
    assert result.read_only_verified is False


@pytest.mark.parametrize(
    "read_only, read_only_error",
    [
        (False, None),
        (True, ReadOnlySafetyError("read-only not proven")),
    ],
)
def test_read_only_safety_not_guaranteed_returns_blocked(read_only, read_only_error):
    runner = FakeReadinessRunner(read_only=read_only, read_only_error=read_only_error)

    result = evaluate_action_feedback_readiness(runner)

    assert result.classification == BLOCKED_READ_ONLY_NOT_GUARANTEED
    assert result.read_only_verified is False


def test_queries_are_aggregate_only_and_do_not_select_raw_phi_pii_fields():
    runner = FakeReadinessRunner(
        counts=_base_counts(action_outcomes=1),
        feedback_labels={"improved": 1},
        metric_labels=[{"metric_type": "user_feedback", "outcome_label": "improved", "count": 1}],
        pairability=1,
    )

    evaluate_action_feedback_readiness(runner)

    all_sql = "\n".join(runner.executed_sql).lower()
    assert "select *" not in all_sql
    assert "select id" not in all_sql
    for forbidden_field in (
        "full_name",
        "display_name",
        "raw_text",
        "title",
        "description",
    ):
        assert forbidden_field not in all_sql
    for forbidden_select in ("select note", "select symptom"):
        assert forbidden_select not in all_sql
