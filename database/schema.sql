-- Personal Health Platform MVP PostgreSQL Schema
-- Date: 2026-03-16

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    account_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(120),
    birth_date DATE,
    gender VARCHAR(20),
    height_cm NUMERIC(5,2),
    weight_kg NUMERIC(5,2),
    allergies TEXT,
    family_history TEXT,
    chronic_conditions TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS person_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    display_name VARCHAR(120) NOT NULL,
    relationship VARCHAR(30) NOT NULL DEFAULT 'self',
    birth_date DATE,
    gender VARCHAR(20),
    height_cm NUMERIC(5,2),
    weight_kg NUMERIC(5,2),
    allergies TEXT,
    family_history TEXT,
    chronic_conditions TEXT,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS health_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_profile_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    systolic_bp INTEGER,
    diastolic_bp INTEGER,
    heart_rate INTEGER,
    blood_glucose NUMERIC(7,2),
    weight_kg NUMERIC(5,2),
    sleep_hours NUMERIC(4,2),
    steps INTEGER,
    note TEXT,
    source VARCHAR(40) DEFAULT 'manual',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS symptom_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_profile_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL,
    symptom VARCHAR(120) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER,
    severity INTEGER NOT NULL CHECK (severity BETWEEN 1 AND 5),
    note TEXT,
    estimated_start_date DATE,
    estimated_duration_days INTEGER,
    temporal_source VARCHAR(40),
    confidence_score NUMERIC(4,3),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS medical_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_profile_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL,
    category VARCHAR(40) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    file_size BIGINT NOT NULL,
    storage_bucket VARCHAR(120) NOT NULL,
    storage_key VARCHAR(255) NOT NULL,
    parse_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    confirmed_data JSONB,
    confirmed_at TIMESTAMPTZ,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lab_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_profile_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL,
    document_id UUID REFERENCES medical_documents(id) ON DELETE SET NULL,
    report_date DATE,
    report_type VARCHAR(40) NOT NULL DEFAULT 'health_check',
    raw_text TEXT,
    parser_version VARCHAR(50) DEFAULT 'v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lab_report_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES lab_reports(id) ON DELETE CASCADE,
    item_name VARCHAR(120) NOT NULL,
    item_code VARCHAR(40),
    value_num NUMERIC(10,3),
    value_text VARCHAR(120),
    unit VARCHAR(30),
    ref_range VARCHAR(120),
    ref_low NUMERIC(10,3),
    ref_high NUMERIC(10,3),
    range_source VARCHAR(30) NOT NULL DEFAULT 'extracted',
    abnormal_flag VARCHAR(20),
    parser_confidence NUMERIC(4,3),
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_profile_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL,
    source_type VARCHAR(30) NOT NULL,
    source_id UUID,
    risk_type VARCHAR(40),
    rule_code VARCHAR(40) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(160) NOT NULL,
    message TEXT NOT NULL,
    description TEXT,
    recommendation TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_profile_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL,
    period_start DATE,
    period_end DATE,
    summary_text TEXT NOT NULL,
    abnormal_explanation TEXT,
    recommendations TEXT,
    disclaimer TEXT NOT NULL,
    model_name VARCHAR(80),
    narrative_json JSONB,
    narrative_version VARCHAR(20) DEFAULT 'v1',
    summary_type VARCHAR(30) DEFAULT 'daily',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    based_on_score_id UUID REFERENCES health_scores(id) ON DELETE SET NULL,
    based_on_alert_snapshot VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS health_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_profile_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL,
    source_period_days INTEGER NOT NULL DEFAULT 30,
    overall_score INTEGER NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
    cardiovascular_score INTEGER NOT NULL CHECK (cardiovascular_score BETWEEN 0 AND 100),
    metabolic_score INTEGER NOT NULL CHECK (metabolic_score BETWEEN 0 AND 100),
    weight_score INTEGER NOT NULL CHECK (weight_score BETWEEN 0 AND 100),
    sleep_score INTEGER NOT NULL CHECK (sleep_score BETWEEN 0 AND 100),
    score_detail JSONB,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS health_insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_profile_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL,
    insight_type VARCHAR(30) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'info',
    title VARCHAR(160) NOT NULL,
    summary TEXT NOT NULL,
    recommendation TEXT,
    evidence_json JSONB,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_person_profiles_owner_user_id ON person_profiles(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_health_metrics_user_recorded_at ON health_metrics(user_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_metrics_subject_profile_id ON health_metrics(subject_profile_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_symptom_logs_user_occurred_at ON symptom_logs(user_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_symptom_logs_subject_profile_id ON symptom_logs(subject_profile_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_medical_documents_user_uploaded_at ON medical_documents(user_id, uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_medical_documents_subject_profile_id ON medical_documents(subject_profile_id, uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_lab_reports_user_created_at ON lab_reports(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lab_report_items_report_id ON lab_report_items(report_id);
CREATE INDEX IF NOT EXISTS idx_risk_alerts_user_status_created_at ON risk_alerts(user_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_alerts_subject_profile_id ON risk_alerts(subject_profile_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_summaries_user_created_at ON ai_summaries(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_summaries_user_generated_at ON ai_summaries(user_id, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_scores_user_calculated_at ON health_scores(user_id, calculated_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_insights_user_generated_at ON health_insights(user_id, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_insights_subject_profile_id ON health_insights(subject_profile_id, generated_at DESC);
