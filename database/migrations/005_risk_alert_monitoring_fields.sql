-- Stage 5 migration: risk monitor fields
-- Date: 2026-03-17

ALTER TABLE risk_alerts
    ADD COLUMN IF NOT EXISTS risk_type VARCHAR(40),
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS recommendation TEXT,
    ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;
