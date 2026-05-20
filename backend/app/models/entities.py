import uuid
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    account_settings = Column(JSON, nullable=False, server_default='{}')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    profile = relationship('UserProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')


class UserProfile(Base):
    __tablename__ = 'user_profiles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    full_name = Column(String(120))
    birth_date = Column(Date)
    gender = Column(String(20))
    height_cm = Column(Numeric(5, 2))
    weight_kg = Column(Numeric(5, 2))
    allergies = Column(Text)
    family_history = Column(Text)
    chronic_conditions = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship('User', back_populates='profile')


class PersonProfile(Base):
    __tablename__ = 'person_profiles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    display_name = Column(String(120), nullable=False)
    relationship = Column(String(30), nullable=False, default='self')
    birth_date = Column(Date)
    gender = Column(String(20))
    height_cm = Column(Numeric(5, 2))
    weight_kg = Column(Numeric(5, 2))
    allergies = Column(Text)
    family_history = Column(Text)
    chronic_conditions = Column(Text)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class HealthMetric(Base):
    __tablename__ = 'health_metrics'
    __table_args__ = (
        Index('ix_health_metric_person_date', 'subject_profile_id', 'recorded_at'),
        Index('ix_health_metric_user_person', 'user_id', 'subject_profile_id'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_profile_id = Column(UUID(as_uuid=True), ForeignKey('person_profiles.id', ondelete='SET NULL'), index=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)
    systolic_bp = Column(Integer)
    diastolic_bp = Column(Integer)
    heart_rate = Column(Integer)
    blood_glucose = Column(Numeric(7, 2))
    weight_kg = Column(Numeric(5, 2))
    sleep_hours = Column(Numeric(4, 2))
    steps = Column(Integer)
    note = Column(Text)
    source = Column(String(40), default='manual')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SymptomLog(Base):
    __tablename__ = 'symptom_logs'
    __table_args__ = (
        Index('ix_symptom_person_date', 'subject_profile_id', 'occurred_at'),
        Index('ix_symptom_user_person', 'user_id', 'subject_profile_id'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_profile_id = Column(UUID(as_uuid=True), ForeignKey('person_profiles.id', ondelete='SET NULL'), index=True)
    symptom = Column(String(120), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes = Column(Integer)
    severity = Column(Integer, nullable=False)
    note = Column(Text)
    estimated_start_date = Column(Date)
    estimated_duration_days = Column(Integer)
    temporal_source = Column(String(40))
    confidence_score = Column(Numeric(4, 3))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MedicalDocument(Base):
    __tablename__ = 'medical_documents'
    __table_args__ = (
        Index('ix_medical_document_person_upload', 'subject_profile_id', 'uploaded_at'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_profile_id = Column(UUID(as_uuid=True), ForeignKey('person_profiles.id', ondelete='SET NULL'), index=True)
    category = Column(String(40), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    mime_type = Column(String(120), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_bucket = Column(String(120), nullable=False)
    storage_key = Column(String(255), nullable=False)
    parse_status = Column(String(20), nullable=False, default='pending')
    confirmed_data = Column(JSON)
    confirmed_at = Column(DateTime(timezone=True))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LabReport(Base):
    __tablename__ = 'lab_reports'
    __table_args__ = (
        Index('ix_lab_report_person_date', 'subject_profile_id', 'report_date'),
        Index('ix_lab_report_document_created', 'document_id', 'created_at'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_profile_id = Column(UUID(as_uuid=True), ForeignKey('person_profiles.id', ondelete='SET NULL'), index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey('medical_documents.id', ondelete='SET NULL'))
    report_date = Column(Date)
    report_type = Column(String(40), nullable=False, default='health_check')
    raw_text = Column(Text)
    parser_version = Column(String(50), default='v1')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LabReportItem(Base):
    __tablename__ = 'lab_report_items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey('lab_reports.id', ondelete='CASCADE'), nullable=False, index=True)
    item_name = Column(String(120), nullable=False)
    item_code = Column(String(40))
    value_num = Column(Numeric(10, 3))
    value_text = Column(String(120))
    unit = Column(String(30))
    ref_range = Column(String(120))
    ref_low = Column(Numeric(10, 3))
    ref_high = Column(Numeric(10, 3))
    range_source = Column(String(30), nullable=False, default='extracted')
    abnormal_flag = Column(String(20))
    parser_confidence = Column(Numeric(4, 3))
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RiskAlert(Base):
    __tablename__ = 'risk_alerts'
    __table_args__ = (
        Index('ix_risk_alert_person_status_severity', 'subject_profile_id', 'status', 'severity'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_profile_id = Column(UUID(as_uuid=True), ForeignKey('person_profiles.id', ondelete='SET NULL'), index=True)
    source_type = Column(String(30), nullable=False)
    source_id = Column(UUID(as_uuid=True))
    risk_type = Column(String(40))
    rule_code = Column(String(40), nullable=False)
    severity = Column(String(20), nullable=False)
    title = Column(String(160), nullable=False)
    message = Column(Text, nullable=False)
    description = Column(Text)
    recommendation = Column(Text)
    status = Column(String(20), nullable=False, default='active')
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AISummary(Base):
    __tablename__ = 'ai_summaries'
    __table_args__ = (
        Index('ix_ai_summary_person_created', 'subject_profile_id', 'created_at'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_profile_id = Column(UUID(as_uuid=True), ForeignKey('person_profiles.id', ondelete='SET NULL'), index=True)
    period_start = Column(Date)
    period_end = Column(Date)
    summary_text = Column(Text, nullable=False)
    abnormal_explanation = Column(Text)
    recommendations = Column(Text)
    disclaimer = Column(Text, nullable=False)
    model_name = Column(String(80))
    narrative_json = Column(JSON)
    narrative_version = Column(String(20), default='v1')
    summary_type = Column(String(30), default='daily')
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    based_on_score_id = Column(UUID(as_uuid=True), ForeignKey('health_scores.id', ondelete='SET NULL'))
    based_on_alert_snapshot = Column(String(64))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class HealthScore(Base):
    __tablename__ = 'health_scores'
    __table_args__ = (
        Index('ix_health_score_person_calculated', 'subject_profile_id', 'calculated_at'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_profile_id = Column(UUID(as_uuid=True), ForeignKey('person_profiles.id', ondelete='SET NULL'), index=True)
    source_period_days = Column(Integer, nullable=False, default=30)
    overall_score = Column(Integer, nullable=False)
    cardiovascular_score = Column(Integer, nullable=False)
    metabolic_score = Column(Integer, nullable=False)
    weight_score = Column(Integer, nullable=False)
    sleep_score = Column(Integer, nullable=False)
    score_detail = Column(JSON)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class HealthInsight(Base):
    __tablename__ = 'health_insights'
    __table_args__ = (
        Index('ix_health_insight_person_active_expiry', 'subject_profile_id', 'is_active', 'expires_at'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_profile_id = Column(UUID(as_uuid=True), ForeignKey('person_profiles.id', ondelete='SET NULL'), index=True)
    insight_type = Column(String(30), nullable=False)
    severity = Column(String(20), nullable=False, default='info')
    title = Column(String(160), nullable=False)
    summary = Column(Text, nullable=False)
    recommendation = Column(Text)
    evidence_json = Column(JSON)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, nullable=False, default=True)


class HealthAction(Base):
    __tablename__ = 'health_actions'
    __table_args__ = (
        Index('ix_health_action_user_person_status_due', 'user_id', 'person_id', 'status', 'due_date'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey('person_profiles.id', ondelete='SET NULL'), index=True)
    source_type = Column(String(30), nullable=False, default='manual')
    source_id = Column(String(120))
    title = Column(String(240), nullable=False)
    description = Column(Text)
    category = Column(String(40))
    action_type = Column(String(30), nullable=False, default='lifestyle')
    priority = Column(String(10), nullable=False, default='medium')
    frequency = Column(String(20), default='daily')
    status = Column(String(20), nullable=False, default='todo')
    due_date = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    snoozed_until = Column(DateTime(timezone=True))
    snoozed_at = Column(DateTime(timezone=True))
    snooze_reason = Column(String(120))
    resurface_count = Column(Integer, nullable=False, default=0)
    streak_count = Column(Integer, nullable=False, default=0)
    last_completed_at = Column(DateTime(timezone=True))
    reminder_status = Column(String(20), default='none')
    impact_status = Column(String(20), default='no_change')
    confidence = Column(Numeric(4, 3))
    evidence_level = Column(String(2))
    guideline_source = Column(String(120))
    rule_id = Column(String(80))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    outcomes = relationship('ActionOutcome', back_populates='action', cascade='all, delete-orphan')


class ActionOutcome(Base):
    __tablename__ = 'action_outcomes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_id = Column(UUID(as_uuid=True), ForeignKey('health_actions.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    person_id = Column(UUID(as_uuid=True), ForeignKey('person_profiles.id', ondelete='SET NULL'), index=True)
    metric_type = Column(String(40), nullable=False)
    before_value = Column(Numeric(10, 3))
    after_value = Column(Numeric(10, 3))
    delta = Column(Numeric(10, 3))
    delta_pct = Column(Numeric(6, 2))
    time_window_days = Column(Integer, nullable=False, default=7)
    outcome_label = Column(String(20), default='no_change')
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    action = relationship('HealthAction', back_populates='outcomes')


class NotificationLog(Base):
    """Persisted record of each notification candidate — enables stateful fatigue guard."""
    __tablename__ = 'notification_logs'
    __table_args__ = (
        Index('ix_notification_log_person_key_at', 'subject_profile_id', 'cooldown_key', 'generated_at'),
        Index('ix_notification_log_user_person_at', 'user_id', 'subject_profile_id', 'generated_at'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_profile_id = Column(UUID(as_uuid=True), ForeignKey('person_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    # Deterministic hash of cooldown_key (12-char hex)
    candidate_id = Column(String(12), nullable=False, index=True)
    cooldown_key = Column(String(120), nullable=False)
    source_type = Column(String(30), nullable=False)
    priority = Column(String(10), nullable=False)
    title = Column(String(240), nullable=False)
    message = Column(Text)
    # generated | delivered | snoozed | ignored | clicked | acted | suppressed
    status = Column(String(20), nullable=False, default='generated')
    suppress_reason = Column(Text)
    generated_at = Column(DateTime(timezone=True), nullable=False)
    delivered_at = Column(DateTime(timezone=True))
    snoozed_until = Column(DateTime(timezone=True))
    clicked_at = Column(DateTime(timezone=True))
    acted_at = Column(DateTime(timezone=True))
    # Cumulative counters (updated in-place on the most recent record per cooldown_key)
    snooze_count = Column(Integer, nullable=False, default=0)
    ignore_count = Column(Integer, nullable=False, default=0)
    evidence_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PersonalizationProfile(Base):
    """Per-person adaptive personalization profile — learns from engagement history."""
    __tablename__ = 'personalization_profiles'
    __table_args__ = (
        Index('ix_pers_profile_user_person', 'user_id', 'subject_profile_id', unique=True),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_profile_id = Column(UUID(as_uuid=True), ForeignKey('person_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    # 0.0 (disengaged) – 1.0 (highly engaged); default 0.5 (neutral)
    engagement_score = Column(Numeric(4, 3), nullable=False, server_default='0.5')
    # 'proactive' | 'balanced' | 'minimal'
    response_style = Column(String(20), nullable=False, server_default="'balanced'")
    # {hour_of_day: weight} — learned from click/act timestamps
    preferred_notification_timing = Column(JSON, nullable=False, server_default='{}')
    # ['lab_abnormality', 'device_escalation', ...] — top engaged types
    preferred_notification_types = Column(JSON, nullable=False, server_default='[]')
    # {source_type: ignore_count} — accumulated ignore signals
    ignored_categories = Column(JSON, nullable=False, server_default='{}')
    # {source_type: act_count} — accumulated act signals
    acted_categories = Column(JSON, nullable=False, server_default='{}')
    # source_types with consistently high response (act_count >= 2)
    high_response_categories = Column(JSON, nullable=False, server_default='[]')
    # Median minutes from notification delivered → user click/act
    avg_response_delay_minutes = Column(Numeric(8, 2))
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
