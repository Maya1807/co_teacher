-- Co-Teacher Supabase Schema Reset Script
-- This script drops all existing tables and recreates them with the correct schema
-- Run this in the Supabase SQL Editor

-- ============================================
-- DROP ALL TABLES
-- ============================================

DROP TABLE IF EXISTS conversation_messages CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS daily_context CASCADE;
DROP TABLE IF EXISTS response_cache CASCADE;
DROP TABLE IF EXISTS alerts_sent CASCADE;
DROP TABLE IF EXISTS pending_feedback CASCADE;
DROP TABLE IF EXISTS budget_tracking CASCADE;

-- ============================================
-- CREATE TABLES (no foreign keys for easier CSV import)
-- ============================================

-- conversations: Track session context
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(100) NOT NULL,
    teacher_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- conversation_messages: Individual messages (no FK for simpler import)
CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    agent_used VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- daily_context: Daily alerts/observations
CREATE TABLE daily_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id VARCHAR(100) NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    context_type VARCHAR(50),
    student_id VARCHAR(100),
    content TEXT NOT NULL,
    is_resolved BOOLEAN DEFAULT FALSE,
    priority INTEGER DEFAULT 0
);

-- response_cache: LLM response caching
CREATE TABLE response_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key VARCHAR(255) UNIQUE,
    prompt_hash VARCHAR(255),
    response TEXT NOT NULL,
    agent_type VARCHAR(50),
    expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '24 hours'),
    hit_count INTEGER DEFAULT 0
);

-- alerts_sent: Track sent alerts to avoid duplicates
CREATE TABLE alerts_sent (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id VARCHAR(100) NOT NULL,
    alert_type VARCHAR(50),
    alert_content TEXT,
    student_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- pending_feedback: Teacher feedback on suggestions
CREATE TABLE pending_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id VARCHAR(100) NOT NULL,
    action_type VARCHAR(50),
    original_suggestion TEXT,
    student_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    feedback_notes TEXT,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- budget_tracking: LLM API usage and costs
CREATE TABLE budget_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model VARCHAR(100),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    cost DECIMAL(10, 6),
    agent_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- CREATE INDEXES FOR PERFORMANCE
-- ============================================

CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_conversations_teacher ON conversations(teacher_id);
CREATE INDEX idx_messages_conversation ON conversation_messages(conversation_id);
CREATE INDEX idx_daily_context_teacher_date ON daily_context(teacher_id, date);
CREATE INDEX idx_daily_context_student ON daily_context(student_id);
CREATE INDEX idx_response_cache_key ON response_cache(cache_key);
CREATE INDEX idx_response_cache_expires ON response_cache(expires_at);
CREATE INDEX idx_alerts_sent_teacher ON alerts_sent(teacher_id);
CREATE INDEX idx_pending_feedback_teacher ON pending_feedback(teacher_id);
CREATE INDEX idx_pending_feedback_status ON pending_feedback(status);
CREATE INDEX idx_budget_tracking_created ON budget_tracking(created_at);

-- ============================================
-- ENABLE ROW LEVEL SECURITY (with permissive policies)
-- ============================================

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_context ENABLE ROW LEVEL SECURITY;
ALTER TABLE response_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts_sent ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE budget_tracking ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all on conversations" ON conversations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on conversation_messages" ON conversation_messages FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on daily_context" ON daily_context FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on response_cache" ON response_cache FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on alerts_sent" ON alerts_sent FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on pending_feedback" ON pending_feedback FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on budget_tracking" ON budget_tracking FOR ALL USING (true) WITH CHECK (true);

-- ============================================
-- VERIFY
-- ============================================

SELECT 'Schema reset complete!' AS status;
