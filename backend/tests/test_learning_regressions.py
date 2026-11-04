import pytest
from app.models import Question
from app.services.classroom_service import get_class_assessment
from app.services.intervention_service import generate_intervention_for_group
from app.services.reassessment_service import generate_reassessment, submit_reassessment
from test_intervention_workflow import _approved_group


def test_reassessment_questions_do_not_enter_baseline_bank(db_session):
    classroom, group, students = _approved_group(db_session, 'M01')
    db_session.add(Question(topic='Fractions', question_text='Baseline only', correct_answer='1'))
    _, assignments, _ = generate_intervention_for_group(db_session, group.id)
    assignments[0].status = 'completed'
    db_session.commit()
    generate_reassessment(db_session, assignments[0].id)
    assert [q.question_text for q in get_class_assessment(db_session, classroom.id).questions] == ['Baseline only']


def test_reassessment_retry_returns_saved_result_without_extra_evidence(db_session):
    _, group, students = _approved_group(db_session, 'M01')
    _, assignments, _ = generate_intervention_for_group(db_session, group.id)
    assignments[0].status = 'completed'
    db_session.commit()
    reassessment = generate_reassessment(db_session, assignments[0].id)
    answers = {q.question_id: q.question.correct_answer for q in reassessment.questions}
    first, _ = submit_reassessment(db_session, reassessment.id, answers, student_id=students[0].id)
    repeated, _ = submit_reassessment(db_session, reassessment.id, answers, student_id=students[0].id)
    assert repeated.id == first.id
    with pytest.raises(PermissionError, match='different answers'):
        submit_reassessment(db_session, reassessment.id, {k: 'incorrect' for k in answers}, student_id=students[0].id)
