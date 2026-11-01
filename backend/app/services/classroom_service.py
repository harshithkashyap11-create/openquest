from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Class,
    Question,
    Student,
    Submission,
)
from app.schemas.classroom import (
    AssessmentSubmissionRequest,
    AssessmentSubmissionResponse,
    AssessmentSummaryResponse,
    ClassAssessmentResponse,
    DemoClassResponse,
    DemoStudentResponse,
    DemoStudentResolutionResponse,
    StudentAssessmentStatus,
)


def list_demo_classes(db: Session) -> list[DemoClassResponse]:
    rows = db.execute(
        select(Class, func.count(Student.id))
        .outerjoin(Class.students)
        .group_by(Class.id)
        .order_by(Class.class_name)
    )
    return [
        DemoClassResponse(
            id=classroom.id,
            class_name=classroom.class_name,
            subject=classroom.subject,
            topic=classroom.topic,
            student_count=count,
        )
        for classroom, count in rows
    ]


def list_demo_students(db: Session, class_id: UUID) -> list[DemoStudentResponse]:
    if db.get(Class, class_id) is None:
        raise LookupError("Class not found")
    students = db.scalars(
        select(Student)
        .where(Student.class_id == class_id)
        .order_by(Student.student_code)
    )
    return [
        DemoStudentResponse(student_id=student.id, student_code=student.student_code)
        for student in students
    ]


def resolve_demo_student(
    db: Session, class_id: UUID, student_code: str
) -> DemoStudentResolutionResponse:
    student = db.scalar(
        select(Student).where(
            Student.class_id == class_id,
            Student.student_code == student_code.strip(),
        )
    )
    if student is None:
        raise LookupError("Student code was not found in this class")
    return DemoStudentResolutionResponse(
        student_id=student.id,
        class_id=student.class_id,
        student_code=student.student_code,
    )


def get_class_assessment(
    db: Session, class_id: UUID, *, student_id: UUID | None = None
) -> ClassAssessmentResponse:
    classroom = db.get(Class, class_id)
    if classroom is None:
        raise LookupError("Class not found")
    questions = db.scalars(
        select(Question)
        .where(
            Question.subject == classroom.subject,
            Question.topic == classroom.topic,
        )
        .order_by(Question.created_at, Question.id)
    )
    attempt_count = 0
    latest_attempt_no = None
    latest_attempt_answered = 0
    if student_id is not None:
        attempts = list(
            db.scalars(
                select(Submission.attempt_no)
                .where(Submission.student_id == student_id)
                .distinct()
            )
        )
        attempt_count = len(attempts)
        if attempt_count > 0:
            latest_attempt_no = max(attempts)
            latest_attempt_answered = (
                db.scalar(
                    select(func.count(Submission.id)).where(
                        Submission.student_id == student_id,
                        Submission.attempt_no == latest_attempt_no,
                    )
                )
                or 0
            )

    return ClassAssessmentResponse(
        class_id=class_id,
        title=f"{classroom.topic} Diagnostic",
        subject=classroom.subject,
        topic=classroom.topic,
        questions=[
            {
                "id": question.id,
                "question_text": question.question_text,
                "subject": question.subject,
                "topic": question.topic,
            }
            for question in questions
        ],
        attempt_count=attempt_count,
        latest_attempt_no=latest_attempt_no,
        latest_attempt_answered=latest_attempt_answered,
    )


def submit_student_assessment(
    db: Session,
    student_id: UUID,
    payload: AssessmentSubmissionRequest,
) -> AssessmentSubmissionResponse:
    student = db.get(Student, student_id)
    if student is None:
        raise LookupError("Student not found")
    expected_questions = list(
        db.scalars(
            select(Question.id)
            .where(
                Question.subject == student.classroom.subject,
                Question.topic == student.classroom.topic,
            )
            .order_by(Question.created_at, Question.id)
        )
    )
    submitted_ids = [answer.question_id for answer in payload.answers]
    if len(submitted_ids) != len(set(submitted_ids)):
        raise ValueError("A question may only appear once in an assessment submission")
    if set(submitted_ids) != set(expected_questions):
        raise ValueError("Submit one answer for every question in this assessment")

    max_attempt = db.scalar(
        select(func.max(Submission.attempt_no)).where(
            Submission.student_id == student_id
        )
    ) or 0
    attempt_no = max_attempt + 1
    now = datetime.now(timezone.utc)
    submissions = [
        Submission(
            student_id=student_id,
            question_id=answer.question_id,
            attempt_no=attempt_no,
            answer=answer.answer,
            explanation=answer.explanation,
            submitted_at=now,
        )
        for answer in payload.answers
    ]
    db.add_all(submissions)
    db.commit()
    return AssessmentSubmissionResponse(
        student_id=student_id,
        attempt_no=attempt_no,
        submitted_count=len(submissions),
    )


def get_assessment_summary(db: Session, class_id: UUID) -> AssessmentSummaryResponse:
    classroom = db.get(Class, class_id)
    if classroom is None:
        raise LookupError("Class not found")
    students = list(
        db.scalars(
            select(Student)
            .where(Student.class_id == class_id)
            .order_by(Student.student_code)
        )
    )
    total_questions = db.scalar(
        select(func.count(Question.id)).where(
            Question.subject == classroom.subject,
            Question.topic == classroom.topic,
        )
    ) or 0
    student_statuses: list[StudentAssessmentStatus] = []
    for student in students:
        latest_attempt = db.scalar(
            select(func.max(Submission.attempt_no)).where(
                Submission.student_id == student.id
            )
        )
        if latest_attempt is None:
            student_statuses.append(
                StudentAssessmentStatus(
                    student_id=student.id,
                    student_code=student.student_code,
                    attempt_no=None,
                    answered_questions=0,
                    diagnosed_answers=0,
                    pending_diagnoses=0,
                )
            )
            continue
        submitted = list(
            db.scalars(
                select(Submission)
                .where(
                    Submission.student_id == student.id,
                    Submission.attempt_no == latest_attempt,
                )
                .options(joinedload(Submission.diagnoses))
            ).unique()
        )
        diagnosed_count = sum(bool(item.diagnoses) for item in submitted)
        student_statuses.append(
            StudentAssessmentStatus(
                student_id=student.id,
                student_code=student.student_code,
                attempt_no=latest_attempt,
                answered_questions=len(submitted),
                diagnosed_answers=diagnosed_count,
                pending_diagnoses=len(submitted) - diagnosed_count,
            )
        )
    return AssessmentSummaryResponse(
        class_id=class_id,
        total_students=len(students),
        submitted_students=sum(
            status.answered_questions > 0 for status in student_statuses
        ),
        total_questions_per_student=total_questions,
        answered_questions=sum(
            status.answered_questions for status in student_statuses
        ),
        diagnosed_answers=sum(
            status.diagnosed_answers for status in student_statuses
        ),
        pending_diagnoses=sum(
            status.pending_diagnoses for status in student_statuses
        ),
        students=student_statuses,
    )
