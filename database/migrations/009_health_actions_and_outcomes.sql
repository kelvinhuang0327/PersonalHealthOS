-- Migration 009: Health Actions Backend + Action Outcomes
-- Behavior Change System: Action → Outcome → Feedback loop
-- Date: 2026-04-18

-- ============================================================
-- health_actions: persistent action store (replaces localStorage)
-- ============================================================
CREATE TABLE IF NOT EXISTS health_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    person_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL,
    source_type VARCHAR(30) NOT NULL DEFAULT 'manual',   -- alert / insight / recommendation / manual
    source_id VARCHAR(120),
    title VARCHAR(240) NOT NULL,
    description TEXT,
    category VARCHAR(40),                                 -- bp / uric_acid / sleep / activity / weight / general
    action_type VARCHAR(30) NOT NULL DEFAULT 'lifestyle', -- monitor / habit / follow_up / lifestyle
    priority VARCHAR(10) NOT NULL DEFAULT 'medium',       -- low / medium / high
    frequency VARCHAR(20) DEFAULT 'daily',                -- daily / weekly / custom
    status VARCHAR(20) NOT NULL DEFAULT 'todo',           -- todo / in_progress / done / snoozed
    due_date TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    snoozed_until TIMESTAMPTZ,
    snoozed_at TIMESTAMPTZ,
    snooze_reason VARCHAR(120),
    resurface_count INTEGER NOT NULL DEFAULT 0,
    streak_count INTEGER NOT NULL DEFAULT 0,
    last_completed_at TIMESTAMPTZ,
    reminder_status VARCHAR(20) DEFAULT 'none',           -- none / overdue / risk_up / no_data / streak_break
    impact_status VARCHAR(20) DEFAULT 'no_change',        -- improved / no_change / worse
    confidence NUMERIC(4, 3),
    evidence_level VARCHAR(2),                            -- A / B / C
    guideline_source VARCHAR(120),
    rule_id VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- action_outcomes: measures what changed after completing action
-- ============================================================
CREATE TABLE IF NOT EXISTS action_outcomes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_id UUID NOT NULL REFERENCES health_actions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    person_id UUID REFERENCES person_profiles(id) ON DELETE SET NULL,
    metric_type VARCHAR(40) NOT NULL,   -- bp_systolic / bp_diastolic / weight_kg / uric_acid / sleep_hours / steps / blood_glucose
    before_value NUMERIC(10, 3),
    after_value NUMERIC(10, 3),
    delta NUMERIC(10, 3),
    delta_pct NUMERIC(6, 2),
    time_window_days INTEGER NOT NULL DEFAULT 7,  -- 7 / 14 / 30
    outcome_label VARCHAR(20) DEFAULT 'no_change', -- improved / no_change / worse
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_health_actions_user_id ON health_actions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_actions_person_id ON health_actions(person_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_actions_status ON health_actions(status);
CREATE INDEX IF NOT EXISTS idx_health_actions_source ON health_actions(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_action_outcomes_action_id ON action_outcomes(action_id);
CREATE INDEX IF NOT EXISTS idx_action_outcomes_user_id ON action_outcomes(user_id, computed_at DESC);
