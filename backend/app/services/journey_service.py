"""Chronology of student sources; assignment/reassessment links are explicit FKs.

There is no response-to-assignment FK. Responses are shown as a separate history,
never claimed as the cause of support or of a later score.
"""
from sqlalchemy import String, cast, func, literal, select, union_all
from app.models import Intervention, InterventionAssignment, PracticeResponse, Question, Reassessment, Submission
from app.services.misconception_map_service import utc


def student_journey(db, student, *, limit=30, offset=0):
    classroom = student.classroom
    sources = union_all(
        select(literal('response').label('kind'), cast(Submission.id, String).label('id'), Submission.submitted_at.label('at'))
            .join(Question).where(Submission.student_id == student.id, Question.subject == classroom.subject, Question.topic == classroom.topic),
        select(literal('support'), cast(InterventionAssignment.id, String), InterventionAssignment.assigned_at)
            .join(Intervention).where(InterventionAssignment.student_id == student.id, Intervention.subject == classroom.subject, Intervention.topic == classroom.topic),
        select(literal('practice'), cast(PracticeResponse.id, String), PracticeResponse.submitted_at)
            .join(InterventionAssignment).where(InterventionAssignment.student_id == student.id),
        select(literal('reassessment'), cast(Reassessment.id, String), Reassessment.submitted_at)
            .join(InterventionAssignment).where(InterventionAssignment.student_id == student.id, Reassessment.status == 'completed'),
    ).subquery()
    from uuid import UUID
    events = []
    for kind, identifier, at in db.execute(select(sources).order_by(sources.c.at, sources.c.kind, sources.c.id).limit(limit).offset(offset)):
        source_id = UUID(identifier)
        event = dict(kind=kind, source_id=source_id, at=utc(at))
        if kind == 'response':
            source = db.get(Submission, source_id)
            event.update(question_id=source.question_id, question_text=source.question.question_text, answer=source.answer)
        elif kind == 'support':
            source = db.get(InterventionAssignment, source_id)
            event.update(assignment_id=source.id, title=source.intervention.title, status=source.status)
        elif kind == 'practice':
            source = db.get(PracticeResponse, source_id)
            event.update(assignment_id=source.assignment_id, answer=source.answer, correct=int(source.is_correct), total=1)
        else:
            source = db.get(Reassessment, source_id)
            event.update(assignment_id=source.assignment_id, correct=source.correct_answers, total=source.total_questions, status=source.status)
        events.append(event)
    return dict(student_id=student.id, subject=classroom.subject, topic=classroom.topic,
        total=db.scalar(select(func.count()).select_from(sources)) or 0, limit=limit, offset=offset, events=events)
