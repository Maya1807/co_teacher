-- Seed data for events table
-- Run this after creating the events table

INSERT INTO events (teacher_id, title, description, event_type, event_date, start_time, end_time, is_recurring, recurrence_pattern, sensory_factors, affected_students, notes) VALUES
('default', 'Fire Drill', 'Monthly fire safety drill - alarm will sound for approximately 2 minutes', 'drill', '2026-02-02', '10:30', '10:45', false, NULL, '{"loud_sounds": true, "unexpected": true}', '{}', 'Prepare noise-sensitive students in advance. Have headphones ready.'),

('default', 'School Assembly', 'Black History Month kickoff assembly in gymnasium', 'special_event', '2026-02-02', '14:00', '15:00', false, NULL, '{"crowds": true, "loud_sounds": true}', '{}', 'Full school attendance expected. Seating near exits available for students who need breaks.'),

('default', 'Math Quiz', 'Weekly math assessment - 20 minutes timed', 'testing', '2026-02-03', '09:00', '09:30', true, 'weekly', '{"time_pressure": true}', '{}', 'Extended time accommodations apply for IEP students.'),

('default', 'Science Museum Field Trip', 'Field trip to Natural History Museum', 'field_trip', '2026-02-04', '08:30', '14:30', false, NULL, '{"new_environment": true, "crowds": true, "transitions": true}', '{}', 'Chaperone ratio 1:4. Buddy system in place. Quiet space identified at museum.'),

('default', 'Substitute Teacher Day', 'Regular teacher absent - Ms. Patterson substituting', 'transition', '2026-02-05', '08:00', '15:00', false, NULL, '{"transitions": true, "unexpected": true}', '{}', 'Visual schedule and routine cards prepared. Sub has been briefed on all IEPs.'),

('default', 'Art Class - Clay Project', 'Hands-on clay sculpting activity', 'class_schedule', '2026-02-03', '13:00', '14:00', false, NULL, '{"textures": true}', '{}', 'Alternative materials (playdough) available for texture-sensitive students.'),

('default', 'Reading Assessment', 'Quarterly reading fluency assessment', 'testing', '2026-02-06', '10:00', '11:30', false, NULL, '{"time_pressure": true}', '{}', 'Private testing room available. Text-to-speech accommodations ready.'),

('default', 'PE - Basketball Tournament', 'Inter-class basketball competition in gym', 'class_schedule', '2026-02-03', '11:00', '12:00', false, NULL, '{"loud_sounds": true, "crowds": true, "physical_contact": true}', '{}', 'Spectator area available for students who prefer to watch. Noise levels will be high.'),

('default', 'Morning Assembly', 'Weekly Monday morning assembly', 'special_event', '2026-02-03', '08:15', '08:45', true, 'weekly', '{"crowds": true}', '{}', 'Brief assembly - attendance announcements and weekly goals.'),

('default', 'Lockdown Drill', 'Quarterly safety drill - practiced lockdown procedure', 'drill', '2026-02-07', '11:00', '11:15', false, NULL, '{"unexpected": true, "confined_spaces": true}', '{}', 'Students will shelter in place. Social stories reviewed day before.');
