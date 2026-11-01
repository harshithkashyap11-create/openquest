from decimal import Decimal

from app.models import (
    Class,
    Diagnosis,
    GroupMember,
    LearningGroup,
    Question,
    Student,
    Submission,
    Teacher,
)
from app.services.grouping_service import generate_proposed_groups


def _add_diagnosis(db_session, classroom, code, confidence, student_code):
    student = Student(student_code=student_code, classroom=classroom)
    question = Question(
        topic="Fractions",
        question_text=f"Question for {student_code}",
        correct_answer="5/6",
    )
    submission = Submission(student=student, question=question, answer="2/5")
    db_session.add(submission)
    db_session.flush()
    db_session.add(
        Diagnosis(
            submission_id=submission.id,
            misconception_code=code,
            confidence=Decimal(str(confidence)),
            evidence="The response supports this label.",
        )
    )
    db_session.flush()
    return student


def test_grouping_only_proposes_supported_misconceptions_for_two_students(db_session):
    teacher = Teacher(name="Teacher", email="groups@example.test")
    classroom = Class(class_name="Fractions", teacher=teacher)
    db_session.add(classroom)
    db_session.flush()
    first = _add_diagnosis(db_session, classroom, "M01", 0.91, "S001")
    second = _add_diagnosis(db_session, classroom, "M01", 0.80, "S002")
    _add_diagnosis(db_session, classroom, "M02", 0.95, "S003")
    _add_diagnosis(db_session, classroom, "M03", 0.74, "S004")
    _add_diagnosis(db_session, classroom, "M06", 0.99, "S005")
    _add_diagnosis(db_session, classroom, "CORRECT", 0.99, "S006")

    groups = generate_proposed_groups(db_session, classroom.id)

    assert len(groups) == 1
    assert groups[0].misconception_code == "M01"
    assert groups[0].teacher_approved is False
    assert groups[0].review_status == "proposed"
    assert {
        member.student_id for member in groups[0].group_members
    } == {first.id, second.id}


def test_grouping_is_idempotent_and_does_not_duplicate_membership(db_session):
    teacher = Teacher(name="Teacher", email="idempotent-groups@example.test")
    classroom = Class(class_name="Fractions", teacher=teacher)
    db_session.add(classroom)
    db_session.flush()
    _add_diagnosis(db_session, classroom, "M01", 0.90, "S001")
    _add_diagnosis(db_session, classroom, "M01", 0.82, "S002")

    first = generate_proposed_groups(db_session, classroom.id)
    first_group_id = first[0].id
    second = generate_proposed_groups(db_session, classroom.id)

    assert len(second) == 1
    assert second[0].id == first_group_id
    assert db_session.query(LearningGroup).count() == 1
    assert db_session.query(GroupMember).count() == 2


def test_regeneration_preserves_approved_group_and_members(db_session):
    teacher = Teacher(name="Teacher", email="approved-groups@example.test")
    classroom = Class(class_name="Fractions", teacher=teacher)
    db_session.add(classroom)
    db_session.flush()
    first = _add_diagnosis(db_session, classroom, "M01", 0.90, "S001")
    second = _add_diagnosis(db_session, classroom, "M01", 0.82, "S002")
    group = generate_proposed_groups(db_session, classroom.id)[0]
    original_members = {first.id, second.id}
    group.teacher_approved = True
    group.review_status = "approved"
    db_session.commit()

    regenerated = generate_proposed_groups(db_session, classroom.id)

    assert regenerated == []
    assert group.teacher_approved is True
    assert group.review_status == "approved"
    assert {
        member.student_id for member in group.group_members
    } == original_members


def test_regeneration_moves_student_to_only_the_current_primary_group(db_session):
    teacher = Teacher(name="Teacher", email="reclassified@example.test")
    classroom = Class(class_name="Fractions", teacher=teacher)
    db_session.add(classroom)
    db_session.flush()
    reclassified = _add_diagnosis(db_session, classroom, "M01", 0.90, "S001")
    remaining_m01 = _add_diagnosis(db_session, classroom, "M01", 0.85, "S002")
    old_group = generate_proposed_groups(db_session, classroom.id)[0]

    question = Question(
        topic="Fractions",
        question_text="A new comparison question for S001",
        correct_answer="1/4",
    )
    newer_submission = Submission(
        student_id=reclassified.id,
        question=question,
        answer="1/4",
        explanation="Eight is bigger than four.",
    )
    db_session.add(newer_submission)
    db_session.flush()
    db_session.add(
        Diagnosis(
            submission_id=newer_submission.id,
            misconception_code="M02",
            confidence=Decimal("0.96"),
            evidence="Eight is bigger than four.",
        )
    )
    new_m02_member = _add_diagnosis(db_session, classroom, "M02", 0.90, "S003")
    db_session.flush()

    groups = generate_proposed_groups(db_session, classroom.id)

    assert [group.misconception_code for group in groups] == ["M02"]
    assert db_session.get(LearningGroup, old_group.id) is None
    assert {
        member.student_id for member in groups[0].group_members
    } == {reclassified.id, new_m02_member.id}
    assert remaining_m01.id not in {
        member.student_id for member in groups[0].group_members
    }


def test_regeneration_proposes_new_group_for_approved_misconception_when_new_students_arrive(
    db_session,
):
    teacher = Teacher(name="Teacher", email="approved-lockout@example.test")
    classroom = Class(class_name="Fractions", teacher=teacher)
    db_session.add(classroom)
    db_session.flush()

    _add_diagnosis(db_session, classroom, "M01", 0.90, "S001")
    _add_diagnosis(db_session, classroom, "M01", 0.85, "S002")
    first_group = generate_proposed_groups(db_session, classroom.id)[0]
    first_group.teacher_approved = True
    first_group.review_status = "approved"
    db_session.commit()

    # Two new students arrive with the same misconception (M01)
    s3 = _add_diagnosis(db_session, classroom, "M01", 0.92, "S003")
    s4 = _add_diagnosis(db_session, classroom, "M01", 0.88, "S004")

    new_groups = generate_proposed_groups(db_session, classroom.id)
    assert len(new_groups) == 1
    assert new_groups[0].id != first_group.id
    assert new_groups[0].misconception_code == "M01"
    assert new_groups[0].review_status == "proposed"
    assert {m.student_id for m in new_groups[0].group_members} == {s3.id, s4.id}
