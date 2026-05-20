-- Personal Health Platform MVP PostgreSQL Schema
-- Date: 2026-03-16

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
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

CREATE TABLE IF NOT EXISTS health_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recorded_at TIMESTAMPTZ NOT NULL,
    systolic_bp INTEGER,
    diastolic_bp INTEGER,
    heart_rate INTEGER,
    blood_glucose NUMERIC(7,2),
    weight_kg NUMERIC(5,2),
    sleep_hours NUMERIC(4,2),
    note TEXT,
    source VARCHAR(40) DEFAULT 'manual',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS symptom_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symptom VARCHAR(120) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER,
    severity INTEGER NOT NULL CHECK (severity BETWEEN 1 AND 5),
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS medical_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(40) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    file_size BIGINT NOT NULL,
    storage_bucket VARCHAR(120) NOT NULL,
    storage_key VARCHAR(255) NOT NULL,
    parse_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lab_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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
    abnormal_flag VARCHAR(20),
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_type VARCHAR(30) NOT NULL,
    source_id UUID,
    rule_code VARCHAR(40) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(160) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_health_metrics_user_recorded_at ON health_metrics(user_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_symptom_logs_user_occurred_at ON symptom_logs(user_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_medical_documents_user_uploaded_at ON medical_documents(user_id, uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_lab_reports_user_created_at ON lab_reports(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lab_report_items_report_id ON lab_report_items(report_id);
CREATE INDEX IF NOT EXISTS idx_risk_alerts_user_status_created_at ON risk_alerts(user_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_summaries_user_created_at ON ai_summaries(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_summaries_user_generated_at ON ai_summaries(user_id, generated_at DESC);
