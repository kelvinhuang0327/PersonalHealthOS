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

CREATE INDEX IF NOT EXISTS idx_health_insights_user_generated_at ON health_insights(user_id, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_insights_subject_profile_id ON health_insights(subject_profile_id, generated_at DESC);
