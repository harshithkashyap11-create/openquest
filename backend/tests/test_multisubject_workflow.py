from pathlib import Path

from app.models import (
    Class,
    Diagnosis,
    GroupMember,
    InterventionAssignment,
    LearningGroup,
    Question,
    Student,
    Submission,
    Teacher,
)
from app.services.classroom_service import get_class_assessment
from app.services.diagnosis_service import DiagnosisService
from app.services.diagnosis_prompt import build_diagnosis_prompt
from app.services.dataset_import import import_synthetic_dataset
from app.services.intervention_service import generate_intervention_for_group
from app.services.reassessment_service import generate_reassessment
from app.schemas.diagnosis import DiagnosisResult
from app.services.intervention_service import INTERVENTION_TEMPLATES
from app.services.reassessment_service import REASSESSMENT_QUESTIONS
from app.subject_taxonomy import SUBJECT_TAXONOMY

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_diagnosis_prompt_uses_selected_subject_topic_and_taxonomy():
    prompt = build_diagnosis_prompt(
        subject="Science",
        topic="Force and motion",
        question="A puck keeps sliding after the push stops. Why?",
        correct_answer="It continues because of inertia.",
        expected_approach="Use inertia to explain motion.",
        answer="It keeps moving because it was pushed.",
        explanation="Objects need a continuing force to keep moving.",
    )

    assert 'Subject: "Science"' in prompt
    assert 'Topic: "Force and motion"' in prompt
    assert "FM01" in prompt
    assert "- M01 " not in prompt


def test_assessment_questions_are_scoped_to_class_subject_and_topic(db_session):
    teacher = Teacher(name="Teacher", email="science@classpulse.test")
    classroom = Class(
        class_name="Motion demo",
        subject="Science",
        topic="Force and motion",
        teacher=teacher,
    )
    classroom.students.append(Student(student_code="SCI001"))
    classroom_questions = [
        Question(
            subject="Science",
            topic="Force and motion",
            question_text=f"Motion question {index}",
            correct_answer="answer",
        )
        for index in range(2)
    ]
    other_question = Question(
        subject="Science",
        topic="Basic electricity",
        question_text="Electricity question",
        correct_answer="answer",
    )
    db_session.add_all([classroom, *classroom_questions, other_question])
    db_session.flush()

    assessment = get_class_assessment(db_session, classroom.id)

    assert assessment.subject == "Science"
    assert assessment.topic == "Force and motion"
    assert {item.question_text for item in assessment.questions} == {
        question.question_text for question in classroom_questions
    }


def test_multi_subject_synthetic_dataset_creates_subject_topic_classes(db_session):
    dataset_path = REPOSITORY_ROOT / "data" / "multi_subject_synthetic_responses.csv"

    summary = import_synthetic_dataset(db_session, dataset_path)

    assert summary.classes_created == 5
    assert summary.students_created == 30
    assert summary.questions_created == 15
    assert summary.submissions_created == 90
    classes = db_session.query(Class).all()
    assert {
        (classroom.subject, classroom.topic)
        for classroom in classes
    } == set(SUBJECT_TAXONOMY) - {("Mathematics", "Fractions")}


def test_non_fraction_taxonomy_codes_have_targeted_activities_and_fresh_checks():
    non_fraction_codes = {
        item.code
        for (subject, topic), taxonomy in SUBJECT_TAXONOMY.items()
        if (subject, topic) != ("Mathematics", "Fractions")
        for item in taxonomy
    }

    assert non_fraction_codes <= INTERVENTION_TEMPLATES.keys()
    assert non_fraction_codes <= REASSESSMENT_QUESTIONS.keys()
    assert "M06" not in INTERVENTION_TEMPLATES
    assert all(
        len(INTERVENTION_TEMPLATES[code].practice_questions) == 3
        and len(INTERVENTION_TEMPLATES[code].expected_answers) == 3
        and len(REASSESSMENT_QUESTIONS[code]) == 3
        for code in non_fraction_codes
    )


def test_science_diagnosis_uses_domain_code_and_rejects_fraction_code(db_session):
    teacher = Teacher(name="Teacher", email="motion@classpulse.test")
    classroom = Class(
        class_name="Motion demo",
        subject="Science",
        topic="Force and motion",
        teacher=teacher,
    )
    student = Student(student_code="SCI001", classroom=classroom)
    question = Question(
        subject="Science",
        topic="Force and motion",
        question_text="A cart continues moving. Why?",
        correct_answer="Inertia",
    )
    submission = Submission(
        student=student,
        question=question,
        answer="It keeps moving",
        explanation="It keeps moving because it was pushed.",
    )
    db_session.add(submission)
    db_session.flush()

    class DomainProvider:
        name = "mock"
        model_version = "domain-test"

        def diagnose(self, **kwargs):
            assert kwargs["subject"] == "Science"
            assert kwargs["topic"] == "Force and motion"
            return DiagnosisResult(
                misconception_code="FM01",
                confidence=0.9,
                evidence="It keeps moving because it was pushed.",
                misconception_description="Motion requires continuing force",
                misunderstanding_explanation="The explanation suggests a force is needed to maintain motion.",
                suggested_intervention="Compare motion with and without friction.",
            )

    outcome = DiagnosisService(db_session, provider=DomainProvider()).diagnose_class(
        classroom.id
    )

    assert outcome.diagnosed == 1
    diagnosis = db_session.query(Diagnosis).one()
    assert diagnosis.misconception_code == "FM01"
    assert diagnosis.misunderstanding_explanation


def test_non_fraction_group_receives_topic_specific_intervention_and_reassessment(
    db_session,
):
    teacher = Teacher(name="Teacher", email="algebra@classpulse.test")
    classroom = Class(
        class_name="Algebra demo",
        subject="Mathematics",
        topic="Basic algebra",
        teacher=teacher,
    )
    student = Student(student_code="ALG001", classroom=classroom)
    group = LearningGroup(
        classroom=classroom,
        topic="Basic algebra",
        misconception_code="ALG02",
        name="Distribution support",
        teacher_approved=True,
        review_status="approved",
    )
    db_session.add_all([teacher, classroom, student, group])
    db_session.flush()
    db_session.add(GroupMember(group_id=group.id, student_id=student.id))
    db_session.commit()

    intervention, assignments, created = generate_intervention_for_group(
        db_session, group.id
    )

    assert created == 1
    assert intervention.subject == "Mathematics"
    assert intervention.topic == "Basic algebra"
    assert len(intervention.practice_questions) == 3
    assignment = assignments[0]
    assignment.status = "completed"
    db_session.commit()

    reassessment = generate_reassessment(db_session, assignment.id)

    assert reassessment.total_questions == 3
    assert all(
        question.question.subject == "Mathematics"
        and question.question.topic == "Basic algebra"
        for question in reassessment.questions
    )
    assert not any(
        question.question.question_text.startswith(("Solve 2x + 3", "Expand 3(x"))
        for question in reassessment.questions
    )
