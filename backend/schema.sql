BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_initial

CREATE TABLE teachers (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_teachers_email UNIQUE (email)
);

CREATE TABLE classes (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    teacher_id UUID NOT NULL,
    class_name TEXT NOT NULL,
    subject TEXT DEFAULT 'Mathematics' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(teacher_id) REFERENCES teachers (id) ON DELETE CASCADE,
    CONSTRAINT uq_classes_teacher_name UNIQUE (teacher_id, class_name)
);

CREATE TABLE questions (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    topic TEXT NOT NULL,
    question_text TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    explanation_expected TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_questions_topic_text UNIQUE (topic, question_text)
);

CREATE TABLE interventions (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    topic TEXT NOT NULL,
    misconception_code TEXT NOT NULL,
    title TEXT NOT NULL,
    instructions TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE students (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    class_id UUID NOT NULL,
    student_code TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(class_id) REFERENCES classes (id) ON DELETE CASCADE,
    CONSTRAINT uq_students_class_code UNIQUE (class_id, student_code)
);

CREATE TABLE learning_groups (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    class_id UUID NOT NULL,
    topic TEXT NOT NULL,
    misconception_code TEXT NOT NULL,
    name TEXT NOT NULL,
    teacher_approved BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(class_id) REFERENCES classes (id) ON DELETE CASCADE
);

CREATE TABLE submissions (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    student_id UUID NOT NULL,
    question_id UUID NOT NULL,
    answer TEXT,
    explanation TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE CASCADE,
    FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE,
    CONSTRAINT uq_submissions_student_question UNIQUE (student_id, question_id)
);

CREATE TABLE group_members (
    group_id UUID NOT NULL,
    student_id UUID NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (group_id, student_id),
    FOREIGN KEY(group_id) REFERENCES learning_groups (id) ON DELETE CASCADE,
    FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE
);

CREATE TABLE diagnoses (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    submission_id UUID NOT NULL,
    misconception_code TEXT NOT NULL,
    confidence NUMERIC(4, 3) NOT NULL,
    evidence TEXT NOT NULL,
    status TEXT DEFAULT 'provisional' NOT NULL,
    model_version TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_diagnoses_confidence_range CHECK (confidence >= 0 AND confidence <= 1),
    CONSTRAINT ck_diagnoses_status CHECK (status IN ('provisional', 'needs_followup', 'teacher_reviewed', 'confirmed', 'rejected')),
    FOREIGN KEY(submission_id) REFERENCES submissions (id) ON DELETE CASCADE
);

CREATE TABLE intervention_assignments (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    intervention_id UUID NOT NULL,
    student_id UUID NOT NULL,
    status TEXT DEFAULT 'assigned' NOT NULL,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    CONSTRAINT ck_intervention_assignments_status CHECK (status IN ('assigned', 'in_progress', 'completed')),
    FOREIGN KEY(intervention_id) REFERENCES interventions (id),
    FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE
);

CREATE TABLE reassessment_results (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    student_id UUID NOT NULL,
    question_id UUID NOT NULL,
    intervention_assignment_id UUID,
    answer TEXT,
    is_correct BOOLEAN NOT NULL,
    assessed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(intervention_assignment_id) REFERENCES intervention_assignments (id),
    FOREIGN KEY(question_id) REFERENCES questions (id),
    FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE
);

INSERT INTO alembic_version (version_num) VALUES ('0001_initial') RETURNING alembic_version.version_num;

-- Running upgrade 0001_initial -> 0002_milestone_3_diagnosis

ALTER TABLE diagnoses ADD COLUMN followup_question TEXT;

ALTER TABLE diagnoses ADD COLUMN provider TEXT DEFAULT 'mock' NOT NULL;

ALTER TABLE learning_groups ADD COLUMN review_status TEXT DEFAULT 'proposed' NOT NULL;

ALTER TABLE learning_groups ADD CONSTRAINT ck_learning_groups_review_status CHECK (review_status IN ('proposed', 'approved', 'rejected'));

UPDATE learning_groups SET review_status = CASE WHEN teacher_approved THEN 'approved' ELSE 'proposed' END;

UPDATE alembic_version SET version_num='0002_milestone_3_diagnosis' WHERE alembic_version.version_num = '0001_initial';

-- Running upgrade 0002_milestone_3_diagnosis -> 0003_milestone_4_interventions

ALTER TABLE interventions ADD COLUMN group_id UUID;

ALTER TABLE interventions ADD CONSTRAINT fk_interventions_group_id_learning_groups FOREIGN KEY(group_id) REFERENCES learning_groups (id) ON DELETE CASCADE;

ALTER TABLE interventions ADD CONSTRAINT uq_interventions_group_id UNIQUE (group_id);

ALTER TABLE interventions ADD COLUMN learning_objective TEXT DEFAULT '' NOT NULL;

ALTER TABLE interventions ADD COLUMN explanation TEXT DEFAULT '' NOT NULL;

ALTER TABLE interventions ADD COLUMN introduction TEXT DEFAULT '' NOT NULL;

ALTER TABLE interventions ADD COLUMN guided_example JSON DEFAULT '{}' NOT NULL;

ALTER TABLE interventions ADD COLUMN practice_questions JSON DEFAULT '[]' NOT NULL;

ALTER TABLE interventions ADD COLUMN expected_answers JSON DEFAULT '[]' NOT NULL;

ALTER TABLE interventions ADD COLUMN hints JSON DEFAULT '[]' NOT NULL;

ALTER TABLE interventions ADD COLUMN provider TEXT DEFAULT 'template' NOT NULL;

ALTER TABLE interventions ADD COLUMN generation_note TEXT;

ALTER TABLE intervention_assignments ADD COLUMN started_at TIMESTAMP WITH TIME ZONE;

CREATE UNIQUE INDEX uq_intervention_assignments_active ON intervention_assignments (student_id, intervention_id) WHERE status IN ('assigned', 'in_progress');

CREATE TABLE practice_responses (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    assignment_id UUID NOT NULL,
    question_index INTEGER NOT NULL,
    answer TEXT,
    is_correct BOOLEAN NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(assignment_id) REFERENCES intervention_assignments (id) ON DELETE CASCADE,
    CONSTRAINT uq_practice_responses_assignment_question UNIQUE (assignment_id, question_index)
);

CREATE TABLE reassessments (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    assignment_id UUID NOT NULL,
    misconception_code TEXT NOT NULL,
    status TEXT DEFAULT 'pending' NOT NULL,
    total_questions INTEGER NOT NULL,
    correct_answers INTEGER,
    incorrect_answers INTEGER,
    accuracy_percentage FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    CONSTRAINT ck_reassessments_status CHECK (status IN ('pending', 'completed')),
    FOREIGN KEY(assignment_id) REFERENCES intervention_assignments (id) ON DELETE CASCADE,
    CONSTRAINT uq_reassessments_assignment UNIQUE (assignment_id)
);

CREATE TABLE reassessment_questions (
    reassessment_id UUID NOT NULL,
    question_id UUID NOT NULL,
    ordinal INTEGER NOT NULL,
    PRIMARY KEY (reassessment_id, question_id),
    FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE CASCADE,
    FOREIGN KEY(reassessment_id) REFERENCES reassessments (id) ON DELETE CASCADE,
    CONSTRAINT uq_reassessment_questions_ordinal UNIQUE (reassessment_id, ordinal)
);

ALTER TABLE reassessment_results ADD COLUMN reassessment_id UUID;

ALTER TABLE reassessment_results ADD CONSTRAINT fk_reassessment_results_reassessment_id FOREIGN KEY(reassessment_id) REFERENCES reassessments (id) ON DELETE CASCADE;

UPDATE alembic_version SET version_num='0003_milestone_4_interventions' WHERE alembic_version.version_num = '0002_milestone_3_diagnosis';

-- Running upgrade 0003_milestone_4_interventions -> 0004_submission_attempts

ALTER TABLE submissions ADD COLUMN attempt_no INTEGER DEFAULT '1' NOT NULL;

ALTER TABLE submissions DROP CONSTRAINT uq_submissions_student_question;

ALTER TABLE submissions ADD CONSTRAINT uq_submissions_student_question_attempt UNIQUE (student_id, question_id, attempt_no);

ALTER TABLE submissions ADD CONSTRAINT ck_submissions_attempt_no_positive CHECK (attempt_no > 0);

UPDATE alembic_version SET version_num='0004_submission_attempts' WHERE alembic_version.version_num = '0003_milestone_4_interventions';

COMMIT;
