-- Runtime compatibility migration for current SQLAlchemy models
-- Date: 2026-03-16

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS account_settings JSONB NOT NULL DEFAULT '{}'::jsonb;

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

CREATE INDEX IF NOT EXISTS idx_person_profiles_owner_user_id
  ON person_profiles(owner_user_id);

ALTER TABLE health_metrics
  ADD COLUMN IF NOT EXISTS subject_profile_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS steps INTEGER;

ALTER TABLE symptom_logs
  ADD COLUMN IF NOT EXISTS subject_profile_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL;

ALTER TABLE medical_documents
  ADD COLUMN IF NOT EXISTS subject_profile_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS confirmed_data JSONB,
  ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;

ALTER TABLE lab_reports
  ADD COLUMN IF NOT EXISTS subject_profile_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL;

ALTER TABLE risk_alerts
  ADD COLUMN IF NOT EXISTS subject_profile_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL;

ALTER TABLE ai_summaries
  ADD COLUMN IF NOT EXISTS subject_profile_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL;

ALTER TABLE health_scores
  ADD COLUMN IF NOT EXISTS subject_profile_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_health_metrics_subject_profile_id ON health_metrics(subject_profile_id);
CREATE INDEX IF NOT EXISTS idx_symptom_logs_subject_profile_id ON symptom_logs(subject_profile_id);
CREATE INDEX IF NOT EXISTS idx_medical_documents_subject_profile_id ON medical_documents(subject_profile_id);
CREATE INDEX IF NOT EXISTS idx_lab_reports_subject_profile_id ON lab_reports(subject_profile_id);
CREATE INDEX IF NOT EXISTS idx_risk_alerts_subject_profile_id ON risk_alerts(subject_profile_id);
CREATE INDEX IF NOT EXISTS idx_ai_summaries_subject_profile_id ON ai_summaries(subject_profile_id);
CREATE INDEX IF NOT EXISTS idx_health_scores_subject_profile_id ON health_scores(subject_profile_id);
