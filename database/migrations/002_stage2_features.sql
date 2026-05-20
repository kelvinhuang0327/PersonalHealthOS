-- Stage 2 migration: advanced lab parsing + health score
-- Date: 2026-03-16

ALTER TABLE lab_report_items
    ADD COLUMN IF NOT EXISTS ref_low NUMERIC(10,3),
    ADD COLUMN IF NOT EXISTS ref_high NUMERIC(10,3),
    ADD COLUMN IF NOT EXISTS range_source VARCHAR(30) NOT NULL DEFAULT 'extracted',
    ADD COLUMN IF NOT EXISTS parser_confidence NUMERIC(4,3);

CREATE TABLE IF NOT EXISTS health_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_period_days INTEGER NOT NULL DEFAULT 30,
    overall_score INTEGER NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
    cardiovascular_score INTEGER NOT NULL CHECK (cardiovascular_score BETWEEN 0 AND 100),
    metabolic_score INTEGER NOT NULL CHECK (metabolic_score BETWEEN 0 AND 100),
    weight_score INTEGER NOT NULL CHECK (weight_score BETWEEN 0 AND 100),
    sleep_score INTEGER NOT NULL CHECK (sleep_score BETWEEN 0 AND 100),
    score_detail JSONB,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_health_scores_user_calculated_at
    ON health_scores(user_id, calculated_at DESC);
