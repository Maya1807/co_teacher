-- Seed script for schedule_templates table
-- Run this after creating the schema

-- Use a default teacher_id (replace with actual teacher ID in production)
-- Delete existing templates for clean re-seed
DELETE FROM schedule_templates WHERE teacher_id = 'default';

-- =====================================================
-- WEEKLY SCHEDULE: Daily Classes (Monday-Friday)
-- =====================================================

-- Math Class (Mon-Fri)
INSERT INTO schedule_templates (teacher_id, title, event_type, recurrence_type, days_of_week, start_time, end_time, sensory_factors, metadata)
VALUES (
    'default',
    'Math Class',
    'class',
    'weekly',
    ARRAY[1,2,3,4,5],  -- Mon-Fri
    '09:00',
    '10:00',
    '{"requires_focus": true, "seated_work": true}'::jsonb,
    '{"subject": "math"}'::jsonb
);

-- Science Class (Mon-Fri)
INSERT INTO schedule_templates (teacher_id, title, event_type, recurrence_type, days_of_week, start_time, end_time, sensory_factors, metadata)
VALUES (
    'default',
    'Science Class',
    'class',
    'weekly',
    ARRAY[1,2,3,4,5],
    '10:15',
    '11:15',
    '{"hands_on_activity": true, "group_work": true}'::jsonb,
    '{"subject": "science"}'::jsonb
);

-- Reading Class (Mon-Fri)
INSERT INTO schedule_templates (teacher_id, title, event_type, recurrence_type, days_of_week, start_time, end_time, sensory_factors, metadata)
VALUES (
    'default',
    'Reading Class',
    'class',
    'weekly',
    ARRAY[1,2,3,4,5],
    '11:30',
    '12:15',
    '{"quiet_environment": true, "seated_work": true}'::jsonb,
    '{"subject": "reading"}'::jsonb
);

-- Art Class (Mon-Fri)
INSERT INTO schedule_templates (teacher_id, title, event_type, recurrence_type, days_of_week, start_time, end_time, sensory_factors, metadata)
VALUES (
    'default',
    'Art Class',
    'class',
    'weekly',
    ARRAY[1,2,3,4,5],
    '13:00',
    '14:00',
    '{"hands_on_activity": true, "sensory_materials": true, "creative_expression": true}'::jsonb,
    '{"subject": "art"}'::jsonb
);

-- PE Class (Mon-Fri)
INSERT INTO schedule_templates (teacher_id, title, event_type, recurrence_type, days_of_week, start_time, end_time, sensory_factors, metadata)
VALUES (
    'default',
    'PE Class',
    'class',
    'weekly',
    ARRAY[1,2,3,4,5],
    '14:15',
    '15:00',
    '{"physical_activity": true, "loud_environment": true, "competitive": true}'::jsonb,
    '{"subject": "pe"}'::jsonb
);

-- Planning Time (Mon-Fri)
INSERT INTO schedule_templates (teacher_id, title, event_type, recurrence_type, days_of_week, start_time, end_time, sensory_factors, metadata)
VALUES (
    'default',
    'Planning Time',
    'planning',
    'weekly',
    ARRAY[1,2,3,4,5],
    '08:00',
    '08:45',
    NULL,
    '{"tasks": ["lesson_planning", "accommodations_planning"]}'::jsonb
);

-- =====================================================
-- WEEKLY SCHEDULE: One-on-One Sessions
-- =====================================================

-- Monday: One-on-One with Alex
INSERT INTO schedule_templates (teacher_id, title, event_type, recurrence_type, days_of_week, start_time, end_time, sensory_factors, metadata)
VALUES (
    'default',
    'One-on-One: Alex',
    'one_on_one',
    'weekly',
    ARRAY[1],  -- Monday
    '15:15',
    '15:45',
    '{"quiet_environment": true, "individual_attention": true}'::jsonb,
    '{"student": "Alex"}'::jsonb
);

-- Tuesday: One-on-One with Jordan
INSERT INTO schedule_templates (teacher_id, title, event_type, recurrence_type, days_of_week, start_time, end_time, sensory_factors, metadata)
VALUES (
    'default',
    'One-on-One: Jordan',
    'one_on_one',
    'weekly',
    ARRAY[2],  -- Tuesday
    '15:15',
    '15:45',
    '{"quiet_environment": true, "individual_attention": true}'::jsonb,
    '{"student": "Jordan"}'::jsonb
);

-- Wednesday: One-on-One with Sam
INSERT INTO schedule_templates (teacher_id, title, event_type, recurrence_type, days_of_week, start_time, end_time, sensory_factors, metadata)
VALUES (
    'default',
    'One-on-One: Sam',
    'one_on_one',
    'weekly',
    ARRAY[3],  -- Wednesday
    '15:15',
    '15:45',
    '{"quiet_environment": true, "individual_attention": true}'::jsonb,
    '{"student": "Sam"}'::jsonb
);

-- Thursday: One-on-One with Maya
INSERT INTO schedule_templates (teacher_id, title, event_type, recurrence_type, days_of_week, start_time, end_time, sensory_factors, metadata)
VALUES (
    'default',
    'One-on-One: Maya',
    'one_on_one',
    'weekly',
    ARRAY[4],  -- Thursday
    '15:15',
    '15:45',
    '{"quiet_environment": true, "individual_attention": true}'::jsonb,
    '{"student": "Maya"}'::jsonb
);

