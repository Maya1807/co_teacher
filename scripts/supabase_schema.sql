-- Supabase SQL Schema for Co-Teacher
-- Run this in the Supabase SQL Editor

-- =====================================================
-- Table: conversations
-- Purpose: Track conversation context within a session
-- =====================================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(100) NOT NULL,
    teacher_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_teacher ON conversations(teacher_id);

-- =====================================================
-- Table: conversation_messages
-- Purpose: Individual messages in a conversation
-- =====================================================
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    agent_used VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON conversation_messages(conversation_id);

-- =====================================================
-- Table: daily_context
-- Purpose: Store daily classroom context/alerts
-- =====================================================
CREATE TABLE IF NOT EXISTS daily_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id VARCHAR(100) NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    context_type VARCHAR(50) NOT NULL CHECK (context_type IN ('alert', 'observation', 'note', 'event')),
    student_id VARCHAR(100),
    content TEXT NOT NULL,
    priority INTEGER DEFAULT 0 CHECK (priority >= 0 AND priority <= 2),
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_context_teacher_date ON daily_context(teacher_id, date);
CREATE INDEX IF NOT EXISTS idx_daily_context_student ON daily_context(student_id);

-- =====================================================
-- Table: alerts_sent
-- Purpose: Track alerts already sent to avoid duplicates
-- =====================================================
CREATE TABLE IF NOT EXISTS alerts_sent (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id VARCHAR(100) NOT NULL,
    student_id VARCHAR(100),
    alert_type VARCHAR(50) NOT NULL,
    alert_content TEXT NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_sent_teacher ON alerts_sent(teacher_id, sent_at);

-- =====================================================
-- Table: pending_feedback
-- Purpose: Actions awaiting teacher feedback
-- =====================================================
CREATE TABLE IF NOT EXISTS pending_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id VARCHAR(100) NOT NULL,
    student_id VARCHAR(100),
    action_type VARCHAR(50) NOT NULL CHECK (action_type IN ('method_suggestion', 'iep_draft', 'parent_message')),
    original_suggestion TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    feedback_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_pending_feedback_teacher ON pending_feedback(teacher_id, status);

-- =====================================================
-- Table: response_cache
-- Purpose: Cache common LLM responses to save costs
-- =====================================================
CREATE TABLE IF NOT EXISTS response_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    prompt_hash VARCHAR(64) NOT NULL,
    response TEXT NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    hit_count INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours')
);

CREATE INDEX IF NOT EXISTS idx_response_cache_key ON response_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_response_cache_expires ON response_cache(expires_at);

-- =====================================================
-- Table: budget_tracking
-- Purpose: Track LLM API costs
-- =====================================================
CREATE TABLE IF NOT EXISTS budget_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model VARCHAR(100) NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    cost DECIMAL(10, 6) NOT NULL,
    agent_type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_budget_tracking_date ON budget_tracking(created_at);

-- =====================================================
-- Function: Update updated_at timestamp
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for conversations table
DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Function: Clean expired cache entries (run periodically)
-- =====================================================
CREATE OR REPLACE FUNCTION clean_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM response_cache WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ language 'plpgsql';

-- =====================================================
-- Table: events
-- Purpose: Track scheduled events for predictive analysis
-- =====================================================
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN (
        'class_schedule',    -- Regular class activities (math, reading, PE)
        'special_event',     -- Assemblies, performances, picture day
        'drill',             -- Fire drill, lockdown drill
        'field_trip',        -- Off-campus activities
        'holiday',           -- No school days
        'testing',           -- Standardized tests, assessments
        'transition'         -- Schedule changes, substitute teacher
    )),
    event_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_pattern VARCHAR(50),  -- 'daily', 'weekly', 'monthly'
    sensory_factors JSONB,  -- {"loud_sounds": true, "bright_lights": false, "crowds": true}
    affected_students TEXT[],  -- Student IDs particularly affected
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_teacher_date ON events(teacher_id, event_date);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);

-- Trigger for events table
DROP TRIGGER IF EXISTS update_events_updated_at ON events;
CREATE TRIGGER update_events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Table: schedule_templates
-- Purpose: Store recurring schedule patterns
-- =====================================================
CREATE TABLE IF NOT EXISTS schedule_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN (
        'class',            -- Regular classes (math, science, reading, art, pe)
        'one_on_one',       -- Individual student sessions
        'meeting',          -- Staff meetings, principal meetings
        'communication',    -- Parent emails, check-ins
        'planning',         -- Lesson planning, accommodations planning
        'reporting'         -- IEP progress, report writing
    )),
    recurrence_type VARCHAR(20) NOT NULL CHECK (recurrence_type IN (
        'weekly',           -- Repeats every week
        'monthly',          -- Repeats every month
        'quarterly'         -- Repeats every quarter
    )),
    -- Weekly recurrence: which days (0=Sunday, 1=Monday, ..., 6=Saturday)
    days_of_week INTEGER[],
    -- Monthly recurrence: which week of month (1-4)
    week_of_month INTEGER CHECK (week_of_month >= 1 AND week_of_month <= 4),
    -- Quarterly recurrence: which part of quarter
    quarter_period VARCHAR(20) CHECK (quarter_period IN ('start', 'middle', 'end')),
    -- Time slots
    start_time TIME,
    end_time TIME,
    duration_days INTEGER DEFAULT 1,  -- For multi-day tasks (quarterly reporting)
    -- Sensory factors for prediction matching
    sensory_factors JSONB,
    -- Additional metadata (student name for 1:1, task lists, notes)
    metadata JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_schedule_templates_teacher ON schedule_templates(teacher_id);
CREATE INDEX IF NOT EXISTS idx_schedule_templates_type ON schedule_templates(event_type);
CREATE INDEX IF NOT EXISTS idx_schedule_templates_recurrence ON schedule_templates(recurrence_type);

-- Trigger for schedule_templates table
DROP TRIGGER IF EXISTS update_schedule_templates_updated_at ON schedule_templates;
CREATE TRIGGER update_schedule_templates_updated_at
    BEFORE UPDATE ON schedule_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
