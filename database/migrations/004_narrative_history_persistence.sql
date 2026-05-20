ALTER TABLE ai_summaries
    ADD COLUMN IF NOT EXISTS narrative_json JSONB,
    ADD COLUMN IF NOT EXISTS narrative_version VARCHAR(20) DEFAULT 'v1',
    ADD COLUMN IF NOT EXISTS summary_type VARCHAR(30) DEFAULT 'daily',
    ADD COLUMN IF NOT EXISTS generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS based_on_score_id UUID REFERENCES health_scores(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS based_on_alert_snapshot VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_ai_summaries_user_generated_at
    ON ai_summaries(user_id, generated_at DESC);
