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

-- Running upgrade 0004_submission_attempts -> 0005_multisubject_diagnoses

ALTER TABLE classes ADD COLUMN topic TEXT DEFAULT 'Fractions' NOT NULL;

ALTER TABLE questions ADD COLUMN subject TEXT DEFAULT 'Mathematics' NOT NULL;

ALTER TABLE questions DROP CONSTRAINT uq_questions_topic_text;

ALTER TABLE questions ADD CONSTRAINT uq_questions_subject_topic_text UNIQUE (subject, topic, question_text);

ALTER TABLE diagnoses ADD COLUMN misconception_description TEXT;

ALTER TABLE diagnoses ADD COLUMN misunderstanding_explanation TEXT;

ALTER TABLE diagnoses ADD COLUMN suggested_intervention TEXT;

ALTER TABLE interventions ADD COLUMN subject TEXT DEFAULT 'Mathematics' NOT NULL;

UPDATE alembic_version SET version_num='0005_multisubject_diagnoses' WHERE alembic_version.version_num = '0004_submission_attempts';

-- Running upgrade 0005_multisubject_diagnoses -> 0006_quiz_learning_loop

CREATE TABLE quizzes (
    id UUID NOT NULL,
    class_id UUID NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    questions JSON NOT NULL,
    lesson JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_quiz_status CHECK (status IN ('draft', 'published')),
    FOREIGN KEY(class_id) REFERENCES classes (id) ON DELETE CASCADE
);

CREATE INDEX ix_quizzes_class_id ON quizzes (class_id);

CREATE TABLE quiz_attempts (
    id UUID NOT NULL,
    quiz_id UUID NOT NULL,
    student_id UUID NOT NULL,
    answers JSON NOT NULL,
    score INTEGER NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_quiz_student_attempt UNIQUE (quiz_id, student_id),
    FOREIGN KEY(quiz_id) REFERENCES quizzes (id) ON DELETE CASCADE,
    FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE
);

CREATE INDEX ix_quiz_attempts_quiz_id ON quiz_attempts (quiz_id);

CREATE INDEX ix_quiz_attempts_student_id ON quiz_attempts (student_id);

CREATE TABLE quiz_reflections (
    id UUID NOT NULL,
    attempt_id UUID NOT NULL,
    question_id TEXT NOT NULL,
    messages JSON NOT NULL,
    feedback JSON NOT NULL,
    flagged BOOLEAN NOT NULL,
    repair_answer INTEGER,
    PRIMARY KEY (id),
    CONSTRAINT uq_quiz_reflection UNIQUE (attempt_id, question_id),
    FOREIGN KEY(attempt_id) REFERENCES quiz_attempts (id) ON DELETE CASCADE
);

CREATE INDEX ix_quiz_reflections_attempt_id ON quiz_reflections (attempt_id);

UPDATE alembic_version SET version_num='0006_quiz_learning_loop' WHERE alembic_version.version_num = '0005_multisubject_diagnoses';

-- Running upgrade 0006_quiz_learning_loop -> 0007_learning_intelligence

