from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app
from app.models import (
    Class,
    Diagnosis,
    InterventionAssignment,
    Intervention,
    LearningGroup,
    Question,
    Student,
    Submission,
    Teacher,
)
from app.question_catalog import QUESTION_CATALOG


def _seed_demo_class(db_session, *, with_baseline: bool = True):
    teacher = Teacher(
        name="Demo Teacher", email=f"demo-{uuid4()}@example.test"
    )
    classroom = Class(class_name=f"Fractions {uuid4()}", teacher=teacher)
    student = Student(classroom=classroom, student_code="STU-001")
    other_student = Student(classroom=classroom, student_code="STU-002")
    questions = [
        Question(
            topic=question.topic,
            question_text=question.question_text,
            correct_answer=question.correct_answer,
            explanation_expected=question.explanation_expected,
        )
        for question in list(QUESTION_CATALOG.values())[:5]
    ]
    db_session.add_all(
        [teacher, classroom, student, other_student, *questions]
    )
    db_session.flush()
    if with_baseline:
        db_session.add(
            Submission(
                student_id=student.id,
                question_id=questions[0].id,
                answer="2/5",
                explanation="Synthetic baseline answer",
            )
        )
    db_session.commit()
    return classroom, student, other_student, questions


def _client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_demo_class_discovery_and_student_code_resolution(db_session):
    classroom, student, _, _ = _seed_demo_class(db_session, with_baseline=False)
    client = _client(db_session)
    try:
        classes = client.get("/api/demo/classes")
        assert classes.status_code == 200
        assert any(item["id"] == str(classroom.id) for item in classes.json())

        roster = client.get(f"/api/demo/classes/{classroom.id}/students")
        assert roster.status_code == 200
        assert [item["student_code"] for item in roster.json()] == [
            "STU-001",
            "STU-002",
        ]
        assert all("answer" not in item for item in roster.json())
        assert client.get(f"/api/demo/classes/{uuid4()}/students").status_code == 404

        resolved = client.post(
            "/api/demo/students/resolve",
            json={"class_id": str(classroom.id), "student_code": "STU-001"},
        )
        assert resolved.status_code == 200
        assert resolved.json()["student_id"] == str(student.id)
        assert resolved.json()["class_id"] == str(classroom.id)

        missing = client.post(
            "/api/demo/students/resolve",
            json={"class_id": str(classroom.id), "student_code": "UNKNOWN"},
        )
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_student_assessment_submission_creates_new_attempt_without_replacing_baseline(
    db_session,
):
    classroom, student, _, questions = _seed_demo_class(db_session)
    client = _client(db_session)
    try:
        assessment = client.get(
            f"/api/classes/{classroom.id}/assessment",
            headers={"X-Student-ID": str(student.id)},
        )
        assert assessment.status_code == 200
        assert len(assessment.json()["questions"]) == 5
        assert "correct_answer" not in assessment.json()["questions"][0]

        submission = client.post(
            f"/api/students/{student.id}/assessment-submissions",
            headers={"X-Student-ID": str(student.id)},
            json={
                "answers": [
                    {
                        "question_id": str(question.id),
                        "answer": "student answer",
                        "explanation": "student explanation",
                    }
                    for question in questions
                ]
            },
        )
        assert submission.status_code == 201
        assert submission.json()["attempt_no"] == 2
        assert submission.json()["submitted_count"] == 5

        first_question_rows = (
            db_session.query(Submission)
            .filter(
                Submission.student_id == student.id,
                Submission.question_id == questions[0].id,
            )
            .order_by(Submission.attempt_no)
            .all()
        )
        assert [(row.attempt_no, row.answer) for row in first_question_rows] == [
            (1, "2/5"),
            (2, "student answer"),
        ]
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_student_cannot_read_another_students_assessment_or_progress(db_session):
    classroom, student, _, _ = _seed_demo_class(db_session)
    other_teacher = Teacher(
        name="Other Teacher", email=f"other-{uuid4()}@example.test"
    )
    other_class = Class(class_name=f"Other {uuid4()}", teacher=other_teacher)
    other_student = Student(classroom=other_class, student_code="OUTSIDER")
    db_session.add_all([other_teacher, other_class, other_student])
    db_session.commit()
    client = _client(db_session)
    try:
        mismatch = {"X-Student-ID": str(other_student.id)}
        assert client.get(
            f"/api/classes/{classroom.id}/assessment",
            headers=mismatch,
        ).status_code == 403
        assert client.get(
            f"/api/students/{student.id}/progress",
            headers=mismatch,
        ).status_code == 403
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_assessment_summary_and_individual_diagnosis_filter(db_session):
    classroom, student, other_student, questions = _seed_demo_class(db_session)
    first_submission = db_session.query(Submission).filter_by(
        student_id=student.id
    ).one()
    db_session.add(
        Diagnosis(
            submission_id=first_submission.id,
            misconception_code="M01",
            confidence=0.9,
            evidence="Synthetic baseline answer",
            status="provisional",
        )
    )
    db_session.commit()
    client = _client(db_session)
    try:
        summary = client.get(f"/api/classes/{classroom.id}/assessment-summary")
        assert summary.status_code == 200
        payload = summary.json()
        assert payload["total_students"] == 2
        assert payload["submitted_students"] == 1
        assert payload["answered_questions"] == 1
        assert payload["diagnosed_answers"] == 1
        assert payload["pending_diagnoses"] == 0

        diagnoses = client.get(
            f"/api/classes/{classroom.id}/diagnoses",
            params={"student_id": str(student.id)},
        )
        assert diagnoses.status_code == 200
        assert [item["student_id"] for item in diagnoses.json()] == [
            str(student.id)
        ]
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_class_assignment_report_and_student_progress_include_sample_sizes(db_session):
    classroom, student, _, questions = _seed_demo_class(db_session)
    intervention = Intervention(
        topic="Fractions",
        misconception_code="M01",
        title="Add with common denominators",
        instructions="Use twelfths.",
        learning_objective="Use a common denominator.",
        explanation="Keep part sizes the same.",
        introduction="Let's try.",
        guided_example={"question": "1/4 + 1/6", "answer": "5/12"},
        practice_questions=["1/4 + 1/6"],
        expected_answers=["5/12"],
        hints=["Use twelfths."],
    )
    group = LearningGroup(
        class_id=classroom.id,
        topic="Fractions",
        misconception_code="M01",
        name="M01 support",
        teacher_approved=True,
        review_status="approved",
    )
    db_session.add_all([intervention, group])
    db_session.flush()
    assignment = InterventionAssignment(
        intervention_id=intervention.id,
        student_id=student.id,
        status="assigned",
    )
    db_session.add(assignment)
    db_session.commit()
    client = _client(db_session)
    try:
        assignments = client.get(
            f"/api/classes/{classroom.id}/intervention-assignments"
        )
        assert assignments.status_code == 200
        assert assignments.json()[0]["student_code"] == "STU-001"
        assert assignments.json()[0]["status"] == "assigned"

        progress = client.get(
            f"/api/students/{student.id}/progress",
            headers={"X-Student-ID": str(student.id)},
        )
        assert progress.status_code == 200
        assert progress.json()["assigned_interventions"] == 1
        assert progress.json()["initial_assessment"]["sample_size"] == 1
        assert progress.json()["followup_assessment"]["sample_size"] == 0
    finally:
        app.dependency_overrides.pop(get_db, None)
