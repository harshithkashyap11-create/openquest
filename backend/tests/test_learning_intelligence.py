"""Educational evidence must survive retries without manufacturing mastery."""

import pytest
from sqlalchemy import select

from app.models import Class, Student, Teacher
from app.models.learning import LearningEvent, LearnerState
from app.services.learning_service import record_evidence, learner_view, transition


@pytest.fixture
def learner(db_session):
    teacher = Teacher(name="Synthetic teacher", email="learning@test.invalid")
    classroom = Class(class_name="Synthetic fractions", teacher=teacher)
    student = Student(student_code="LEARN001", classroom=classroom)
    db_session.add(student)
    db_session.commit()
    return student


def test_retry_is_one_evidence_event_and_identical_projection(db_session, learner):
    first = record_evidence(db_session, learner, "Mathematics", "Fractions",
        "diagnosis", "diagnosis:one", {"code": "M01", "correct": False,
        "question_id": "q1", "attempt": "a1", "provider": "mock"})
    before = learner_view(db_session, learner.id)[0]
    second = record_evidence(db_session, learner, "Mathematics", "Fractions",
        "diagnosis", "diagnosis:one", {"code": "M01", "correct": False,
        "question_id": "q1", "attempt": "a1", "provider": "mock"})
    assert first.id == second.id
    assert learner_view(db_session, learner.id)[0] == before
    assert db_session.query(LearningEvent).filter_by(kind="diagnosis").count() == 1
    assert before["active_misconceptions"] == ["M01"]
    assert before["decision"]["requires_teacher_approval"] is True
    assert before["decision"]["source"] == "deterministic_policy"


def test_same_retry_key_with_different_content_conflicts(db_session, learner):
    record_evidence(db_session, learner, "Science", "Force and motion",
        "diagnosis", "diagnosis:one", {"code": "FM01", "correct": False})
    with pytest.raises(ValueError, match="IDEMPOTENCY_CONFLICT"):
        record_evidence(db_session, learner, "Science", "Force and motion",
            "diagnosis", "diagnosis:one", {"code": "CORRECT", "correct": True})


def test_one_correct_answer_or_hints_do_not_imply_secure_mastery(db_session, learner):
    record_evidence(db_session, learner, "Mathematics", "Fractions",
        "diagnosis", "d:1", {"code": "CORRECT", "correct": True,
        "question_id": "q1", "attempt": "a1", "provider": "mock"})
    for i in range(4):
        record_evidence(db_session, learner, "Mathematics", "Fractions",
            "hint", f"h:{i}", {"level": i + 1})
    state = learner_view(db_session, learner.id)[0]
    assert state["mastery_category"] != "secure"
    assert state["independent_evidence_count"] == 1
    assert state["hint_count"] == 4
    assert state["difficulty"] == "standard"
    assert "heuristic" in state["score_note"]


def test_rebuild_and_subject_isolation(db_session, learner):
    for i in range(3):
        record_evidence(db_session, learner, "English", "Grammar",
            "reassessment", f"r:{i}", {"correct": True, "question_id": f"q{i}",
            "attempt": f"a{i // 2}"})
    record_evidence(db_session, learner, "Science", "Force and motion",
        "diagnosis", "d:science", {"code": "FOLLOW_UP", "correct": None})
    states = learner_view(db_session, learner.id)
    english = next(s for s in states if s["subject"] == "English")
    assert english["mastery_category"] == "secure"
    assert english["difficulty"] == "challenging"
    assert len(states) == 2
    assert len(list(db_session.scalars(select(LearnerState)))) == 2


def test_invalid_or_unapproved_session_transition_is_rejected(db_session, learner):
    record_evidence(db_session, learner, "Mathematics", "Fractions",
        "assessment", "a:1", {"attempt": "1"})
    state = learner_view(db_session, learner.id)[0]
    with pytest.raises(ValueError, match="INVALID_TRANSITION"):
        transition(db_session, state["session_id"], "COMPLETED", "student", "bad")
    with pytest.raises(PermissionError, match="TEACHER_APPROVAL_REQUIRED"):
        transition(db_session, state["session_id"], "INTERVENTION_APPROVED", "policy", "bad2")