CREATE TABLE mutation_receipts (
    id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    response JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE lessons (
    id UUID NOT NULL,
    class_id UUID NOT NULL,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    misconception_code TEXT NOT NULL,
    created_by UUID NOT NULL,
    generation_context JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(class_id) REFERENCES classes (id),
    FOREIGN KEY(created_by) REFERENCES teachers (id)
);

CREATE INDEX ix_lessons_class_id ON lessons (class_id);

CREATE TABLE auth_accounts (
    id UUID NOT NULL,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    teacher_id UUID,
    student_id UUID,
    PRIMARY KEY (id),
    CONSTRAINT ck_account_one_role CHECK ((teacher_id IS NULL) != (student_id IS NULL)),
    FOREIGN KEY(student_id) REFERENCES students (id),
    FOREIGN KEY(teacher_id) REFERENCES teachers (id),
    UNIQUE (username)
);

CREATE TABLE learner_states (
    id UUID NOT NULL,
    student_id UUID NOT NULL,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    projection JSON NOT NULL,
    version INTEGER NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(student_id) REFERENCES students (id),
    CONSTRAINT uq_learner_topic UNIQUE (student_id, subject, topic)
);

CREATE INDEX ix_learner_states_student_id ON learner_states (student_id);

CREATE TABLE learning_events (
    id UUID NOT NULL,
    student_id UUID NOT NULL,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    kind TEXT NOT NULL,
    source_key TEXT NOT NULL,
    data JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(student_id) REFERENCES students (id),
    UNIQUE (source_key)
);

CREATE INDEX ix_learning_events_student_id ON learning_events (student_id);

CREATE TABLE learning_sessions (
    id UUID NOT NULL,
    student_id UUID NOT NULL,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    state TEXT NOT NULL,
    version INTEGER NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(student_id) REFERENCES students (id),
    CONSTRAINT uq_session_topic UNIQUE (student_id, subject, topic)
);

CREATE INDEX ix_learning_sessions_student_id ON learning_sessions (student_id);

CREATE TABLE lesson_revisions (
    id UUID NOT NULL,
    lesson_id UUID NOT NULL,
    revision_no INTEGER NOT NULL,
    language TEXT NOT NULL,
    content JSON NOT NULL,
    status TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT,
    generation_note TEXT NOT NULL,
    version INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_lesson_language CHECK (language IN ('en','hi','te')),
    CONSTRAINT ck_lesson_revision_status CHECK (status IN ('draft','approved','published','rejected','archived')),
    FOREIGN KEY(lesson_id) REFERENCES lessons (id),
    CONSTRAINT uq_lesson_revision UNIQUE (lesson_id, revision_no)
);

CREATE INDEX ix_lesson_revisions_lesson_id ON lesson_revisions (lesson_id);

CREATE TABLE auth_sessions (
    token_hash TEXT NOT NULL,
    account_id UUID NOT NULL,
    csrf_token TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (token_hash),
    FOREIGN KEY(account_id) REFERENCES auth_accounts (id)
);

CREATE INDEX ix_auth_sessions_account_id ON auth_sessions (account_id);

CREATE TABLE learning_decisions (
    id UUID NOT NULL,
    event_id UUID NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    requires_teacher_approval BOOLEAN NOT NULL,
    policy_version TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(event_id) REFERENCES learning_events (id),
    UNIQUE (event_id)
);

CREATE TABLE lesson_reviews (
    id UUID NOT NULL,
    revision_id UUID NOT NULL,
    teacher_id UUID NOT NULL,
    action TEXT NOT NULL,
    notes JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(revision_id) REFERENCES lesson_revisions (id),
    FOREIGN KEY(teacher_id) REFERENCES teachers (id),
    CONSTRAINT uq_lesson_review_action UNIQUE (revision_id, action)
);

CREATE INDEX ix_lesson_reviews_revision_id ON lesson_reviews (revision_id);

CREATE TABLE diagnosis_corrections (
    id UUID NOT NULL,
    diagnosis_id UUID NOT NULL,
    teacher_id UUID NOT NULL,
    code TEXT NOT NULL,
    reason TEXT NOT NULL,
    version INTEGER NOT NULL,
    request_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(diagnosis_id) REFERENCES diagnoses (id),
    FOREIGN KEY(teacher_id) REFERENCES teachers (id),
    CONSTRAINT uq_diagnosis_correction_version UNIQUE (diagnosis_id, version),
    UNIQUE (request_id)
);

CREATE INDEX ix_diagnosis_corrections_diagnosis_id ON diagnosis_corrections (diagnosis_id);

CREATE TABLE assigned_lessons (
    id UUID NOT NULL,
    assignment_id UUID NOT NULL,
    revision_id UUID NOT NULL,
    teacher_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_assigned_lesson_revision UNIQUE (assignment_id, revision_id),
    FOREIGN KEY(assignment_id) REFERENCES intervention_assignments (id),
    FOREIGN KEY(revision_id) REFERENCES lesson_revisions (id),
    FOREIGN KEY(teacher_id) REFERENCES teachers (id)
);

CREATE INDEX ix_assigned_lessons_assignment_id ON assigned_lessons (assignment_id);

UPDATE alembic_version SET version_num='0007_learning_intelligence' WHERE alembic_version.version_num = '0006_quiz_learning_loop';

-- Running upgrade 0007_learning_intelligence -> 0008_classroom_studio

CREATE TABLE studio_bank_items (
    id UUID NOT NULL,
    teacher_id UUID NOT NULL,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    question JSON NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(teacher_id) REFERENCES teachers (id) ON DELETE CASCADE
);

CREATE INDEX ix_studio_bank_items_teacher_id ON studio_bank_items (teacher_id);

CREATE TABLE studio_activities (
    id UUID NOT NULL,
    class_id UUID NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    questions JSON NOT NULL,
    max_attempts INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(class_id) REFERENCES classes (id) ON DELETE CASCADE
);

CREATE INDEX ix_studio_activities_class_id ON studio_activities (class_id);

CREATE TABLE studio_sets (
    id UUID NOT NULL,
    class_id UUID NOT NULL,
    title TEXT NOT NULL,
    activity_ids JSON NOT NULL,
    minimum_percent INTEGER NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(class_id) REFERENCES classes (id) ON DELETE CASCADE
);

CREATE INDEX ix_studio_sets_class_id ON studio_sets (class_id);

CREATE TABLE studio_qr_sessions (
    id UUID NOT NULL,
    class_id UUID NOT NULL,
    activity_id UUID NOT NULL,
    question_id TEXT NOT NULL,
    responses JSON NOT NULL,
    status TEXT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(activity_id) REFERENCES studio_activities (id) ON DELETE CASCADE,
    FOREIGN KEY(class_id) REFERENCES classes (id) ON DELETE CASCADE
);

CREATE INDEX ix_studio_qr_sessions_class_id ON studio_qr_sessions (class_id);

CREATE TABLE studio_work (
    id UUID NOT NULL,
    class_id UUID NOT NULL,
    activity_id UUID NOT NULL,
    student_id UUID NOT NULL,
    request_id TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    answers JSON NOT NULL,
    reasoning JSON NOT NULL,
    media JSON NOT NULL,
    results JSON NOT NULL,
    conversations JSON NOT NULL,
    lms_receipt JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(activity_id) REFERENCES studio_activities (id) ON DELETE CASCADE,
    FOREIGN KEY(class_id) REFERENCES classes (id) ON DELETE CASCADE,
    FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE,
    CONSTRAINT uq_studio_work_request UNIQUE (student_id, request_id),
    CONSTRAINT uq_studio_work_attempt UNIQUE (student_id, activity_id, attempt)
);

CREATE INDEX ix_studio_work_activity_id ON studio_work (activity_id);

CREATE INDEX ix_studio_work_class_id ON studio_work (class_id);

CREATE INDEX ix_studio_work_student_id ON studio_work (student_id);

UPDATE alembic_version SET version_num='0008_classroom_studio' WHERE alembic_version.version_num = '0007_learning_intelligence';

COMMIT;
