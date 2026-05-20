-- Stage 4 migration: temporal parsing fields for symptom narratives
-- Date: 2026-03-17

ALTER TABLE symptom_logs
    ADD COLUMN IF NOT EXISTS estimated_start_date DATE,
    ADD COLUMN IF NOT EXISTS estimated_duration_days INTEGER,
    ADD COLUMN IF NOT EXISTS temporal_source VARCHAR(40),
    ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(4,3);