-- Friday: One-on-One with Ethan
INSERT INTO schedule_templates (teacher_id, title, event_type, recurrence_type, days_of_week, start_time, end_time, sensory_factors, metadata)
VALUES (
    'default',
    'One-on-One: Ethan',
    'one_on_one',
    'weekly',
    ARRAY[5],  -- Friday
    '15:15',
    '15:45',
    '{"quiet_environment": true, "individual_attention": true}'::jsonb,
    '{"student": "Ethan"}'::jsonb
);

-- =====================================================
-- WEEKLY SCHEDULE: Meetings & Communication
-- =====================================================

-- Weekly Staff Meeting (Mondays)
INSERT INTO schedule_templates (teacher_id, title, event_type, recurrence_type, days_of_week, start_time, end_time, sensory_factors, metadata)
VALUES (
    'default',
    'Weekly Staff Meeting',
    'meeting',
    'weekly',
    ARRAY[1],  -- Monday
    '16:00',
    '17:00',
    NULL,
    '{"notes": "Team coordination, student updates, scheduling"}'::jsonb
);

-- Weekly Parent Update Emails (Thursdays)
INSERT INTO schedule_templates (teacher_id, title, event_type, recurrence_type, days_of_week, start_time, end_time, sensory_factors, metadata)
VALUES (
    'default',
    'Weekly Parent Update Emails',
    'communication',
    'weekly',
    ARRAY[4],  -- Thursday
    '16:00',
    '17:00',
    NULL,
    '{"tasks": ["weekly_updates", "behavior_notes", "upcoming_events"]}'::jsonb
);

-- =====================================================
-- MONTHLY SCHEDULE
-- =====================================================

-- Monthly Meeting with Principal (Week 1, Tuesday)
INSERT INTO schedule_templates (teacher_id, title, description, event_type, recurrence_type, week_of_month, days_of_week, start_time, end_time, sensory_factors, metadata)
VALUES (
    'default',
    'Monthly Meeting with Principal',
    'Student progress updates, resource needs, upcoming events coordination',
    'meeting',
    'monthly',
    1,  -- First week of month
    ARRAY[2],  -- Tuesday
    '15:30',
    '16:15',
    NULL,
    '{"notes": "Student progress updates, resource needs, upcoming events coordination"}'::jsonb
);

-- Monthly Parent Check-ins (Week 2)
INSERT INTO schedule_templates (teacher_id, title, description, event_type, recurrence_type, week_of_month, days_of_week, start_time, end_time, sensory_factors, metadata)
VALUES (
    'default',
    'Monthly Parent Check-ins',
    'Monthly check-in messages for selected students - share wins, focus areas, coordinate on triggers/sleep/med/routine changes',
    'communication',
    'monthly',
    2,  -- Second week of month
    ARRAY[2,3,4],  -- Tue, Wed, Thu
    NULL,
    NULL,
    NULL,
    '{"tasks": ["send_monthly_checkin_messages", "share_wins_and_focus_areas", "coordinate_on_triggers", "discuss_sleep_med_routine_changes"], "target_students": "selected_students_with_needs"}'::jsonb
);

-- =====================================================
-- QUARTERLY SCHEDULE
-- =====================================================

-- IEP Progress Reporting (End of Quarter)
INSERT INTO schedule_templates (teacher_id, title, description, event_type, recurrence_type, quarter_period, duration_days, sensory_factors, metadata)
VALUES (
    'default',
    'IEP Progress Reporting',
    'Quarterly check-in on IEP goal progress for all students',
    'reporting',
    'quarterly',
    'end',
    5,  -- 5 days to complete
    NULL,
    '{"tasks": ["review_iep_goals_for_each_student", "document_progress_on_goals", "update_baseline_to_current_levels", "prepare_progress_summaries"]}'::jsonb
);

-- Write Progress Reports (End of Quarter)
INSERT INTO schedule_templates (teacher_id, title, description, event_type, recurrence_type, quarter_period, duration_days, sensory_factors, metadata)
VALUES (
    'default',
    'Write Progress Reports',
    'Write and submit progress reports aligned with report card periods',
    'reporting',
    'quarterly',
    'end',
    3,  -- 3 days to complete
    NULL,
    '{"tasks": ["write_progress_reports", "align_with_report_card_periods", "summarize_quarterly_iep_progress", "provide_updated_levels_baseline_to_now"]}'::jsonb
);

-- Planning for Next Term (End of Quarter)
INSERT INTO schedule_templates (teacher_id, title, description, event_type, recurrence_type, quarter_period, duration_days, sensory_factors, metadata)
VALUES (
    'default',
    'Planning for Next Term',
    'Strategic planning session for the upcoming term',
    'planning',
    'quarterly',
    'end',
    3,  -- 3 days to complete
    NULL,
    '{"tasks": ["review_what_worked_this_quarter", "adjust_strategies_and_accommodations", "set_goals_for_next_quarter", "plan_curriculum_adjustments", "coordinate_with_support_staff"]}'::jsonb
);

-- =====================================================
-- Verification query
-- =====================================================
-- SELECT recurrence_type, event_type, title, days_of_week, week_of_month, quarter_period
-- FROM schedule_templates
-- WHERE teacher_id = 'default'
-- ORDER BY recurrence_type, event_type;
