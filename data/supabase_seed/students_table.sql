-- Students table for canonical student profile storage
-- Pinecone will store embeddings for semantic search

DROP TABLE IF EXISTS students CASCADE;

CREATE TABLE students (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    grade VARCHAR(20),
    disability_type VARCHAR(100),
    learning_style VARCHAR(100),
    triggers TEXT[],
    successful_methods TEXT[],
    failed_methods TEXT[],
    notes TEXT,
    iep_goals TEXT[],
    accommodations TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for common queries
CREATE INDEX idx_students_name ON students(name);
CREATE INDEX idx_students_disability_type ON students(disability_type);
CREATE INDEX idx_students_grade ON students(grade);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_students_updated_at
    BEFORE UPDATE ON students
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Sample data (matches sample_students.json)
INSERT INTO students (id, name, grade, disability_type, learning_style, triggers, successful_methods, failed_methods, notes, iep_goals, accommodations) VALUES
(
    'student_alex_m',
    'Alex M.',
    '3rd',
    'ADHD',
    'visual',
    ARRAY['loud noises', 'sudden changes', 'long waiting periods'],
    ARRAY['visual schedules', 'movement breaks', 'fidget tools'],
    ARRAY['group work without support', 'timed tests'],
    'Alex responds well to positive reinforcement and needs frequent check-ins. Morning transitions are particularly challenging.',
    ARRAY['Improve focus during independent work to 15 minutes', 'Reduce off-task behaviors by 50%'],
    ARRAY['Preferential seating', 'Extended time on tests', 'Movement breaks every 20 minutes']
),
(
    'student_jordan_k',
    'Jordan K.',
    '4th',
    'Autism Spectrum Disorder',
    'visual',
    ARRAY['unexpected transitions', 'sensory overload', 'changes in routine'],
    ARRAY['social stories', 'visual timers', 'quiet space access'],
    ARRAY['open-ended assignments', 'improvised activities'],
    'Jordan excels in math and science. Needs advance warning for transitions and prefers written instructions.',
    ARRAY['Initiate peer interactions 2x daily', 'Use coping strategies independently'],
    ARRAY['Visual schedule', 'Noise-canceling headphones available', 'Written instructions for all tasks']
),
(
    'student_maya_r',
    'Maya R.',
    '2nd',
    'Dyslexia',
    'auditory',
    ARRAY['reading aloud in front of class', 'timed reading tests'],
    ARRAY['audiobooks', 'text-to-speech', 'multisensory phonics'],
    ARRAY['traditional spelling tests', 'independent silent reading'],
    'Maya is creative and participates enthusiastically in discussions. Benefits from audio support for reading tasks.',
    ARRAY['Improve reading fluency by 20 words per minute', 'Decode multisyllabic words'],
    ARRAY['Audio versions of texts', 'Speech-to-text for writing', 'Extra time for reading tasks']
),
(
    'student_sam_t',
    'Sam T.',
    '5th',
    'Emotional/Behavioral Disorder',
    'kinesthetic',
    ARRAY['perceived criticism', 'competitive situations', 'unstructured time'],
    ARRAY['check-in/check-out', 'calm corner access', 'choice boards'],
    ARRAY['public corrections', 'loss of privileges as first response'],
    'Sam has made significant progress with self-regulation. Responds well to private feedback and building relationship.',
    ARRAY['Use self-regulation strategies 80% of the time', 'Complete assignments with minimal prompting'],
    ARRAY['Private feedback only', 'Access to calm-down space', 'Daily check-ins with counselor']
),
(
    'student_emma_l',
    'Emma L.',
    '1st',
    'Developmental Delay',
    'kinesthetic',
    ARRAY['multi-step directions', 'fast-paced activities'],
    ARRAY['hands-on learning', 'peer buddies', 'visual cues'],
    ARRAY['verbal-only instructions', 'abstract concepts without manipulatives'],
    'Emma is social and eager to please. Benefits from simplified instructions and concrete examples.',
    ARRAY['Follow 2-step directions independently', 'Count to 20 with 1:1 correspondence'],
    ARRAY['Simplified instructions', 'Visual supports', 'Extended processing time']
),
(
    'student_carlos_d',
    'Carlos D.',
    '3rd',
    'ADHD',
    'kinesthetic',
    ARRAY['sitting still for long periods', 'boring tasks', 'waiting'],
    ARRAY['standing desk', 'task chunking', 'immediate feedback'],
    ARRAY['long worksheets', 'delayed rewards'],
    'Carlos is enthusiastic and creative. Thrives with movement-based learning and immediate positive feedback.',
    ARRAY['Complete assignments within time limits', 'Stay seated during instruction for 10 minutes'],
    ARRAY['Standing desk option', 'Frequent movement breaks', 'Chunked assignments']
);
